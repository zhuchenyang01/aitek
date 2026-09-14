import json

from django.core.management.base import BaseCommand, CommandError

from ai_testcase.models import KnowledgeBase, KnowledgeChunk


class Command(BaseCommand):
    help = '导出知识库分块，方便编写 retrieval 评测标注（relevant_chunk_ids）'

    def add_arguments(self, parser):
        parser.add_argument('--kb-id', type=int, required=True, help='知识库 ID')
        parser.add_argument('--output', default='', help='输出 JSON 路径，默认打印到终端')

    def handle(self, *args, **options):
        kb = KnowledgeBase.objects.filter(pk=options['kb_id']).first()
        if kb is None:
            raise CommandError(f'知识库不存在: {options["kb_id"]}')

        chunks = (
            KnowledgeChunk.objects.filter(knowledge_base=kb)
            .select_related('document')
            .order_by('document_id', 'chunk_index', 'id')
        )
        payload = {
            'knowledge_base_id': kb.id,
            'name': kb.name,
            'kb_type': kb.kb_type,
            'chunk_count': chunks.count(),
            'chunks': [
                {
                    'id': chunk.id,
                    'document_id': chunk.document_id,
                    'document_title': chunk.document.title or f'文档#{chunk.document_id}',
                    'chunk_index': chunk.chunk_index,
                    'content': chunk.content,
                }
                for chunk in chunks
            ],
            'queries': [
                {
                    'query': '在这里填写真实会问的问题',
                    'relevant_chunk_ids': [],
                    'relevant_doc_ids': [],
                    'note': '',
                }
            ],
        }
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        output = options['output']
        if output:
            with open(output, 'w', encoding='utf-8') as fh:
                fh.write(text)
                fh.write('\n')
            self.stdout.write(self.style.SUCCESS(f'已写入 {output}，共 {payload["chunk_count"]} 个分块'))
            return
        self.stdout.write(text)
