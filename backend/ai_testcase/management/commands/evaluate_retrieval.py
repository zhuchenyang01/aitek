import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from ai_testcase.evaluation import evaluate_queries, load_eval_dataset
from ai_testcase.generator import TestCaseGenerator
from ai_testcase.models import KnowledgeBase


class Command(BaseCommand):
    help = '对知识库检索做 Precision@K / Recall@K 评测'

    def add_arguments(self, parser):
        parser.add_argument('--dataset', required=True, help='评测集 JSON 路径')
        parser.add_argument('--kb-id', type=int, default=0, help='知识库 ID，缺省则读评测集里的 knowledge_base_id')
        parser.add_argument('--ks', default='3,5', help='评测截断，逗号分隔，默认 3,5')
        parser.add_argument('--no-rerank', action='store_true', help='只评向量召回，不做 rerank')
        parser.add_argument('--output', default='', help='把完整结果写到该 JSON 文件')

    def handle(self, *args, **options):
        dataset_path = Path(options['dataset']).expanduser()
        if not dataset_path.exists():
            raise CommandError(f'找不到评测集: {dataset_path}')

        try:
            payload = json.loads(dataset_path.read_text(encoding='utf-8'))
            dataset_kb_id, queries = load_eval_dataset(payload)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise CommandError(f'评测集无法解析: {exc}') from exc

        kb_id = options['kb_id'] or dataset_kb_id
        if not kb_id:
            raise CommandError('请通过 --kb-id 或评测集 knowledge_base_id 指定知识库')

        kb = KnowledgeBase.objects.filter(pk=kb_id).first()
        if kb is None:
            raise CommandError(f'知识库不存在: {kb_id}')
        if not queries:
            raise CommandError('评测集 queries 为空')

        try:
            ks = [int(item.strip()) for item in str(options['ks']).split(',') if item.strip()]
        except ValueError as exc:
            raise CommandError('--ks 必须是逗号分隔的整数，例如 3,5') from exc
        if not ks:
            raise CommandError('--ks 不能为空')
        max_k = max(ks)

        generator = TestCaseGenerator(top_k=max_k, rerank_top_k=max_k)
        use_rerank = not options['no_rerank']

        def retrieve_fn(query):
            return generator.retrieve(kb, query, rerank=use_rerank)

        result = evaluate_queries(queries, retrieve_fn, ks=ks)
        result['knowledge_base_id'] = kb.id
        result['knowledge_base_name'] = kb.name
        result['kb_type'] = kb.kb_type
        result['rerank'] = use_rerank
        result['dataset'] = str(dataset_path)

        self.stdout.write(self.style.NOTICE(
            f'知识库 #{kb.id} {kb.name}（{kb.kb_type}） | 查询 {result["query_count"]} 条 | rerank={use_rerank}'
        ))
        self._print_summary('分块级', result['chunk'], ks)
        self._print_summary('文档级', result['doc'], ks)

        output = options['output']
        if output:
            Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            self.stdout.write(self.style.SUCCESS(f'明细已写入 {output}'))

    def _print_summary(self, title, summary, ks):
        labeled = summary.get('labeled') or 0
        if not labeled:
            self.stdout.write(f'{title}: 无标注，跳过')
            return
        parts = [f'{title} n={labeled}']
        for k in ks:
            p = summary.get(f'precision@{k}')
            r = summary.get(f'recall@{k}')
            if p is None and r is None:
                continue
            parts.append(f'P@{k}={_fmt(p)}  R@{k}={_fmt(r)}')
        parts.append(f'MRR={_fmt(summary.get("mrr"))}')
        self.stdout.write(' | '.join(parts))


def _fmt(value):
    if value is None:
        return '-'
    return f'{value:.4f}'
