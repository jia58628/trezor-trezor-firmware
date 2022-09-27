from typing import TYPE_CHECKING

from trezor import strings, ui
from trezor.ui.components.common.confirm import CONFIRMED, SHOW_PAGINATED
from trezor.ui.components.tt.scroll import AskPaginated, Paginated, paginate_paragraphs
from trezor.ui.components.tt.text import Text
from trezor.ui.constants.tt import MONO_ADDR_PER_LINE
from trezor.ui.layouts import confirm_action, confirm_address
from trezor.ui.layouts.tt import Confirm, interact, raise_if_cancelled
from trezor.utils import chunks, chunks_intersperse, ensure

from apps.bitcoin.sign_tx.helpers import UiConfirm

if TYPE_CHECKING:
    from typing import Awaitable, Any
    from apps.common.coininfo import CoinInfo
    from trezor.wire import Context
    from trezor.messages import ZcashOrchardOutput, TxOutput
    from trezor.ui import Component
    from trezor.ui.layouts.common import LayoutType


def _format_amount(value: int, coin: CoinInfo) -> str:
    return "%s %s" % (strings.format_amount(value, 8), coin.coin_shortcut)


class UiConfirmTransparentOutput(UiConfirm):
    def __init__(self, txo: TxOutput, coin: CoinInfo) -> None:
        self.txo = txo
        self.coin = coin

    def confirm_dialog(self, ctx: Context) -> Awaitable[Any]:
        content = Confirm(get_pay_page(self.txo, self.coin, "t"))
        assert self.txo.address is not None  # typing
        return maybe_show_full_address(ctx, content, self.txo.address)


class UiConfirmOrchardOutput(UiConfirm):
    def __init__(self, txo: ZcashOrchardOutput, coin: CoinInfo) -> None:
        self.txo = txo
        self.coin = coin

    def confirm_dialog(self, ctx: Context) -> Awaitable[Any]:
        pages = []
        pages.append(get_pay_page(self.txo, self.coin, "z"))
        pages.extend(get_memo_pages(self.txo.memo))

        pages[-1] = Confirm(pages[-1])

        assert len(pages) >= 2  # pay page + memo page
        content = Paginated(pages)
        assert self.txo.address is not None  # typing
        return maybe_show_full_address(ctx, content, self.txo.address)


def get_pay_page(
    txo: TxOutput | ZcashOrchardOutput, coin: CoinInfo, transfer_type: str
) -> Component:
    assert transfer_type in ("t", "z")
    title = "Confirm %s-sending" % transfer_type
    text = Text(title, ui.ICON_SEND, ui.GREEN, new_lines=False)
    text.bold(_format_amount(txo.amount, coin))
    text.normal(" to\n")

    assert txo.address is not None  # typing
    if txo.address.startswith("t"):  # transparent address
        ensure(len(txo.address) == 35)
        text.mono(*chunks_intersperse(txo.address, MONO_ADDR_PER_LINE))
        return text
    elif txo.address.startswith("u"):  # unified address
        address_lines = chunks(txo.address, MONO_ADDR_PER_LINE)
        text.mono(next(address_lines) + "\n")
        text.mono(next(address_lines)[:-3] + "...")
        return AskPaginated(text, "show full address")
    else:
        raise ValueError("Unexpected address prefix.")


def get_memo_pages(memo: str | None) -> list[Component]:
    if memo is None:
        return [Text("without memo", ui.ICON_SEND, ui.GREEN)]

    paginated = paginate_paragraphs(
        [(ui.NORMAL, memo)],
        "with memo",
        header_icon=ui.ICON_SEND,
        icon_color=ui.GREEN,
    )

    if isinstance(paginated, Confirm):
        return [paginated.content]
    else:
        assert isinstance(paginated, Paginated)
        return paginated.pages


async def maybe_show_full_address(
    ctx: Context, content: LayoutType, full_address: str
) -> None:
    """Lets user to toggle between output-confirmation-dialog
    and see-full-address-dialog before he confirms an output."""
    while True:
        result = await raise_if_cancelled(
            interact(
                ctx,
                content,
                "confirm_output",
            )
        )
        if result is SHOW_PAGINATED:
            await confirm_address(
                ctx,
                "Confirm address",
                full_address,
                description=None,
            )
        else:
            assert result is CONFIRMED
            break
