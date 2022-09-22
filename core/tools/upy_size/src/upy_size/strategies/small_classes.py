from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterator

from . import Settings, SpaceSaving
from .helpers import get_all_toplevel_nodes, get_method_names


@dataclass
class InitOnlyClass(SpaceSaving):
    name: str
    line_no: int

    def saved_bytes(self) -> int:
        # it depends...
        return 0

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.line_no} :: {self.name}"


def init_only_classes(
    file_content: str, settings: Settings = Settings()
) -> list[InitOnlyClass]:
    def iterator() -> Iterator[InitOnlyClass]:
        for node in get_all_toplevel_nodes(file_content):
            if isinstance(node, ast.ClassDef):
                if get_method_names(node) == ["__init__"]:
                    yield InitOnlyClass(name=node.name, line_no=node.lineno)

    return sorted(list(iterator()), key=lambda x: x.line_no)
