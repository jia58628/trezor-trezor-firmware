from ..src.upy_size.strategies.import_unused import import_unused

CODE = """\
from typing import TYPE_CHECKING
from message import MessageType2, MessageType3
from enums import Enum1
import trezor.crypto

if TYPE_CHECKING:
    from message import MessageType1

def main(msg: MessageType1, xyz):
    x = 54
    MessageType3(xyz=x)
    return MessageType2(x)

def abc(x: Enum1):
    return x.ABC + 3
"""


def test_unused_imports():
    res = import_unused(CODE)
    assert len(res) == 1
    assert res[0].symbol == "Enum1"
    assert res[0].saved_bytes() == 7
