# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from . import exceptions, messages
from .messages import ZcashSignatureType as SigType
from .tools import expect


@expect(messages.ZcashFullViewingKey, field="fvk")
def get_fvk(client, z_address_n, coin_name="Zcash",):
    """
    Returns raw Zcash Orchard Full Viewing Key encoded as:

    ak (32 bytes) || nk (32 bytes) || rivk (32 bytes)

    acording to the https://zips.z.cash/protocol/protocol.pdf § 5.6.4.4
    """
    return client.call(
        messages.ZcashGetFullViewingKey(
            z_address_n=z_address_n,
            coin_name=coin_name,
        )
    )


@expect(messages.ZcashIncomingViewingKey, field="ivk")
def get_ivk(client, z_address_n, coin_name = "Zcash",):
    """
    Returns raw Zcash Orchard Incoming Viewing Key encoded as:

    dk (32 bytes) || ivk (32 bytes)

    acording to the https://zips.z.cash/protocol/protocol.pdf § 5.6.4.3
    """
    return client.call(
        messages.ZcashGetIncomingViewingKey(
            z_address_n=z_address_n,
            coin_name=coin_name,
        )
    )


@expect(messages.ZcashAddress, field="address")
def get_address(
    client,
    t_address_n=[],
    z_address_n=[],
    diversifier_index=0,
    show_display=False,
    coin_name = "Zcash",
):
    """
    Returns a Zcash address.
    """
    return client.call(
        messages.ZcashGetAddress(
            t_address_n=t_address_n,
            z_address_n=z_address_n,
            diversifier_index=diversifier_index,
            show_display=show_display,
            coin_name=coin_name,
        )
    )


def encode_memo(memo):
    encoded = memo.encode("utf-8")
    if len(encoded) < 512:
        raise ValueError("Memo is too long.")
    return encoded + (512 - len(encoded))*b"\x00"


EMPTY_ANCHOR = bytes.fromhex("ae2935f1dfd8a24aed7c70df7de3a668eb7a49b1319880dde2bbd9031ae5d82f")


def sign_tx(
    client,
    t_inputs = [],
    t_outputs = [],
    o_inputs = [],
    o_outputs = [],
    coin_name = "Zcash",
    version_group_id = 0x26A7270A,  # protocol spec §7.1.2
    branch_id = 0xC2D6D0B4,  # https://zips.z.cash/zip-0252
    expiry = 0,
    anchor = EMPTY_ANCHOR,
    verbose = False,
):
    def log(*args, **kwargs):
        if verbose:
            print(*args, **kwargs)

    msg = messages.SignTx()

    msg.inputs_count = len(t_inputs)
    msg.outputs_count = len(t_outputs)
    msg.coin_name = coin_name
    msg.version = 5
    msg.version_group_id = version_group_id
    msg.branch_id = branch_id
    msg.expiry = expiry

    orchard = messages.ZcashOrchardBundleInfo()
    orchard.outputs_count = len(o_outputs)
    orchard.inputs_count = len(o_inputs)
    orchard.anchor = anchor
    orchard.enable_spends = True
    orchard.enable_outputs = True

    msg.orchard = orchard
    if o_inputs or o_outputs:
        actions_count = max(2, len(o_inputs), len(o_outputs))
    else:
        actions_count = 0

    signatures = {
        SigType.TRANSPARENT: [None] * len(t_inputs),
        SigType.ORCHARD_SPEND_AUTH: [None] * actions_count,
    }

    serialized_tx = b""

    print("T <- sign tx")
    res = client.call(msg)

    R = messages.RequestType
    while isinstance(res, messages.TxRequest):
        # If there's some part of signed transaction, let's add it
        if res.serialized:
            if res.serialized.serialized_tx:
                log("T -> serialized tx ({} bytes)".format(len(res.serialized.serialized_tx)))
                serialized_tx += res.serialized.serialized_tx

            if res.serialized.signature_index is not None:
                idx = res.serialized.signature_index
                sig = res.serialized.signature
                sig_type = res.serialized.signature_type
                if signatures[sig_type][idx] is not None:
                    raise ValueError("Signature for index {} already filled".format(idx))
                log("T -> {} signature {}".format(
                    {
                        SigType.TRANSPARENT: "t",
                        SigType.ORCHARD_SPEND_AUTH: "o auth",
                    }[sig_type],
                    idx)
                )
                signatures[sig_type][idx] = sig


        log("")

        if res.request_type == R.TXFINISHED:
            break

        elif res.request_type == R.TXINPUT:
            log("T <- t input", res.details.request_index)
            msg = messages.TransactionType()
            msg.inputs = [t_inputs[res.details.request_index]]
            res = client.call(messages.TxAck(tx=msg))

        elif res.request_type == R.TXOUTPUT:
            log("T <- t output", res.details.request_index)
            msg = messages.TransactionType()
            msg.outputs = [t_outputs[res.details.request_index]]
            res = client.call(messages.TxAck(tx=msg))

        elif res.request_type == R.TXORCHARDINPUT:
            txi = o_inputs[res.details.request_index]
            log("T <- o input ", res.details.request_index)
            res = client.call(txi)

        elif res.request_type == R.TXORCHARDOUTPUT:
            txo = o_outputs[res.details.request_index]
            log("T <- o output", res.details.request_index)
            res = client.call(txo)

        elif res.request_type == R.NO_OP:
            res = client.call(messages.ZcashAck())

        else:
            raise ValueError("unexpected request type: {}".format(res.request_type))

    if not isinstance(res, messages.TxRequest):
        raise exceptions.TrezorException("Unexpected message")

    return signatures, serialized_tx
