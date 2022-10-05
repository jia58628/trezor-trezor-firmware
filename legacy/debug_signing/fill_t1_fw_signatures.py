#!/usr/bin/env python3

import sys

class Signatures:
    # offsets from T1 firmware hash
    sig_offsets = [544, 608, 672]
    sigindex_offsets = [736, 737, 738]
    signature_pairs = [] # list of tupes (int, bytes)

# arg1 - unsigned trezor.bin FW
# arg2 - list of 3 signatures and indexes in this format (split by single space):
# index_num signature
# e.g.
# 1 adec956df6282c15ee4344b4cf6edbe435ed4bb13b2b7bebb9920f3d1c4a791a446e492f3ff9b86ca43f28cfce1be97c4eefa65e505e8a936876f01833366d5d

in_fw_fname = sys.argv[1]
signatures_fname = sys.argv[2]

out_fw_fname = in_fw_fname + ".signed"
data = open(in_fw_fname, "rb").read()
fwdata = bytearray(data) # mutable

signatures = Signatures()
i = 0
for line in open(signatures_fname):
    i += 1
    print(f"Parsing sig line {i} - {line}")
    idx, sig = line.rstrip().split(" ")
    idx = int(idx)
    sig = bytes.fromhex(sig)
    assert idx in range(1, 4) # 1 <= idx <= 3
    assert len(sig) == 64
    signatures.signature_pairs.append((idx, sig))

for i in range(3):
    sigindex_ofs = signatures.sigindex_offsets[i]
    sig_ofs = signatures.sig_offsets[i]
    (sigindex, sig) = signatures.signature_pairs[i]

    print(f"Patching sigindex {sigindex} at offset {sigindex_ofs}")
    fwdata[sigindex_ofs] = sigindex

    print(f"Patching signature {sig.hex()} at offset {sig_ofs}")
    fwdata[sig_ofs:sig_ofs+64] = sig

with open(out_fw_fname, "wb") as signed_fw_file:
    signed_fw_file.write(fwdata)

