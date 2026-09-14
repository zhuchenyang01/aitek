import re

CASE_BLOCK_SPLIT_RE = re.compile(
    r'(?=^#{1,3}\s*测试用例编号\s*[:：])',
    re.MULTILINE,
)
CASE_BLOCK_FALLBACK_SPLIT_RE = re.compile(
    r'(?=^#{1,3}\s*(?:TC[-_]\S+|用例\s*\d+|测试用例\s*\d+))',
    re.MULTILINE | re.IGNORECASE,
)
CASE_NO_RE = re.compile(r'测试用例编号\s*[:：]\s*(TC\S+)', re.IGNORECASE)
CASE_NO_FALLBACK_RE = re.compile(r'(TC[-_][^\s，,。；;]+)', re.IGNORECASE)
FIELD_LINE_RE = re.compile(
    r'^(?:[-*+]\s+|\d+[.、)]\s+)?\*{0,2}'
    r'(所属模块|模块名称|模块|标题|前置条件|测试步骤|步骤|预期结果|优先级|测试数据|备注)'
    r'\*{0,2}\s*[:：]\s*(.*)$'
)
FIELD_KEY_MAP = {
    '所属模块': '模块',
    '模块名称': '模块',
    '测试步骤': '步骤',
}
MODULE_PLACEHOLDERS = {'', '中文模块名称', '模块名称', '模块名', '模块', 'module', 'none', '无'}
SKIP_HEADING_RE = re.compile(r'测试用例|覆盖要求|输出格式|结构化分析|用户需求|历史用例|图片理解|附录')
HEADING_LINE_RE = re.compile(r'^#{1,6}\s+\S')
HEADER_TITLE_RE = re.compile(
    r'^#{1,3}\s*(?:TC[-_]\S+|用例\s*\d+)\s*(.+)$',
    re.IGNORECASE,
)
TABLE_SEP_CELL_RE = re.compile(r'^:?-{3,}:?$')

HEADER_ALIASES = {
    'case_no': ('编号', '用例编号', 'id', 'case'),
    'module': ('模块', '所属模块'),
    'title': ('标题', '名称', '用例名称'),
    'precondition': ('前置条件', '前置', '预置条件'),
    'steps': ('测试步骤', '步骤', '操作步骤'),
    'expected_result': ('预期结果', '期望结果', '预期'),
    'priority': ('优先级', '优先'),
}


def _clean(value):
    text = (value or '').strip()
    text = re.sub(r'\*\*', '', text)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = text.replace('<br>', '\n')
    return text.strip(' \t\r\n-:：')


def _normalize_case_no(value, index):
    raw = _clean(value)
    if not raw:
        return f'TC-{index + 1:02d}'
    raw = raw.replace('_', '-')
    if not re.match(r'^TC', raw, re.IGNORECASE):
        raw = f'TC-{raw}'
    simple = re.match(r'^TC-(\d+)$', raw, re.IGNORECASE)
    if simple:
        return f'TC-{int(simple.group(1)):02d}'
    return raw


def _normalize_field_key(key):
    return FIELD_KEY_MAP.get(key, key)


def _clean_module(value):
    module = _first_line(_clean(value), 128)
    if module.lower() in MODULE_PLACEHOLDERS or module in MODULE_PLACEHOLDERS:
        return ''
    return module


def _heading_as_module(line):
    text = (line or '').strip()
    if not HEADING_LINE_RE.match(text):
        return ''
    text = re.sub(r'^#{1,6}\s+', '', text)
    text = re.sub(r'^模块\s*[:：]\s*', '', text)
    text = re.sub(r'^[\(（]?[一二三四五六七八九十百千]+[\)）\.．、]\s*', '', text)
    text = re.sub(r'^\d+(?:\.\d+)*[.．、]?\s*', '', text)
    case_heading = re.match(r'^TC[-_][^\s]+(?:\s+(.+))?$', text, re.IGNORECASE)
    if case_heading:
        text = (case_heading.group(1) or '').strip()
    text = _clean(text)
    if not text or len(text) > 32 or SKIP_HEADING_RE.search(text):
        return ''
    if re.match(r'^[A-Za-z]$', text):
        return ''
    return text


