from typing import TYPE_CHECKING

from trezor.wire import ProcessError

if TYPE_CHECKING:
    from trezor.messages import NEMSignTx, NEMTransactionCommon


def validate(msg: NEMSignTx) -> None:
    from trezor.crypto import nem
    from trezor.enums import NEMModificationType
    from .helpers import (
        NEM_MAX_ENCRYPTED_PAYLOAD_SIZE,
        NEM_MAX_PLAIN_PAYLOAD_SIZE,
        NEM_MAX_DIVISIBILITY,
        NEM_MAX_SUPPLY,
    )

    _ProcessError = ProcessError  # local_cache_global

    nem_validate_address = nem.validate_address  # local_cache_attribute
    msg_transfer = msg.transfer  # local_cache_attribute
    msg_aggregate_modification = msg.aggregate_modification  # local_cache_attribute
    msg_multisig = msg.multisig  # local_cache_attribute
    msg_mosaic_creation = msg.mosaic_creation  # local_cache_attribute
    msg_transaction_network = msg.transaction.network  # local_cache_attribute

    # _validate_single_tx
    # ensure exactly one transaction is provided
    tx_count = (
        bool(msg_transfer)
        + bool(msg.provision_namespace)
        + bool(msg_mosaic_creation)
        + bool(msg.supply_change)
        + bool(msg_aggregate_modification)
        + bool(msg.importance_transfer)
    )
    if tx_count == 0:
        raise _ProcessError("No transaction provided")
    if tx_count > 1:
        raise _ProcessError("More than one transaction provided")

    _validate_common(msg.transaction)

    if msg_multisig:
        _validate_common(msg_multisig, True)
        # _validate_multisig
        if msg_multisig.network != msg_transaction_network:
            raise _ProcessError("Inner transaction network is different")
        _validate_public_key(
            msg_multisig.signer, "Invalid multisig signer public key provided"
        )
        # END _validate_multisig
    if not msg_multisig and msg.cosigning:
        raise _ProcessError("No multisig transaction to cosign")

    if msg_transfer:
        # _validate_transfer
        msg_transfer_payload = msg_transfer.payload  # local_cache_attribute

        if msg_transfer.public_key is not None:
            _validate_public_key(
                msg_transfer.public_key, "Invalid recipient public key"
            )
            if not msg_transfer_payload:
                raise _ProcessError("Public key provided but no payload to encrypt")

        if msg_transfer_payload:
            if len(msg_transfer_payload) > NEM_MAX_PLAIN_PAYLOAD_SIZE:
                raise _ProcessError("Payload too large")
            if (
                msg_transfer.public_key
                and len(msg_transfer_payload) > NEM_MAX_ENCRYPTED_PAYLOAD_SIZE
            ):
                raise _ProcessError("Payload too large")

        if not nem_validate_address(msg_transfer.recipient, msg_transaction_network):
            raise _ProcessError("Invalid recipient address")
        # END _validate_transfer
    if msg.provision_namespace:
        # _validate_provision_namespace
        if not nem_validate_address(
            msg.provision_namespace.sink, msg_transaction_network
        ):
            raise _ProcessError("Invalid rental sink address")
        # END _validate_provision_namespace
    if msg_mosaic_creation:
        # _validate_mosaic_creation
        if not nem_validate_address(msg_mosaic_creation.sink, msg_transaction_network):
            raise _ProcessError("Invalid creation sink address")

        msg_mosaic_creation_definition = msg_mosaic_creation.definition  # local_cache_attribute
        supply = msg_mosaic_creation_definition.supply  # local_cache_attribute
        divisibility = msg_mosaic_creation_definition.divisibility  # local_cache_attribute

        if msg_mosaic_creation_definition.name is not None:
            raise _ProcessError("Name not allowed in mosaic creation transactions")
        if msg_mosaic_creation_definition.ticker is not None:
            raise _ProcessError("Ticker not allowed in mosaic creation transactions")
        if msg_mosaic_creation_definition.networks:
            raise _ProcessError("Networks not allowed in mosaic creation transactions")

        if supply is not None and divisibility is None:
            raise _ProcessError(
                "Definition divisibility needs to be provided when supply is"
            )
        if supply is None and divisibility is not None:
            raise _ProcessError(
                "Definition supply needs to be provided when divisibility is"
            )

        if msg_mosaic_creation_definition.levy is not None:
            if msg_mosaic_creation_definition.fee is None:
                raise _ProcessError("No levy fee provided")
            if msg_mosaic_creation_definition.levy_address is None:
                raise _ProcessError("No levy address provided")
            if msg_mosaic_creation_definition.levy_namespace is None:
                raise _ProcessError("No levy namespace provided")
            if msg_mosaic_creation_definition.levy_mosaic is None:
                raise _ProcessError("No levy mosaic name provided")

            if divisibility is None:
                raise _ProcessError("No divisibility provided")
            if supply is None:
                raise _ProcessError("No supply provided")
            if msg_mosaic_creation_definition.mutable_supply is None:
                raise _ProcessError("No supply mutability provided")
            if msg_mosaic_creation_definition.transferable is None:
                raise _ProcessError("No mosaic transferability provided")
            if msg_mosaic_creation_definition.description is None:
                raise _ProcessError("No description provided")

            if divisibility > NEM_MAX_DIVISIBILITY:
                raise _ProcessError("Invalid divisibility provided")
            if supply > NEM_MAX_SUPPLY:
                raise _ProcessError("Invalid supply provided")

            if not nem_validate_address(
                msg_mosaic_creation_definition.levy_address, msg_transaction_network
            ):
                raise _ProcessError("Invalid levy address")
        # END _validate_mosaic_creation
    if msg.supply_change:
        # _validate_supply_change
        pass
        # END _validate_supply_change
    if msg_aggregate_modification:
        # _validate_aggregate_modification
        creation = msg_multisig is None
        if creation and not msg_aggregate_modification.modifications:
            raise _ProcessError("No modifications provided")

        for m in msg_aggregate_modification.modifications:
            if (
                creation
                and m.type == NEMModificationType.CosignatoryModification_Delete
            ):
                raise _ProcessError("Cannot remove cosignatory when converting account")
            _validate_public_key(
                m.public_key, "Invalid cosignatory public key provided"
            )
        # END _validate_aggregate_modification
    if msg.importance_transfer:
        # _validate_importance_transfer
        _validate_public_key(
            msg.importance_transfer.public_key,
            "Invalid remote account public key provided",
        )
        # END _validate_importance_transfer


