from ..src.upy_size.strategies.import_one_function import one_function_import

CODE = """\
from micropython import const
from typing import TYPE_CHECKING
from message import MessageType2, OnlyInOneFunc, InFuncAndTypeHint
import ENUM, abc
from trezor import ui
import decorators

nine = const(9)

def main(msg: MessageType1, xyz: InFuncAndTypeHint.abc):
    x = 54
    OnlyInOneFunc(
        xyz=x
    )
    trial()
    return MessageType2(x)

@decorators.decorator("hoho")
def abc(x: int):
    decorators.hello()
    receive(InFuncAndTypeHint)
    send(InFuncAndTypeHint)
    return MessageType2(x)

class ABC(ui.Component, abc.Layout, Generic[K, V]):
    abc = ENUM.abc

    def _init__(self, x: int):
        self.x = const(x)

def trial():
    ui.show("hello")
    return ENUM.xyz
"""


def test_one_function_import():
    res = one_function_import(CODE)
    assert len(res) == 2

    assert res[0].symbol == "OnlyInOneFunc"
    assert res[0].func.name == "main"
    assert res[0].used_as_type_hint is False
    assert res[0].usages_in_func == 1
    assert res[0].saved_bytes() == 4

    assert res[1].symbol == "InFuncAndTypeHint"
    assert res[1].func.name == "abc"
    assert res[1].used_as_type_hint is True
    assert res[1].usages_in_func == 2
    assert res[1].saved_bytes() == 6