def _section_module_before(text, start):
    module = ''
    for line in (text or '')[: max(start, 0)].splitlines():
        stripped = line.strip()
        heading = _heading_as_module(stripped)
        if heading:
            module = heading
            continue
        field = re.match(
            r'^\*{0,2}(?:所属)?模块(?:名称)?\*{0,2}\s*[:：]\s*(.+)$',
            stripped,
        )
        if field:
            candidate = _clean_module(field.group(1))
            if candidate:
                module = candidate
    return module


def _preceding_module(text, start):
    return _section_module_before(text, start)


def _fill_blank_modules(cases):
    last = ''
    for case in cases:
        module = (case.get('module') or '').strip()
        if module:
            last = module
        elif last:
            case['module'] = last
    return cases


def _infer_module(case_no, explicit=''):
    module = _clean_module(explicit)
    if module:
        return module
    match = re.match(r'^TC-(.+)-(\d+)$', case_no or '', re.IGNORECASE)
    if not match:
        return ''
    middle = match.group(1).strip()
    if re.match(r'^\d+$', middle):
        return ''
    # 新编号为 TC-需求首字母-001，字母缩写不能当作模块名
    if not re.search(r'[\u4e00-\u9fff]', middle):
        return ''
    return middle


def _split_blocks(text):
    blocks = [
        item.strip()
        for item in CASE_BLOCK_SPLIT_RE.split(text)
        if item.strip() and CASE_NO_RE.search(item.splitlines()[0] if item.strip() else '')
    ]
    if blocks:
        return blocks

    blocks = []
    for item in CASE_BLOCK_FALLBACK_SPLIT_RE.split(text):
        item = item.strip()
        if not item:
            continue
        first_line = item.splitlines()[0]
        if CASE_NO_FALLBACK_RE.search(first_line):
            blocks.append(item)
    return blocks


def _parse_sections(block):
    sections = {}
    current_key = None
    current_lines = []

    for line in block.splitlines():
        stripped = line.strip()
        if not stripped:
            if current_key is not None:
                current_lines.append('')
            continue
        if re.match(r'^#{1,3}\s*测试用例编号', stripped):
            continue

        field_match = FIELD_LINE_RE.match(stripped)
        if field_match:
            if current_key is not None:
                sections[current_key] = _clean('\n'.join(current_lines))
            current_key = _normalize_field_key(field_match.group(1))
            remainder = field_match.group(2).strip()
            current_lines = [remainder] if remainder else []
            continue

        if current_key is not None:
            current_lines.append(stripped)

    if current_key is not None:
        sections[current_key] = _clean('\n'.join(current_lines))

    return sections


def _first_line(value, max_len=None):
    lines = [line.strip() for line in (value or '').splitlines() if line.strip()]
    if not lines:
        return ''
    line = lines[0]
    if max_len and len(line) > max_len:
        return line[:max_len]
    return line


def _split_table_cells(line):
    return [cell.strip() for cell in line.strip().strip('|').split('|')]


def _header_index_map(headers):
    mapping = {}
    for index, header in enumerate(headers):
        name = re.sub(r'\s+', '', header).lower()
        for field, aliases in HEADER_ALIASES.items():
            if field in mapping:
                continue
            if any(alias.lower() in name or name in alias.lower() for alias in aliases):
                mapping[field] = index
                break
    return mapping


def _is_table_separator(line):
    cells = _split_table_cells(line)
    if not cells:
        return False
    return all(TABLE_SEP_CELL_RE.match(re.sub(r'\s+', '', cell) or '') for cell in cells if cell)


