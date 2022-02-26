# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, ClassVar, Optional, TypeVar, Union, cast

from dataclasses_json import Undefined, dataclass_json

FuncT = TypeVar("FuncT", bound=Callable[..., Any])


def dataschema(
    undefined: Optional[Union[str, Undefined]] = None, *args: Any, **kwargs: Any
) -> Any:
    def wrapper(cls: Any) -> Any:
        @wraps(cls)
        def inner(cls: Any) -> Any:

            dataclass(
                dataclass_json(
                    cls,
                    undefined=undefined,
                    *args,
                    **kwargs,
                ),
                *args,
                **kwargs,
            )

        return inner

    return wrapper
