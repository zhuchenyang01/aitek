import tempfile
import uuid
from typing import Iterator

from app.exceptions import RagError
from app.services.config_factory import build_llm_client
from app.services.document_processor import load_document
from app.services.feature_extractor import extract_features
from app.services.generator_service import TestCaseGenerator
from app.services.image_processor import analyze_images, merge_document_text
from app.services.kb_repository import get_knowledge_base
from app.services.requirement_matcher import match_single_requirement
from app.services.test_direction_splitter import split_test_directions
from app.utils.prompt_loader import render_prompt


PIPELINE_STEPS = {
    'document_load': '文档解析',
    'image_analyze': '图片理解',
    'feature_extract': '功能点提取',
    'kb_match': '需求关联',
    'direction_split': '测试方向拆分',
    'testcase_generate': '用例生成',
}


class PipelineOrchestrator:
    def __init__(
        self,
        llm_config=None,
        vision_config=None,
        embedding_config=None,
        rerank_config=None,
    ):
        self.llm_config = llm_config or {}
        self.vision_config = vision_config or {}
        self.embedding_config = embedding_config or {}
        self.rerank_config = rerank_config or {}
        self.generator = TestCaseGenerator(
            llm_config=self.llm_config,
            embedding_config=self.embedding_config,
            rerank_config=self.rerank_config,
        )

    def run(
        self,
        query,
        requirement_kb_id,
        testcase_kb_id,
        file_path=None,
    ) -> Iterator[dict]:
        req_kb = get_knowledge_base(requirement_kb_id)
        case_kb = get_knowledge_base(testcase_kb_id)
        if req_kb is None or case_kb is None:
            raise RagError('知识库不存在', status_code=404)

        message_id = str(uuid.uuid4())
        document_text = (query or '').strip()
        blocks = []
        image_result = {'insights': [], 'appendix_text': '', 'skipped': True, 'reason': ''}

        if file_path:
            yield self._pipeline_event(message_id, 'document_load', 'running', '正在解析文档...')
            try:
                with tempfile.TemporaryDirectory(prefix='pipeline-images-') as tmp_dir:
                    blocks = load_document(file_path, tmp_dir)
                    text_count = sum(1 for block in blocks if block.get('type') == 'text')
                    image_count = sum(1 for block in blocks if block.get('type') == 'image')
                    yield self._pipeline_event(
                        message_id,
                        'document_load',
                        'done',
                        f'文档解析完成：文本块 {text_count}，图片 {image_count}',
                    )

                    yield self._pipeline_event(message_id, 'image_analyze', 'running', '正在分析图片...')
                    image_result = analyze_images(blocks, self.vision_config)
                    if image_result.get('skipped'):
                        yield self._pipeline_event(
                            message_id,
                            'image_analyze',
                            'done',
                            image_result.get('reason') or '已跳过图片理解',
                        )
                    else:
                        yield self._pipeline_event(
                            message_id,
                            'image_analyze',
                            'done',
                            f'图片理解完成：共 {len(image_result.get("insights") or [])} 张',
                        )
                    document_text = merge_document_text(blocks, image_result)
            except Exception as exc:
                yield self._pipeline_event(message_id, 'document_load', 'error', f'文档解析失败：{exc}')
                yield self._error_event(message_id, f'文档解析失败：{exc}')
                return
        else:
            yield self._pipeline_event(message_id, 'document_load', 'done', '未提供文档路径，使用 query 文本')
            yield self._pipeline_event(message_id, 'image_analyze', 'done', '无文档图片，已跳过')

        if not document_text:
            document_text = query

        yield self._pipeline_event(message_id, 'feature_extract', 'running', '正在提取功能点...')
        features = None
        try:
            for item in extract_features(document_text, self.llm_config):
                if item.get('kind') == 'chunk':
                    yield self._llm_chunk_event(message_id, 'feature_extract', item.get('content') or '')
                elif item.get('kind') == 'result':
                    features = item.get('features') or []
        except Exception as exc:
            yield self._pipeline_event(message_id, 'feature_extract', 'error', str(exc))
            yield self._error_event(message_id, str(exc))
            return
        yield self._feature_points_event(message_id, features)
        yield self._pipeline_event(message_id, 'feature_extract', 'done', f'功能点提取完成：共 {len(features or [])} 条')

        yield self._pipeline_event(message_id, 'kb_match', 'running', '正在关联项目知识库...')
        matched = [
            match_single_requirement(feature, requirement_kb_id, self.generator)
            for feature in (features or [])
        ]
        yield self._matched_requirements_event(message_id, matched)
        total_hits = sum(item.get('hit_count', 0) for item in matched)
        yield self._pipeline_event(message_id, 'kb_match', 'done', f'需求关联完成：共匹配 {total_hits} 条片段')

        yield self._pipeline_event(message_id, 'direction_split', 'running', '正在拆分测试方向...')
        directions = None
        try:
            for item in split_test_directions(features, matched, self.llm_config):
                if item.get('kind') == 'chunk':
                    yield self._llm_chunk_event(message_id, 'direction_split', item.get('content') or '')
                elif item.get('kind') == 'result':
                    directions = item.get('directions') or []
        except Exception as exc:
            yield self._pipeline_event(message_id, 'direction_split', 'error', str(exc))
            yield self._error_event(message_id, str(exc))
            return
        yield self._test_directions_event(message_id, directions)
        yield self._pipeline_event(
            message_id,
            'direction_split',
            'done',
            self._direction_summary(directions),
        )

        yield self._pipeline_event(message_id, 'testcase_generate', 'running', '正在生成测试用例...')
        case_hits = self.generator.retrieve(testcase_kb_id, query)
        references = self._collect_references(matched, case_hits)
        yield {
            'id': message_id,
            'response_type': 'references',
            'content': '',
            'done': False,
            'knowledge_references': references,
        }

        context = self._build_generation_context(features, matched, directions, image_result)
        messages = [
            {
                'role': 'system',
                'content': '你是测试用例生成助手，请覆盖业务/功能/其他三类测试方向。',
            },
            {
                'role': 'user',
                'content': render_prompt(
                    'testcase_generation',
                    query=query,
                    context=context,
                    case_hits=self.generator._format_hits(case_hits),
                ),
            },
        ]
        llm = build_llm_client(self.llm_config)
        try:
            if not llm.api_key:
                answer = self._fallback_answer(query, context, case_hits)
                yield self._event(message_id, 'answer', answer, done=False)
            else:
                for delta in llm.chat_stream(messages, temperature=0.3, max_tokens=8192):
                    yield self._event(message_id, 'answer', delta, done=False)
        except Exception as exc:
            yield self._error_event(message_id, f'生成测试用例失败：{exc}')
            return

        yield self._pipeline_event(message_id, 'testcase_generate', 'done', '用例生成完成')
        yield self._event(message_id, 'answer', '', done=True)

    @staticmethod
    def _llm_chunk_event(message_id, step, content):
        return {
            'id': message_id,
            'response_type': 'llm_chunk',
            'step': step,
            'step_label': PIPELINE_STEPS.get(step, step),
            'content': content,
            'done': False,
        }

    @staticmethod
    def _pipeline_event(message_id, step, status, content):
        return {
            'id': message_id,
            'response_type': 'pipeline',
            'step': step,
            'step_label': PIPELINE_STEPS.get(step, step),
            'status': status,
            'content': content,
            'done': status == 'error',
        }

    @staticmethod
    def _feature_points_event(message_id, features):
        return {
            'id': message_id,
            'response_type': 'feature_points',
            'content': '',
            'count': len(features or []),
            'items': features or [],
            'done': False,
        }

    @staticmethod
    def _matched_requirements_event(message_id, matched):
        items = []
        for item in matched or []:
            items.append(
                {
                    '模块': item.get('模块') or '',
                    '功能点': item.get('功能点') or '',
                    'hit_count': item.get('hit_count', 0),
                }
            )
        return {
            'id': message_id,
            'response_type': 'matched_requirements',
            'content': '',
            'items': items,
            'done': False,
        }

    @staticmethod
    def _test_directions_event(message_id, directions):
        return {
            'id': message_id,
            'response_type': 'test_directions',
            'content': '',
            'items': directions or [],
            'done': False,
        }

    @staticmethod
    def _event(message_id, response_type, content, done=False):
        return {
            'id': message_id,
            'response_type': response_type,
            'content': content,
            'done': done,
        }

    @staticmethod
    def _error_event(message_id, content):
        return {
            'id': message_id,
            'response_type': 'error',
            'content': content,
            'done': True,
        }

    @staticmethod
    def _direction_summary(directions):
        counts = {'业务测试': 0, '功能测试': 0, '其他测试': 0}
        for item in directions or []:
            direction = item.get('方向') or '功能测试'
            counts[direction] = counts.get(direction, 0) + 1
        return f'方向拆分完成：业务 {counts["业务测试"]} / 功能 {counts["功能测试"]} / 其他 {counts["其他测试"]}'

    @staticmethod
    def _collect_references(matched, case_hits):
        references = list(case_hits or [])
        seen = {ref.get('id') for ref in references}
        for item in matched or []:
            for hit in item.get('hits') or []:
                hit_id = hit.get('id')
                if hit_id in seen:
                    continue
                seen.add(hit_id)
                references.append(hit)
        return references

    @staticmethod
    def _build_generation_context(features, matched, directions, image_result):
        matched_map = {}
        for item in matched or []:
            key = (item.get('模块') or '', item.get('功能点') or '')
            matched_map[key] = item.get('hits') or []

        direction_map = {}
        for item in directions or []:
            key = (item.get('模块') or '', item.get('功能点') or '')
            direction_map.setdefault(key, []).append(item)

        lines = []
        for feature in features or []:
            module = feature.get('模块') or ''
            point = feature.get('功能点') or ''
            key = (module, point)
            hits = matched_map.get(key, [])
            hit_text = '\n'.join(f'- {hit.get("content", "")}' for hit in hits[:3]) or '- （无关联需求）'
            dir_text = '\n'.join(
                f'- {d.get("方向")}：{d.get("说明") or ""}' for d in direction_map.get(key, [])
            ) or '- 功能测试'
            lines.append(
                f'## 模块：{module}\n功能点：{point}\n关联需求：\n{hit_text}\n测试方向：\n{dir_text}'
            )

        appendix = (image_result or {}).get('appendix_text') or ''
        if appendix:
            lines.append('## 图片理解附录\n' + appendix)
        return '\n\n'.join(lines)

    @staticmethod
    def _fallback_answer(query, context, case_hits):
        case_text = '\n'.join(f'- {hit.get("content", "")}' for hit in (case_hits or [])) or '- （用例库暂无分块）'
        return (
            '未配置对话模型，以下为基于结构化分析整理的测试要点。\n\n'
            f'用户需求：{query}\n\n'
            f'{context}\n\n'
            f'## 可参考的历史用例\n{case_text}\n'
        )
