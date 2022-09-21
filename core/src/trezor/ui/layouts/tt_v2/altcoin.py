from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Sequence
    from trezor.wire import GenericContext

    pass


async def confirm_total_ethereum(
    ctx: GenericContext, total_amount: str, gas_price: str, fee_max: str
) -> None:
    raise NotImplementedError


async def confirm_total_ripple(
    ctx: GenericContext,
    address: str,
    amount: str,
) -> None:
    raise NotImplementedError


async def confirm_transfer_binance(
    ctx: GenericContext, inputs_outputs: Sequence[tuple[str, str, str]]
) -> None:
    raise NotImplementedError


async def confirm_decred_sstx_submission(
    ctx: GenericContext,
    address: str,
    amount: str,
) -> None:
    raise NotImplementedError
