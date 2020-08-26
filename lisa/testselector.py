import re
from functools import partial
from typing import Callable, Dict, List, Mapping, Optional, Pattern, Set, Union, cast

from lisa import schema
from lisa.testsuite import TestCaseData, TestCaseMetadata, get_cases_metadata
from lisa.util import constants
from lisa.util.exceptions import LisaException
from lisa.util.logger import get_logger

_get_logger = partial(get_logger, "init", "selector")


def select_testcases(
    filters: Optional[List[schema.TestCase]] = None,
    init_cases: Optional[List[TestCaseMetadata]] = None,
) -> List[TestCaseData]:
    """
    based on filters to select test cases. If filters are None, return all cases.
    """
    results: List[TestCaseData] = []
    log = _get_logger()
    if init_cases:
        full_list: Dict[str, TestCaseMetadata] = dict()
        for item in init_cases:
            full_list[item.full_name] = item
    else:
        full_list = get_cases_metadata()
    if filters:
        selected: Dict[str, TestCaseData] = dict()
        force_included: Set[str] = set()
        force_excluded: Set[str] = set()
        for filter in filters:
            if filter.enable:
                selected = _apply_filter(
                    filter, selected, force_included, force_excluded, full_list
                )
            else:
                log.debug(f"skip disabled rule: {filter}")
        log.info(f"selected cases count: {len(list(selected.values()))}")
        results = list(selected.values())
    else:
        for metadata in full_list.values():
            results.append(TestCaseData(metadata))

    return results


def _match_string(
    case: Union[TestCaseData, TestCaseMetadata], pattern: Pattern[str], attr_name: str,
) -> bool:
    content = cast(str, getattr(case, attr_name))
    match = pattern.fullmatch(content)
    return match is not None


def _match_priority(
    case: Union[TestCaseData, TestCaseMetadata], pattern: Union[int, List[int]]
) -> bool:
    priority = case.priority
    is_matched: bool = False
    if isinstance(pattern, int):
        is_matched = priority == pattern
    else:
        is_matched = any(x == priority for x in pattern)
    return is_matched


def _match_tag(
    case: Union[TestCaseData, TestCaseMetadata], criteria_tags: Union[str, List[str]]
) -> bool:
    case_tags = case.tags
    is_matched: bool = False
    if isinstance(criteria_tags, str):
        is_matched = criteria_tags in case_tags
    else:
        is_matched = any(x in case_tags for x in criteria_tags)
    return is_matched


def _match_cases(
    candidates: Mapping[str, Union[TestCaseData, TestCaseMetadata]],
    patterns: List[Callable[[Union[TestCaseData, TestCaseMetadata]], bool]],
) -> Dict[str, TestCaseData]:
    changed_cases: Dict[str, TestCaseData] = dict()

    for candidate_name in candidates:
        candidate = candidates[candidate_name]
        is_matched = all(pattern(candidate) for pattern in patterns)
        if is_matched:
            if isinstance(candidate, TestCaseMetadata):
                candidate = TestCaseData(candidate)
            changed_cases[candidate_name] = candidate
    return changed_cases


def _apply_settings(
    applied_case_data: TestCaseData, case_runbook: schema.TestCase, action: str
) -> None:
    fields = [
        constants.TESTCASE_TIMES,
        constants.TESTCASE_RETRY,
        constants.TESTCASE_USE_NEW_ENVIRONMENT,
        constants.TESTCASE_IGNORE_FAILURE,
        constants.ENVIRONMENT,
    ]
    for field in fields:
        data = getattr(case_runbook, field)
        if data is not None:
            setattr(applied_case_data, field, data)

    # use default value from selector
    applied_case_data.select_action = action


def _force_check(
    name: str,
    is_force: bool,
    force_expected_set: Set[str],
    force_exclusive_set: Set[str],
    temp_force_exclusive_set: Set[str],
    case_runbook: schema.TestCase,
) -> bool:
    is_skip = False
    if name in force_exclusive_set:
        if is_force:
            raise LisaException(f"case {name} has force conflict on {case_runbook}")
        else:
            temp_force_exclusive_set.add(name)
        is_skip = True
    if not is_skip and is_force:
        force_expected_set.add(name)
    return is_skip


