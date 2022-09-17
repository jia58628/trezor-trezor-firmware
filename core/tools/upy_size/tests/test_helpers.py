import ast

from ..src.upy_size.strategies.helpers import (
    get_all_global_symbols,
    get_all_nodes,
    get_all_toplevel_imported_symbols,
    get_all_toplevel_nodes,
    get_function_body_code,
    get_node_code,
)

CODE = """\
from typing import TYPE_CHECKING
from message import MessageType2, MessageType3
from enums import Enum1 as ENUM
import trezor.crypto

if TYPE_CHECKING:
    from message import MessageType1

def main(msg: MessageType1, xyz):
    x = 54  # some comment here
    # other comment
    MessageType3(xyz=x)

    MessageType2(
        xyz=x
    )

    return MessageType2(x)

def abc(x: ENUM):
    return x.ABC + 3
"""


def test_get_all_toplevel_imported_symbols():
    all_toplevel_imports = get_all_toplevel_imported_symbols(CODE)
    assert len(all_toplevel_imports) == 5
    for item in (
        "MessageType2",
        "MessageType3",
        "ENUM",
        "trezor.crypto",
        "TYPE_CHECKING",
    ):
        assert item in all_toplevel_imports


def test_get_all_global_symbols():
    all_global_symbols = get_all_global_symbols(CODE)
    assert len(all_global_symbols) == 7
    for item in (
        "MessageType2",
        "MessageType3",
        "ENUM",
        "trezor.crypto",
        "TYPE_CHECKING",
        "main",
        "abc",
    ):
        assert item in all_global_symbols


def test_get_node_code():
    all_toplevel_nodes = get_all_toplevel_nodes(CODE)
    assert len(all_toplevel_nodes) == 7

    first_node_code = get_node_code(CODE, all_toplevel_nodes[0])
    assert first_node_code == "from typing import TYPE_CHECKING"

    last_node_code = get_node_code(CODE, all_toplevel_nodes[-1])
    assert (
        last_node_code
        == """\
def abc(x: ENUM):
    return x.ABC + 3"""
    )


def test_get_function_body_code():
    all_toplevel_nodes = get_all_toplevel_nodes(CODE)
    main_func_node = all_toplevel_nodes[-2]
    assert isinstance(main_func_node, ast.FunctionDef)
    body_code = get_function_body_code(CODE, main_func_node)
    assert (
        body_code
        == """\
x = 54
MessageType3(xyz=x)
MessageType2(
        xyz=x
    )
return MessageType2(x)"""
    )
