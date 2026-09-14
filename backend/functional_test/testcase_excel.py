import re
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

from openpyxl import Workbook

HEADERS = (
    '用例编号',
    '模块',
    '标题',
    '前置条件',
    '测试步骤',
    '预期结果',
    '优先级',
    '创建人',
    '所属项目',
    '关联需求',
    '生成时间',
)


def build_testcase_workbook(rows):
    wb = Workbook()
    ws = wb.active
    ws.title = '测试用例'
    ws.append(list(HEADERS))

    for row in rows:
        ws.append([
            row.get('case_no') or '',
            row.get('module') or '',
            row.get('title') or '',
            row.get('precondition') or '',
            row.get('steps') or '',
            row.get('expected_result') or '',
            row.get('priority') or '',
            row.get('creator_name') or '',
            row.get('project_name') or '',
            row.get('requirement_title') or '',
            row.get('created_at') or '',
        ])

    ws.column_dimensions['A'].width = 18
    ws.column_dimensions['B'].width = 16
    ws.column_dimensions['C'].width = 28
    ws.column_dimensions['D'].width = 24
    ws.column_dimensions['E'].width = 42
    ws.column_dimensions['F'].width = 28
    ws.column_dimensions['G'].width = 10
    ws.column_dimensions['H'].width = 14
    ws.column_dimensions['I'].width = 18
    ws.column_dimensions['J'].width = 24
    ws.column_dimensions['K'].width = 20

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def requirement_export_stem(requirement):
    if requirement is None:
        return ''
    title = (getattr(requirement, 'title', None) or '').strip()
    if title:
        return Path(title).stem
    source = (getattr(requirement, 'source_filename', None) or '').strip()
    return Path(source).stem if source else ''


def testcase_export_filename(queryset):
    names = []
    seen = set()
    for item in queryset.select_related('requirement'):
        stem = requirement_export_stem(item.requirement)
        if stem and stem not in seen:
            seen.add(stem)
            names.append(stem)
        if len(names) > 1:
            break
    stem = names[0] if len(names) == 1 else '测试用例'
    stem = re.sub(r'[\\/:*?"<>|]+', '_', stem).strip(' .') or '测试用例'
    return f'{stem}.xlsx'


def attachment_content_disposition(filename):
    ascii_name = 'testcases.xlsx'
    encoded = quote(filename)
    return f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{encoded}'
