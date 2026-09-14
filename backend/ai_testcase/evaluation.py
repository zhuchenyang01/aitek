"""检索评测：Precision@K / Recall@K / MRR。"""


def normalize_ids(values):
    ids = set()
    for value in values or []:
        if value is None or value == '':
            continue
        ids.add(str(value))
    return ids


def precision_at_k(retrieved_ids, relevant_ids, k):
    if k <= 0:
        return 0.0
    top = [str(item) for item in retrieved_ids[:k]]
    if not top:
        return 1.0 if not relevant_ids else 0.0
    if not relevant_ids:
        return 0.0
    hits = len(set(top) & relevant_ids)
    return hits / len(top)


def recall_at_k(retrieved_ids, relevant_ids, k):
    if not relevant_ids:
        return 1.0
    top = [str(item) for item in retrieved_ids[:k]]
    hits = len(set(top) & relevant_ids)
    return hits / len(relevant_ids)


def mrr(retrieved_ids, relevant_ids):
    if not relevant_ids:
        return 0.0
    relevant = set(relevant_ids)
    for index, item in enumerate(retrieved_ids, start=1):
        if str(item) in relevant:
            return 1.0 / index
    return 0.0


def load_eval_dataset(payload):
    if isinstance(payload, list):
        return None, payload
    if not isinstance(payload, dict):
        raise ValueError('评测集必须是 JSON 对象或数组')
    queries = payload.get('queries')
    if not isinstance(queries, list):
        raise ValueError('评测集缺少 queries 数组')
    return payload.get('knowledge_base_id'), queries


def evaluate_queries(queries, retrieve_fn, ks=(3, 5)):
    ks = tuple(sorted({int(k) for k in ks if int(k) > 0}))
    if not ks:
        raise ValueError('ks 不能为空')

    details = []
    chunk_scores = {k: {'precision': [], 'recall': []} for k in ks}
    doc_scores = {k: {'precision': [], 'recall': []} for k in ks}
    chunk_mrrs = []
    doc_mrrs = []

    for index, item in enumerate(queries, start=1):
        query = (item.get('query') or '').strip()
        if not query:
            raise ValueError(f'第 {index} 条缺少 query')

        relevant_chunks = normalize_ids(item.get('relevant_chunk_ids'))
        relevant_docs = normalize_ids(item.get('relevant_doc_ids'))
        hits = retrieve_fn(query) or []
        retrieved_chunks = [str(hit.get('id')) for hit in hits if hit.get('id') is not None]
        retrieved_docs = [str(hit.get('knowledge_id')) for hit in hits if hit.get('knowledge_id') is not None]

        row = {
            'query': query,
            'note': item.get('note') or '',
            'retrieved_chunk_ids': retrieved_chunks,
            'retrieved_doc_ids': retrieved_docs,
            'relevant_chunk_ids': sorted(relevant_chunks, key=_id_sort),
            'relevant_doc_ids': sorted(relevant_docs, key=_id_sort),
            'chunk': {},
            'doc': {},
        }

        if relevant_chunks:
            chunk_mrrs.append(mrr(retrieved_chunks, relevant_chunks))
            for k in ks:
                p = precision_at_k(retrieved_chunks, relevant_chunks, k)
                r = recall_at_k(retrieved_chunks, relevant_chunks, k)
                chunk_scores[k]['precision'].append(p)
                chunk_scores[k]['recall'].append(r)
                row['chunk'][f'p@{k}'] = round(p, 4)
                row['chunk'][f'r@{k}'] = round(r, 4)
        if relevant_docs:
            doc_mrrs.append(mrr(retrieved_docs, relevant_docs))
            for k in ks:
                p = precision_at_k(retrieved_docs, relevant_docs, k)
                r = recall_at_k(retrieved_docs, relevant_docs, k)
                doc_scores[k]['precision'].append(p)
                doc_scores[k]['recall'].append(r)
                row['doc'][f'p@{k}'] = round(p, 4)
                row['doc'][f'r@{k}'] = round(r, 4)
        details.append(row)

    return {
        'query_count': len(details),
        'ks': list(ks),
        'chunk': _summarize(chunk_scores, chunk_mrrs, ks),
        'doc': _summarize(doc_scores, doc_mrrs, ks),
        'details': details,
    }


def _mean(values):
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _summarize(score_map, mrrs, ks):
    summary = {'labeled': 0, 'mrr': _mean(mrrs)}
    for k in ks:
        summary[f'precision@{k}'] = _mean(score_map[k]['precision'])
        summary[f'recall@{k}'] = _mean(score_map[k]['recall'])
        summary['labeled'] = max(summary['labeled'], len(score_map[k]['precision']))
    return summary


def _id_sort(value):
    try:
        return (0, int(value))
    except (TypeError, ValueError):
        return (1, str(value))
