from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Callable, Iterator

import click
from typing_extensions import TypedDict  # older python compatibility

from strategies import Settings, SpaceSaving
from strategies.constants_local_only import local_only_constants
from strategies.constants_no_const import no_const_number
from strategies.function_inline import function_inline
from strategies.import_global_cache import global_import_cache
from strategies.import_one_function import one_function_import
from strategies.import_type_only import type_only_import
from strategies.keyword_arguments import keyword_arguments
from strategies.local_cache_attribute import local_cache_attribute
from strategies.local_cache_global import local_cache_global
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

VALIDATORS: list[Callable[[str, Settings], list[SpaceSaving]]] = [  # type: ignore
    function_inline,
    global_import_cache,
    one_function_import,
    type_only_import,
    keyword_arguments,
    local_cache_attribute,
    local_cache_global,
    local_only_constants,
    no_const_number,
    init_only_classes,
]


UNEXPECTED_ERRORS = False


class ResultCache:
    """Saving file results locally to avoid recomputing them
    if the file is not changed"""

    def __init__(
        self, cache: dict[str, FileResults], cache_file: Path, force_invalid: bool
    ) -> None:
        self.cache = cache
        self.cache_file = cache_file
        self.force_invalid = force_invalid

    @classmethod
    def load(cls, cache_file: Path, force_invalid: bool = False) -> ResultCache:
        if not cache_file.exists():
            return cls({}, cache_file, force_invalid)

        with open(cache_file, "r") as f:
            try:
                return cls(json.load(f), cache_file, force_invalid)
            except json.JSONDecodeError:
                return cls({}, cache_file, force_invalid)

    def is_valid(self, file_path: str, file_hash: str) -> bool:
        if self.force_invalid:
            return False

        return (
            file_path in self.cache and self.cache[file_path]["file_hash"] == file_hash
        )

    def get(self, file_path: str) -> FileResults:
        return self.cache[file_path]

    def set(self, file_path: str, file_results: FileResults) -> None:
        self.cache[file_path] = file_results

    def save(self) -> None:
        with open(self.cache_file, "w") as f:
            json.dump(self.cache, f, indent=4)


def get_uninlinable_functions(file_path: Path) -> list[str]:
    with open(NOT_INLINED_FILE, "r") as f:
        NOT_INLINABLE_FUNCTIONS = json.load(f)

    file_abs_path = str(file_path.absolute())
    for file, functions in NOT_INLINABLE_FUNCTIONS.items():
        if file_abs_path.endswith(file):
            return functions

    return []


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


def analyze_file(file_path: Path, cache: ResultCache) -> int:
    with open(file_path, "r") as f:
        file_content = f.read()

    abs_path = str(file_path.absolute())
    file_hash = hashlib.md5(file_content.encode()).hexdigest()

    if cache.is_valid(abs_path, file_hash):
        file_results = cache.get(abs_path)
    else:
        results = get_file_results(file_content, file_path)
        saved_bytes = sum(r["saved_bytes"] for r in results)
        file_results = FileResults(
            file_name=abs_path,
            saved_bytes=saved_bytes,
            results=results,
            file_hash=file_hash,
        )
        cache.set(abs_path, file_results)

    report_file_results(file_results)

    return file_results["saved_bytes"]


def get_file_results(file_content: str, file_path: Path) -> list[Result]:
    not_inlineable_funcs = get_uninlinable_functions(file_path)
    FILE_SETTINGS = Settings(
        file_path=file_path, not_inlineable_funcs=not_inlineable_funcs
    )

    def iterator() -> Iterator[Result]:
        for validator in VALIDATORS:
            # Error handling so that it is usable even for untested codebases,
            # where one uncaught error does not stop the whole process
            try:
                result = validator(file_content, FILE_SETTINGS)
            except Exception as e:
                report_uncaught_error(validator.__name__, str(file_path), str(e))
                continue

            if result:
                yield Result(
                    validator_name=validator.__name__,
                    saved_bytes=sum(p.saved_bytes() for p in result),
                    lines=[str(p) for p in result],
                )

    return list(iterator())


def report_uncaught_error(validator_name: str, file_path: str, err: str) -> None:
    global UNEXPECTED_ERRORS
    UNEXPECTED_ERRORS = True  # type: ignore
    print(f"Error happened while validating file {file_path}")
    print(f"Validator: {validator_name}")
    print(err)


@click.command()
@click.argument(
    "path", type=click.Path(exists=True, file_okay=True, dir_okay=True), default="."
)
@click.option("-n", "--no-cache", is_flag=True, help="Do not use cache (dev purposes)")
def main(path: Path, no_cache: bool) -> None:
    path = Path(path)
    possible_saved_bytes = 0
    cache = ResultCache.load(CACHE_FILE, force_invalid=no_cache)

    file_iterable = path.rglob("*.py") if path.is_dir() else [path]
    for file in file_iterable:
        possible_saved_bytes += analyze_file(file, cache)

    cache.save()
    print(f"Potentially saved bytes: {possible_saved_bytes}")

    if UNEXPECTED_ERRORS:
        print("ERROR: There was some unexpected issue. Please check the output.")
        sys.exit(1)


if __name__ == "__main__":
    main()
