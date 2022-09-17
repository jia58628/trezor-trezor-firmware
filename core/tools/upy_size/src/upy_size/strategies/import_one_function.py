from __future__ import annotations

from dataclasses import dataclass

from . import Settings, SpaceSaving
from .helpers import (
    Function,
    get_all_functions,
    get_all_toplevel_imported_symbols,
    is_used_as_type_hint,
    is_used_outside_function,
    number_of_occurrences,
)


@dataclass
class OneFunctionImport(SpaceSaving):
    func: Function
    symbol: str
    usages_in_func: int
    used_as_type_hint: bool = False

    def saved_bytes(self) -> int:
        return 4 + (self.usages_in_func - 1) * 2

    def __repr__(self) -> str:  # pragma: no cover
        type_hint_msg = (
            " (WARNING: used as type-hint)" if self.used_as_type_hint else ""
        )
        return (
            f"{self.func} - {self.symbol} (~{self.saved_bytes()} bytes){type_hint_msg}"
        )


def one_function_import(
    file_content: str, settings: Settings = Settings()
) -> list[OneFunctionImport]:
    one_function_imports: list[OneFunctionImport] = []

    all_functions = get_all_functions(file_content)

    for symbol in get_all_toplevel_imported_symbols(file_content):
        if is_used_outside_function(file_content, symbol):
            continue

        used = 0

        symbol_regex = rf"\b{symbol}\b"
        used_func: Function | None = None
        usages_in_func: int | None = None
        for func in all_functions:
            occurrences = number_of_occurrences(func.body_code, symbol_regex)
            if occurrences > 0:
                used += 1
                used_func = func
                usages_in_func = occurrences

        # Used only in one function, means we can import it just there
        if used == 1:
            assert used_func is not None
            assert usages_in_func is not None
            one_function_imports.append(
                OneFunctionImport(
                    func=used_func,
                    symbol=symbol,
                    usages_in_func=usages_in_func,
                    used_as_type_hint=is_used_as_type_hint(file_content, symbol),
                )
            )

    return sorted(one_function_imports, key=lambda x: x.func.line_no)
