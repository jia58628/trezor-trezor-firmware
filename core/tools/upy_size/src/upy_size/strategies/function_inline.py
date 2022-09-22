from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from . import Settings, SpaceSaving
from .helpers import Function, all_toplevel_functions, number_of_occurrences


@dataclass
class InlineFunction(SpaceSaving):
    func: Function

    def saved_bytes(self) -> int:
        return 50

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.func} (~ {self.saved_bytes()} bytes)"


def function_inline(
    file_content: str, settings: Settings = Settings()
) -> list[InlineFunction]:
    def iterator() -> Iterator[InlineFunction]:
        not_to_report = settings.not_inlineable_funcs

        for toplevel_func in all_toplevel_functions(file_content):
            if toplevel_func.name in not_to_report:
                continue

            # Looking whether the function is called only once in this file
            # (it indicates it MIGHT BE a one-time helper function)
            # Negative lookbehind on dot, not to catch methods on other objects
            func_regex = rf"(?<!\.)\b{toplevel_func.name}\("
            if number_of_occurrences(file_content, func_regex) == 2:
                yield InlineFunction(toplevel_func)

    return sorted(list(iterator()), key=lambda x: x.func.line_no)
