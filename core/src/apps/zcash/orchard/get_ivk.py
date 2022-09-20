from typing import TYPE_CHECKING

from trezor.messages import ZcashGetIncomingViewingKey, ZcashIncomingViewingKey

from .. import layout
from .keychain import with_keychain

if TYPE_CHECKING:
    from trezor.wire import Context
    from .keychain import OrchardKeychain


@with_keychain
async def get_ivk(
    ctx: Context, msg: ZcashGetIncomingViewingKey, keychain: OrchardKeychain
) -> ZcashIncomingViewingKey:
    await layout.require_confirm_export_ivk(ctx)
    fvk = keychain.derive(msg.z_address_n).full_viewing_key()
    return ZcashIncomingViewingKey(ivk=fvk.incoming_viewing_key())
