from __future__ import annotations

from dataclasses import dataclass

from . import Settings, SpaceSaving
from .helpers import (
    CacheCandidate,
    Function,
    get_all_functions,
    get_cache_candidates,
    number_of_occurrences,
)


@dataclass
class LocalCache(SpaceSaving):
    cache_candidate: CacheCandidate
    func: Function
    gets_mutated: bool

    def saved_bytes(self) -> int:
        return self.cache_candidate.amount * 2

    def __repr__(self) -> str:  # pragma: no cover
        mutated_msg = " (WARNING: gets mutated)" if self.gets_mutated else ""
        return f"{self.func} - {self.cache_candidate} (~{self.saved_bytes()} bytes){mutated_msg}"


def local_cache(
    file_content: str, settings: Settings = Settings(), low_threshold: int = 4
) -> list[LocalCache]:
    local_cache_possibilities: list[LocalCache] = []

    for func in get_all_functions(file_content):
        something_dot_something = r"\b\w+\.\w+\b"
        cache_candidates = get_cache_candidates(
            func.body_code, something_dot_something, low_threshold=low_threshold
        )
        if cache_candidates:
            for candidate in cache_candidates:
                # In case it gets reassigned, letting the user know
                # (it can still be partially cached after the last assignment)
                mutation = candidate.cache_string + r"\s(=|\+=|-=)\s"
                gets_mutated = bool(number_of_occurrences(func.body_code, mutation))

                local_cache_possibilities.append(
                    LocalCache(
                        func=func,
                        cache_candidate=candidate,
                        gets_mutated=gets_mutated,
                    )
                )

    return sorted(local_cache_possibilities, key=lambda x: x.func.line_no)
