from micropython import const
from typing import TYPE_CHECKING

from trezor import loop, res, ui, utils, wire, workflow
from trezor.enums import ButtonRequestType
from trezor.messages import ButtonAck, ButtonRequest

from ..common.confirm import GO_BACK, SHOW_PAGINATED
from .button import Button, ButtonDefault
from .confirm import Confirm
from .swipe import SWIPE_DOWN, SWIPE_UP, SWIPE_VERTICAL, Swipe
from .text import (
    LINE_WIDTH_PAGINATED,
    TEXT_MAX_LINES,
    TEXT_MAX_LINES_NO_HEADER,
    Span,
    Text,
)

if TYPE_CHECKING:
    from typing import Any, Callable, Iterable

    from ..common.text import TextContent


WAS_PAGED = object()


def render_scrollbar(pages: int, page: int) -> None:
    _BBOX = const(220)
    _SIZE = const(8)

    padding = 14
    if pages * padding > _BBOX:
        padding = _BBOX // pages

    X = const(220)
    Y = (_BBOX // 2) - (pages // 2) * padding

    for i in range(0, pages):
        if i == page:
            fg = ui.FG
        else:
            fg = ui.GREY
        ui.display.bar_radius(X, Y + i * padding, _SIZE, _SIZE, fg, ui.BG, 4)


def render_swipe_icon(x_offset: int = 0) -> None:
    if utils.DISABLE_ANIMATION:
        c = ui.GREY
    else:
        PULSE_PERIOD = const(1_200_000)
        t = ui.pulse(PULSE_PERIOD)
        c = ui.blend(ui.GREY, ui.DARK_GREY, t)

    icon = res.load(ui.ICON_SWIPE)
    ui.display.icon(70 + x_offset, 205, icon, c, ui.BG)


def render_swipe_text(x_offset: int = 0) -> None:
    ui.display.text_center(130 + x_offset, 220, "Swipe", ui.BOLD, ui.GREY, ui.BG)


class Paginated(ui.Layout):
    def __init__(
        self, pages: list[ui.Component], page: int = 0, back_button: bool = False
    ):
        super().__init__()
        self.pages = pages
        self.page = page
        self.back_button = None
        if back_button:
            area = ui.grid(16, n_x=4)
            icon = res.load(ui.ICON_BACK)
            self.back_button = Button(area, icon, ButtonDefault)
            self.back_button.on_click = self.on_back_click

    def dispatch(self, event: int, x: int, y: int) -> None:
        pages = self.pages
        page = self.page
        length = len(pages)
        last_page = page >= length - 1
        x_offset = 0

        pages[page].dispatch(event, x, y)
        if self.back_button is not None and not last_page:
            self.back_button.dispatch(event, x, y)
            x_offset = 30

        if event is ui.REPAINT:
            self.repaint = True
        elif event is ui.RENDER:
            if not last_page:
                render_swipe_icon(x_offset=x_offset)
                if self.repaint:
                    render_swipe_text(x_offset=x_offset)
            if self.repaint:
                render_scrollbar(length, page)
                self.repaint = False

    async def handle_paging(self) -> None:
        if self.page == 0:
            directions = SWIPE_UP
        elif self.page == len(self.pages) - 1:
            directions = SWIPE_DOWN
        else:
            directions = SWIPE_VERTICAL

        if __debug__:
            from apps.debug import swipe_signal

            swipe = await loop.race(Swipe(directions), swipe_signal())
        else:
            swipe = await Swipe(directions)

        if swipe is SWIPE_UP:
            self.page = min(self.page + 1, len(self.pages) - 1)
        elif swipe is SWIPE_DOWN:
            self.page = max(self.page - 1, 0)

        self.on_change()
        raise ui.Result(WAS_PAGED)

    async def interact(
        self,
        ctx: wire.GenericContext,
        code: ButtonRequestType = ButtonRequestType.Other,
    ) -> Any:
        workflow.close_others()
        await ctx.call(ButtonRequest(code=code, pages=len(self.pages)), ButtonAck)
        result = WAS_PAGED
        while result is WAS_PAGED:
            result = await ctx.wait(self)

        return result

    def create_tasks(self) -> tuple[loop.AwaitableTask, ...]:
        tasks: tuple[loop.AwaitableTask, ...] = (
            self.handle_input(),
            self.handle_rendering(),
            self.handle_paging(),
        )

        if __debug__:
            # XXX This isn't strictly correct, as it allows *any* Paginated layout to be
            # shut down by a DebugLink confirm, even if used outside of a confirm() call
            # But we don't have any such usages in the codebase, and it doesn't actually
            # make much sense to use a Paginated without a way to confirm it.
            from apps.debug import confirm_signal

            return tasks + (confirm_signal(),)
        else:
            return tasks

    def on_change(self) -> None:
        pass

    def on_back_click(self) -> None:
        raise ui.Result(GO_BACK)

    if __debug__:

        def read_content(self) -> list[str]:
            return self.pages[self.page].read_content()


class AskPaginated(ui.Component):
    def __init__(self, content: ui.Component, button_text: str = "Show all") -> None:
        super().__init__()
        self.content = content
        self.button = Button(ui.grid(3, n_x=1), button_text, ButtonDefault)
        self.button.on_click = self.on_show_paginated_click

    def dispatch(self, event: int, x: int, y: int) -> None:
        self.content.dispatch(event, x, y)
        self.button.dispatch(event, x, y)

    def on_show_paginated_click(self) -> None:
        raise ui.Result(SHOW_PAGINATED)

    if __debug__:

        def read_content(self) -> list[str]:
            return self.content.read_content()


PAGEBREAK = 0, ""


def paginate_paragraphs(
    para: Iterable[tuple[int, str]],
    header: str | None,
    header_icon: str = ui.ICON_DEFAULT,
    icon_color: int = ui.ORANGE_ICON,
    break_words: bool = False,
    confirm: Callable[[ui.Component], ui.Layout] = Confirm,
    back_button: bool = False,
) -> ui.Layout:
    span = Span("", 0, ui.NORMAL, break_words=break_words)
    lines = 0
    content: list[TextContent] = []
    max_lines = TEXT_MAX_LINES_NO_HEADER if header is None else TEXT_MAX_LINES
    for item in para:
        if item is PAGEBREAK:
            continue
        span.reset(item[1], 0, item[0], break_words=break_words)
        lines += span.count_lines()

        # we'll need this for multipage too
        if content:
            content.append("\n")
        content.extend(item)

    if lines <= max_lines:
        result = Text(
            header,
            header_icon=header_icon,
            icon_color=icon_color,
            new_lines=False,
            break_words=break_words,
        )
        result.content = content
        return confirm(result)

    else:
        pages: list[ui.Component] = []
        lines_left = 0
        content_ctr = 0
        page: Text | None = None
        for item in para:
            if item is PAGEBREAK:
                if page is not None:
                    page.max_lines -= lines_left
                lines_left = 0
                continue

            span.reset(
                item[1],
                0,
                item[0],
                break_words=break_words,
                line_width=LINE_WIDTH_PAGINATED,
            )

            while span.has_more_content():
                span.next_line()
                if lines_left <= 0:
                    page = Text(
                        header,
                        header_icon=header_icon,
                        icon_color=icon_color,
                        new_lines=False,
                        content_offset=content_ctr * 3 + 1,  # font, _text_, newline
                        char_offset=span.start,
                        line_width=LINE_WIDTH_PAGINATED,
                        render_page_overflow=False,
                        break_words=break_words,
                    )
                    page.content = content
                    pages.append(page)
                    lines_left = max_lines - 1
                else:
                    lines_left -= 1

            content_ctr += 1

        pages[-1] = confirm(pages[-1])
        return Paginated(pages, back_button=back_button)
