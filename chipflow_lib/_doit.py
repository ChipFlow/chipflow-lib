# -*- coding: utf-8 *-*
# SPDX-License-Identifier: BSD-2-Clause

from pathlib import Path
from typing import List, Tuple, Any, Callable, TypeVar, Generic
from typing_extensions import TypedDict, NotRequired

T=TypeVar('T')
class TaskParams(TypedDict, Generic[T]):
    name: str
    default: T
    short: NotRequired[str]
    long: NotRequired[str]
    type: NotRequired[Callable[[T], str]]
    choices: NotRequired[List[Tuple[str, str]]]
    help: NotRequired[str]
    inverse: NotRequired[str]


