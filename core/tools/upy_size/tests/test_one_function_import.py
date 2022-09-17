from ..src.upy_size.strategies.import_one_function import one_function_import

CODE = """\
from micropython import const
from typing import TYPE_CHECKING
from message import MessageType2, MessageType3, MyMSG
import ENUM, abc
from trezor import ui
import decorators

nine = const(9)

def main(msg: MessageType1, xyz: MyMSG.abc):
    x = 54
    MessageType3(
        xyz=x
    )
    return MessageType2(x)

@decorators.decorator("hoho")
def abc(x: int):
    decorators.hello()
    send(MyMSG)
    return MessageType2(x)

class ABC(ui.Component, abc.Layout):
    abc = ENUM.abc

    def _init__(self, x: int):
        self.x = x

def trial():
    ui.show("hello")
    return ENUM.xyz
"""


def test_one_function_import():
    res = one_function_import(CODE)
    assert len(res) == 2

    assert res[0].symbol == "MessageType3"
    assert res[0].func.name == "main"
    assert res[0].used_as_type_hint == False
    assert res[0].saved_bytes() == 4

    assert res[1].symbol == "MyMSG"
    assert res[1].func.name == "abc"
    assert res[1].used_as_type_hint == True
    assert res[1].saved_bytes() == 4
