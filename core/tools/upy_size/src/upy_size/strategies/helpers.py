from __future__ import annotations

import ast
import re
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Iterator

from typing_extensions import TypeAlias, TypeGuard

FUNC_ASTS = (ast.FunctionDef, ast.AsyncFunctionDef)
IMPORT_ASTS = (ast.Import, ast.ImportFrom)

if TYPE_CHECKING:  # pragma: no cover
    FuncAst: TypeAlias = ast.FunctionDef | ast.AsyncFunctionDef  # type: ignore
    ImportAst: TypeAlias = ast.Import | ast.ImportFrom  # type: ignore


@dataclass
class Function:
    name: str
    loc: int
    line_no: int
    node: FuncAst

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.line_no} :: {self.name} ({self.loc} LOC)"


@dataclass
class CacheCandidate:
    cache_string: str
    amount: int

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.cache_string} ({self.amount}x)"


@dataclass
class FunctionSymbolUsage:
    func: Function
    usages: int


@lru_cache(maxsize=16)
def all_global_symbols(file_content: str) -> list[str]:
    imported = all_toplevel_imported_symbols(file_content)
    constants = all_constants(file_content)
    functions = all_function_names(file_content)
    return imported + constants + functions


@lru_cache(maxsize=16)
def all_toplevel_nodes(file_content: str) -> list[ast.AST]:
    parsed_ast = ast.parse(file_content)
    return list(parsed_ast.body)


@lru_cache(maxsize=16)
def all_nodes(file_content: str) -> list[ast.AST]:
    parsed_ast = ast.parse(file_content)
    return list(ast.walk(parsed_ast))


@lru_cache(maxsize=16)
def all_function_names(file_content: str) -> list[str]:
    functions = all_functions(file_content)
    return [f.name for f in functions]


@lru_cache(maxsize=16)
def all_toplevel_functions(file_content: str) -> list[Function]:
    def iterator() -> Iterator[Function]:
        for node in all_toplevel_nodes(file_content):
            if isinstance(node, FUNC_ASTS):
                yield create_function_from_node(file_content, node)

    return list(iterator())


@lru_cache(maxsize=16)
def all_functions(file_content: str) -> list[Function]:
    def iterator() -> Iterator[Function]:
        for node in all_nodes(file_content):
            if isinstance(node, FUNC_ASTS):
                yield create_function_from_node(file_content, node)

    return list(iterator())


@lru_cache(maxsize=16)
def all_global_assignments(file_content: str) -> list[ast.Assign]:
    def iterator() -> Iterator[ast.Assign]:
        for node in ast.parse(file_content).body:
            if isinstance(node, ast.Assign):
                yield node

    return list(iterator())


@lru_cache(maxsize=16)
def all_constants(file_content: str) -> list[str]:
    def iterator() -> Iterator[str]:
        for ass in all_global_assignments(file_content):
            if is_const_assignment(ass):
                yield get_variable_name(ass)

    return list(iterator())


@lru_cache(maxsize=16)
def all_toplevel_symbol_usages(file_content: str) -> dict[str, int]:
    """Get the numbers of times toplevel symbols are used in the file."""
    toplevel_symbols = all_global_symbols(file_content)

    used_symbols: dict[str, int] = defaultdict(int)
    for node in all_nodes(file_content):
        if _is_symbol_usage(node):
            used_symbols[node.id] += 1

    return {k: v for k, v in used_symbols.items() if k in toplevel_symbols}


@lru_cache(maxsize=16)
def all_toplevel_imported_symbols(
    file_content: str, include_star: bool = False
) -> list[str]:
    nodes = all_toplevel_nodes(file_content)
    return _get_imported_symbols(nodes, include_star=include_star)


@lru_cache(maxsize=16)
def all_function_imported_symbols(
    func_node: FuncAst, include_star: bool = False
) -> list[str]:
    nodes = list(ast.walk(func_node))
    return _get_imported_symbols(nodes, include_star=include_star)


