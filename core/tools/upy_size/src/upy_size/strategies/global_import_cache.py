from __future__ import annotations

from dataclasses import dataclass

from . import Settings, SpaceSaving
from .helpers import (
    CacheCandidate,
    get_all_toplevel_imported_symbols,
    get_cache_candidates,
)


@dataclass
class GlobalImportCache(SpaceSaving):
    cache_candidate: CacheCandidate

    def saved_bytes(self) -> int:
        return self.cache_candidate.amount

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.cache_candidate} (~{self.saved_bytes()} bytes)"


def global_import_cache(
    file_content: str, settings: Settings = Settings(), low_threshold: int = 3
) -> list[GlobalImportCache]:
    imports_to_cache: list[GlobalImportCache] = []

    for symbol in get_all_toplevel_imported_symbols(file_content):
        symbol_dot_regex = rf"\b{symbol}\.\w+\b"
        cache_candidates = get_cache_candidates(
            file_content, symbol_dot_regex, low_threshold=low_threshold
        )

        if cache_candidates:
            for candidate in cache_candidates:
                imports_to_cache.append(GlobalImportCache(cache_candidate=candidate))

    return imports_to_cache
