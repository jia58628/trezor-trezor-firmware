# generated from tokens.py.mako
# (by running `make templates` in `core`)
# do not edit manually!
# fmt: off
from trezor.messages import EthereumTokenInfo

UNKNOWN_TOKEN = EthereumTokenInfo(
    symbol="Wei UNKN",
    decimals=0,
    address=b"",
    chain_id=0,
    name="Unknown token",
)


def token_by_chain_address(chain_id: int, address: bytes) -> EthereumTokenInfo:
    if chain_id == 1:  # eth
        if address == b"\x00\x00\x00\x00\x00\x00\x45\x16\x6c\x45\xaf\x0f\xc6\xe4\xcf\x31\xd9\xe1\x4b\x9a":
            return EthereumTokenInfo(
                symbol="BID",
                decimals=18,
                address=address,
                chain_id=chain_id,
                name="TopBidder",
            )
        if address == b"\x00\x00\x00\x00\x00\x08\x5d\x47\x80\xb7\x31\x19\xb6\x44\xae\x5e\xcd\x22\xb3\x76":
            return EthereumTokenInfo(
                symbol="TUSD",
                decimals=18,
                address=address,
                chain_id=chain_id,
                name="TrueUSD",
            )
    if chain_id == 56:  # bnb
        if address == b"\xfe\x1d\x7f\x7a\x8f\x0b\xda\x6e\x41\x55\x93\xa2\xe4\xf8\x2c\x64\xb4\x46\xd4\x04":
            return EthereumTokenInfo(
                symbol="BLP",
                decimals=18,
                address=address,
                chain_id=chain_id,
                name="BullPerks",
            )
        if address == b"\xfe\x19\xf0\xb5\x14\x38\xfd\x61\x2f\x6f\xd5\x9c\x1d\xbb\x3e\xa3\x19\xf4\x33\xba":
            return EthereumTokenInfo(
                symbol="MIM",
                decimals=18,
                address=address,
                chain_id=chain_id,
                name="Magic Internet Money",
            )
    return UNKNOWN_TOKEN
