from __future__ import annotations

from dataclasses import dataclass

from . import Settings, SpaceSaving
from .helpers import (
    CacheCandidate,
    Function,
    get_all_functions,
    get_all_global_symbols,
    get_cache_candidates,
)


@dataclass
class LocalCacheGlobal(SpaceSaving):
    cache_candidate: CacheCandidate
    func: Function

    def saved_bytes(self) -> int:
        return self.cache_candidate.amount + 1

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.func} - {self.cache_candidate} (~{self.saved_bytes()} bytes)"


def local_cache_global(
    file_content: str, settings: Settings = Settings(), low_threshold: int = 5
) -> list[LocalCacheGlobal]:
    cacheable_global_symbols: list[LocalCacheGlobal] = []

    all_functions = get_all_functions(file_content)

    for symbol in get_all_global_symbols(file_content):
        symbol_regex = rf"\b{symbol}\b"

        for func in all_functions:
            cache_candidates = get_cache_candidates(
                func.body_code, symbol_regex, low_threshold=low_threshold
            )

            if cache_candidates:
                for candidate in cache_candidates:
                    cacheable_global_symbols.append(
                        LocalCacheGlobal(
                            func=func,
                            cache_candidate=candidate,
                        )
                    )

    return sorted(cacheable_global_symbols, key=lambda x: x.func.line_no)
