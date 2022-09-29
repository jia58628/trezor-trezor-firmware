from micropython import const
from typing import TYPE_CHECKING

from trezor.crypto import hashlib
from trezor.wire import ProcessError

from apps.common import cbor

from . import addresses

if TYPE_CHECKING:
    CatalystRegistrationPayload = dict[int, bytes | int]
    SignedCatalystRegistrationPayload = tuple[CatalystRegistrationPayload, bytes]
    CatalystRegistrationSignature = dict[int, bytes]
    CatalystRegistration = dict[
        int, CatalystRegistrationPayload | CatalystRegistrationSignature
    ]

    from trezor import messages
    from trezor.wire import Context

    from . import seed

_AUXILIARY_DATA_HASH_SIZE = const(32)
_CATALYST_VOTING_PUBLIC_KEY_LENGTH = const(32)
_CATALYST_REGISTRATION_HASH_SIZE = const(32)

_METADATA_KEY_CATALYST_REGISTRATION = const(61284)
_METADATA_KEY_CATALYST_REGISTRATION_SIGNATURE = const(61285)


def validate(auxiliary_data: messages.CardanoTxAuxiliaryData) -> None:
    fields_provided = 0
    if auxiliary_data.hash:
        fields_provided += 1
        # _validate_hash
        if len(auxiliary_data.hash) != _AUXILIARY_DATA_HASH_SIZE:
            raise ProcessError("Invalid auxiliary data")
    if auxiliary_data.catalyst_registration_parameters:
        fields_provided += 1
        _validate_catalyst_registration_parameters(
            auxiliary_data.catalyst_registration_parameters
        )

    if fields_provided != 1:
        raise ProcessError("Invalid auxiliary data")


def _validate_catalyst_registration_parameters(
    catalyst_registration_parameters: messages.CardanoCatalystRegistrationParametersType,
) -> None:
    from trezor.enums import CardanoAddressType
    from .helpers.paths import SCHEMA_STAKING_ANY_ACCOUNT

    if (
        len(catalyst_registration_parameters.voting_public_key)
        != _CATALYST_VOTING_PUBLIC_KEY_LENGTH
    ):
        raise ProcessError("Invalid auxiliary data")

    if not SCHEMA_STAKING_ANY_ACCOUNT.match(
        catalyst_registration_parameters.staking_path
    ):
        raise ProcessError("Invalid auxiliary data")

    address_parameters = catalyst_registration_parameters.reward_address_parameters
    if address_parameters.address_type == CardanoAddressType.BYRON:
        raise ProcessError("Invalid auxiliary data")

    addresses.validate_address_parameters(address_parameters)


async def show(
    ctx: Context,
    keychain: seed.Keychain,
    auxiliary_data_hash: bytes,
    catalyst_registration_parameters: messages.CardanoCatalystRegistrationParametersType
    | None,
    protocol_magic: int,
    network_id: int,
    should_show_details: bool,
) -> None:
    from .layout import show_auxiliary_data_hash

    if catalyst_registration_parameters:
        await _show_catalyst_registration(
            ctx,
            keychain,
            catalyst_registration_parameters,
            protocol_magic,
            network_id,
        )

    if should_show_details:
        await show_auxiliary_data_hash(ctx, auxiliary_data_hash)


async def _show_catalyst_registration(
    ctx: Context,
    keychain: seed.Keychain,
    catalyst_registration_parameters: messages.CardanoCatalystRegistrationParametersType,
    protocol_magic: int,
    network_id: int,
) -> None:
    from .helpers import bech32
    from .layout import confirm_catalyst_registration

    public_key = catalyst_registration_parameters.voting_public_key
    encoded_public_key = bech32.encode(bech32.HRP_JORMUN_PUBLIC_KEY, public_key)
    staking_path = catalyst_registration_parameters.staking_path
    reward_address = addresses.derive_human_readable(
        keychain,
        catalyst_registration_parameters.reward_address_parameters,
        protocol_magic,
        network_id,
    )
    nonce = catalyst_registration_parameters.nonce

    await confirm_catalyst_registration(
        ctx, encoded_public_key, staking_path, reward_address, nonce
    )


