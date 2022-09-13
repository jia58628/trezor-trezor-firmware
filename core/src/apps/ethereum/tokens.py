# generated from tokens.py.mako
# (by running `make templates` in `core`)
# do not edit manually!
# fmt: off

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

def token_by_chain_address(chain_id: int, address: bytes) -> TokenInfo:
    if chain_id == 1:
        if address == b"\x00\x00\x00\x00\x00\x00\x45\x16\x6c\x45\xaf\x0f\xc6\xe4\xcf\x31\xd9\xe1\x4b\x9a":
            return TokenInfo("BID", 18, address, chain_id)  # eth / TopBidder
        if address == b"\x00\x00\x00\x00\x00\x08\x5d\x47\x80\xb7\x31\x19\xb6\x44\xae\x5e\xcd\x22\xb3\x76":
            return TokenInfo("TUSD", 18, address, chain_id)  # eth / TrueUSD
    if chain_id == 56:
        if address == b"\xfe\x1d\x7f\x7a\x8f\x0b\xda\x6e\x41\x55\x93\xa2\xe4\xf8\x2c\x64\xb4\x46\xd4\x04":
            return TokenInfo("BLP", 18, address, chain_id)  # bnb / BullPerks
        if address == b"\xfe\x19\xf0\xb5\x14\x38\xfd\x61\x2f\x6f\xd5\x9c\x1d\xbb\x3e\xa3\x19\xf4\x33\xba":
            return TokenInfo("MIM", 18, address, chain_id)  # bnb / Magic Internet Money
    return UNKNOWN_TOKEN
