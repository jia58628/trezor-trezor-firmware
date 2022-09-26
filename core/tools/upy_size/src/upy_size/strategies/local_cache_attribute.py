from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from . import Settings, SpaceSaving
from .helpers import (
    CacheCandidate,
    Function,
    all_functions,
    attr_gets_modified,
    get_func_local_attribute_lookups,
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


def local_cache_attribute(
    file_content: str, settings: Settings = Settings(), threshold: int = 4
) -> list[LocalCache]:
    def iterator() -> Iterator[LocalCache]:
        for func in all_functions(file_content):
            attr_lookups = get_func_local_attribute_lookups(file_content, func.node)
            for obj_name, attrs in attr_lookups.items():
                for attr_name, amount in attrs.items():
                    if amount >= threshold:
                        yield LocalCache(
                            cache_candidate=CacheCandidate(
                                f"{obj_name}.{attr_name}", amount
                            ),
                            func=func,
                            gets_mutated=attr_gets_modified(
                                func.node, obj_name, attr_name
                            ),
                        )

    return sorted(list(iterator()), key=lambda x: x.func.line_no)
