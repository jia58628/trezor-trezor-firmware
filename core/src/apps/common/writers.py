from typing import TYPE_CHECKING

from trezor.utils import ensure

if TYPE_CHECKING:
    from trezor.utils import Writer


def write_uint8(w: Writer, n: int) -> int:
    ensure(0 <= n <= 0xFF)
    w.append(n)
    return 1


def write_uint16_le(w: Writer, n: int) -> int:
    ensure(0 <= n <= 0xFFFF)
    w.append(n & 0xFF)
    w.append((n >> 8) & 0xFF)
    return 2


def write_uint32_le(w: Writer, n: int) -> int:
    ensure(0 <= n <= 0xFFFF_FFFF)
    w.append(n & 0xFF)
    for num in (8, 16, 24):
        w.append((n >> num) & 0xFF)
    return 4


def write_uint32_be(w: Writer, n: int) -> int:
    ensure(0 <= n <= 0xFFFF_FFFF)
    for num in (24, 16, 8):
        w.append((n >> num) & 0xFF)
    w.append(n & 0xFF)
    return 4


def write_uint64_le(w: Writer, n: int) -> int:
    ensure(0 <= n <= 0xFFFF_FFFF_FFFF_FFFF)

    w.append(n & 0xFF)
    for num in (8, 16, 24, 32, 40, 48, 56):
        w.append((n >> num) & 0xFF)

    return 8


def write_uint64_be(w: Writer, n: int) -> int:
    ensure(0 <= n <= 0xFFFF_FFFF_FFFF_FFFF)

    for num in (56, 48, 40, 32, 24, 16, 8):
        w.append((n >> num) & 0xFF)
    w.append(n & 0xFF)

    return 8


def write_bytes_unchecked(w: Writer, b: bytes | memoryview) -> int:
    w.extend(b)
    return len(b)


def write_bytes_fixed(w: Writer, b: bytes, length: int) -> int:
    ensure(len(b) == length)
    w.extend(b)
    return length


def write_bytes_reversed(w: Writer, b: bytes, length: int) -> int:
    ensure(len(b) == length)
    w.extend(bytes(reversed(b)))
    return length


def write_compact_size(w: Writer, n: int) -> None:
    ensure(0 <= n <= 0xFFFF_FFFF)

    w_append = w.append  # cache

    if n < 253:
        w_append(n & 0xFF)
    elif n < 0x1_0000:
        w_append(253)
        write_uint16_le(w, n)
    elif n < 0x1_0000_0000:
        w_append(254)
        write_uint32_le(w, n)
    else:
        w_append(255)
        write_uint64_le(w, n)


def write_uvarint(w: Writer, n: int) -> None:
    ensure(0 <= n <= 0xFFFF_FFFF_FFFF_FFFF)
    shifted = 1
    while shifted:
        shifted = n >> 7
        byte = (n & 0x7F) | (0x80 if shifted else 0x00)
        w.append(byte)
        n = shifted
