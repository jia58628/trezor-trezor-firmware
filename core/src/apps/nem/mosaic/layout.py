from typing import TYPE_CHECKING

from ..layout import require_confirm_content, require_confirm_final

if TYPE_CHECKING:
    from trezor.messages import (
        NEMMosaicCreation,
        NEMMosaicDefinition,
        NEMMosaicSupplyChange,
        NEMTransactionCommon,
    )
    from trezor.wire import Context


async def ask_mosaic_creation(
    ctx: Context, common: NEMTransactionCommon, creation: NEMMosaicCreation
) -> None:
    from ..layout import require_confirm_fee

    creation_message = [
        ("Create mosaic", creation.definition.mosaic),
        ("under namespace", creation.definition.namespace),
    ]
    await require_confirm_content(ctx, "Create mosaic", creation_message)
    await _require_confirm_properties(ctx, creation.definition)
    await require_confirm_fee(ctx, "Confirm creation fee", creation.fee)

    await require_confirm_final(ctx, common.fee)


async def ask_supply_change(
    ctx: Context, common: NEMTransactionCommon, change: NEMMosaicSupplyChange
) -> None:
    from trezor.enums import NEMSupplyChangeType
    from ..layout import require_confirm_text

    supply_message = [
        ("Modify supply for", change.mosaic),
        ("under namespace", change.namespace),
    ]
    await require_confirm_content(ctx, "Supply change", supply_message)
    common_msg = " supply by " + str(change.delta) + " whole units?"
    if change.type == NEMSupplyChangeType.SupplyChange_Decrease:
        msg = "Decrease" + common_msg
    elif change.type == NEMSupplyChangeType.SupplyChange_Increase:
        msg = "Increase" + common_msg
    else:
        raise ValueError("Invalid supply change type")
    await require_confirm_text(ctx, msg)

    await require_confirm_final(ctx, common.fee)


async def _require_confirm_properties(
    ctx: Context, definition: NEMMosaicDefinition
) -> None:
    from trezor.enums import NEMMosaicLevy
    from trezor import ui
    from trezor.ui.layouts import confirm_properties

    properties = []
    properties_append = properties.append  # cache

    # description
    if definition.description:
        properties_append(("Description:", definition.description))

    # transferable
    transferable = "Yes" if definition.transferable else "No"
    properties_append(("Transferable?", transferable))

    # mutable_supply
    imm = "mutable" if definition.mutable_supply else "immutable"
    if definition.supply:
        properties_append(("Initial supply:", str(definition.supply) + "\n" + imm))
    else:
        properties_append(("Initial supply:", imm))

    # levy
    if definition.levy:
        # asserts below checked in nem.validators._validate_mosaic_creation
        assert definition.levy_address is not None
        assert definition.levy_namespace is not None
        assert definition.levy_mosaic is not None

        properties_append(("Levy recipient:", definition.levy_address))

        properties_append(("Levy fee:", str(definition.fee)))
        properties_append(("Levy divisibility:", str(definition.divisibility)))

        properties_append(("Levy namespace:", definition.levy_namespace))
        properties_append(("Levy mosaic:", definition.levy_mosaic))

        levy_type = (
            "absolute"
            if definition.levy == NEMMosaicLevy.MosaicLevy_Absolute
            else "percentile"
        )
        properties_append(("Levy type:", levy_type))

    await confirm_properties(
        ctx,
        "confirm_properties",
        "Confirm properties",
        properties,
        icon_color=ui.ORANGE_ICON,
    )
