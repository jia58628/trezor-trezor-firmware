#!/usr/bin/env python3
import sys
from hashlib import sha256
from pathlib import Path
from trezorlib.client import get_default_client
from trezorlib.btc import sign_message, get_public_node
from trezorlib.tools import parse_path
from binascii import *

client = get_default_client()
# arg1 is SHA256 digest as reported by "trezorctl firmware-update -f trezor.bin", not the one shown on cibuild!
# The same should be shown on T1 screen
digest = unhexlify(sys.argv[1])
print("Hash before sig: ", digest.hex())
assert(len(digest) == 32)

for i in range(0, 5):
    print(f"--- Key/sig {i}")
    path_text = f"m/44'/0'/{i}'/0/0"
    ADDRESS_N = parse_path(path_text)
    print("Addres_n", path_text, ADDRESS_N)

    node = get_public_node(client, ADDRESS_N)
    print("Public key:", node.node.public_key.hex())
    print("xpub:", node.xpub)

    signature = sign_message(client, "Bitcoin", ADDRESS_N, digest)
    sig_64bytes = signature.signature[1:] #first byte stripped to match normal secp256k1
    assert (len(sig_64bytes) == 64)
    print("Signature:", sig_64bytes.hex())