@lru_cache(maxsize=16)
def all_type_hint_usages(file_content: str) -> dict[str, int]:
    """Get the numbers of times symbols are used as type-hints."""
    type_hint_symbols: dict[str, int] = defaultdict(int)

    def _add_symbol_from_node_attr(node_attr: ast.AST) -> None:
        symbol = _resolve_type_hint(file_content, node_attr)
        if symbol:
            type_hint_symbols[symbol] += 1

    for node in all_nodes(file_content):
        # Function arguments
        if (
            isinstance(node, ast.arg)
            and hasattr(node, "annotation")
            and node.annotation is not None
        ):
            _add_symbol_from_node_attr(node.annotation)

        # Function return values
        elif (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and hasattr(node, "returns")
            and node.returns is not None
        ):
            _add_symbol_from_node_attr(node.returns)

        # Variable annotations
        elif (
            isinstance(node, ast.AnnAssign)
            and hasattr(node, "annotation")
            and node.annotation is not None
        ):
            _add_symbol_from_node_attr(node.annotation)

    return type_hint_symbols


@lru_cache(maxsize=16)
def all_nodes_outside_of_function(file_content: str) -> list[ast.AST]:
    """Get the code outside of any function."""
    return list(_yield_nonfunction_nodes(file_content))


def _yield_nonfunction_nodes(file_content: str) -> Iterator[ast.AST]:
    """Get all nodes that are not functions and not imports."""
    tree = ast.parse(file_content)
    yield from _recursively_yield_nonfunction_nodes(tree)


def _recursively_yield_nonfunction_nodes(node: ast.AST) -> Iterator[ast.AST]:
    """Get all nodes that are not functions and not imports."""
    if isinstance(node, IMPORT_ASTS + FUNC_ASTS):
        return

    if not hasattr(node, "body"):
        yield node
    else:
        for subnode in node.body:  # type: ignore
            yield from _recursively_yield_nonfunction_nodes(subnode)  # type: ignore


def _resolve_type_hint(file_content: str, node_attr: ast.AST) -> str:
    def _get_unknown() -> str:
        # We couldn't easily parse the symbol
        return get_node_code(file_content, node_attr)

    if isinstance(node_attr, (ast.Name, ast.Attribute)):
        symbol = _resolve_attribute_name(node_attr).split(".")[0]
        return symbol
    elif isinstance(node_attr, ast.Constant) and node_attr.value is None:
        return ""
    elif (
        isinstance(node_attr, ast.Subscript)
        and isinstance(node_attr.value, ast.Name)
        and isinstance(node_attr.slice, ast.Name)
    ):
        keywords_val = ("list", "dict", "set", "tuple")
        keywords_slice = ("int", "bytes", "str", "float")
        value = node_attr.value.id
        slice = node_attr.slice.id
        if value in keywords_val and slice not in keywords_slice:
            return slice
        elif value not in keywords_val and slice in keywords_slice:
            return value
        elif value not in keywords_val and slice not in keywords_slice:
            return _get_unknown()
        else:
            return ""
    else:
        return _get_unknown()


def _get_imported_symbols(
    nodes: list[ast.AST], include_star: bool = False
) -> list[str]:
    def iterator() -> Iterator[str]:
        for node in nodes:
            if isinstance(node, IMPORT_ASTS):
                for n in node.names:
                    if not include_star and n.name == "*":
                        continue

                    if n.asname is not None:
                        yield n.asname
                    else:
                        yield n.name

    return list(iterator())


def create_function_from_node(file_content: str, node: FuncAst) -> Function:
    return Function(
        name=str(node.name),
        loc=int(node.end_lineno or 0) - node.lineno,
        line_no=node.lineno,
        node=node,
    )


def get_method_names(node: ast.ClassDef) -> list[str]:
    return [n.name for n in node.body if isinstance(n, FUNC_ASTS)]


