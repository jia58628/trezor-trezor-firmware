from typing import TYPE_CHECKING

from trezor import wire
from trezor.enums import ButtonRequestType

import trezorui2

from ..common import interact
from . import _RustLayout, is_confirmed

if TYPE_CHECKING:
    from ...components.common.webauthn import ConfirmInfo

    Pageable = object


async def confirm_webauthn(
    ctx: wire.GenericContext | None,
    info: ConfirmInfo,
    pageable: Pageable | None = None,
) -> bool:
    if pageable is not None:
        # TODO: how to even replicate this situation?
        # Called from Fido2ConfirmGetAssertion and Fido2ConfirmNoCredentials
        # cbor_get_assertion_process -> cbor_get_assertion ->
        # dispatch_cmd -> req.data[0] == _CBOR_GET_ASSERTION
        # TODO: should create a UI test if relevant
        raise NotImplementedError

    confirm = _RustLayout(
        trezorui2.confirm_webauthn(
            title=info.get_header(),
            app_name=info.app_name(),
            account_name=info.account_name(),
            icon=info.app_icon_name,
        )
    )

    if ctx is None:
        return is_confirmed(await confirm)
    else:
        return is_confirmed(
            await interact(ctx, confirm, "confirm_webauthn", ButtonRequestType.Other)
        )


async def confirm_webauthn_reset() -> bool:
    confirm = _RustLayout(
        trezorui2.confirm_action(
            title="FIDO2 RESET",
            action="erase all credentials?",
            description="Do you really want to",
            reverse=True,
        )
    )
    return is_confirmed(await confirm)
