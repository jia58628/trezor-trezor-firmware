from micropython import const
from typing import TYPE_CHECKING

from apps.monero.xmr.serialize.message_types import ContainerType, MessageType
from apps.monero.xmr.serialize_messages.base import ECKey

if TYPE_CHECKING:
    from ..serialize.base_types import XmrType


class _KeyV(ContainerType):
    FIX_SIZE = const(0)
    ELEM_TYPE: XmrType[bytes] = ECKey


class Bulletproof(MessageType):
    __slots__ = ("A", "S", "T1", "T2", "taux", "mu", "L", "R", "a", "b", "t", "V")

    @classmethod
    def f_specs(cls) -> tuple:
        _ECKey = ECKey  # local_cache_global
        return (
            ("A", _ECKey),
            ("S", _ECKey),
            ("T1", _ECKey),
            ("T2", _ECKey),
            ("taux", _ECKey),
            ("mu", _ECKey),
            ("L", _KeyV),
            ("R", _KeyV),
            ("a", _ECKey),
            ("b", _ECKey),
            ("t", _ECKey),
        )


class BulletproofPlus(MessageType):
    __slots__ = ("A", "A1", "B", "r1", "s1", "d1", "V", "L", "R")

    @classmethod
    def f_specs(cls) -> tuple:
        _ECKey = ECKey  # local_cache_global
        return (
            ("A", _ECKey),
            ("A1", _ECKey),
            ("B", _ECKey),
            ("r1", _ECKey),
            ("s1", _ECKey),
            ("d1", _ECKey),
            ("L", _KeyV),
            ("R", _KeyV),
        )
