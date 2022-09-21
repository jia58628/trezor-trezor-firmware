from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.utils import BufferReader


def read_memoryview_prefixed(r: BufferReader) -> memoryview:
    from apps.common.readers import read_compact_size

    n = read_compact_size(r)
    return r.read_memoryview(n)


def read_op_push(r: BufferReader) -> int:
    r_get = r.get  # cache

    prefix = r_get()
    if prefix < 0x4C:
        n = prefix
    elif prefix == 0x4C:
        n = r_get()
    elif prefix == 0x4D:
        n = r_get()
        n += r_get() << 8
    elif prefix == 0x4E:
        n = r_get()
        n += r_get() << 8
        n += r_get() << 16
        n += r_get() << 24
    else:
        raise ValueError
    return n