def _apply_filter(
    case_runbook: schema.TestCase,
    current_selected: Dict[str, TestCaseData],
    force_included: Set[str],
    force_excluded: Set[str],
    full_list: Dict[str, TestCaseMetadata],
) -> Dict[str, TestCaseData]:

    log = _get_logger()
    # initialize criterias
    patterns: List[Callable[[Union[TestCaseData, TestCaseMetadata]], bool]] = []
    criterias_runbook = case_runbook.criteria
    assert criterias_runbook, "test case criteria cannot be None"
    criterias_runbook_dict = criterias_runbook.__dict__
    for runbook_key, runbook_value in criterias_runbook_dict.items():
        if runbook_value is None:
            continue
        if runbook_key in [
            constants.NAME,
            constants.TESTCASE_CRITERIA_AREA,
            constants.TESTCASE_CRITERIA_CATEGORY,
        ]:
            pattern = cast(str, criterias_runbook_dict[runbook_key])
            expression = re.compile(pattern)
            patterns.append(
                partial(_match_string, pattern=expression, attr_name=runbook_key)
            )
        elif runbook_key == constants.TESTCASE_CRITERIA_PRIORITY:
            priority_pattern = cast(
                Union[int, List[int]], criterias_runbook_dict[runbook_key]
            )
            patterns.append(partial(_match_priority, pattern=priority_pattern))
        elif runbook_key == constants.TESTCASE_CRITERIA_TAG:
            tag_pattern = cast(
                Union[str, List[str]], criterias_runbook_dict[runbook_key]
            )
            patterns.append(partial(_match_tag, criteria_tags=tag_pattern))
        else:
            raise LisaException(f"unknown criteria key: {runbook_key}")

    # match by select Action:
    changed_cases: Dict[str, TestCaseData] = dict()
    is_force = case_runbook.select_action in [
        constants.TESTCASE_SELECT_ACTION_FORCE_INCLUDE,
        constants.TESTCASE_SELECT_ACTION_FORCE_EXCLUDE,
    ]
    is_update_setting = case_runbook.select_action in [
        constants.TESTCASE_SELECT_ACTION_NONE,
        constants.TESTCASE_SELECT_ACTION_INCLUDE,
        constants.TESTCASE_SELECT_ACTION_FORCE_INCLUDE,
    ]
    temp_force_set: Set[str] = set()
    if case_runbook.select_action is constants.TESTCASE_SELECT_ACTION_NONE:
        # Just apply settings on test cases
        changed_cases = _match_cases(current_selected, patterns)
    elif case_runbook.select_action in [
        constants.TESTCASE_SELECT_ACTION_INCLUDE,
        constants.TESTCASE_SELECT_ACTION_FORCE_INCLUDE,
    ]:
        # to include cases
        changed_cases = _match_cases(full_list, patterns)
        for name, new_case_data in changed_cases.items():
            is_skip = _force_check(
                name,
                is_force,
                force_included,
                force_excluded,
                temp_force_set,
                case_runbook,
            )
            if is_skip:
                continue

            # reuse original test cases
            case_data = current_selected.get(name, new_case_data)
            current_selected[name] = case_data
            changed_cases[name] = case_data
    elif case_runbook.select_action in [
        constants.TESTCASE_SELECT_ACTION_EXCLUDE,
        constants.TESTCASE_SELECT_ACTION_FORCE_EXCLUDE,
    ]:
        changed_cases = _match_cases(current_selected, patterns)
        for name in changed_cases:
            is_skip = _force_check(
                name,
                is_force,
                force_excluded,
                force_included,
                temp_force_set,
                case_runbook,
            )
            if is_skip:
                continue
            del current_selected[name]
    else:
        raise LisaException(f"unknown selectAction: '{case_runbook.select_action}'")

    # changed set cannot be operated in it's for loop, so update it here.
    for name in temp_force_set:
        del changed_cases[name]
    if is_update_setting:
        for case_data in changed_cases.values():
            _apply_settings(case_data, case_runbook, case_runbook.select_action)

    log.debug(
        f"applying action: [{case_runbook.select_action}] on "
        f"case [{changed_cases.keys()}], "
        f"data: {case_runbook}, loaded criteria count: {len(patterns)}"
    )

    return current_selected