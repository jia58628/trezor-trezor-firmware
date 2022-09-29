import utime
from micropython import const
from typing import TYPE_CHECKING, Tuple

import storage.cache
from trezor import config, ui

from . import HomescreenBase

if TYPE_CHECKING:
    from trezor import loop


_LOADER_DELAY_MS = const(500)
_LOADER_TOTAL_MS = const(2500)


async def homescreen() -> None:
    from apps.base import lock_device

    await Homescreen()
    lock_device()


class Homescreen(HomescreenBase):
    RENDER_INDICATOR = storage.cache.HOMESCREEN_ON

    def __init__(self) -> None:
        from trezor.ui.loader import Loader, LoaderNeutral
        import storage.device as storage_device

        super().__init__()
        self.is_connected = False
        if not storage_device.is_initialized():
            self.label = "Go to trezor.io/start"

        self.loader = Loader(
            LoaderNeutral,
            _LOADER_TOTAL_MS - _LOADER_DELAY_MS,
            -10,
            3,
        )
        self.touch_ms: int | None = None

    def create_tasks(self) -> Tuple[loop.AwaitableTask, ...]:
        return super().create_tasks() + (self.usb_checker_task(),)

    async def usb_checker_task(self) -> None:
        from trezor import loop, io

        usbcheck = loop.wait(io.USB_CHECK)
        while True:
            is_connected = await usbcheck
            if is_connected != self.is_connected:
                self.is_connected = is_connected
                self.set_repaint(True)

    def do_render(self) -> None:
        from trezor import utils
        import storage.device as storage_device

        local_ui = ui  # cache
        header_error = local_ui.header_error  # cache
        header_warning = local_ui.header_warning  # cache
        display = local_ui.display  # cache
        model = utils.MODEL  # cache

        # warning bar on top
        if storage_device.is_initialized() and storage_device.no_backup():
            header_error("SEEDLESS")
        elif storage_device.is_initialized() and storage_device.unfinished_backup():
            header_error("BACKUP FAILED!")
        elif storage_device.is_initialized() and storage_device.needs_backup():
            header_warning("NEEDS BACKUP!")
        elif storage_device.is_initialized() and not config.has_pin():
            header_warning("PIN NOT SET!")
        elif storage_device.get_experimental_features():
            header_warning("EXPERIMENTAL MODE!")
        else:
            display.bar(0, 0, local_ui.WIDTH, local_ui.HEIGHT, local_ui.BG)

        # homescreen with shifted avatar and text on bottom
        # Differs for each model

        if not utils.usb_data_connected():
            header_error("NO USB CONNECTION")

        # TODO: support homescreen avatar change for R and 1
        if model in ("T",):
            display.avatar(
                48, 48 - 10, self.get_image(), local_ui.WHITE, local_ui.BLACK
            )
        elif model in ("R",):
            icon = "trezor/res/homescreen_model_r.toif"  # 92x92 px
            display.icon(
                18, 18, local_ui.res.load(icon), local_ui.style.FG, local_ui.style.BG
            )
        elif model in ("1",):
            icon = "trezor/res/homescreen_model_1.toif"  # 64x36 px
            display.icon(
                33, 14, local_ui.res.load(icon), local_ui.style.FG, local_ui.style.BG
            )

        label_heights = {"1": 60, "R": 120, "T": 220}
        display.text_center(
            local_ui.WIDTH // 2,
            label_heights[model],
            self.label,
            local_ui.BOLD,
            local_ui.FG,
            local_ui.BG,
        )

        local_ui.refresh()

    def on_touch_start(self, _x: int, _y: int) -> None:
        if self.loader.start_ms is not None:
            self.loader.start()
        elif config.has_pin():
            self.touch_ms = utime.ticks_ms()

    def on_touch_end(self, _x: int, _y: int) -> None:
        if self.loader.start_ms is not None:
            self.set_repaint(True)
        self.loader.stop()
        self.touch_ms = None

        # raise here instead of self.loader.on_finish so as not to send TOUCH_END to the lockscreen
        if self.loader.elapsed_ms() >= self.loader.target_ms:
            raise ui.Result(None)

    def dispatch(self, event: int, x: int, y: int) -> None:
        if (
            self.touch_ms is not None
            and self.touch_ms + _LOADER_DELAY_MS < utime.ticks_ms()
        ):
            self.touch_ms = None

            # _loader_start
            ui.display.clear()
            ui.display.text_center(
                ui.WIDTH // 2, 35, "Hold to lock", ui.BOLD, ui.FG, ui.BG
            )
            self.loader.start()
            # END _loader_start

        if event is ui.RENDER and self.loader.start_ms is not None:
            self.loader.dispatch(event, x, y)
        else:
            super().dispatch(event, x, y)