def get_hash_and_supplement(
    keychain: seed.Keychain,
    auxiliary_data: messages.CardanoTxAuxiliaryData,
    protocol_magic: int,
    network_id: int,
) -> tuple[bytes, messages.CardanoTxAuxiliaryDataSupplement]:
    from trezor.enums import CardanoTxAuxiliaryDataSupplementType
    from trezor import messages

    if parameters := auxiliary_data.catalyst_registration_parameters:
        (
            catalyst_registration_payload,
            catalyst_signature,
        ) = _get_signed_catalyst_registration_payload(
            keychain, parameters, protocol_magic, network_id
        )
        auxiliary_data_hash = _get_catalyst_registration_hash(
            catalyst_registration_payload, catalyst_signature
        )
        auxiliary_data_supplement = messages.CardanoTxAuxiliaryDataSupplement(
            type=CardanoTxAuxiliaryDataSupplementType.CATALYST_REGISTRATION_SIGNATURE,
            auxiliary_data_hash=auxiliary_data_hash,
            catalyst_signature=catalyst_signature,
        )
        return auxiliary_data_hash, auxiliary_data_supplement
    else:
        assert auxiliary_data.hash is not None  # validate_auxiliary_data
        return auxiliary_data.hash, messages.CardanoTxAuxiliaryDataSupplement(
            type=CardanoTxAuxiliaryDataSupplementType.NONE
        )


def _get_catalyst_registration_hash(
    catalyst_registration_payload: CatalystRegistrationPayload,
    catalyst_registration_payload_signature: bytes,
) -> bytes:
    # _cborize_catalyst_registration
    catalyst_registration_signature = {1: catalyst_registration_payload_signature}
    cborized_catalyst_registration = {
        _METADATA_KEY_CATALYST_REGISTRATION: catalyst_registration_payload,
        _METADATA_KEY_CATALYST_REGISTRATION_SIGNATURE: catalyst_registration_signature,
    }

    # _get_hash
    # _wrap_metadata
    # A new structure of metadata is used after Cardano Mary era. The metadata
    # is wrapped in a tuple and auxiliary_scripts may follow it. Cardano
    # tooling uses this new format of "wrapped" metadata even if no
    # auxiliary_scripts are included. So we do the same here.
    # https://github.com/input-output-hk/cardano-ledger-specs/blob/f7deb22be14d31b535f56edc3ca542c548244c67/shelley-ma/shelley-ma-test/cddl-files/shelley-ma.cddl#L212
    metadata = (cborized_catalyst_registration, ())
    auxiliary_data = cbor.encode(metadata)
    return hashlib.blake2b(
        data=auxiliary_data, outlen=_AUXILIARY_DATA_HASH_SIZE
    ).digest()


def _get_signed_catalyst_registration_payload(
    keychain: seed.Keychain,
    catalyst_registration_parameters: messages.CardanoCatalystRegistrationParametersType,
    protocol_magic: int,
    network_id: int,
) -> SignedCatalystRegistrationPayload:
    from .helpers.utils import derive_public_key

    staking_key = derive_public_key(
        keychain, catalyst_registration_parameters.staking_path
    )

    payload: CatalystRegistrationPayload = {
        1: catalyst_registration_parameters.voting_public_key,
        2: staking_key,
        3: addresses.derive_bytes(
            keychain,
            catalyst_registration_parameters.reward_address_parameters,
            protocol_magic,
            network_id,
        ),
        4: catalyst_registration_parameters.nonce,
    }

    signature = _create_catalyst_registration_payload_signature(
        keychain,
        payload,
        catalyst_registration_parameters.staking_path,
    )

    return payload, signature


def _create_catalyst_registration_payload_signature(
    keychain: seed.Keychain,
    catalyst_registration_payload: CatalystRegistrationPayload,
    path: list[int],
) -> bytes:
    from trezor.crypto.curve import ed25519

    node = keychain.derive(path)

    encoded_catalyst_registration = cbor.encode(
        {_METADATA_KEY_CATALYST_REGISTRATION: catalyst_registration_payload}
    )

    catalyst_registration_hash = hashlib.blake2b(
        data=encoded_catalyst_registration,
        outlen=_CATALYST_REGISTRATION_HASH_SIZE,
    ).digest()

    return ed25519.sign_ext(
        node.private_key(), node.private_key_ext(), catalyst_registration_hash
    )
