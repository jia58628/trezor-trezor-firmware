from typing import TYPE_CHECKING

from trezor.enums import ButtonRequestType
from trezor.ui.layouts import confirm_action

if TYPE_CHECKING:
    from trezor.messages import ApplySettings, Success
    from trezor.wire import Context, GenericContext
    from trezor.enums import SafetyCheckLevel


BRT_PROTECT_CALL = ButtonRequestType.ProtectCall  # CACHE


def _validate_homescreen(homescreen: bytes) -> None:
    from trezor import ui
    import storage.device as storage_device
    from trezor.wire import DataError

    if homescreen == b"":
        return

    if len(homescreen) > storage_device.HOMESCREEN_MAXSIZE:
        raise DataError(
            f"Homescreen is too large, maximum size is {storage_device.HOMESCREEN_MAXSIZE} bytes"
        )

    try:
        w, h, grayscale = ui.display.toif_info(homescreen)
    except ValueError:
        raise DataError("Invalid homescreen")
    if w != 144 or h != 144:
        raise DataError("Homescreen must be 144x144 pixel large")
    if grayscale:
        raise DataError("Homescreen must be full-color TOIF image")


async def apply_settings(ctx: Context, msg: ApplySettings) -> Success:
    import storage.device as storage_device
    from apps.common import safety_checks
    from trezor.messages import Success
    from trezor.wire import DataError, ProcessError, NotInitialized
    from apps.base import reload_settings_from_storage

    if not storage_device.is_initialized():
        raise NotInitialized("Device is not initialized")

    msg_homescreen = msg.homescreen  # local_cache_attribute
    msg_label = msg.label  # local_cache_attribute
    msg_auto_lock_delay_ms = msg.auto_lock_delay_ms  # local_cache_attribute
    msg_use_passphrase = msg.use_passphrase  # local_cache_attribute
    msg_passphrase_always_on_device = (
        msg.passphrase_always_on_device
    )  # local_cache_attribute
    msg_display_rotation = msg.display_rotation  # local_cache_attribute
    msg_safety_checks = msg.safety_checks  # local_cache_attribute
    msg_experimental_features = msg.experimental_features  # local_cache_attribute

    if (
        msg_homescreen is None
        and msg_label is None
        and msg_use_passphrase is None
        and msg_passphrase_always_on_device is None
        and msg_display_rotation is None
        and msg_auto_lock_delay_ms is None
        and msg_safety_checks is None
        and msg_experimental_features is None
    ):
        raise ProcessError("No setting provided")

    if msg_homescreen is not None:
        _validate_homescreen(msg_homescreen)
        await _require_confirm_change_homescreen(ctx)
        try:
            storage_device.set_homescreen(msg_homescreen)
        except ValueError:
            raise DataError("Invalid homescreen")

    if msg_label is not None:
        if len(msg_label) > storage_device.LABEL_MAXLENGTH:
            raise DataError("Label too long")
        await _require_confirm_change_label(ctx, msg_label)
        storage_device.set_label(msg_label)

    if msg_use_passphrase is not None:
        await _require_confirm_change_passphrase(ctx, msg_use_passphrase)
        storage_device.set_passphrase_enabled(msg_use_passphrase)

    if msg_passphrase_always_on_device is not None:
        if not storage_device.is_passphrase_enabled():
            raise DataError("Passphrase is not enabled")
        await _require_confirm_change_passphrase_source(
            ctx, msg_passphrase_always_on_device
        )
        storage_device.set_passphrase_always_on_device(msg_passphrase_always_on_device)

    if msg_auto_lock_delay_ms is not None:
        if msg_auto_lock_delay_ms < storage_device.AUTOLOCK_DELAY_MINIMUM:
            raise ProcessError("Auto-lock delay too short")
        if msg_auto_lock_delay_ms > storage_device.AUTOLOCK_DELAY_MAXIMUM:
            raise ProcessError("Auto-lock delay too long")
        await _require_confirm_change_autolock_delay(ctx, msg_auto_lock_delay_ms)
        storage_device.set_autolock_delay_ms(msg_auto_lock_delay_ms)

    if msg_safety_checks is not None:
        await _require_confirm_safety_checks(ctx, msg_safety_checks)
        safety_checks.apply_setting(msg_safety_checks)

    if msg_display_rotation is not None:
        await _require_confirm_change_display_rotation(ctx, msg_display_rotation)
        storage_device.set_rotation(msg_display_rotation)

    if msg_experimental_features is not None:
        await _require_confirm_experimental_features(ctx, msg_experimental_features)
        storage_device.set_experimental_features(msg_experimental_features)

    reload_settings_from_storage()

    return Success(message="Settings applied")


