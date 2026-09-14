from app.services.generator_service import TestCaseGenerator


def match_single_requirement(feature, requirement_kb_id, generator):
    module = feature.get('模块') or ''
    point = feature.get('功能点') or ''
    query = f'{module} {point}'.strip()
    hits = generator.retrieve(requirement_kb_id, query, rerank=True)
    return {
        '模块': module,
        '功能点': point,
        'query': query,
        'hits': hits,
        'hit_count': len(hits),
    }


def match_requirements(features, requirement_kb_id, embedding_config=None, rerank_config=None):
    generator = TestCaseGenerator(
        embedding_config=embedding_config or {},
        rerank_config=rerank_config or {},
    )
    return [
        match_single_requirement(feature, requirement_kb_id, generator)
        for feature in (features or [])
    ]
