from ai_testcase.ingest import extract_text_from_file
from ai_testcase.models import KnowledgeBase, KnowledgeDocument

from .models import RequirementDocument


def get_or_create_project_requirement_kb(user, project):
    name = f'{project.name} - 需求库'
    kb, _ = KnowledgeBase.objects.get_or_create(
        user=user,
        name=name,
        kb_type=KnowledgeBase.TYPE_REQUIREMENT,
        defaults={'description': f'项目「{project.name}」自动关联的需求文档知识库'},
    )
    return kb


def get_or_create_default_testcase_kb(user):
    kb = KnowledgeBase.objects.filter(user=user, kb_type=KnowledgeBase.TYPE_TESTCASE).order_by('id').first()
    if kb:
        return kb
    return KnowledgeBase.objects.create(
        user=user,
        name='默认测试用例库',
        kb_type=KnowledgeBase.TYPE_TESTCASE,
        description='功能测试生成用例时引用的历史用例知识库',
    )


def requirement_document_already_ingested(document, knowledge_base):
    return KnowledgeDocument.objects.filter(
        knowledge_base=knowledge_base,
        source_filename=document.source_filename,
    ).exists()


def extract_requirement_text(document: RequirementDocument):
    if not document.file:
        raise ValueError('需求文件不存在，无法解析入库')
    return extract_text_from_file(document.file.path, document.source_filename)