async def _require_confirm_change_homescreen(ctx: GenericContext) -> None:
    await confirm_action(
        ctx,
        "set_homescreen",
        "Set homescreen",
        description="Do you really want to change the homescreen image?",
        br_code=BRT_PROTECT_CALL,
    )


async def _require_confirm_change_label(ctx: GenericContext, label: str) -> None:
    await confirm_action(
        ctx,
        "set_label",
        "Change label",
        description="Do you really want to change the label to {}?",
        description_param=label,
        br_code=BRT_PROTECT_CALL,
    )


async def _require_confirm_change_passphrase(ctx: GenericContext, use: bool) -> None:
    template = "Do you really want to {} passphrase encryption?"
    description = template.format("enable" if use else "disable")
    await confirm_action(
        ctx,
        "set_passphrase",
        "Enable passphrase" if use else "Disable passphrase",
        description=description,
        br_code=BRT_PROTECT_CALL,
    )


async def _require_confirm_change_passphrase_source(
    ctx: GenericContext, passphrase_always_on_device: bool
) -> None:
    description = (
        "Do you really want to enter passphrase always on the device?"
        if passphrase_always_on_device
        else "Do you want to revoke the passphrase on device setting?"
    )
    await confirm_action(
        ctx,
        "set_passphrase_source",
        "Passphrase source",
        description=description,
        br_code=BRT_PROTECT_CALL,
    )


async def _require_confirm_change_display_rotation(
    ctx: GenericContext, rotation: int
) -> None:
    from trezor.wire import DataError

    label = {
        0: "north",
        90: "east",
        180: "south",
        270: "west",
    }.get(rotation)
    if label is None:
        raise DataError("Unsupported display rotation")
    await confirm_action(
        ctx,
        "set_rotation",
        "Change rotation",
        description="Do you really want to change display rotation to {}?",
        description_param=label,
        br_code=BRT_PROTECT_CALL,
    )


async def _require_confirm_change_autolock_delay(
    ctx: GenericContext, delay_ms: int
) -> None:
    from trezor.strings import format_duration_ms

    await confirm_action(
        ctx,
        "set_autolock_delay",
        "Auto-lock delay",
        description="Do you really want to auto-lock your device after {}?",
        description_param=format_duration_ms(delay_ms),
        br_code=BRT_PROTECT_CALL,
    )


async def _require_confirm_safety_checks(
    ctx: GenericContext, level: SafetyCheckLevel
) -> None:
    from trezor.enums import SafetyCheckLevel

    if level == SafetyCheckLevel.Strict:
        await confirm_action(
            ctx,
            "set_safety_checks",
            "Safety checks",
            description="Do you really want to enforce strict safety checks (recommended)?",
            br_code=BRT_PROTECT_CALL,
        )
    elif level in (SafetyCheckLevel.PromptAlways, SafetyCheckLevel.PromptTemporarily):
        # Reusing most stuff for both levels
        template = (
            "Trezor will{}allow you to approve some actions which might be unsafe."
        )
        description = template.format(
            " temporarily " if level == SafetyCheckLevel.PromptTemporarily else " "
        )

        await confirm_action(
            ctx,
            "set_safety_checks",
            "Safety override",
            "Are you sure?",
            description,
            hold=True,
            verb="Hold to confirm",
            reverse=True,
            larger_vspace=level == SafetyCheckLevel.PromptAlways,
            br_code=BRT_PROTECT_CALL,
        )
    else:
        raise ValueError  # enum value out of range


async def _require_confirm_experimental_features(
    ctx: GenericContext, enable: bool
) -> None:
    if enable:
        await confirm_action(
            ctx,
            "set_experimental_features",
            "Experimental mode",
            "Only for development and beta testing!",
            "Enable experimental features?",
            reverse=True,
            br_code=BRT_PROTECT_CALL,
        )
