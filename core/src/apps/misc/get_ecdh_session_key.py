from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import GetECDHSessionKey, ECDHSessionKey
    from trezor.wire import Context

# This module implements the SLIP-0017 Elliptic Curve Diffie-Hellman algorithm, using a
# deterministic hierarchy, see https://github.com/satoshilabs/slips/blob/master/slip-0017.md.


async def get_ecdh_session_key(ctx: Context, msg: GetECDHSessionKey) -> ECDHSessionKey:
    from ustruct import pack, unpack
    from trezor.crypto.hashlib import sha256
    from trezor.ui.layouts import confirm_address
    from .sign_identity import serialize_identity_without_proto, serialize_identity
    from trezor import ui
    from trezor.wire import DataError
    from trezor.messages import ECDHSessionKey
    from apps.common.keychain import get_keychain
    from apps.common.paths import HARDENED, AlwaysMatchingSchema

    msg_ecdsa_curve_name = msg.ecdsa_curve_name or "secp256k1"  # local_cache_attribute
    msg_identity = msg.identity  # local_cache_attribute
    msg_peer_public_key = msg.peer_public_key  # local_cache_attribute

    keychain = await get_keychain(ctx, msg_ecdsa_curve_name, [AlwaysMatchingSchema])
    identity = serialize_identity(msg_identity)

    # require_confirm_ecdh_session_key
    proto = msg_identity.proto.upper() if msg_identity.proto else "identity"
    await confirm_address(
        ctx,
        f"Decrypt {proto}",
        serialize_identity_without_proto(msg_identity),
        None,
        icon=ui.ICON_DEFAULT,
        icon_color=ui.ORANGE_ICON,
    )
    # END require_confirm_ecdh_session_key

    # get_ecdh_path
    index = msg.identity.index or 0
    identity_hash = sha256(pack("<I", index) + identity.encode()).digest()
    address_n = [HARDENED | x for x in (17,) + unpack("<IIII", identity_hash[:16])]
    # END get_ecdh_path

    node = keychain.derive(address_n)

    # ecdh
    if msg_ecdsa_curve_name == "secp256k1":
        from trezor.crypto.curve import secp256k1

        session_key = secp256k1.multiply(node.private_key(), msg_peer_public_key)
    elif msg_ecdsa_curve_name == "nist256p1":
        from trezor.crypto.curve import nist256p1

        session_key = nist256p1.multiply(node.private_key(), msg_peer_public_key)
    elif msg_ecdsa_curve_name == "curve25519":
        from trezor.crypto.curve import curve25519

        if msg_peer_public_key[0] != 0x40:
            raise DataError("Curve25519 public key should start with 0x40")
        session_key = b"\x04" + curve25519.multiply(
            node.private_key(), msg_peer_public_key[1:]
        )
    else:
        raise DataError("Unsupported curve for ECDH: " + msg_ecdsa_curve_name)
    # END ecdh

    return ECDHSessionKey(session_key=session_key, public_key=node.public_key())
