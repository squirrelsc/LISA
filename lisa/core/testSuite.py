from __future__ import annotations

import unittest
from abc import ABCMeta
from typing import TYPE_CHECKING, List

from lisa.core.action import Action
from lisa.core.actionStatus import ActionStatus
from lisa.core.testResult import TestResult, TestStatus
from lisa.util.logger import log
from lisa.util.perf_timer import create_timer

if TYPE_CHECKING:
    from lisa.core.environment import Environment
    from lisa.core.testFactory import TestSuiteData


class TestSuite(Action, unittest.TestCase, metaclass=ABCMeta):
    def __init__(
        self,
        environment: Environment,
        caseResults: List[TestResult],
        testSuiteData: TestSuiteData,
    ) -> None:
        self.environment = environment
        # test cases to run, must be a test method in this class.
        self.caseResults = caseResults
        self.testSuiteData = testSuiteData
        self.shouldStop = False

    @property
    def skipRun(self) -> bool:
        return False

    def beforeSuite(self) -> None:
        pass

    def afterSuite(self) -> None:
        pass

    def beforeCase(self) -> None:
        pass

    def afterCase(self) -> None:
        pass

    def getTypeName(self) -> str:
        return "TestSuite"

    async def start(self) -> None:
        suite_prefix = f"suite[{self.testSuiteData.name}]"
        if self.skipRun:
            log.info(f"{suite_prefix} skipped on this run")
            for case_result in self.caseResults:
                case_result.status = TestStatus.SKIPPED
            return

        timer = create_timer()
        self.beforeSuite()
        log.debug(f"{suite_prefix} beforeSuite end with {timer}")

        for case_result in self.caseResults:
            case_name = case_result.case.name
            case_prefix = f"case[{self.testSuiteData.name}.{case_name}]"
            test_method = getattr(self, case_name)

            log.info(f"{case_prefix} started")
            is_continue: bool = True
            total_timer = create_timer()

            timer = create_timer()
            try:
                self.beforeCase()
            except Exception as identifier:
                log.error(f"{case_prefix} beforeCase failed {identifier}")
                is_continue = False
            case_result.elapsed = timer.elapsed()
            log.debug(f"{case_prefix} beforeCase end with {timer}")

            if is_continue:
                timer = create_timer()
                try:
                    test_method()
                    case_result.status = TestStatus.PASSED
                except Exception as identifier:
                    log.error(f"{case_prefix} failed {identifier}")
                    case_result.status = TestStatus.FAILED
                    case_result.errorMessage = str(identifier)
                case_result.elapsed = timer.elapsed()
                log.debug(f"{case_prefix} method end with {timer}")
            else:
                case_result.status = TestStatus.SKIPPED
                case_result.errorMessage = f"{case_prefix} skipped as beforeCase failed"

            timer = create_timer()
            try:
                self.afterCase()
            except Exception as identifier:
                log.error(f"{case_prefix} afterCase failed {identifier}")
            log.debug(f"{case_prefix} afterCase end with {timer}")

            case_result.elapsed = total_timer.elapsed()
            log.info(
                f"{case_prefix} result: {case_result.status.name}, "
                f"elapsed: {total_timer}"
            )
            if self.shouldStop:
                log.info("received stop message, stop run")
                self.setStatus(ActionStatus.STOPPED)
                break

        timer = create_timer()
        self.afterSuite()
        log.debug(f"{suite_prefix} afterSuite end with {timer}")

    async def stop(self) -> None:
        self.setStatus(ActionStatus.STOPPING)
        self.shouldStop = True

    async def close(self) -> None:
        pass
