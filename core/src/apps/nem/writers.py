from typing import TYPE_CHECKING

from apps.common.writers import write_bytes_unchecked, write_uint32_le, write_uint64_le

if TYPE_CHECKING:
    from trezor.messages import NEMTransactionCommon
    from trezor.utils import Writer


def serialize_tx_common(
    common: NEMTransactionCommon,
    public_key: bytes,
    transaction_type: int,
    version: int | None = None,
) -> bytearray:
    w = bytearray()

    write_uint32_le_local = write_uint32_le  # local_cache_global

    write_uint32_le_local(w, transaction_type)
    if version is None:
        version = common.network << 24 | 1
    write_uint32_le_local(w, version)
    write_uint32_le_local(w, common.timestamp)

    write_bytes_with_len(w, public_key)
    write_uint64_le(w, common.fee)
    write_uint32_le_local(w, common.deadline)

    return w


def write_bytes_with_len(w: Writer, buf: bytes) -> None:
    write_uint32_le(w, len(buf))
    write_bytes_unchecked(w, buf)
