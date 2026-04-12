"""
AST-based Python validator for user-submitted strategy code.

Checks:
1. Syntax is valid Python.
2. No dangerous imports (os, sys, subprocess, socket, builtins…).
3. No dangerous builtins (exec, eval, open, __import__…).
4. The `run(ohlcv)` function is defined.

Does NOT execute the code. Full sandbox execution happens in the
Celery worker (Phase 4) using RestrictedPython + resource limits.
"""

from __future__ import annotations

import ast
from typing import List

_FORBIDDEN_IMPORTS = frozenset({
    "os", "sys", "subprocess", "socket", "shutil", "pathlib",
    "builtins", "importlib", "ctypes", "multiprocessing", "threading",
    "asyncio", "signal", "resource", "pty", "termios",
})

_FORBIDDEN_BUILTINS = frozenset({
    "exec", "eval", "compile", "open", "__import__",
    "globals", "locals", "vars", "dir",
})

_ALLOWED_IMPORTS = frozenset({
    "numpy", "np", "pandas", "pd", "math", "statistics",
    "collections", "itertools", "functools", "typing",
    "datetime", "decimal", "fractions",
})


class _Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.errors: List[str] = []
        self.has_run_fn = False

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root = alias.name.split(".")[0]
            if root in _FORBIDDEN_IMPORTS:
                self.errors.append(f"Line {node.lineno}: import '{alias.name}' is not allowed")
            elif root not in _ALLOWED_IMPORTS:
                self.errors.append(
                    f"Line {node.lineno}: import '{alias.name}' is not in the allowed list"
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = (node.module or "").split(".")[0]
        if module in _FORBIDDEN_IMPORTS:
            self.errors.append(f"Line {node.lineno}: import from '{node.module}' is not allowed")
        elif module and module not in _ALLOWED_IMPORTS:
            self.errors.append(
                f"Line {node.lineno}: import from '{node.module}' is not in the allowed list"
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in _FORBIDDEN_BUILTINS:
            self.errors.append(
                f"Line {node.lineno}: call to '{node.func.id}' is not allowed"
            )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Block dunder attribute access like obj.__class__.__bases__
        if node.attr.startswith("__") and node.attr.endswith("__"):
            self.errors.append(
                f"Line {node.lineno}: dunder attribute access '{node.attr}' is not allowed"
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name == "run":
            args = [a.arg for a in node.args.args]
            if args and args[0] in ("ohlcv", "df", "data"):
                self.has_run_fn = True
        self.generic_visit(node)


def validate(code: str) -> tuple[bool, List[str]]:
    """
    Returns (is_valid, errors).
    is_valid is True only when there are no errors.
    """
    errors: List[str] = []

    # 1. Syntax check
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, [f"Syntax error at line {e.lineno}: {e.msg}"]

    # 2. AST safety checks
    visitor = _Visitor()
    visitor.visit(tree)
    errors.extend(visitor.errors)

    # 3. run() function must be defined
    if not visitor.has_run_fn:
        errors.append(
            "Strategy must define a 'run(ohlcv)' function that returns "
            "{'entries': pd.Series, 'exits': pd.Series}"
        )

    return len(errors) == 0, errors
