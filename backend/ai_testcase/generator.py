import json
import uuid
from typing import Iterator

import numpy as np
from django.conf import settings

from rag.models.embedding_client import EmbeddingClient
from rag.models.llm_client import LLMClient
from rag.models.rerank_client import RerankClient
from rag.utils.vector_store import packed_vector, vector_for_dim

from system.llm import resolve_embedding_client, resolve_rerank_client

from .exceptions import RagError
from .models import KnowledgeChunk

SYSTEM_PROMPT = (
    '你是测试用例生成助手。请同时依据「需求文档」和「历史测试用例」：\n'
    '1. 从需求中提取功能点、边界条件、业务规则与验收标准；\n'
    '2. 参考历史用例的写法、粒度与覆盖策略；\n'
    '3. 输出结构化测试用例（编号、标题、前置条件、步骤、预期结果、优先级）。\n'
    '不要编造检索结果中没有依据的需求。'
)


def _llm_kwargs():
    api_key = getattr(settings, 'DEEPSEEK_API_KEY', '') or None
    return {
        'api_key': api_key or '',
        'base_url': getattr(settings, 'DEEPSEEK_BASE_URL', None),
        'model': getattr(settings, 'DEEPSEEK_CHAT_MODEL', None),
        'timeout': float(getattr(settings, 'RAG_HTTP_TIMEOUT', 120)),
    }


def _embedder():
    return EmbeddingClient(
        api_key=getattr(settings, 'EMBEDDING_API_KEY', '') or '',
        base_url=getattr(settings, 'EMBEDDING_BASE_URL', None),
        model=getattr(settings, 'EMBEDDING_MODEL', None),
        use_local=bool(getattr(settings, 'EMBEDDING_USE_LOCAL', False)),
    )


class TestCaseGenerator:
    def __init__(self, llm=None, embedder=None, reranker=None, user=None, top_k=None, rerank_top_k=None, use_env_llm=True):
        self.llm = llm
        self.embedder = embedder
        self.reranker = reranker
        self.user = user
        self.use_env_llm = use_env_llm
        self.top_k = top_k or int(getattr(settings, 'RAG_RETRIEVE_TOP_K', 5))
        self.rerank_top_k = rerank_top_k or int(getattr(settings, 'RAG_RERANK_TOP_K', 3))

    def _get_llm(self):
        if self.llm is not None:
            return self.llm
        if not self.use_env_llm:
            return LLMClient(api_key='')
        return LLMClient(**_llm_kwargs())

    def _get_embedder(self):
        if self.embedder is not None:
            return self.embedder
        if self.user is not None:
            client = resolve_embedding_client(self.user)
            if client is not None:
                return client
        return _embedder()

    def _get_reranker(self):
        if self.reranker is not None:
            return self.reranker
        if self.user is not None:
            return resolve_rerank_client(self.user)
        return RerankClient(
            api_key=getattr(settings, 'RERANK_API_KEY', '') or '',
            base_url=getattr(settings, 'RERANK_BASE_URL', '') or '',
        )

    def retrieve(self, knowledge_base, query, rerank=True):
        chunks = list(
            KnowledgeChunk.objects.filter(knowledge_base=knowledge_base).select_related('document')
        )
        if not chunks:
            return []

        embedder = self._get_embedder()
        query_vec = embedder.embed_batch([query])[0]
        query_dim = len(query_vec or [])
        if query_dim <= 0:
            return []
        aligned_chunks, aligned_vectors = [], []
        stale = []
        for chunk in chunks:
            vec = vector_for_dim(chunk.vector, query_dim)
            if vec:
                aligned_chunks.append(chunk)
                aligned_vectors.append(vec)
            else:
                stale.append(chunk)
        if stale:
            new_vecs = embedder.embed_batch([item.content or '' for item in stale])
            updates = []
            for chunk, vec in zip(stale, new_vecs):
                if not vec or len(vec) != query_dim:
                    continue
                chunk.vector = packed_vector(vec, chunk.vector)
                updates.append(chunk)
                aligned_chunks.append(chunk)
                aligned_vectors.append(list(vec))
            if updates:
                KnowledgeChunk.objects.bulk_update(updates, ['vector'])
        if not aligned_vectors:
            return []
        chunks = aligned_chunks
        scores = batch_cosine(query_vec, np.asarray(aligned_vectors, dtype=np.float32))
        ranked = sorted(zip(chunks, scores.tolist()), key=lambda item: item[1], reverse=True)
        hits = []
        for chunk, score in ranked[: self.top_k]:
            hits.append(
                {
                    'id': str(chunk.id),
                    'content': chunk.content,
                    'score': float(score),
                    'knowledge_id': str(chunk.document_id),
                    'knowledge_title': chunk.document.title or f'文档#{chunk.document_id}',
                    'chunk_index': chunk.chunk_index,
                    'kb_id': knowledge_base.id,
                    'kb_name': knowledge_base.name,
                    'kb_type': knowledge_base.kb_type,
                }
            )
        if hits and rerank:
            reranked = self._get_reranker().rerank(query, hits, top_k=self.rerank_top_k, text_key='content')
            return reranked or hits[: self.rerank_top_k]
        return hits

    def generate(self, query, requirement_kb, testcase_kb):
        req_hits, case_hits, thinking, references = self._retrieve_both(query, requirement_kb, testcase_kb)
        messages = self._messages(query, req_hits, case_hits)
        llm = self._get_llm()
        if not getattr(llm, 'api_key', ''):
            answer = self._fallback_answer(query, req_hits, case_hits)
        else:
            try:
                answer = llm.chat(messages, temperature=0.3, max_tokens=4096)
            except Exception as exc:
                raise RagError(f'生成测试用例失败：{exc}', status_code=502) from exc
        return {
            'message_id': str(uuid.uuid4()),
            'answer': answer,
            'thinking': thinking,
            'references': references,
        }

    def generate_stream(self, query, requirement_kb, testcase_kb) -> Iterator[dict]:
        message_id = str(uuid.uuid4())
        req_hits, case_hits, thinking, references = self._retrieve_both(query, requirement_kb, testcase_kb)
        yield self._event(message_id, 'thinking', thinking, done=False)
        yield {
            'id': message_id,
            'response_type': 'references',
            'content': '',
            'done': False,
            'knowledge_references': references,
        }

        messages = self._messages(query, req_hits, case_hits)
        llm = self._get_llm()
        try:
            if not getattr(llm, 'api_key', ''):
                answer = self._fallback_answer(query, req_hits, case_hits)
                yield self._event(message_id, 'answer', answer, done=False)
            else:
                for delta in llm.chat_stream(messages, temperature=0.3, max_tokens=4096):
                    yield self._event(message_id, 'answer', delta, done=False)
        except Exception as exc:
            yield self._event(message_id, 'error', f'生成测试用例失败：{exc}', done=True)
            return
        yield self._event(message_id, 'answer', '', done=True)

    def _retrieve_both(self, query, requirement_kb, testcase_kb):
        thinking = (
            f'正在检索「{requirement_kb.name}」与「{testcase_kb.name}」，'
            '并结合历史用例风格生成测试用例。'
        )
        req_hits = self.retrieve(requirement_kb, query)
        case_hits = self.retrieve(testcase_kb, query)
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


def sse_bytes(event: dict) -> bytes:
    payload = json.dumps(event, ensure_ascii=False)
    return f'event: message\ndata: {payload}\n\n'.encode('utf-8')
