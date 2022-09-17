from typing import TYPE_CHECKING

from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERNS, SLIP44_ID

if TYPE_CHECKING:
    from apps.common.keychain import Keychain
    from trezor.wire import Context
    from trezor.messages import NEMGetAddress, NEMAddress


@with_slip44_keychain(*PATTERNS, slip44_id=SLIP44_ID, curve=CURVE)
async def get_address(
    ctx: Context, msg: NEMGetAddress, keychain: Keychain
) -> NEMAddress:
    from trezor.messages import NEMAddress
    from trezor.ui.layouts import show_address
    from apps.common.paths import address_n_to_str, validate_path
    from .helpers import check_path, get_network_str
    from .validators import validate_network

    msg_address_n = msg.address_n  # cache
    msg_network = msg.network  # cache

    validate_network(msg_network)
    await validate_path(
        ctx, keychain, msg_address_n, check_path(msg_address_n, msg_network)
    )

    node = keychain.derive(msg_address_n)
    address = node.nem_address(msg_network)

    if msg.show_display:
        title = address_n_to_str(msg_address_n)
        await show_address(
            ctx,
            address,
            case_sensitive=False,
            title=title,
            network=get_network_str(msg_network),
        )

    return NEMAddress(address=address)
