from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.utils import BufferReader


def read_compact_size(r: BufferReader) -> int:
    r_get = r.get  # cache

    prefix = r_get()
    if prefix < 253:
        n = prefix
    elif prefix == 253:
        n = r_get()
        n += r_get() << 8
    elif prefix == 254:
        n = r_get()
        n += r_get() << 8
        n += r_get() << 16
        n += r_get() << 24
    elif prefix == 255:
        n = r_get()
        n += r_get() << 8
        n += r_get() << 16
        n += r_get() << 24
        n += r_get() << 32
        n += r_get() << 40
        n += r_get() << 48
        n += r_get() << 56
    else:
        raise ValueError
    return n


def read_uint16_be(r: BufferReader) -> int:
    n = r.get()
    return (n << 8) + r.get()


def read_uint32_be(r: BufferReader) -> int:
    n = r.get()
    for _ in range(3):
        n = (n << 8) + r.get()
    return n


def read_uint64_be(r: BufferReader) -> int:
    n = r.get()
    for _ in range(7):
        n = (n << 8) + r.get()
    return n
