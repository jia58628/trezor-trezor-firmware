from __future__ import annotations

from dataclasses import dataclass

from . import Settings, SpaceSaving
from .helpers import get_all_toplevel_imported_symbols, number_of_occurrences


@dataclass
class TypeOnlyImport(SpaceSaving):
    symbol: str

    def saved_bytes(self) -> int:
        return 7

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.symbol} (~{self.saved_bytes()} bytes)"


def import_unused(
    file_content: str, settings: Settings = Settings()
) -> list[TypeOnlyImport]:
    unused_imports: list[TypeOnlyImport] = []

    for symbol in get_all_toplevel_imported_symbols(file_content):
        regex = rf"\b{symbol}\b"
        # TODO: also account for other usages like list[MyType]
        type_regex = rf": {symbol}\b"
        occurrences = number_of_occurrences(file_content, regex)
        if occurrences == 1:
            continue  # reexported
        type_occurrences = number_of_occurrences(file_content, type_regex)

        if type_occurrences == occurrences - 1:
            unused_imports.append(TypeOnlyImport(symbol))

    return unused_imports
