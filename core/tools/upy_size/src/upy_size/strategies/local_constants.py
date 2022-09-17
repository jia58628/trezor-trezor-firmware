from __future__ import annotations

from dataclasses import dataclass

from . import Settings, SpaceSaving
from .helpers import (
    get_all_constants,
    get_all_toplevel_imported_symbols,
    get_global_assignments,
    get_variable_name,
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
    local_only_constants: list[LocalConstant] = []

    all_consts = get_all_constants(file_content)
    for const in all_consts:
        # Those with underscores are already fine
        if const.startswith("_"):
            continue

        const_regex = rf"\b{const}\b"
        occurrences = number_of_occurrences(file_content, const_regex)
        if occurrences > 1:
            local_only_constants.append(LocalConstant(const, occurrences))

    return local_only_constants


def no_const_number(
    file_content: str, settings: Settings = Settings()
) -> list[NoConstNumber]:
    no_const_numbers: list[NoConstNumber] = []

    for assignment in get_global_assignments(file_content):
        if is_a_constant_number_var(file_content, assignment):
            var_name = get_variable_name(assignment)
            no_const_numbers.append(NoConstNumber(var_name))

    # When `const` is not already imported, it is not worth
    # importing it just for one symbol
    imported_symbols = get_all_toplevel_imported_symbols(file_content)
    if not "const" in imported_symbols and len(no_const_numbers) < 2:
        return []

    return no_const_numbers
