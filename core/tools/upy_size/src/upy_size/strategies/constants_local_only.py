from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from . import Settings, SpaceSaving
from .helpers import all_constants, all_toplevel_symbol_usages


@dataclass
class LocalConstant(SpaceSaving):
    name: str
    occurrences: int

    def saved_bytes(self) -> int:
        return 4

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.occurrences} x) (~{self.saved_bytes()} bytes)"


def local_only_constants(
    file_content: str, settings: Settings = Settings()
) -> list[LocalConstant]:
    def iterator() -> Iterator[LocalConstant]:
        usages = all_toplevel_symbol_usages(file_content)

        for const in all_constants(file_content):
            # Those with underscores are already fine
            if const.startswith("_"):
                continue

            if const in usages:
                yield LocalConstant(const, usages[const])

    return list(iterator())