def validate_network(network: int) -> None:
    from .helpers import (
        NEM_NETWORK_MAINNET,
        NEM_NETWORK_MIJIN,
        NEM_NETWORK_TESTNET,
    )

    if network not in (NEM_NETWORK_MAINNET, NEM_NETWORK_TESTNET, NEM_NETWORK_MIJIN):
        raise ProcessError("Invalid NEM network")


def _validate_common(common: NEMTransactionCommon, inner: bool = False) -> None:
    validate_network(common.network)

    common_signer = common.signer  # local_cache_attribute

    err = None

    if not inner and common_signer:
        raise ProcessError("Signer not allowed in outer transaction")

    if inner and common_signer is None:
        err = "signer"

    if err:
        if inner:
            raise ProcessError(f"No {err} provided in inner transaction")
        else:
            raise ProcessError(f"No {err} provided")

    if common_signer is not None:
        _validate_public_key(
            common_signer, "Invalid signer public key in inner transaction"
        )


def _validate_public_key(public_key: bytes | None, err_msg: str) -> None:
    from .helpers import NEM_PUBLIC_KEY_SIZE

    if not public_key:
        raise ProcessError(f"{err_msg} (none provided)")
    if len(public_key) != NEM_PUBLIC_KEY_SIZE:
        raise ProcessError(f"{err_msg} (invalid length)")
