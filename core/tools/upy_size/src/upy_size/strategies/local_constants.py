from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from . import Settings, SpaceSaving
from .helpers import (
    all_constants,
    get_variable_name,
    global_assignments,
    is_a_constant_number_var,
    number_of_occurrences,
)


@dataclass
class LocalConstant(SpaceSaving):
    name: str
    occurrences: int

    def saved_bytes(self) -> int:
        return 4

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.occurrences} x) (~{self.saved_bytes()} bytes)"


@dataclass
class NoConstNumber(SpaceSaving):
    name: str

    def saved_bytes(self) -> int:
        return 4

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.name} (~{self.saved_bytes()} bytes)"


def local_constants(
    file_content: str, settings: Settings = Settings()
) -> list[LocalConstant]:
    def iterator() -> Iterator[LocalConstant]:
        for const in all_constants(file_content):
            # Those with underscores are already fine
            if const.startswith("_"):
                continue

            const_regex = rf"\b{const}\b"
            occurrences = number_of_occurrences(file_content, const_regex)
            if occurrences > 1:
                yield LocalConstant(const, occurrences)

    return list(iterator())


def no_const_number(
    file_content: str, settings: Settings = Settings()
) -> list[NoConstNumber]:
    def iterator() -> Iterator[NoConstNumber]:
        for assignment in global_assignments(file_content):
            if is_a_constant_number_var(file_content, assignment):
                var_name = get_variable_name(assignment)
                yield NoConstNumber(var_name)

    return list(iterator())
