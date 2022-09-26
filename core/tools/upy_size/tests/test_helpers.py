import ast

from ..src.upy_size.strategies.helpers import (
    all_global_symbols,
    all_toplevel_imported_symbols,
    all_toplevel_nodes,
    all_toplevel_symbol_usages,
    all_type_hint_usages,
    attr_gets_modified,
    get_func_local_attribute_lookups,
    get_function_body_code,
    get_global_attribute_lookups,
    get_node_code,
    get_used_func_import_symbols,
    get_used_func_symbols,
    is_really_a_constant,
    is_used_as_type_hint,
    is_used_outside_function,
)

CODE = """\
from micropython import const
from typing import TYPE_CHECKING
from message import MessageType2, MessageType3
from enums import Enum1 as ENUM
import trezor.crypto

HASH_LENGTH = const(32)

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


def test_all_toplevel_imported_symbols():
    toplevel_imports = all_toplevel_imported_symbols(CODE)
    assert len(toplevel_imports) == 6
    for item in (
        "MessageType2",
        "MessageType3",
        "ENUM",
        "const",
        "trezor.crypto",
        "TYPE_CHECKING",
    ):
        assert item in toplevel_imports


def test_all_global_symbols():
    global_symbols = all_global_symbols(CODE)
    assert len(global_symbols) == 9
    for item in (
        "MessageType2",
        "MessageType3",
        "ENUM",
        "HASH_LENGTH",
        "const",
        "trezor.crypto",
        "TYPE_CHECKING",
        "main",
        "abc",
    ):
        assert item in global_symbols


def test_get_node_code():
    toplevel_nodes = all_toplevel_nodes(CODE)
    assert len(toplevel_nodes) == 9

    first_node_code = get_node_code(CODE, toplevel_nodes[0])
    assert first_node_code == "from micropython import const"

    last_node_code = get_node_code(CODE, toplevel_nodes[-1])
    assert (
        last_node_code
        == """\
def abc(x: ENUM):
    return x.ABC + 3"""
    )


def test_get_function_body_code():
    toplevel_nodes = all_toplevel_nodes(CODE)
    main_func_node = toplevel_nodes[-2]
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


CODE2 = """\
from micropython import const
from messages import MessageType1, MessageType2
import messages
from enums import Enum1 as ENUM

HASH_LENGTH = const(32)

ABC = ENUM.ABC
MT = messages.MessageType3

def helper(x: str) -> str:
    send(MT(xyz=x))
    return str[::-1]

def main(msg: MessageType1) -> None:
    helper("abcd")
    helper("gdfg")
    res = helper("error")
    item = ENUM.ABC
    return MessageType2(xyz=res, abc=item, length=HASH_LENGTH)
"""


def test_get_used_func_symbols():
    toplevel_nodes = all_toplevel_nodes(CODE2)
    func_node = toplevel_nodes[-1]
    assert isinstance(func_node, ast.FunctionDef)
    symbols = get_used_func_symbols(func_node)
    assert symbols == {
        "MessageType2": 1,
        "ENUM": 1,
        "HASH_LENGTH": 1,
        "helper": 3,
        "res": 1,
        "item": 1,
    }


def test_get_used_func_import_symbols():
    toplevel_nodes = all_toplevel_nodes(CODE2)
    func_node = toplevel_nodes[-1]
    assert isinstance(func_node, ast.FunctionDef)
    symbols = get_used_func_import_symbols(CODE2, func_node)
    assert symbols == {
        "MessageType2": 1,
        "ENUM": 1,
    }


def test_toplevel_symbol_usages():
    usages = all_toplevel_symbol_usages(CODE2)
    assert usages == {
        "ENUM": 2,
        "HASH_LENGTH": 1,
        "messages": 1,
        "const": 1,
        "MessageType2": 1,
        "MessageType1": 1,
        "helper": 3,
    }


CODE3 = """\
HASH_LENGTH = 32
_ABC = "abc"
counter = 0

def main() -> None:
    global _ABC, counter
    _ABC  = "def"
    counter += HASH_LENGTH
