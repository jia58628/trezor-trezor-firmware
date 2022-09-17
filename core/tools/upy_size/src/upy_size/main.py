from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from strategies import Settings, SpaceSaving
from strategies.function_inline import function_inline
from strategies.global_import_cache import global_import_cache
from strategies.import_one_function import one_function_import
from strategies.import_unused import import_unused
from strategies.keyword_arguments import keyword_arguments
from strategies.local_cache import local_cache
from strategies.local_cache_global import local_cache_global
from strategies.local_constants import local_constants, no_const_number
from strategies.small_classes import init_only_classes


@dataclass
class Problem:
    validator: str
    problems: list[SpaceSaving]


VALIDATORS = [
    function_inline,
    global_import_cache,
    one_function_import,
    import_unused,
    keyword_arguments,
    local_cache,
    local_cache_global,
    local_constants,
    no_const_number,
    init_only_classes,
]

# TODO: move this into JSON file and take the location as script argument
NOT_INLINABLE_FUNCTIONS = {
    "src/apps/misc/sign_identity.py": ["serialize_identity_without_proto"],
    "src/apps/base.py": [
        "busy_expiry_ms",
        "unlock_device",
        "reload_settings_from_storage",
    ],
    "src/apps/management/reset_device/__init__.py": ["backup_seed"],
    "src/apps/management/recovery_device/recover.py": ["fetch_previous_mnemonics"],
    "src/apps/management/recovery_device/homescreen.py": ["recovery_process"],
    "src/apps/cardano/addresses.py": [
        "validate_address_parameters",
        "get_bytes_unsafe",
        "encode_human_readable",
        "derive_bytes",
    ],
    "src/apps/cardano/layout.py": ["show_native_script"],
    "src/apps/cardano/helpers/utils.py": ["derive_public_key"],
    "src/apps/eos/helpers.py": ["base58_encode"],
    "src/apps/eos/writers.py": [
        "write_action_undelegate",
        "write_action_deleteauth",
        "write_action_unlinkauth",
        "write_bytes_prefixed",
    ],
    "src/apps/ethereum/helpers.py": ["address_from_bytes", "get_type_name"],
    "src/apps/ethereum/networks.py": ["by_chain_id"],
    "src/apps/ethereum/sign_message.py": ["message_digest"],
    "src/apps/ethereum/sign_tx.py": [
        "handle_erc20",
        "send_request_chunk",
        "check_common_fields",
    ],
    "src/apps/bitcoin/addresses.py": ["address_p2wpkh_in_p2sh", "address_p2wpkh"],
    "src/apps/bitcoin/ownership.py": ["get_identifier"],
    "src/apps/bitcoin/scripts.py": [
        "write_witness_p2tr",
        "write_witness_multisig",
        "write_witness_p2wpkh",
        "write_input_script_p2wsh_in_p2sh",
        "write_input_script_p2wpkh_in_p2sh",
        "output_script_native_segwit",
        "write_input_script_prefixed",
        "write_input_script_p2pkh_or_p2sh_prefixed",
        "output_script_p2pkh",
        "output_script_p2sh",
    ],
    "src/apps/bitcoin/sign_tx/omni.py": ["is_valid"],
    "src/apps/bitcoin/sign_tx/progress.py": ["report_init"],
    "src/apps/monero/layout.py": ["transaction_step"],
    "src/apps/monero/xmr/chacha_poly.py": ["encrypt"],
    "src/apps/monero/xmr/monero.py": [
        "generate_key_image",
        "generate_tx_spend_and_key_image",
    ],
    "src/apps/monero/xmr/keccak_hasher.py": ["get_keccak_writer"],
    "src/apps/monero/xmr/crypto_helpers.py": ["decodeint"],
    "src/apps/monero/xmr/serialize/int_serialize.py": [
        "uvarint_size",
        "dump_uvarint_b_into",
    ],
    "src/apps/monero/signing/offloading_keys.py": ["hmac_key_txin"],
    "src/apps/nem/validators.py": ["validate_network"],
    "src/apps/nem/writers.py": ["write_bytes_with_len"],
    "src/apps/stellar/layout.py": ["format_asset", "format_amount"],
    "src/apps/common/address_type.py": ["tobytes", "check"],
    "src/apps/common/address_mac.py": ["get_address_mac"],
    "src/apps/common/sdcard.py": ["ensure_sdcard"],
    "src/apps/common/paths.py": [
        "show_path_warning",
        "is_hardened",
        "address_n_to_str",
    ],
    "src/apps/common/writers.py": [
        "write_uint16_le",
        "write_uint32_le",
        "write_uint64_le",
    ],
    "src/apps/common/safety_checks.py": ["read_setting"],
    "src/apps/common/passphrase.py": ["is_enabled"],
    "src/apps/common/keychain.py": ["get_keychain", "with_slip44_keychain"],
}


UNEXPECTED_ERRORS = False


def get_potentially_saved_space(problems: list[Problem]) -> int:
    return sum(p.saved_bytes() for problem in problems for p in problem.problems)


def analyze_file(file_path: Path) -> int:
    with open(file_path, "r") as f:
        file_content = f.read()

    file_abs_path = str(file_path.absolute())
    for file, functions in NOT_INLINABLE_FUNCTIONS.items():
        if file_abs_path.endswith(file):
            not_inlineable_funcs = functions
            break
    else:
        not_inlineable_funcs = []

    FILE_SETTINGS = Settings(
        file_path=file_path, not_inlineable_funcs=not_inlineable_funcs
    )

    possible_saved_bytes = 0
    problems: list[Problem] = []
    for validator in VALIDATORS:
        try:
            result: list[SpaceSaving] = validator(file_content, FILE_SETTINGS)  # type: ignore
        except Exception as e:
            global UNEXPECTED_ERRORS
            UNEXPECTED_ERRORS = True  # type: ignore
            print(f"Error happened while validating file {file_path}")
            print(f"Validator: {validator.__name__}")
            print(e)
            continue

        if result:
            problems.append(Problem(validator.__name__, result))

    if problems:
        saved_bytes = get_potentially_saved_space(problems)
        possible_saved_bytes += saved_bytes
        print(file_path)
        print(f"Potentially saved bytes: {saved_bytes}")
        indent = " " * 4
        for problem in problems:
            print(f"{indent}{problem.validator}")
            for p in problem.problems:
                print(f"{2 * indent}{p}")
        print(80 * "*")

    return possible_saved_bytes


def main(path: str | Path) -> None:
    path = Path(path)
    possible_saved_bytes = 0
    if path.is_file():
        possible_saved_bytes += analyze_file(path)
    else:
        all_python_files = path.rglob("*.py")
        for file in all_python_files:
            possible_saved_bytes += analyze_file(file)
    print(f"Potentially saved bytes: {possible_saved_bytes}")


if __name__ == "__main__":
    path = sys.argv[1]
    main(path)
    if UNEXPECTED_ERRORS:
        print("There was some unexpected error. Please check the output.")
        sys.exit(1)
