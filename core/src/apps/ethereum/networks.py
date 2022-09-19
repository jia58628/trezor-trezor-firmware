# generated from networks.py.mako
# (by running `make templates` in `core`)
# do not edit manually!
from typing import Iterator

from trezor.messages import EthereumNetworkInfo

from apps.common.paths import HARDENED

UNKNOWN_NETWORK_SHORTCUT = "UNKN"


def by_chain_id(chain_id: int) -> EthereumNetworkInfo | None:
    for n in _networks_iterator():
        if n.chain_id == chain_id:
            return n
    return None


def by_slip44(slip44: int) -> EthereumNetworkInfo | None:
    for n in _networks_iterator():
        if n.slip44 == slip44:
            return n
    return None


def all_slip44_ids_hardened() -> Iterator[int]:
    for n in _networks_iterator():
        yield n.slip44 | HARDENED


# fmt: off
def _networks_iterator() -> Iterator[EthereumNetworkInfo]:
    yield EthereumNetworkInfo(
        chain_id=1,
        slip44=60,
        shortcut="ETH",
        name="Ethereum",
        rskip60=False,
    )
    yield EthereumNetworkInfo(
        chain_id=3,
        slip44=1,
        shortcut="tROP",
        name="Ropsten",
        rskip60=False,
    )
    yield EthereumNetworkInfo(
        chain_id=9,
        slip44=1,
        shortcut="TUBQ",
        name="Ubiq Network Testnet",
        rskip60=False,
    )
