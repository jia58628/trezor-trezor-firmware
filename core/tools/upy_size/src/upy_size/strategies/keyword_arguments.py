from __future__ import annotations

import ast
from dataclasses import dataclass

from . import Settings, SpaceSaving
from .helpers import get_all_nodes, get_function_name


@dataclass
class Kwarg(SpaceSaving):
    name: str
    amount: int
    line_no: int

    def saved_bytes(self) -> int:
        return self.amount * 3

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.line_no} :: {self.name} ({self.amount}x) ({self.saved_bytes()} bytes)"


def keyword_arguments(
    file_content: str, settings: Settings = Settings()
) -> list[Kwarg]:
    used_kwargs: list[Kwarg] = []

    for node in get_all_nodes(file_content):
        if isinstance(node, ast.Call):
            if node.keywords:
                func_name = get_function_name(node)
                used_kwargs.append(
                    Kwarg(
                        name=func_name, amount=len(node.keywords), line_no=node.lineno
                    )
                )

    return sorted(used_kwargs, key=lambda x: x.line_no)