def get_node_code(file_content: str, node: ast.AST) -> str:
    return str(ast.get_source_segment(file_content, node))


def get_function_body_code(file_content: str, func_node: FuncAst) -> str:
    body = func_node.body
    body_lines: list[str] = []
    for node in body:
        node_code = get_node_code(file_content, node)
        body_lines.append(node_code)
    return "\n".join(body_lines)


def get_node_str(node: ast.AST) -> str:
    return ast.dump(node, indent=4)


def print_node(node: ast.AST) -> None:
    node_str = get_node_str(node)
    print(node_str)


def print_node_code(file_content: str, node: ast.AST) -> None:
    node_code = get_node_code(file_content, node)
    print(node_code)


def print_ast(file_content: str) -> None:
    parsed_ast = ast.parse(file_content)
    print_node(parsed_ast)


def get_function_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Attribute):
        return resolve_func_name(node.func)
    else:
        return node.func.id  # type: ignore


def resolve_func_name(node: ast.Attribute) -> str:
    if isinstance(node.value, ast.Attribute):
        return resolve_func_name(node.value) + "." + node.attr
    elif isinstance(node.value, ast.Call):
        return get_function_name(node.value) + "." + node.attr
    else:
        object_name = node.value.id  # type: ignore
        attribute_name = node.attr
        return f"{object_name}.{attribute_name}"


def is_const_assignment(node: ast.AST) -> bool:
    if not isinstance(node, ast.Assign):
        return False

    if len(node.targets) != 1:
        return False

    if not hasattr(node.value, "func"):
        return False

    if hasattr(node.value.func, "id"):  # type: ignore
        func_name = str(node.value.func.id)  # type: ignore
    else:
        func_name = str(node.value.func.attr)  # type: ignore

    return func_name == "const"


def get_variable_name(node: ast.Assign) -> str:
    return node.targets[0].id  # type: ignore


def is_really_a_constant(file_content: str, var_name: str) -> bool:
    """Check if the variable is defined only once."""
    assigned_num = 0
    for node in all_nodes(file_content):
        if _is_symbol_assignment(node):
            if node.id == var_name:
                assigned_num += 1

    return assigned_num == 1


def is_a_constant_number_var(file_content: str, assign: ast.Assign) -> bool:
    if not isinstance(assign.value, ast.Constant):
        return False
    if not isinstance(assign.value.value, int):
        return False
    var_name = get_variable_name(assign)
    return is_really_a_constant(file_content, var_name)


def _contains_symbol(text: str, symbol: str) -> bool:
    regex = rf"\b{symbol}\b"
    return re.search(regex, text) is not None


def _resolve_attribute_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return _resolve_attribute_name(node.value) + "." + node.attr
    elif isinstance(node, ast.Subscript):
        return (
            _resolve_attribute_name(node.value)
            + "["
            + _resolve_attribute_name(node.slice)
            + "]"
        )
    elif isinstance(node, ast.Tuple):
        return ", ".join([_resolve_attribute_name(n) for n in node.elts])
    else:
        raise RuntimeError(f"Unexpected node type - {node}")


def _get_inheritance_bases(node: ast.ClassDef) -> list[str]:
    return [_resolve_attribute_name(base) for base in node.bases]


def _used_in_class_inheritance(file_content: str, symbol: str) -> bool:
    for node in all_nodes(file_content):
        if isinstance(node, ast.ClassDef):
            for base_class in _get_inheritance_bases(node):
                if _contains_symbol(base_class, symbol):
                    return True
    return False


