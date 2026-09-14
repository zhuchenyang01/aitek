from .case_no import assign_unique_case_nos
from .models import FunctionalTestCase, TestCaseGeneration
from .testcase_parser import apply_pipeline_modules, parse_test_cases


def persist_generation_result(
    *,
    user,
    project,
    requirement,
    query,
    answer,
    thinking='',
    references=None,
    feature_points=None,
    test_directions=None,
    llm_config_id=None,
    status=TestCaseGeneration.STATUS_COMPLETED,
):
    references = references or []
    generation = TestCaseGeneration.objects.create(
        user=user,
        project=project,
        requirement=requirement,
        query=query,
        answer_raw=answer or '',
        thinking=thinking or '',
        references=references,
        feature_points=feature_points or [],
        test_directions=test_directions or [],
        llm_config_id=llm_config_id,
        status=status,
    )

    parsed_cases = parse_test_cases(answer)
    parsed_cases = apply_pipeline_modules(parsed_cases, feature_points, test_directions)
    used_nos = FunctionalTestCase.objects.filter(user=user).values_list('case_no', flat=True)
    requirement_name = (requirement.title or requirement.source_filename or '').strip()
    parsed_cases = assign_unique_case_nos(parsed_cases, requirement_name, used_nos)
    case_rows = []
    for item in parsed_cases:
        case_rows.append(
            FunctionalTestCase(
                generation=generation,
                project=project,
                requirement=requirement,
                user=user,
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
    if case_rows:
        FunctionalTestCase.objects.bulk_create(case_rows)

    return generation, len(case_rows)