def _table_lines_to_cases(table_lines, fallback_module=''):
    if len(table_lines) < 2:
        return []
    headers = _split_table_cells(table_lines[0])
    col_map = _header_index_map(headers)
    if 'title' not in col_map and 'case_no' not in col_map:
        return []
    start = 1
    if _is_table_separator(table_lines[1]):
        start = 2
    cases = []
    for row in table_lines[start:]:
        if _is_table_separator(row):
            continue
        cells = _split_table_cells(row)

        def cell(field):
            idx = col_map.get(field)
            if idx is None or idx >= len(cells):
                return ''
            return _clean(cells[idx])

        title = cell('title')
        case_no = cell('case_no')
        steps = cell('steps')
        expected = cell('expected_result')
        priority = _first_line(cell('priority'), 32)
        if not title and not steps and not case_no:
            continue
        if 'expected_result' in col_map and not expected:
            continue
        if 'priority' in col_map and not priority:
            continue
        cases.append(
            {
                'case_no': case_no,
                'module': cell('module') or fallback_module,
                'title': title,
                'precondition': cell('precondition') or '无',
                'steps': steps,
                'expected_result': expected or '无',
                'priority': priority or '中',
            }
        )
    return cases


def _parse_markdown_tables(text):
    cases = []
    current_module = ''
    current = []
    table_module = ''

    def flush():
        nonlocal current, table_module
        if current:
            cases.extend(_table_lines_to_cases(current, table_module))
        current = []
        table_module = ''

    for line in (text or '').splitlines():
        stripped = line.strip()
        if HEADING_LINE_RE.match(stripped):
            flush()
            extracted = _heading_as_module(stripped)
            if extracted:
                current_module = extracted
            continue
        if stripped.startswith('|'):
            if not current:
                table_module = current_module
            current.append(stripped)
            continue
        flush()
    flush()
    return cases


def _parse_block(block, index, fallback_module=''):
    block = (block or '').strip()
    if not block:
        return None

    case_no_match = CASE_NO_RE.search(block) or CASE_NO_FALLBACK_RE.search(block)
    case_no = _normalize_case_no(case_no_match.group(1) if case_no_match else '', index)
    sections = _parse_sections(block)

    first_line = block.splitlines()[0].strip() if block.splitlines() else ''
    header_title_match = HEADER_TITLE_RE.match(first_line)

    title = sections.get('标题') or (header_title_match.group(1).strip() if header_title_match else '') or f'测试用例 {index + 1}'
    precondition = sections.get('前置条件') or '无'
    steps = sections.get('步骤') or sections.get('测试步骤') or ''
    extra_data = sections.get('测试数据') or ''
    if extra_data:
        steps = f'{steps}\n测试数据：{extra_data}'.strip() if steps else f'测试数据：{extra_data}'
    expected_result = sections.get('预期结果') or '无'
    priority = _first_line(sections.get('优先级'), 32) or '中'
    module = _infer_module(case_no, sections.get('模块') or fallback_module)

    if not steps:
        body_lines = [
            line.strip()
            for line in block.splitlines()
            if line.strip() and not re.match(r'^#{1,3}\s*测试用例编号', line.strip())
        ]
        steps = _clean('\n'.join(body_lines)) or '无'

    return {
        'case_no': case_no,
        'module': module,
        'title': title,
        'precondition': precondition,
        'steps': steps,
        'expected_result': expected_result,
        'priority': priority,
        'sort_order': index,
    }


def _finalize_cases(items):
    cases = []
    for index, item in enumerate(items):
        case_no = _normalize_case_no(item.get('case_no') or '', index)
        cases.append(
            {
                'case_no': case_no,
                'module': _infer_module(case_no, item.get('module') or ''),
                'title': item.get('title') or f'测试用例 {index + 1}',
                'precondition': item.get('precondition') or '无',
                'steps': item.get('steps') or '无',
                'expected_result': item.get('expected_result') or '无',
                'priority': item.get('priority') or '中',
                'sort_order': index,
            }
        )
    return cases


EMPTY_FIELD_VALUES = {'', '无', '-', 'n/a', 'none', 'null'}
TRUNCATED_STEPS_RE = re.compile(
    r'(?:^|\n|<br\s*/?>)\s*(?:步骤\s*)?\d+\s*[.、:：]?\s*$',
    re.IGNORECASE,
)


def _is_blank_field(value):
    text = (value or '').strip()
    return not text or text.lower() in EMPTY_FIELD_VALUES


