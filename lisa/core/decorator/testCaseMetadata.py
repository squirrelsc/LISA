from typing import Callable, Optional

from lisa.core.testFactory import TestFactory


class TestCaseMetadata:
    def __init__(self, description: str, priority: Optional[int]) -> None:
        self.priority = priority
        self.description = description

    def __call__(self, func: Callable[..., None]) -> Callable[..., None]:
        factory = TestFactory()
        factory.addTestMethod(func, self.description, self.priority)

        def wrapper(*args: object) -> None:
            func(*args)

        return wrapper
