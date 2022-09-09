#!/usr/bin/env python3
from __future__ import annotations

import copy
import datetime
import io
import json
import os
import pathlib
import re
import shutil
from collections import defaultdict
from typing import Any, Dict, List, TextIO, Tuple, cast

import click
import ed25519
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from coin_info import (
    Coin,
    CoinBuckets,
    Coins,
    _load_builtin_erc20_tokens,
    _load_builtin_ethereum_networks,
    load_json,
)
from merkle_tree import MerkleTree
from trezorlib import protobuf
from trezorlib.messages import (
    EthereumDefinitionType,
    EthereumNetworkInfo,
    EthereumTokenInfo,
)

FORMAT_VERSION = "trzd1"
FORMAT_VERSION_BYTES = FORMAT_VERSION.encode("utf-8").ljust(8, b"\0")
ACTUAL_TIME = datetime.datetime.now(datetime.timezone.utc)
ACTUAL_TIMESTAMP_STR = ACTUAL_TIME.strftime("%d.%m.%Y %X%z")
DATA_VERSION_BYTES = int(ACTUAL_TIME.timestamp()).to_bytes(4, "big")


if os.environ.get("DEFS_DIR"):
    DEFS_DIR = pathlib.Path(os.environ.get("DEFS_DIR")).resolve()
else:
    DEFS_DIR = pathlib.Path(__file__).resolve().parent.parent / "defs"

DEFINITIONS_CACHE_FILEPATH = pathlib.Path().absolute() / "definitions-cache.json"

# ====== utils ======


def hash_dict_on_keys(
    d: Dict,
    include_keys: List[str] | None = None,
    exclude_keys: List[str] | None = None,
) -> int:
    """Get the hash of a dict on selected keys.
    Options `include_keys` and `exclude_keys` are exclusive."""
    if include_keys is not None and exclude_keys is not None:
        raise TypeError("Options `include_keys` and `exclude_keys` are exclusive")

    tmp_dict = dict()
    for k, v in d.items():
        if include_keys is not None and k in include_keys:
            tmp_dict[k] = v
        elif exclude_keys is not None and k not in exclude_keys:
            tmp_dict[k] = v
        elif include_keys is None and exclude_keys is None:
            tmp_dict[k] = v

    return hash(json.dumps(tmp_dict, sort_keys=True))


class Cache:
    """Generic cache object that caches to json."""

    def __init__(self, cache_filepath: pathlib.Path) -> None:
        self.cache_filepath = cache_filepath
        self.cached_data: Any = dict()

    def is_expired(self) -> bool:
        mtime = (
            self.cache_filepath.stat().st_mtime if self.cache_filepath.is_file() else 0
        )
        return mtime <= (ACTUAL_TIME - datetime.timedelta(hours=1)).timestamp()

    def load(self) -> None:
        self.cached_data = load_json(self.cache_filepath)

    def save(self) -> None:
        with open(self.cache_filepath, "w+") as f:
            json.dump(
                obj=self.cached_data, fp=f, ensure_ascii=False, sort_keys=True, indent=1
            )
            f.write("\n")

    def get(self, key: Any, default: Any = None) -> Any:
        return self.cached_data.get(key, default)

    def set(self, key: Any, data: Any) -> None:
        self.cached_data[key] = copy.deepcopy(data)

    def __contains__(self, key):
        return key in self.cached_data


