from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from . import Settings, SpaceSaving
from .helpers import (
    all_toplevel_imported_symbols,
    all_toplevel_symbol_usages,
    all_type_hint_usages,
)


@dataclass
class TypeOnlyImport(SpaceSaving):
    symbol: str

    def saved_bytes(self) -> int:
        return 7

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.symbol} (~{self.saved_bytes()} bytes)"


def type_only_import(
    file_content: str, settings: Settings = Settings()
) -> list[TypeOnlyImport]:
    def iterator() -> Iterator[TypeOnlyImport]:
        symbol_usages = all_toplevel_symbol_usages(file_content)
        type_hints = all_type_hint_usages(file_content)

        for symbol in all_toplevel_imported_symbols(file_content):
            # Reporting when the usage as a type-hint equal to the
            # overall usage as a symbol
            if symbol in type_hints and symbol in symbol_usages:
                if type_hints[symbol] == symbol_usages[symbol]:
                    yield TypeOnlyImport(symbol)

    return list(iterator())