def _is_incomplete_case(item):
    title = (item.get('title') or '').strip()
    if not title or title == '生成的测试用例' or re.match(r'^测试用例\s*\d+$', title):
        return True
    steps = (item.get('steps') or '').strip()
    if _is_blank_field(steps):
        return True
    if TRUNCATED_STEPS_RE.search(steps):
        return True
    if _is_blank_field(item.get('expected_result')):
        return True
    if not (item.get('priority') or '').strip():
        return True
    return False


def _keep_complete_cases(cases):
    kept = []
    for item in cases or []:
        if _is_incomplete_case(item):
            continue
        item['sort_order'] = len(kept)
        kept.append(item)
    return kept


def apply_pipeline_modules(cases, features=None, directions=None):
    catalog = []
    seen = set()
    for src in list(features or []) + list(directions or []):
        if not isinstance(src, dict):
            continue
        module = (src.get('模块') or src.get('module') or '').strip()
        point = (src.get('功能点') or src.get('feature') or '').strip()
        if not module:
            continue
        key = (module, point)
        if key in seen:
            continue
        seen.add(key)
        catalog.append((module, point))
    catalog.sort(key=lambda item: len(item[1]), reverse=True)

    for case in cases or []:
        if (case.get('module') or '').strip():
            continue
        blob = f"{case.get('title') or ''} {case.get('steps') or ''} {case.get('precondition') or ''}"
        matched = ''
        for module, point in catalog:
            if point and point in blob:
                matched = module
                break
        if not matched:
            for module, _point in catalog:
                if module and module in blob:
                    matched = module
                    break
        if matched:
            case['module'] = matched
    return cases


def infer_module_for_title(markdown, title):
    title = (title or '').strip()
    if not title:
        return ''
    idx = (markdown or '').find(title)
    if idx < 0:
        return ''
    return _section_module_before(markdown, idx)


def parse_test_cases(markdown):
    text = (markdown or '').strip()
    if not text:
        return []

    blocks = _split_blocks(text)
    heading_cases = []
    search_from = 0
    for index, block in enumerate(blocks):
        start = text.find(block, search_from)
        if start < 0:
            start = search_from
        parsed = _parse_block(block, index, fallback_module=_preceding_module(text, start))
        if parsed:
            heading_cases.append(parsed)
        search_from = start + 1

    table_cases = _finalize_cases(_parse_markdown_tables(text))

    if len(table_cases) > 1 and len(heading_cases) <= 1:
        return _keep_complete_cases(_fill_blank_modules(table_cases))
    if heading_cases:
        return _keep_complete_cases(_fill_blank_modules(heading_cases))
    if table_cases:
        return _keep_complete_cases(_fill_blank_modules(table_cases))

    return []


def reparse_generation_cases(generation):
    from .case_no import assign_unique_case_nos
    from .models import FunctionalTestCase

    parsed_cases = parse_test_cases(generation.answer_raw)
    parsed_cases = apply_pipeline_modules(
        parsed_cases,
        getattr(generation, 'feature_points', None),
        getattr(generation, 'test_directions', None),
    )
    generation.cases.all().delete()
    used_nos = FunctionalTestCase.objects.filter(user=generation.user).values_list('case_no', flat=True)
    requirement_name = ''
    if generation.requirement_id:
        requirement_name = (
            generation.requirement.title or generation.requirement.source_filename or ''
        ).strip()
    parsed_cases = assign_unique_case_nos(parsed_cases, requirement_name, used_nos)
    rows = []
    for item in parsed_cases:
        rows.append(
            FunctionalTestCase(
                generation=generation,
                project=generation.project,
                requirement=generation.requirement,
                user=generation.user,
                case_no=item.get('case_no') or '',
                module=item.get('module') or '',
                title=item.get('title') or '',
                precondition=item.get('precondition') or '无',
                steps=item.get('steps') or '无',
                expected_result=item.get('expected_result') or '无',
                priority=item.get('priority') or '中',
                sort_order=item.get('sort_order') or 0,
            )
        )
    if rows:
        FunctionalTestCase.objects.bulk_create(rows)
    return len(rows)
