from micropython import const
from typing import TYPE_CHECKING

from .common import BIP32_WALLET_DEPTH

if TYPE_CHECKING:
    from trezor.messages import (
        AuthorizeCoinJoin,
        GetOwnershipProof,
        SignTx,
        TxInput,
    )
    from trezor.protobuf import MessageType

    from apps.common.coininfo import CoinInfo

FEE_RATE_DECIMALS = const(8)


class CoinJoinAuthorization:
    def __init__(self, params: AuthorizeCoinJoin) -> None:
        self.params = params

    def check_get_ownership_proof(self, msg: GetOwnershipProof) -> bool:
        from trezor import utils
        from .writers import write_bytes_prefixed

        self_params = self.params  # cache

        # Check whether the current params matches the parameters of the request.
        coordinator = utils.empty_bytearray(1 + len(self_params.coordinator.encode()))
        write_bytes_prefixed(coordinator, self_params.coordinator.encode())
        return (
            len(msg.address_n) >= BIP32_WALLET_DEPTH
            and msg.address_n[:-BIP32_WALLET_DEPTH] == self_params.address_n
            and msg.coin_name == self_params.coin_name
            and msg.script_type == self_params.script_type
            and msg.commitment_data.startswith(bytes(coordinator))
        )

    def check_sign_tx_input(self, txi: TxInput, coin: CoinInfo) -> bool:
        # Check whether the current input matches the parameters of the request.
        return (
            len(txi.address_n) >= BIP32_WALLET_DEPTH
            and txi.address_n[:-BIP32_WALLET_DEPTH] == self.params.address_n
            and coin.coin_name == self.params.coin_name
            and txi.script_type == self.params.script_type
        )

    def approve_sign_tx(self, msg: SignTx) -> bool:
        from apps.common import authorization

        self_params = self.params  # cache

        if self_params.max_rounds < 1 or msg.coin_name != self_params.coin_name:
            return False

        self_params.max_rounds -= 1
        authorization.set(self_params)
        return True


def from_cached_message(auth_msg: MessageType) -> CoinJoinAuthorization:
    from trezor import wire
    from trezor.messages import AuthorizeCoinJoin

    if not AuthorizeCoinJoin.is_type_of(auth_msg):
        raise wire.ProcessError("Appropriate params was not found")

    return CoinJoinAuthorization(auth_msg)