"""


def test_is_really_a_constant():
    assert is_really_a_constant(CODE3, "HASH_LENGTH")
    assert not is_really_a_constant(CODE3, "counter")
    assert not is_really_a_constant(CODE3, "_ABC")


CODE4 = """\
import messages
import enum

def main(msg: messages.MessageType1, xyz):
    x = 54
    enum.MessageType3(xyz=x)
    send(messages.enum.store)
    y = messages.MessageType2(xyz=x)
    return messages.MessageType2(x)

def abc(x: int):
    return messages.MessageType2(x)
"""


def test_get_global_attribute_lookups():
    lookups = get_global_attribute_lookups(CODE4)
    assert lookups == {
        "messages": {
            "MessageType2": 3,
            "MessageType1": 1,
            "enum": 1,
        },
        "enum": {
            "MessageType3": 1,
        },
    }


CODE5 = """\
from typing import TYPE_CHECKING
from message import MessageType2, MessageType3, SpecialType
from enums import Enum1, Enum2
import trezor.crypto

if TYPE_CHECKING:
    from message import MessageType1

def main(msg: MessageType1[bytes], xyz) -> list[MessageType2]:
    x = 54
    abc: SpecialType[Enum2.ABC] = SpecialType(xyz=x)
    MessageType3(xyz=x)
    res: MessageType2 = MessageType2(xyz=x)
    res2: list[MessageType2] = [MessageType2(xyz=x)]
    return res

def abc(x: Enum1, y: messages.MessageType66):
    return x.ABC + 3
"""


def test_all_type_hint_usages():
    usages = all_type_hint_usages(CODE5)
    assert usages == {
        "Enum1": 1,
        "MessageType1": 1,
        "MessageType2": 3,
        "messages": 1,
        "SpecialType[Enum2.ABC]": 1,
    }


def test_is_used_as_type_hint():
    assert is_used_as_type_hint(CODE5, "Enum1")
    assert is_used_as_type_hint(CODE5, "Enum2")
    assert is_used_as_type_hint(CODE5, "SpecialType")
    assert not is_used_as_type_hint(CODE5, "MessageType3")


CODE6 = """\
import messages
from messages import MyMessage, MyMsg2

def my_func(ctx, msg: MyMsg2) -> messages.MyMessage:
    # comment not to take msg.abc
    new_list = []
    assert msg.abc is not None
    msg.abc = 3
    new_list.append(4)
    new_list.append(abc(msg.abc))
    x = msg.abc.xyz
    y = msg.xyz
    return messages.MyMessage(abc=msg.abc)
"""


def test_get_func_local_attribute_lookups():
    toplevel_nodes = all_toplevel_nodes(CODE6)
    func_node = toplevel_nodes[-1]
    assert isinstance(func_node, ast.FunctionDef)
    lookups = get_func_local_attribute_lookups(CODE6, func_node)
    assert lookups == {
        "msg": {
            "abc": 5,
            "xyz": 1,
        },
        "new_list": {
            "append": 2,
        },
    }


def test_attr_gets_modified():
    toplevel_nodes = all_toplevel_nodes(CODE6)
    func_node = toplevel_nodes[-1]
    assert isinstance(func_node, ast.FunctionDef)
    assert attr_gets_modified(func_node, "msg", "abc") is True
    assert attr_gets_modified(func_node, "msg", "xyz") is False


CODE7 = """\
import messages
HASH_LENGTH = 32
_LOCAL_CONST = 42
counter = 0

TMP = _LOCAL_CONST + 1

@decorator(counter)
def main(msg: messages.ABC) -> None:
    counter += TMP
"""


def test_is_used_outside_function():
    assert is_used_outside_function(CODE7, "_LOCAL_CONST")
    assert not is_used_outside_function(CODE7, "counter")
    assert not is_used_outside_function(CODE7, "messages")
    assert not is_used_outside_function(CODE7, "TMP")
    assert not is_used_outside_function(CODE7, "HASH_LENGTH")
