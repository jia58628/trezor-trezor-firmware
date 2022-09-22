from __future__ import annotations

import sys
from pathlib import Path
import hashlib
import json
from typing import TypedDict

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


class Result(TypedDict):
    validator_name: str
    saved_bytes: int
    lines: list[str]


class FileResults(TypedDict):
    file_name: str
    saved_bytes: int
    results: list[Result]
    file_hash: str


HERE = Path(__file__).parent
NOT_INLINED_FILE = HERE / "not_inlineable.json"
CACHE_FILE = HERE / "cache.json"

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


UNEXPECTED_ERRORS = False


def get_uninlinable_functions(file_path: Path) -> list[str]:
    with open(NOT_INLINED_FILE, "r") as f:
        NOT_INLINABLE_FUNCTIONS = json.load(f)

    file_abs_path = str(file_path.absolute())
    for file, functions in NOT_INLINABLE_FUNCTIONS.items():
        if file_abs_path.endswith(file):
            return functions

    return []


def load_cache() -> dict[str, FileResults]:
    if not CACHE_FILE.exists():
        return {}

    with open(CACHE_FILE, "r") as f:
        return json.load(f)


GLOBAL_CACHE = load_cache()


def save_into_cache(file_results: FileResults) -> None:
    GLOBAL_CACHE[file_results["file_name"]] = file_results
    with open(CACHE_FILE, "w") as f:
        json.dump(GLOBAL_CACHE, f, indent=4)


def report_file_results(file_results: FileResults) -> None:
    if not file_results["results"]:
        return

    print(file_results["file_name"])
    print(f"Potentially saved bytes: {file_results['saved_bytes']}")
    indent = " " * 4
    for result in file_results["results"]:
        print(f"{indent}{result['validator_name']}")
        for line in result["lines"]:
            print(f"{2 * indent}{line}")
    print(80 * "*")


def analyze_file(file_path: Path) -> int:
    with open(file_path, "r") as f:
        file_content = f.read()

    abs_path = str(file_path.absolute())
    file_hash = hashlib.md5(file_content.encode()).hexdigest()
    if abs_path in GLOBAL_CACHE and GLOBAL_CACHE[abs_path]["file_hash"] == file_hash:
        file_results = GLOBAL_CACHE[abs_path]
    else:
        results = get_file_results(file_content, file_path)
        saved_bytes = sum(r["saved_bytes"] for r in results)
        file_results = FileResults(
            file_name=abs_path,
            saved_bytes=saved_bytes,
            results=results,
            file_hash=file_hash,
        )
        save_into_cache(file_results)

    report_file_results(file_results)

    return file_results["saved_bytes"]


def get_file_results(file_content: str, file_path: Path) -> list[Result]:
    not_inlineable_funcs = get_uninlinable_functions(file_path)
    FILE_SETTINGS = Settings(
        file_path=file_path, not_inlineable_funcs=not_inlineable_funcs
    )

    results: list[Result] = []
    for validator in VALIDATORS:
        try:
            # sys.stdout.write(f"Current validator: {validator.__name__}...\r")
            # sys.stdout.flush()
            result: list[SpaceSaving] = validator(file_content, FILE_SETTINGS)  # type: ignore
        except Exception as e:
            global UNEXPECTED_ERRORS
            UNEXPECTED_ERRORS = True  # type: ignore
            print(f"Error happened while validating file {file_path}")
            print(f"Validator: {validator.__name__}")
            print(e)
            continue

        if result:
            saved_bytes = sum(p.saved_bytes() for p in result)
            lines = [str(p) for p in result]
            results.append(
                Result(
                    validator_name=validator.__name__,
                    saved_bytes=saved_bytes,
                    lines=lines,
                )
            )

    return results


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
