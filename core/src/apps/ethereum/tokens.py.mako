# generated from tokens.py.mako
# (by running `make templates` in `core`)
# do not edit manually!
# fmt: off
<%
from collections import defaultdict

def group_tokens(tokens):
    r = defaultdict(list)
    for t in sorted(tokens, key=lambda t: t.chain_id):
        r[t.chain_id].append(t)
    return r
%>\

class TokenInfo:
    def __init__(
        self,
        symbol: str,
        decimals: int,
        address: bytes,
        chain_id: int,
        name: str = None,
    ) -> None:
        self.symbol = symbol
        self.decimals = decimals
        self.address = address
        self.chain_id = chain_id
        self.name = name


UNKNOWN_TOKEN = TokenInfo("Wei UNKN", 0, b"", 0)

# TODO: delete completely
def token_by_chain_address(chain_id: int, address: bytes) -> TokenInfo:
% for token_chain_id, tokens in group_tokens(supported_on("trezor2", erc20)).items():
    return UNKNOWN_TOKEN

    if chain_id == ${token_chain_id}:
        % for t in tokens:
        if address == ${black_repr(t.address_bytes)}:
            return TokenInfo(${black_repr(t.symbol)}, ${t.decimals}, address, chain_id)  # ${t.chain} / ${t.name.strip()}
        % endfor
% endfor
    return UNKNOWN_TOKEN
