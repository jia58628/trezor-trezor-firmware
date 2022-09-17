from __future__ import annotations

import ast
import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterator

FUNC_ASTS = (ast.FunctionDef, ast.AsyncFunctionDef)
IMPORT_ASTS = (ast.Import, ast.ImportFrom)


@dataclass
class Function:
    all_code: str
    body_code: str
    name: str
    line_no: int
    node: ast.FunctionDef | ast.AsyncFunctionDef

    def __repr__(self) -> str:  # pragma: no cover
        code_lines = len(self.all_code.splitlines())
        return f"{self.line_no} :: {self.name} ({code_lines} LOC)"


@dataclass
class CacheCandidate:
    cache_string: str
    amount: int

    def __repr__(self) -> str:
        return f"{self.cache_string} ({self.amount}x)"


def get_cache_candidates(
    file_content: str, regex: str, low_threshold: int = 3, no_comments: bool = True
) -> list[CacheCandidate]:
    if no_comments:
        file_content = remove_comments(file_content)

    matches = re.findall(regex, file_content)
    counter = Counter(matches)

    above_threshold = [(k, v) for k, v in counter.items() if v >= low_threshold]

    res = list(sorted(above_threshold, key=lambda item: item[1], reverse=True))
    return [CacheCandidate(cache_string=k, amount=v) for k, v in res]


def get_all_global_symbols(file_content: str) -> list[str]:
    imported_symbols = get_all_toplevel_imported_symbols(file_content)
    functions = get_all_function_names(file_content)
    return imported_symbols + functions


def get_all_toplevel_nodes(file_content: str) -> list[ast.AST]:
    parsed_ast = ast.parse(file_content)
    return list(parsed_ast.body)


def get_all_nodes(file_content: str) -> list[ast.AST]:
    parsed_ast = ast.parse(file_content)
    return list(ast.walk(parsed_ast))


def get_all_function_names(file_content: str) -> list[str]:
    functions = get_all_functions(file_content)
    return [f.name for f in functions]


def get_all_toplevel_functions(file_content: str) -> list[Function]:
    return [
        create_function_from_node(file_content, node)
        for node in get_all_toplevel_nodes(file_content)
        if isinstance(node, FUNC_ASTS)
    ]


def get_all_functions(file_content: str) -> list[Function]:
    return [
        create_function_from_node(file_content, node)
        for node in get_all_nodes(file_content)
        if isinstance(node, FUNC_ASTS)
    ]


def create_function_from_node(
    file_content: str, node: ast.FunctionDef | ast.AsyncFunctionDef
) -> Function:
    return Function(
        name=str(node.name),
        all_code=get_node_code(file_content, node),
        body_code=get_function_body_code(file_content, node),
        line_no=node.lineno,
        node=node,
    )


def get_method_names(node: ast.ClassDef) -> list[str]:
    return [n.name for n in node.body if isinstance(n, FUNC_ASTS)]


def number_of_occurrences(
    file_content: str, regex: str, no_comments: bool = True
) -> int:
    if no_comments:
        file_content = remove_comments(file_content)
    return len(re.findall(regex, file_content))


def get_all_toplevel_imported_symbols(
    file_content: str, include_star: bool = False
) -> list[str]:
    """Does not look into if TYPE_CHECKING, only toplevel imports."""
    symbols: list[str] = []

    for node in get_all_toplevel_nodes(file_content):
        if isinstance(node, IMPORT_ASTS):
            for n in node.names:
                if not include_star and n.name == "*":
                    continue

                if n.asname is None:
                    symbols.append(n.name)
                else:
                    symbols.append(n.asname)

    return symbols


def get_node_code(file_content: str, node: ast.AST) -> str:
    return str(ast.get_source_segment(file_content, node))


def get_function_body_code(
    file_content: str, func_node: ast.FunctionDef | ast.AsyncFunctionDef
) -> str:
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


def remove_comments(file_content: str) -> str:
    # TODO: should also get rid of docstrings
    # TODO: try to load the AST and then reconstruct it,
    # comments should not be there
    return re.sub("#.*", "", file_content)


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


def get_global_assignments(file_content: str) -> list[ast.Assign]:
    global_assignments: list[ast.Assign] = []

    parsed_ast = ast.parse(file_content)
    for node in parsed_ast.body:
        if isinstance(node, ast.Assign):
            global_assignments.append(node)

    return global_assignments


