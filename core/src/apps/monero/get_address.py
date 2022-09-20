from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import MoneroGetAddress, MoneroAddress
    from trezor.wire import Context

    from apps.common.keychain import Keychain


@auto_keychain(__name__)
async def get_address(
    ctx: Context, msg: MoneroGetAddress, keychain: Keychain
) -> MoneroAddress:
    from trezor import wire
    from trezor.messages import MoneroAddress
    from trezor.ui.layouts import show_address

    from apps.common import paths
    from apps.monero import misc
    from apps.monero.xmr import addresses, crypto_helpers, monero
    from apps.monero.xmr.networks import net_version

    msg_account = msg.account  # cache
    msg_minor = msg.minor  # cache
    msg_payment_id = msg.payment_id  # cache

    await paths.validate_path(ctx, keychain, msg.address_n)

    creds = misc.get_creds(keychain, msg.address_n, msg.network_type)
    addr = creds.address

    have_subaddress = (
        msg_account is not None
        and msg_minor is not None
        and (msg_account, msg_minor) != (0, 0)
    )
    have_payment_id = msg_payment_id is not None

    if (msg_account is None) != (msg_minor is None):
        raise wire.ProcessError("Invalid subaddress indexes")

    if have_payment_id and have_subaddress:
        raise wire.DataError("Subaddress cannot be integrated")

    if have_payment_id:
        assert msg_payment_id is not None
        if len(msg_payment_id) != 8:
            raise ValueError("Invalid payment ID length")
        addr = addresses.encode_addr(
            net_version(msg.network_type, False, True),
            crypto_helpers.encodepoint(creds.spend_key_public),
            crypto_helpers.encodepoint(creds.view_key_public),
            msg_payment_id,
        )

    if have_subaddress:
        assert msg_account is not None
        assert msg_minor is not None

        pub_spend, pub_view = monero.generate_sub_address_keys(
            creds.view_key_private, creds.spend_key_public, msg_account, msg_minor
        )

        addr = addresses.encode_addr(
            net_version(msg.network_type, True, False),
            crypto_helpers.encodepoint(pub_spend),
            crypto_helpers.encodepoint(pub_view),
        )

    if msg.show_display:
        title = paths.address_n_to_str(msg.address_n)
        await show_address(
            ctx,
            addr,
            address_qr="monero:" + addr,
            title=title,
        )

    return MoneroAddress(address=addr.encode())
