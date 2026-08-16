"""Regression checks for exception redaction in the Streamlit UI."""

from __future__ import annotations

import ast
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
RUNTIME_DIRS = (APP_DIR, ROOT / "core", ROOT / "db", ROOT / "services")
DISPLAY_METHODS = {
    "caption",
    "error",
    "exception",
    "info",
    "markdown",
    "toast",
    "warning",
    "write",
}


def _is_generic_exception(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    names = {
        node.id
        for node in ast.walk(handler.type)
        if isinstance(node, ast.Name)
    }
    return bool(names & {"Exception", "BaseException"})


def _references_name(node: ast.AST, name: str) -> bool:
    return any(
        isinstance(child, ast.Name) and child.id == name for child in ast.walk(node)
    )


def _is_streamlit_display(call: ast.Call) -> bool:
    if not isinstance(call.func, ast.Attribute) or call.func.attr not in DISPLAY_METHODS:
        return False
    owner = call.func.value
    if isinstance(owner, ast.Name):
        return owner.id == "st"
    return (
        isinstance(owner, ast.Attribute)
        and isinstance(owner.value, ast.Name)
        and owner.value.id == "st"
    )


def _is_print(call: ast.Call) -> bool:
    return isinstance(call.func, ast.Name) and call.func.id == "print"


def _is_safe_exception_type(node: ast.AST, name: str) -> bool:
    """Allow ``type(exc).__name__`` while rejecting the exception message."""
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "__name__"
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "type"
        and len(node.value.args) == 1
        and isinstance(node.value.args[0], ast.Name)
        and node.value.args[0].id == name
    )


def _has_unsafe_exception_reference(node: ast.AST, name: str) -> bool:
    if _is_safe_exception_type(node, name):
        return False
    if isinstance(node, ast.Name) and node.id == name:
        return True
    return any(
        _has_unsafe_exception_reference(child, name)
        for child in ast.iter_child_nodes(node)
    )


class _GenericHandlerScanner(ast.NodeVisitor):
    def __init__(self, handler: ast.ExceptHandler) -> None:
        self.handler = handler
        self.exception_name = handler.name
        self.violations: list[tuple[int, str]] = []

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:  # noqa: N802
        # A nested handler has its own exception contract and is checked separately.
        if node is self.handler:
            self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        if self.exception_name and _is_streamlit_display(node):
            rendered = [*node.args, *(keyword.value for keyword in node.keywords)]
            if any(_references_name(argument, self.exception_name) for argument in rendered):
                self.violations.append(
                    (node.lineno, "generic exception rendered by Streamlit")
                )
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "traceback"
            and node.func.attr == "format_exc"
        ):
            self.violations.append((node.lineno, "full traceback formatted in UI code"))
        self.generic_visit(node)


class _RawExceptionLogScanner(ast.NodeVisitor):
    def __init__(self, handler: ast.ExceptHandler) -> None:
        self.handler = handler
        self.exception_name = handler.name
        self.violations: list[tuple[int, str]] = []

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:  # noqa: N802
        if node is self.handler:
            self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        if self.exception_name and _is_print(node):
            rendered = [*node.args, *(keyword.value for keyword in node.keywords)]
            if any(
                _has_unsafe_exception_reference(argument, self.exception_name)
                for argument in rendered
            ):
                self.violations.append(
                    (node.lineno, "raw exception message written to application logs")
                )
        self.generic_visit(node)


def test_generic_exceptions_are_not_rendered_in_streamlit() -> None:
    violations: list[str] = []
    for path in APP_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for handler in (
            node for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler)
        ):
            if not handler.name or not _is_generic_exception(handler):
                continue
            scanner = _GenericHandlerScanner(handler)
            scanner.visit(handler)
            violations.extend(
                f"{path.relative_to(ROOT)}:{line}: {reason}"
                for line, reason in scanner.violations
            )

    assert not violations, "\n".join(violations)


def test_ui_exception_logger_omits_exception_message(capsys) -> None:
    sys.path.insert(0, str(APP_DIR))
    try:
        from ui_utils import log_ui_exception

        log_ui_exception("login\ncallback", RuntimeError("password=not-for-logs"))
    finally:
        sys.path.remove(str(APP_DIR))

    stderr = capsys.readouterr().err
    assert "RuntimeError" in stderr
    assert "logincallback" in stderr
    assert "password" not in stderr
    assert "not-for-logs" not in stderr


def test_generic_exception_messages_are_not_printed() -> None:
    violations: list[str] = []
    for directory in RUNTIME_DIRS:
        for path in directory.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
            for handler in (
                node for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler)
            ):
                if not handler.name or not _is_generic_exception(handler):
                    continue
                scanner = _RawExceptionLogScanner(handler)
                scanner.visit(handler)
                violations.extend(
                    f"{path.relative_to(ROOT)}:{line}: {reason}"
                    for line, reason in scanner.violations
                )

    assert not violations, "\n".join(violations)


def test_llm_provider_payloads_are_never_printed() -> None:
    path = ROOT / "core" / "generators" / "llm.py"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    sensitive_names = {"content", "prompt", "response", "exp_content", "fb_response"}
    violations = []
    for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
        if not _is_print(call):
            continue
        rendered = [*call.args, *(keyword.value for keyword in call.keywords)]
        leaked = {
            child.id
            for argument in rendered
            for child in ast.walk(argument)
            if isinstance(child, ast.Name) and child.id in sensitive_names
        }
        if leaked:
            violations.append(
                f"{path.relative_to(ROOT)}:{call.lineno}: provider payload {sorted(leaked)}"
            )

    assert not violations, "\n".join(violations)