def get_all_constants(file_content: str) -> list[str]:
    const: list[str] = []

    global_ass = get_global_assignments(file_content)
    for ass in global_ass:
        if is_const_assignment(ass):
            var_name = get_variable_name(ass)
            const.append(var_name)

    return const


def is_not_redefined(file_content: str, var_name: str) -> bool:
    """Check if the variable is defined only once."""
    const_regex = rf"\b{var_name}\s=\s"
    occurrences = number_of_occurrences(file_content, const_regex)
    return occurrences == 1


def is_a_constant_number_var(file_content: str, assign: ast.Assign) -> bool:
    if not isinstance(assign.value, ast.Constant):
        return False
    if not isinstance(assign.value.value, int):
        return False
    var_name = get_variable_name(assign)
    return is_not_redefined(file_content, var_name)


def contains_symbol(text: str, symbol: str) -> bool:
    regex = rf"\b{symbol}\b"
    return re.search(regex, text) is not None


def resolve_attribute_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return resolve_attribute_name(node.value) + "." + node.attr
    elif isinstance(node, ast.Subscript):
        return (
            resolve_attribute_name(node.value)
            + "["
            + resolve_attribute_name(node.slice)
            + "]"
        )
    elif isinstance(node, ast.Tuple):
        return ", ".join([resolve_attribute_name(n) for n in node.elts])
    else:
        raise RuntimeError(f"Unexpected node type - {node}")


def get_inheritance_bases(node: ast.ClassDef) -> list[str]:
    return [resolve_attribute_name(base) for base in node.bases]


def used_in_class_inheritance(file_content: str, symbol: str) -> bool:
    for node in get_all_nodes(file_content):
        if isinstance(node, ast.ClassDef):
            for base_class in get_inheritance_bases(node):
                if contains_symbol(base_class, symbol):
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


def used_in_decorator(file_content: str, symbol: str) -> bool:
    for node in get_all_nodes(file_content):
        if isinstance(node, FUNC_ASTS):
            for decorator in node.decorator_list:
                decorated = resolve_decorator_symbol(decorator)
                if symbol == decorated.split(".")[0]:
                    return True

    return False


def is_used_outside_function(file_content: str, symbol: str) -> bool:
    """Look at toplevel and classes to see if the symbol is used there."""
    if used_in_class_inheritance(file_content, symbol):
        return True
    if used_in_decorator(file_content, symbol):
        return True

    outside_code = get_code_outside_of_function(file_content)
    occurrences = number_of_occurrences(outside_code, rf"\b{symbol}\b")
    return occurrences > 0


def get_code_outside_of_function(file_content: str) -> str:
    """Get the code outside of the function."""
    node_code_lines: list[str] = []

    outside_func_nodes = list(yield_nonfunction_nodes(file_content))
    for node in outside_func_nodes:
        node_code = get_node_code(file_content, node)
        node_code_lines.append(node_code)

    return "\n".join(node_code_lines)


def yield_nonfunction_nodes(file_content: str) -> Iterator[ast.AST]:
    """Get all nodes that are not functions and not imports."""
    tree = ast.parse(file_content)
    yield from recursively_yield_nonfunction_nodes(tree)


def recursively_yield_nonfunction_nodes(node: ast.AST) -> Iterator[ast.AST]:
    """Get all nodes that are not functions and not imports."""
    if isinstance(node, IMPORT_ASTS + FUNC_ASTS):
        return

    if not hasattr(node, "body"):
        yield node
    else:
        for subnode in node.body:  # type: ignore
            yield from recursively_yield_nonfunction_nodes(subnode)  # type: ignore


def annotation_contains_symbol(
    file_content: str, symbol: str, annotation_node: ast.AST
) -> bool:
    """Check if the annotation contains the symbol."""
    if isinstance(annotation_node, (ast.Name, ast.Attribute)):
        type_hint = resolve_attribute_name(annotation_node)
        return contains_symbol(type_hint, symbol)
    else:
        annotation_code = get_node_code(file_content, annotation_node)
        return contains_symbol(annotation_code, symbol)


def is_used_as_type_hint(file_content: str, symbol: str) -> bool:
    """Check if the symbol is used as a type hint."""
    for node in get_all_nodes(file_content):
        if isinstance(node, ast.arg):
            if hasattr(node, "annotation") and node.annotation is not None:
                if annotation_contains_symbol(file_content, symbol, node.annotation):
                    return True
    return False
