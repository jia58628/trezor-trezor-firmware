from typing import TYPE_CHECKING

from trezor import protobuf
from trezor.crypto import hmac
from trezor.wire import ProcessError

if TYPE_CHECKING:
    from trezor.protobuf import MessageType

    pass

EMPTY = 32 * b"\x00"


def xor(x: bytes, y: bytes) -> bytes:
    return bytes([a ^ b for a, b in zip(x, y)])


class MessageAccumulator:
    def __init__(self, secret: bytes) -> None:
        self.key = secret
        self.state = EMPTY

    def xor_message(self, msg: MessageType, index: int) -> None:
        mac = hmac(hmac.SHA256, self.key)
        assert msg.MESSAGE_WIRE_TYPE is not None
        mac.update(msg.MESSAGE_WIRE_TYPE.to_bytes(2, "big"))
        mac.update(index.to_bytes(4, "little"))
        mac.update(protobuf.dump_message_buffer(msg))
        self.state = xor(self.state, mac.digest())

    def check(self) -> None:
        if self.state != EMPTY:
            raise ProcessError("Orchard input or output changed")
