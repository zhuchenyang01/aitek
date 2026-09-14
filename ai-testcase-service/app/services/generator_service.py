import uuid
from typing import Iterator

import numpy as np
from flask import current_app

from app.exceptions import RagError
from app.services.config_factory import build_embedding_client, build_llm_client, build_rerank_client
from app.services.kb_repository import get_knowledge_base, list_chunks_with_documents, save_chunk_vectors
from app.utils.similarity import batch_cosine
from app.utils.vector_store import vector_for_dim

SYSTEM_PROMPT = (
    '你是测试用例生成助手。请同时依据「需求文档」和「历史测试用例」：\n'
    '1. 从需求中提取功能点、边界条件、业务规则与验收标准；\n'
    '2. 参考历史用例的写法、粒度与覆盖策略；\n'
    '3. 输出结构化测试用例（编号、标题、前置条件、步骤、预期结果、优先级）。\n'
    '不要编造检索结果中没有依据的需求。'
)


class TestCaseGenerator:
    def __init__(self, llm_config=None, embedding_config=None, rerank_config=None, top_k=None, rerank_top_k=None):
        self.llm_config = llm_config or {}
        self.embedding_config = embedding_config or {}
        self.rerank_config = rerank_config or {}
        self.top_k = top_k or current_app.config['RAG_RETRIEVE_TOP_K']
        self.rerank_top_k = rerank_top_k or current_app.config['RAG_RERANK_TOP_K']

    def retrieve(self, knowledge_base_id, query, rerank=True):
        hits = []
        for item in self.iter_retrieve(knowledge_base_id, query, rerank=rerank):
            if item.get('kind') == 'result':
                hits = item.get('hits') or []
        return hits

    def iter_retrieve(self, knowledge_base_id, query, rerank=True) -> Iterator[dict]:
        kb = get_knowledge_base(knowledge_base_id)
        if kb is None:
            yield {'kind': 'progress', 'content': '知识库不存在，跳过检索'}
            yield {'kind': 'result', 'hits': []}
            return

        yield {'kind': 'progress', 'content': f'加载知识库「{kb.name}」分块…'}
        rows = list_chunks_with_documents(knowledge_base_id)
        if not rows:
            yield {'kind': 'progress', 'content': '知识库暂无分块'}
            yield {'kind': 'result', 'hits': []}
            return

        pairs = [(chunk, title) for chunk, title in rows if chunk.content or chunk.vector]
        if not pairs:
            yield {'kind': 'result', 'hits': []}
            return

        yield {
            'kind': 'progress',
            'content': f'可用分块 {len(pairs)} 条，正在对查询做 Embedding…',
        }
        embedder = build_embedding_client(self.embedding_config)
        query_vec = embedder.embed_batch([query])[0]
        query_dim = len(query_vec or [])
        if query_dim <= 0:
            yield {'kind': 'progress', 'content': '查询向量为空，跳过检索'}
            yield {'kind': 'result', 'hits': []}
            return

        aligned = []
        stale = []
        for chunk, title in pairs:
            vec = vector_for_dim(chunk.vector, query_dim)
            if vec:
                aligned.append((chunk, vec, title))
            else:
                stale.append((chunk, title))

        yield {
            'kind': 'progress',
            'content': f'查询向量维度 {query_dim}，已对齐 {len(aligned)} 条，待补算 {len(stale)} 条',
        }

        if stale:
            yield {
                'kind': 'progress',
                'content': f'正在为 {len(stale)} 条分块补算 {query_dim} 维向量…',
            }
            try:
                new_vecs = embedder.embed_batch([item[0].content or '' for item in stale])
                updates = []
                for (chunk, title), vec in zip(stale, new_vecs):
                    if not vec or len(vec) != query_dim:
                        continue
                    updates.append((chunk, vec))
                    aligned.append((chunk, list(vec), title))
                save_chunk_vectors(updates)
                yield {
                    'kind': 'progress',
                    'content': f'补算完成，已写入 {len(updates)} 条向量',
                }
            except Exception as exc:
                yield {'kind': 'progress', 'content': f'补算向量失败：{exc}'}
                if not aligned:
                    yield {'kind': 'result', 'hits': []}
                    return

        if not aligned:
            yield {'kind': 'result', 'hits': []}
            return

        yield {'kind': 'progress', 'content': f'正在对 {len(aligned)} 条分块计算余弦相似度…'}
        chunks = [item[0] for item in aligned]
        vectors = [item[1] for item in aligned]
        titles = [item[2] for item in aligned]
        scores = batch_cosine(query_vec, np.asarray(vectors, dtype=np.float32))
        ranked = sorted(zip(chunks, scores.tolist(), titles), key=lambda item: item[1], reverse=True)

        hits = []
        for chunk, score, doc_title in ranked[: self.top_k]:
            hits.append(
                {
                    'id': str(chunk.id),
                    'content': chunk.content,
                    'score': float(score),
                    'knowledge_id': str(chunk.document_id),
                    'knowledge_title': doc_title or f'文档#{chunk.document_id}',
                    'chunk_index': chunk.chunk_index,
                    'kb_id': knowledge_base_id,
                    'kb_name': kb.name,
                    'kb_type': kb.kb_type,
                }
            )

        top_score = f'{hits[0]["score"]:.3f}' if hits else '-'
        yield {
            'kind': 'progress',
            'content': f'召回 Top-{len(hits)}，最高相似度 {top_score}',
        }

        if hits and rerank:
            yield {'kind': 'progress', 'content': '正在对召回结果重排序…'}
            embedder = build_embedding_client(self.embedding_config)
            reranker = build_rerank_client(self.rerank_config, embedder=embedder)
            reranked = reranker.rerank(query, hits, top_k=self.rerank_top_k, text_key='content')
            hits = reranked or hits[: self.rerank_top_k]
            yield {'kind': 'progress', 'content': f'重排序完成，保留 {len(hits)} 条'}
        yield {'kind': 'result', 'hits': hits}

    def generate_stream(self, query, requirement_kb_id, testcase_kb_id) -> Iterator[dict]:
        req_kb = get_knowledge_base(requirement_kb_id)
        case_kb = get_knowledge_base(testcase_kb_id)
        if req_kb is None or case_kb is None:
            raise RagError('知识库不存在', status_code=404)

        message_id = str(uuid.uuid4())
        req_hits, case_hits, thinking, references = self._retrieve_both(
            query, requirement_kb_id, testcase_kb_id, req_kb.name, case_kb.name
        )
        yield self._event(message_id, 'thinking', thinking, done=False)
        yield {
            'id': message_id,
            'response_type': 'references',
            'content': '',
            'done': False,
            'knowledge_references': references,
        }

        messages = self._messages(query, req_hits, case_hits)
        llm = build_llm_client(self.llm_config)
        try:
            if not llm.api_key:
                answer = self._fallback_answer(query, req_hits, case_hits)
                yield self._event(message_id, 'answer', answer, done=False)
            else:
                for delta in llm.chat_stream(messages, temperature=0.3, max_tokens=4096):
                    yield self._event(message_id, 'answer', delta, done=False)
        except Exception as exc:
            yield self._event(message_id, 'error', f'生成测试用例失败：{exc}', done=True)
            return
        yield self._event(message_id, 'answer', '', done=True)

    def _retrieve_both(self, query, requirement_kb_id, testcase_kb_id, req_name, case_name):
        thinking = f'正在检索「{req_name}」与「{case_name}」，并结合历史用例风格生成测试用例。'
        req_hits = self.retrieve(requirement_kb_id, query)
        case_hits = self.retrieve(testcase_kb_id, query)
        references = req_hits + case_hits
        return req_hits, case_hits, thinking, references

    def _messages(self, query, req_hits, case_hits):
        return [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': self._user_prompt(query, req_hits, case_hits)},
        ]

    def _user_prompt(self, query, req_hits, case_hits):
        return (
            f'用户需求：\n{query}\n\n'
            f'【需求文档检索结果】\n{self._format_hits(req_hits)}\n\n'
            f'【历史测试用例检索结果】\n{self._format_hits(case_hits)}\n'
        )

    @staticmethod
    def _format_hits(hits):
        if not hits:
            return '（无检索结果）'
        lines = []
        for index, hit in enumerate(hits, start=1):
            score = hit.get('rerank_score', hit.get('score', ''))
            title = hit.get('knowledge_title') or hit.get('kb_name') or ''
            lines.append(f'{index}. [{title}] (score={score})\n{hit.get("content", "")}')
        return '\n\n'.join(lines)

    @staticmethod
    def _fallback_answer(query, req_hits, case_hits):
        req_text = '\n'.join(f'- {hit.get("content", "")}' for hit in req_hits) or '- （需求库暂无分块）'
        case_text = '\n'.join(f'- {hit.get("content", "")}' for hit in case_hits) or '- （用例库暂无分块）'
        return (
            '未配置对话模型，以下为基于检索结果整理的测试要点，完整用例请先配置大模型和 API Key。\n\n'
            f'用户需求：{query}\n\n'
            f'## 需求要点\n{req_text}\n\n'
            f'## 可参考的历史用例\n{case_text}\n'
        )

    @staticmethod
    def _event(message_id, response_type, content, done=False):
        return {
            'id': message_id,
            'response_type': response_type,
            'content': content,
            'done': done,
        }
