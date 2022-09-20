from typing import TYPE_CHECKING

from trezor.crypto.hashlib import blake2b
from trezor.crypto.pallas import to_base, to_scalar

from .crypto.address import Address
from .crypto.keys import sk_to_ask

if TYPE_CHECKING:
    from typing import Any
    from trezor.crypto.pallas import Scalar, Fp


class BundleShieldingRng:
    def __init__(self, seed: bytes) -> None:
        self.seed = seed

    def for_action(self, i: int) -> "ActionShieldingRng":
        h = blake2b(personal=b"TrezorActionSeed", outlen=32)
        h.update(self.seed)
        h.update(i.to_bytes(4, "little"))
        return ActionShieldingRng(h.digest())

    def _shuffle(self, x: list[Any], personal: bytes) -> None:
        pass  # Suite shuffles inputs

    def shuffle_outputs(self, outputs: list[int | None]) -> None:
        self._shuffle(outputs, personal=b"TrezorSpendsPerm")

    def shuffle_inputs(self, inputs: list[int | None]) -> None:
        self._shuffle(inputs, personal=b"TrezorInputsPerm")


class ActionShieldingRng:
    def __init__(self, seed: bytes) -> None:
        self.seed = seed

    def random(self, dst: bytes, outlen: int = 64) -> bytes:
        h = blake2b(personal=b"TrezorExpandSeed", outlen=outlen)
        h.update(self.seed)
        h.update(dst)
        return h.digest()

    def alpha(self) -> Scalar:
        return to_scalar(self.random(b"alpha"))

    def rcv(self) -> Scalar:
        return to_scalar(self.random(b"rcv"))

    def recipient(self) -> Address:
        d = self.random(b"d", 11)
        ivk = to_scalar(self.random(b"ivk"))
        return Address.from_ivk(d, ivk)

    def ock(self) -> bytes:
        return self.random(b"ock", 32)

    def op(self) -> bytes:
        return self.random(b"op", 64)

    def rseed_old(self) -> bytes:
        return self.random(b"rseed_old", 32)

    def rseed_new(self) -> bytes:
        return self.random(b"rseed_new", 32)

    def dummy_sk(self) -> bytes:
        return self.random(b"dummy_sk", 32)

    def dummy_ask(self) -> Scalar:
        return sk_to_ask(self.dummy_sk())

    def rho(self) -> Fp:
        return to_base(self.random(b"rho"))
