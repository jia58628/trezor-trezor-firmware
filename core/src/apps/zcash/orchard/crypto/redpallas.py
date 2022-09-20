# https://zips.z.cash/protocol/protocol.pdf#concretereddsa

from typing import TYPE_CHECKING

from trezor.crypto.hashlib import blake2b
from trezor.crypto.pallas import to_scalar

from .generators import SPENDING_KEY_BASE

if TYPE_CHECKING:
    from trezor.crypto.pallas import Scalar

    pass


def randomize(sk: Scalar, randomizer: Scalar) -> Scalar:
    return sk + randomizer


def H_star(x: bytes) -> Scalar:
    digest = blake2b(personal=b"Zcash_RedPallasH", data=x).digest()
    return to_scalar(digest)


def sign_spend_auth(sk: Scalar, message: bytes) -> bytes:
    # According to the Redpallas specification, `T` should be uniformly random
    # sequence of 32 bytes. Since Trezor output must be deterministic (to prevent
    # secret leakage caused by mallicious hw randomness generator), we set
    T = sk.to_bytes()
    # We use the same technique for BIP-340 Bitcoin signatures.
    # The only differences between these two schemes are:
    # 1. in BIP-340 we set `T = sk xor some_constant`
    # 2. BIP-340 uses secp256k1 curve
    # 3. BIP-340 additionally requires y coordinate of `R` to be non negative
    # According to our security analysis, setting `T = bytes(sk)` does harm
    # security the RedPallas signature scheme. Also notice that this change does
    # not require changes in RedPallas verification algorithm.

    vk: bytes = (sk * SPENDING_KEY_BASE).to_bytes()
    r: Scalar = H_star(T + vk + message)
    R: bytes = (r * SPENDING_KEY_BASE).to_bytes()
    e: Scalar = H_star(R + vk + message)
    S: bytes = (r + e * sk).to_bytes()
    return R + S