class EthereumDefinitionsCachedDownloader:
    """Class that handles all the downloading and caching of Ethereum definitions."""

    def __init__(self, refresh: bool | None = None) -> None:
        force_refresh = refresh is True
        disable_refresh = refresh is False
        self.use_cache = False
        self.cache = Cache(DEFINITIONS_CACHE_FILEPATH)

        if disable_refresh or (not self.cache.is_expired() and not force_refresh):
            print("Loading cached Ethereum definitions data")
            self.cache.load()
            self.use_cache = True
        else:
            self._init_requests_session()

    def save_cache(self):
        if not self.use_cache:
            self.cache.save()

    def _download_as_json_from_url(
        self, url: str, url_params: dict[str, Any] | None = None
    ) -> Any:
        # convert params to strings
        params = dict()
        if url_params:
            params = {key: str(value).lower() for key, value in url_params.items()}

        key = url + str(params)
        if self.use_cache:
            return self.cache.get(key)

        print(f"Fetching data from {url}")

        r = self.session.get(url, params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
        self.cache.set(key, data)
        return data

    def _init_requests_session(self) -> requests.Session:
        self.session = requests.Session()
        retries = Retry(total=5, status_forcelist=[502, 503, 504])
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def get_coingecko_asset_platforms(self) -> Any:
        url = "https://api.coingecko.com/api/v3/asset_platforms"
        return self._download_as_json_from_url(url)

    def get_defillama_chains(self) -> Any:
        url = "https://api.llama.fi/chains"
        return self._download_as_json_from_url(url)

    def get_coingecko_tokens_for_network(self, coingecko_network_id: str) -> Any:
        url = f"https://tokens.coingecko.com/{coingecko_network_id}/all.json"
        data = None
        try:
            data = self._download_as_json_from_url(url)
        except requests.exceptions.HTTPError as err:
            # "Forbidden" is raised by Coingecko if no tokens are available under specified id
            if err.response.status_code != requests.codes.forbidden:
                raise err

        return [] if data is None else data.get("tokens", [])

    def get_coingecko_coins_list(self) -> Any:
        url = "https://api.coingecko.com/api/v3/coins/list"
        return self._download_as_json_from_url(url, {"include_platform": "true"})

    def get_coingecko_top100(self) -> Any:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        return self._download_as_json_from_url(
            url,
            {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": 100,
                "page": 1,
                "sparkline": "false",
            },
        )


def _load_ethereum_networks_from_repo(repo_dir: pathlib.Path) -> List[Dict]:
    """Load ethereum networks from submodule."""
    chains_path = repo_dir / "_data" / "chains"
    networks = []
    for chain in sorted(
        chains_path.glob("eip155-*.json"),
        key=lambda x: int(x.stem.replace("eip155-", "")),
    ):
        chain_data = load_json(chain)
        shortcut = chain_data["nativeCurrency"]["symbol"]
        name = chain_data["name"]
        title = chain_data.get("title", "")
        is_testnet = "testnet" in name.lower() or "testnet" in title.lower()
        if is_testnet:
            slip44 = 1
        else:
            slip44 = chain_data.get("slip44", 60)

        if is_testnet and not shortcut.lower().startswith("t"):
            shortcut = "t" + shortcut

        rskip60 = shortcut in ("RBTC", "TRBTC")

        # strip out bullcrap in network naming
        if "mainnet" in name.lower():
            name = re.sub(r" mainnet.*$", "", name, flags=re.IGNORECASE)

        networks.append(
            dict(
                chain=chain_data["shortName"],
                chain_id=chain_data["chainId"],
                slip44=slip44,
                shortcut=shortcut,
                name=name,
                rskip60=rskip60,
                url=chain_data["infoURL"],
            )
        )

    return networks


def _create_cropped_token_dict(
    complex_token: dict, chain_id: str, chain: str
) -> dict | None:
    # simple validation
    if complex_token["address"][:2] != "0x" or int(complex_token["decimals"]) < 0:
        return None
    try:
        bytes.fromhex(complex_token["address"][2:])
    except ValueError:
        return None

    return dict(
        chain=chain,
        chain_id=chain_id,
        name=complex_token["name"],
        decimals=complex_token["decimals"],
        address=str(complex_token["address"]).lower(),
        shortcut=complex_token["symbol"],
    )


def _load_erc20_tokens_from_coingecko(
    downloader: EthereumDefinitionsCachedDownloader, networks: List[Dict]
) -> List[Dict]:
    tokens: List[Dict] = []
    for network in networks:
        if network.get("coingecko_id") is not None:
            all_tokens = downloader.get_coingecko_tokens_for_network(
                network.get("coingecko_id")
            )

            for token in all_tokens:
                t = _create_cropped_token_dict(
                    token, network["chain_id"], network["chain"]
                )
                if t is not None:
                    tokens.append(t)

    return tokens


def _load_erc20_tokens_from_repo(
    repo_dir: pathlib.Path, networks: List[Dict]
) -> List[Dict]:
    """Load ERC20 tokens from submodule."""
    tokens: List[Dict] = []
    for network in networks:
        chain = network["chain"]

        chain_path = repo_dir / "tokens" / chain
        for file in sorted(chain_path.glob("*.json")):
            token: dict = load_json(file)
            t = _create_cropped_token_dict(token, network["chain_id"], network["chain"])
            if t is not None:
                tokens.append(t)

    return tokens


def remove_builtin_definitions(networks: List[Dict], tokens: List[Dict]) -> None:
    builtin_networks = _load_builtin_ethereum_networks()
    builtin_tokens = _load_builtin_erc20_tokens()

    networks_by_chain_id = defaultdict(list)
    for n in networks:
        networks_by_chain_id[n["chain_id"]].append(n)

    tokens_by_chain_id_and_address = defaultdict(list)
    for t in tokens:
        tokens_by_chain_id_and_address[(t["chain_id"], t["address"])].append(t)

    for bn in builtin_networks:
        for n in networks_by_chain_id.get(int(bn["chain_id"]), []):
            networks.remove(n)

    for bt in builtin_tokens:
        for t in tokens_by_chain_id_and_address.get(
            (int(bt["chain_id"]), bt["address"]), []
        ):
            tokens.remove(t)


def _set_definition_metadata(
    definition: Dict,
    old_definition: Dict | None = None,
    keys: str | None = None,
    deleted: bool = False,
) -> None:
    if "metadata" not in definition:
        definition["metadata"] = dict()

    if deleted:
        definition["metadata"]["deleted"] = ACTUAL_TIMESTAMP_STR
    else:
        definition["metadata"].pop("deleted", None)

    if old_definition is not None and keys is not None:
        for key in keys:
            definition["metadata"]["previous_" + key] = old_definition.get(key)

    # if metadata are empty, delete them
    if len(definition["metadata"]) == 0:
        definition.pop("metadata", None)


def print_definition_change(
    name: str,
    status: str,
    old: Dict,
    new: Dict | None = None,
    original: Dict | None = None,
    prompt: bool = False,
    use_default: bool = True,
) -> bool | None:
    """Print changes made between definitions and ask for prompt if requested. Returns the prompt result if prompted otherwise None."""
    old_deleted_status = get_definition_deleted_status(old)
    old_deleted_status_wrapped = (
        " (" + old_deleted_status + ")" if old_deleted_status else ""
    )

    title = f"{old_deleted_status + ' ' if old_deleted_status else ''}{name} PROBABLY {status}"
    print(f"== {title} ==")
    print(f"OLD{old_deleted_status_wrapped}:")
    print(json.dumps(old, sort_keys=True, indent=None))
    if new is not None:
        print("NEW:")
        print(json.dumps(new, sort_keys=True, indent=None))
        if original is not None:
            original_deleted_status_wrapped = (
                " (" + get_definition_deleted_status(original) + ")"
                if get_definition_deleted_status(original)
                else ""
            )
            print(f"REPLACING{original_deleted_status_wrapped}:")
            print(json.dumps(original, sort_keys=True, indent=None))

    if prompt:
        answer = click.prompt(
            "Confirm change:",
            type=click.Choice(["y", "n"]),
            show_choices=True,
            default="y" if use_default else None,
            show_default=use_default,
        )
        return True if answer == "y" else False
    return None


def print_definitions_collision(
    name: str,
    definitions: List[Dict],
    old_definitions: List[Dict] | None = None,
    prompt: bool = True,
) -> int | None:
    """Print colliding definitions and ask which one to keep if requested.
    Returns a tuple composed from the prompt result if prompted otherwise None and the default value."""
    if old_definitions:
        old_defs_hash_no_metadata = [
            hash_dict_on_keys(d, exclude_keys=["metadata"]) for d in old_definitions
        ]

    default_index = None
    title = f"COLLISION BETWEEN {name}S"
    print(f"== {title} ==")
    for idx, definition in enumerate(definitions):
        found = ""
        if (
            old_definitions
            and hash_dict_on_keys(definition, exclude_keys=["metadata"])
            in old_defs_hash_no_metadata
        ):
            found = " (found in old definitions)"
            default_index = idx
        print(f"DEFINITION {idx}{found}:")
        print(json.dumps(definition, sort_keys=True, indent=None))

    answer = None
    if prompt:
        answer = int(
            click.prompt(
                "Which definition do you want to keep? Please enter a valid integer",
                type=click.Choice([str(n) for n in range(len(definitions))]),
                show_choices=True,
                default=str(default_index) if default_index is not None else None,
                show_default=default_index is not None,
            )
        )
    return answer, default_index


def get_definition_deleted_status(definition: Dict) -> str:
    return (
        "PREVIOUSLY DELETED"
        if definition.get("metadata", {}).get("deleted") is not None
        else ""
    )


def check_tokens_collisions(tokens: List[Dict], old_tokens: List[Dict] | None) -> None:
    collisions: defaultdict = defaultdict(list)
    for idx, nd in enumerate(tokens):
        collisions[hash_dict_on_keys(nd, ["chain_id", "address"])].append(idx)

    no_of_collisions = 0
    for _, v in collisions.items():
        if len(v) > 1:
            no_of_collisions += 1

    if no_of_collisions > 0:
        print(f"\nNumber of collisions: {no_of_collisions}")

    # solve collisions
    delete_indexes = []
    for _, v in collisions.items():
        if len(v) > 1:
            coliding_networks = [tokens[i] for i in v]
            choice, default = print_definitions_collision(
                "TOKEN", coliding_networks, old_tokens
            )
            index = choice if choice is not None else default
            print(f"Keeping the definition with index {index}.")
            v.pop(index)
            delete_indexes.extend(v)

    # delete collisions
    delete_indexes.sort(reverse=True)
    for idx in delete_indexes:
        tokens.pop(idx)


def check_definitions_list(
    old_defs: List[Dict],
    new_defs: List[Dict],
    main_keys: List[str],
    def_name: str,
    interactive: bool,
    force: bool,
    top100_coingecko_ids: List[str] | None = None,
) -> None:
    # store already processed definitions
    deleted_definitions: List[Dict] = []
    modified_definitions: List[Dict] = []
    moved_definitions: List[Tuple] = []
    resurrected_definitions: List[Tuple] = []

    # dicts of new definitions
    defs_hash_no_metadata = dict()
    defs_hash_no_main_keys_and_metadata = dict()
    defs_hash_only_main_keys = dict()
    for nd in new_defs:
        defs_hash_no_metadata[hash_dict_on_keys(nd, exclude_keys=["metadata"])] = nd
        defs_hash_no_main_keys_and_metadata[
            hash_dict_on_keys(nd, exclude_keys=main_keys + ["metadata"])
        ] = nd
        defs_hash_only_main_keys[hash_dict_on_keys(nd, main_keys)] = nd

    # dict of old definitions
    old_defs_hash_only_main_keys = {
        hash_dict_on_keys(d, main_keys): d for d in old_defs
    }

    # mark all resurrected, moved, modified or deleted definitions
    for old_def in old_defs:
        old_def_hash_only_main_keys = hash_dict_on_keys(old_def, main_keys)
        old_def_hash_no_metadata = hash_dict_on_keys(old_def, exclude_keys=["metadata"])
        old_def_hash_no_main_keys_and_metadata = hash_dict_on_keys(
            old_def, exclude_keys=main_keys + ["metadata"]
        )

        was_deleted_status = get_definition_deleted_status(old_def)

        if old_def_hash_no_metadata in defs_hash_no_metadata:
            # same definition found, check if it was not marked as deleted before
            if was_deleted_status:
                resurrected_definitions.append(old_def)
            else:
                # definition is unchanged, copy its metadata
                old_def_metadata = old_def.get("metadata")
                if old_def_metadata:
                    defs_hash_no_metadata[old_def_hash_no_metadata][
                        "metadata"
                    ] = old_def_metadata
        elif (
            old_def_hash_no_main_keys_and_metadata
            in defs_hash_no_main_keys_and_metadata
        ):
            # definition was moved
            # check if there was something before on this "position"
            new_def = defs_hash_no_main_keys_and_metadata[
                old_def_hash_no_main_keys_and_metadata
            ]
            new_def_hash_only_main_keys = hash_dict_on_keys(new_def, main_keys)
            orig_def = old_defs_hash_only_main_keys.get(new_def_hash_only_main_keys)

            # check if the move is valid - "old_def" is not marked as deleted
            # and there was a change in the original definition
            if (
                orig_def is None
                or not was_deleted_status
                or hash_dict_on_keys(orig_def, exclude_keys=["metadata"])
                != hash_dict_on_keys(new_def, exclude_keys=["metadata"])
            ):
                moved_definitions.append((old_def, new_def, orig_def))
            else:
                # invalid move - this was an old move so we have to check if anything else
                # is coming to "old_def" position
                if old_def_hash_only_main_keys in defs_hash_only_main_keys:
                    modified_definitions.append(
                        (old_def, defs_hash_only_main_keys[old_def_hash_only_main_keys])
                    )
                else:
                    # no - so just maintain the "old_def"
                    new_defs.append(old_def)
        elif old_def_hash_only_main_keys in defs_hash_only_main_keys:
            # definition was modified
            modified_definitions.append(
                (old_def, defs_hash_only_main_keys[old_def_hash_only_main_keys])
            )
        else:
            # definition was not found - was it deleted before or just now?
            if not was_deleted_status:
                # definition was deleted now
                deleted_definitions.append(old_def)
            else:
                # no confirmation needed
                new_defs.append(old_def)

    # try to pair moved and modified definitions
    for old_def, new_def, orig_def in moved_definitions:
        # check if there is modified definition, that was modified to "new_def"
        # if yes it was because this "old_def" was moved to "orig_def" position
        if (orig_def, new_def) in modified_definitions:
            modified_definitions.remove((orig_def, new_def))

    def any_in_top_100(*definitions) -> bool:
        if definitions is not None:
            for d in definitions:
                if d is not None and d.get("coingecko_id") in top100_coingecko_ids:
                    return True
        return False

    # go through changes and ask for confirmation
    for old_def, new_def, orig_def in moved_definitions:
        accept_change = True
        print_change = any_in_top_100(old_def, new_def, orig_def)
        # if the change contains symbol change "--force" parameter must be used to be able to accept this change
        if (
            orig_def is not None
            and orig_def.get("shortcut") != new_def.get("shortcut")
            and not force
        ):
            print(
                "\nERROR: Symbol change in this definition! To be able to approve this change re-run with `--force` argument."
            )
            accept_change = False
            print_change = True

        answer = (
            print_definition_change(
                def_name.upper(),
                "MOVED",
                old_def,
                new_def,
                orig_def,
                prompt=interactive and accept_change,
            )
            if print_change
            else None
        )
        if answer is False or answer is None and not accept_change:
            # revert change - replace "new_def" with "old_def" and "orig_def"
            new_defs.remove(new_def)
            new_defs.append(old_def)
            new_defs.append(orig_def)
        else:
            _set_definition_metadata(new_def, old_def, main_keys)

            # if position of the "old_def" will remain empty leave on its former position a "mark"
            # that it has been deleted
            old_def_remains_empty = True
            for _, nd, _ in moved_definitions:
                if hash_dict_on_keys(old_def, main_keys) == hash_dict_on_keys(
                    nd, main_keys
                ):
                    old_def_remains_empty = False

            if old_def_remains_empty:
                _set_definition_metadata(old_def, deleted=True)
                new_defs.append(old_def)

    for old_def, new_def in modified_definitions:
        accept_change = True
        print_change = any_in_top_100(old_def, new_def)
        # if the change contains symbol change "--force" parameter must be used to be able to accept this change
        if (
            old_def.get("shortcut") != new_def.get("shortcut")
            and not force
        ):
            print(
                "\nERROR: Symbol change in this definition! To be able to approve this change re-run with `--force` argument."
            )
            accept_change = False
            print_change = True

        answer = (
            print_definition_change(
                def_name.upper(),
                "MODIFIED",
                old_def,
                new_def,
                prompt=interactive and accept_change,
            )
            if print_change
            else None
        )
        if answer is False or answer is None and not accept_change:
            # revert change - replace "new_def" with "old_def"
            new_defs.remove(new_def)
            new_defs.append(old_def)

    for definition in deleted_definitions:
        if (
            any_in_top_100(definition)
            and print_definition_change(
                def_name.upper(), "DELETED", definition, prompt=interactive
            )
            is False
        ):
            # revert change - add back the deleted definition
            new_defs.append(definition)
        else:
            _set_definition_metadata(definition, deleted=True)
            new_defs.append(definition)

    for definition in resurrected_definitions:
        if (
            any_in_top_100(definition)
            and print_definition_change(
                def_name.upper(), "RESURRECTED", definition, prompt=interactive
            )
            is not False
        ):
            # clear deleted mark
            _set_definition_metadata(definition)


def _load_prepared_definitions(definitions_file: pathlib.Path) -> tuple[list[dict], list[dict]]:
    if not definitions_file.is_file():
        click.ClickException(f"File {definitions_file} with prepared definitions does not exists or is not a file.")

    prepared_definitions_data = load_json(definitions_file)
    try:
        networks_data = prepared_definitions_data["networks"]
        tokens_data = prepared_definitions_data["tokens"]
    except KeyError:
        click.ClickException(f"File with prepared definitions is not complete. Whole \"networks\" and/or \"tokens\" section are missing.")

    networks: Coins = []
    for network_data in networks_data:
        network_data.update(
            chain_id=str(network_data["chain_id"]),
            key=f"eth:{network_data['shortcut']}",
        )
        networks.append(cast(Coin, network_data))

    tokens: Coins = []

    for token in tokens_data:
        token.update(
            chain_id=str(token["chain_id"]),
            address=token["address"].lower(),
            address_bytes=bytes.fromhex(token["address"][2:]),
            symbol=token["shortcut"],
            key=f"erc20:{token['chain']}:{token['shortcut']}",
        )
        tokens.append(cast(Coin, token))

    return networks, tokens


# ====== coindefs generators ======


def eth_info_from_dict(
    coin: Coin, msg_type: EthereumNetworkInfo | EthereumTokenInfo
) -> EthereumNetworkInfo | EthereumTokenInfo:
    attributes: Dict[str, Any] = dict()
    for field in msg_type.FIELDS.values():
        val = coin.get(field.name)

        if field.name in ("chain_id", "slip44"):
            attributes[field.name] = int(val)
        elif msg_type == EthereumTokenInfo and field.name == "address":
            attributes[field.name] = coin.get("address_bytes")
        else:
            attributes[field.name] = val

    proto = msg_type(**attributes)

    return proto


def serialize_eth_info(
    info: EthereumNetworkInfo | EthereumTokenInfo, data_type_num: EthereumDefinitionType
) -> bytes:
    ser = FORMAT_VERSION_BYTES
    ser += data_type_num.to_bytes(1, "big")
    ser += DATA_VERSION_BYTES

    buf = io.BytesIO()
    protobuf.dump_message(buf, info)
    msg = buf.getvalue()
    # write the length of encoded protobuf message
    ser += len(msg).to_bytes(2, "big")
    ser += msg

    return ser


def sign_data(sign_key: ed25519.SigningKey, data: bytes) -> bytes:
    return sign_key.sign(data)


# ====== click command handlers ======


@click.group()
def cli() -> None:
    """Script for handling Ethereum definitions (networks and tokens)."""


@cli.command()
@click.option(
    "-r/-R",
    "--refresh/--no-refresh",
    default=None,
    help="Force refresh or no-refresh data. By default tries to load cached data.",
)
@click.option(
    "-i",
    "--interactive",
    is_flag=True,
    help="Ask about every change. Without this option script will automatically accept all changes to the definitions "
    "(except those in symbols, see `--force` option).",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Changes to symbols in definitions could be accepted.",
)
@click.option(
    "-s",
    "--show-all",
    is_flag=True,
    help="Show the differences of all definitions. By default only changes to top 100 definitions (by Coingecko market cap ranking) are shown.",
)
@click.option(
    "-d",
    "--deffile",
    type=click.Path(resolve_path=True, dir_okay=False, path_type=pathlib.Path),
    default="./definitions-latest.json",
    help="File where the definitions will be saved in json format. If file already exists, it is used to check "
    "the changes in definitions.",
)
@click.option(
    "-n",
    "--networks-dir",
    type=click.Path(
        exists=True, file_okay=False, resolve_path=True, path_type=pathlib.Path
    ),
    default=DEFS_DIR / "ethereum" / "chains",
    help="Directory pointing at cloned networks definition repo (https://github.com/ethereum-lists/chains). "
    "Defaults to `$(DEFS_DIR)/ethereum/chains` if env variable `DEFS_DIR` is set, otherwise to "
    '`"this script location"/../defs/ethereum/chains`',
)
@click.option(
    "-t",
    "--tokens-dir",
    type=click.Path(
        exists=True, file_okay=False, resolve_path=True, path_type=pathlib.Path
    ),
    default=DEFS_DIR / "ethereum" / "tokens",
    help="Directory pointing at cloned networks definition repo (https://github.com/ethereum-lists/tokens). "
    "Defaults to `$(DEFS_DIR)/ethereum/tokens` if env variable `DEFS_DIR` is set, otherwise to "
    '`"this script location"/../defs/ethereum/tokens`',
)
def prepare_definitions(
    refresh: bool | None,
    interactive: bool,
    force: bool,
    show_all: bool,
    deffile: pathlib.Path,
    networks_dir: pathlib.Path,
    tokens_dir: pathlib.Path,
) -> None:
    """Prepare Ethereum definitions."""
    # init Ethereum definitions downloader
    downloader = EthereumDefinitionsCachedDownloader(refresh)

    networks = _load_ethereum_networks_from_repo(networks_dir)

    # coingecko API
    cg_platforms = downloader.get_coingecko_asset_platforms()
    cg_platforms_by_chain_id: dict[int, Any] = dict()
    for chain in cg_platforms:
        # We want only informations about chains, that have both chain id and coingecko id,
        # otherwise we could not link local and coingecko networks.
        if chain["chain_identifier"] is not None and chain["id"] is not None:
            cg_platforms_by_chain_id[chain["chain_identifier"]] = chain["id"]

    # defillama API
    dl_chains = downloader.get_defillama_chains()
    dl_chains_by_chain_id: dict[int, Any] = dict()
    for chain in dl_chains:
        # We want only informations about chains, that have both chain id and coingecko id,
        # otherwise we could not link local and coingecko networks.
        if chain["chainId"] is not None and chain["gecko_id"] is not None:
            dl_chains_by_chain_id[chain["chainId"]] = chain["gecko_id"]

    # We will try to get as many "coingecko_id"s as possible to be able to use them afterwards
    # to load tokens from coingecko. We won't use coingecko networks, because we don't know which
    # ones are EVM based.
    coingecko_id_to_chain_id = dict()
    for network in networks:
        if network.get("coingecko_id") is None:
            # first try to assign coingecko_id to local networks from coingecko via chain_id
            if network["chain_id"] in cg_platforms_by_chain_id:
                network["coingecko_id"] = cg_platforms_by_chain_id[network["chain_id"]]
            # or try to assign coingecko_id to local networks from defillama via chain_id
            elif network["chain_id"] in dl_chains_by_chain_id:
                network["coingecko_id"] = dl_chains_by_chain_id[network["chain_id"]]

        # if we found "coingecko_id" add it to the map - used later to map tokens with coingecko ids
        if network.get("coingecko_id") is not None:
            coingecko_id_to_chain_id[network["coingecko_id"]] = network["chain_id"]

    # get tokens
    cg_tokens = _load_erc20_tokens_from_coingecko(downloader, networks)
    repo_tokens = _load_erc20_tokens_from_repo(tokens_dir, networks)

    # merge tokens
    tokens: List[Dict] = []
    cg_tokens_chain_id_and_address = []
    for t in cg_tokens:
        if t not in tokens:
            # add only unique tokens
            tokens.append(t)
            cg_tokens_chain_id_and_address.append((t["chain_id"], t["address"]))
    for t in repo_tokens:
        if (
            t not in tokens
            and (t["chain_id"], t["address"]) not in cg_tokens_chain_id_and_address
        ):
            # add only unique tokens and prefer CoinGecko in case of collision of chain id and token address
            tokens.append(t)

    old_defs = None
    if deffile.exists():
        # load old definitions
        old_defs = load_json(deffile)

    remove_builtin_definitions(networks, tokens)

    check_tokens_collisions(
        tokens, old_defs["tokens"] if old_defs is not None else None
    )

    # map coingecko ids to tokens
    tokens_by_chain_id_and_address = {(t["chain_id"], t["address"]): t for t in tokens}
    cg_coin_list = downloader.get_coingecko_coins_list()
    for coin in cg_coin_list:
        for platform_name, address in coin.get("platforms", dict()).items():
            key = (coingecko_id_to_chain_id.get(platform_name), address)
            if key in tokens_by_chain_id_and_address:
                tokens_by_chain_id_and_address[key]["coingecko_id"] = coin["id"]

    # load top 100 (by market cap) definitions from CoinGecko
    cg_top100_ids = [d["id"] for d in downloader.get_coingecko_top100()]

    # save cache
    downloader.save_cache()

    # check changes in definitions
    if old_defs is not None:
        # check networks and tokens
        check_definitions_list(
            old_defs["networks"],
            networks,
            ["chain_id"],
            "network",
            interactive,
            force,
            cg_top100_ids if not show_all else None,
        )
        check_definitions_list(
            old_defs["tokens"],
            tokens,
            ["chain_id", "address"],
            "token",
            interactive,
            force,
            cg_top100_ids if not show_all else None,
        )

    # sort networks and tokens
    networks.sort(key=lambda x: x["chain_id"])
    tokens.sort(key=lambda x: (x["chain_id"], x["address"]))

    # save results
    with open(deffile, "w+") as f:
        json.dump(
            obj=dict(networks=networks, tokens=tokens),
            fp=f,
            ensure_ascii=False,
            sort_keys=True,
            indent=1,
        )
        f.write("\n")


@cli.command()
@click.option(
    "-o",
    "--outdir",
    type=click.Path(resolve_path=True, file_okay=False, path_type=pathlib.Path),
    default="./definitions-latest",
)
@click.option(
    "-k",
    "--privatekey",
    type=click.File(mode="r"),
    help="Private key (text, hex formated) to use to sign data. Could be also loaded from `PRIVATE_KEY` env variable. Provided file is preffered over env variable.",
)
@click.option(
    "-d",
    "--deffile",
    type=click.Path(resolve_path=True, dir_okay=False, path_type=pathlib.Path),
    default="./definitions-latest.json",
    help="File where the prepared definitions are saved in json format."
)
def sign_definitions(outdir: pathlib.Path, privatekey: TextIO, deffile: pathlib.Path) -> None:
    """Generate signed Ethereum definitions for python-trezor and others."""
    hex_key = None
    if privatekey is None:
        # load from env variable
        hex_key = os.getenv("PRIVATE_KEY", default=None)
    else:
        with privatekey:
            hex_key = privatekey.readline()

    if hex_key is None:
        raise click.ClickException("No private key for signing was provided.")

    sign_key = ed25519.SigningKey(ed25519.from_ascii(hex_key, encoding="hex"))

    def save_definition(directory: pathlib.Path, keys: list[str], data: bytes):
        complete_file_path = directory / ("_".join(keys) + ".dat")

        if complete_file_path.exists():
            raise click.ClickException(
                f"Definition \"{complete_file_path}\" already generated - attempt to generate another definition."
            )

        directory.mkdir(parents=True, exist_ok=True)
        with open(complete_file_path, mode="wb+") as f:
            f.write(data)

    def generate_token_defs(tokens: Coins):
        for token in tokens:
            if token["address"] is None or token["chain_id"] is None:
                continue

            # save token definition
            save_definition(
                outdir / "by_chain_id" / token["chain_id"],
                ["token", token["address"][2:].lower()],
                token["serialized"],
            )

    def generate_network_def(network: Coin):
        if network["chain_id"] is None:
            return

        # create path for networks identified by chain and slip44 ids
        network_dir = outdir / "by_chain_id" / network["chain_id"]
        slip44_dir = outdir / "by_slip44" / str(network["slip44"])
        # save network definition
        save_definition(network_dir, ["network"], network["serialized"])

        try:
            # TODO: this way only the first network with given slip is saved - save other networks??
            save_definition(slip44_dir, ["network"], network["serialized"])
        except click.ClickException:
            pass

    # load prepared definitions
    networks, tokens = _load_prepared_definitions(deffile)

    # clear defs directory
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True)

    # serialize definitions
    definitions_by_serialization: dict[bytes, dict] = dict()
    for network in networks:
        ser = serialize_eth_info(
            eth_info_from_dict(network, EthereumNetworkInfo), EthereumDefinitionType.NETWORK
        )
        network["serialized"] = ser
        definitions_by_serialization[ser] = network
    for token in tokens:
        ser = serialize_eth_info(
            eth_info_from_dict(token, EthereumTokenInfo), EthereumDefinitionType.TOKEN
        )
        token["serialized"] = ser
        definitions_by_serialization[ser] = token

    # build Merkle tree
    mt = MerkleTree(
        [network["serialized"] for network in networks] +
        [token["serialized"] for token in tokens]
    )

    # sign tree root hash
    signed_root_hash = sign_data(sign_key, mt.get_root_hash())

    # update definitions
    for ser, proof in mt.get_proofs().items():
        definition = definitions_by_serialization[ser]
        # append number of hashes in proof
        definition["serialized"] += len(proof).to_bytes(1, "big")
        # append proof itself
        for p in proof:
            definition["serialized"] += p
        # append signed tree root hash
        definition["serialized"] += signed_root_hash

    for network in networks:
        generate_network_def(network)

    generate_token_defs(tokens)


if __name__ == "__main__":
    cli()
