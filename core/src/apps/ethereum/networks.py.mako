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
% for n in supported_on("trezor2", eth):
    yield EthereumNetworkInfo(
        chain_id=${n.chain_id},
        slip44=${n.slip44},
        shortcut="${n.shortcut}",
        name="${n.name}",
        rskip60=${n.rskip60},
    )
% endfor