def resolve_decorator_symbol(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return resolve_decorator_symbol(node.value) + "." + node.attr
    elif isinstance(node, ast.Call):
        return resolve_decorator_symbol(node.func)
    else:
        raise RuntimeError(f"Unexpected node type - {node}")


def _used_in_decorator(file_content: str, symbol: str) -> bool:
    for node in all_nodes(file_content):
        if isinstance(node, FUNC_ASTS):
            for decorator in node.decorator_list:
                decorated = resolve_decorator_symbol(decorator)
                if symbol == decorated.split(".")[0]:
                    return True

    return False


def is_used_outside_function(file_content: str, symbol: str) -> bool:
    """Look at toplevel and classes to see if the symbol is used there."""
    if _used_in_class_inheritance(file_content, symbol):
        return True
    if _used_in_decorator(file_content, symbol):
        return True

    for body_node in all_nodes_outside_of_function(file_content):
        for node in ast.walk(body_node):
            if _is_symbol_usage(node):
                if node.id == symbol:
                    return True

    return False




def is_used_as_type_hint(file_content: str, symbol: str) -> bool:
    """Check if the symbol is used as a type hint."""
    for type_hint in all_type_hint_usages(file_content):
        if _contains_symbol(type_hint, symbol):
            return True
    return False


def _is_symbol_assignment(node: ast.AST) -> TypeGuard[ast.Name]:
    return isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)


def _is_symbol_usage(node: ast.AST) -> TypeGuard[ast.Name]:
    return isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)


def get_used_func_symbols(func_node: FuncAst) -> dict[str, int]:
    used_symbols: dict[str, int] = defaultdict(int)

    for body_node in func_node.body:
        for node in ast.walk(body_node):
            if _is_symbol_usage(node):
                used_symbols[node.id] += 1

    return used_symbols


def get_used_func_import_symbols(
    file_content: str, func_node: FuncAst
) -> dict[str, int]:
    toplevel_symbols = all_toplevel_imported_symbols(file_content)
    used_symbols = get_used_func_symbols(func_node)
    return {k: v for k, v in used_symbols.items() if k in toplevel_symbols}

def get_func_toplevel_symbol_usages(
    file_content: str,
) -> dict[str, list[FunctionSymbolUsage]]:
    symbol_usages: dict[str, list[FunctionSymbolUsage]] = defaultdict(list)

    for func in all_functions(file_content):
        usages = get_used_func_import_symbols(file_content, func.node)
        for symbol, usage_num in usages.items():
            symbol_usages[symbol].append(FunctionSymbolUsage(func, usage_num))

    return symbol_usages


def get_function_call_amounts(
    file_content: str,
) -> dict[str, int]:
    function_calls: dict[str, int] = defaultdict(int)

    for node in all_nodes(file_content):
        if isinstance(node, ast.Call):
            if _is_symbol_usage(node.func):
                function_calls[node.func.id] += 1

    return function_calls


def get_global_attribute_lookups(file_content: str) -> dict[str, dict[str, int]]:
    return _get_attribute_lookups(file_content, all_nodes(file_content), is_local=False)


def get_func_local_attribute_lookups(
    file_content: str, func_node: FuncAst
) -> dict[str, dict[str, int]]:
    return _get_attribute_lookups(
        file_content, list(ast.walk(func_node)), is_local=True
    )


def _get_attribute_lookups(
    file_content: str, nodes: list[ast.AST], is_local: bool
) -> dict[str, dict[str, int]]:
    lookups: dict[str, dict[str, int]] = defaultdict(dict)

    all_imported_symbols = all_toplevel_imported_symbols(file_content)

    def _include_lookup(node: ast.Name) -> bool:
        if is_local:
            return node.id not in all_imported_symbols
        else:
            return node.id in all_imported_symbols

    for node in nodes:
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                if _include_lookup(node.value):
                    symbol = node.value.id
                    attr = node.attr
                    if attr not in lookups[symbol]:
                        lookups[symbol][attr] = 0
                    lookups[symbol][attr] += 1

    return lookups


def attr_gets_modified(func_node: FuncAst, obj_name: str, attr_name: str) -> bool:
    """Check if the given attribute of the given object is modified in the function."""
    for node in ast.walk(func_node):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute):
                    if isinstance(target.value, ast.Name):
                        if target.value.id == obj_name and target.attr == attr_name:
                            return True
    return False
