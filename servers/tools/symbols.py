"""
Symbol outline extraction for code files in Cerberus.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Optional

from servers.tools.pathutil import (
    WorkspacePathError,
    is_binary_sample,
    resolve_workspace_path,
)


def list_symbols(
    path: str,
    *,
    workspace: Path,
    enforce_boundary: bool = False,
) -> str:
    """Extract symbols (classes, functions, methods, constants) with line numbers."""
    return view_outline(path, workspace=workspace, enforce_boundary=enforce_boundary)


def view_outline(
    path: str,
    *,
    workspace: Path,
    enforce_boundary: bool = False,
) -> str:
    if not path:
        return "ERROR: path must be non-empty"

    try:
        target = resolve_workspace_path(
            path, workspace, enforce_boundary=enforce_boundary, for_write=False
        )
    except WorkspacePathError as exc:
        return f"ERROR: {exc}"

    if not target.exists():
        return f"ERROR: file not found: {target}"
    if not target.is_file():
        return f"ERROR: not a regular file: {target}"

    try:
        raw_bytes = target.read_bytes()
    except OSError as exc:
        return f"ERROR: cannot read {target}: {exc}"

    if is_binary_sample(raw_bytes):
        return f"ERROR: binary file cannot be parsed for outline: {target}"

    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw_bytes.decode("latin-1")
        except Exception as exc:
            return f"ERROR: cannot decode file {target}: {exc}"

    ext = target.suffix.lower()

    if ext in {".py", ".pyi"}:
        return _python_outline(text, str(target))
    elif ext in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
        return _js_ts_outline(text, str(target))
    elif ext == ".go":
        return _go_outline(text, str(target))
    elif ext == ".rs":
        return _rust_outline(text, str(target))
    elif ext in {".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hxx"}:
        return _c_cpp_outline(text, str(target))
    elif ext in {".java", ".kt", ".scala"}:
        return _java_outline(text, str(target))
    elif ext == ".rb":
        return _ruby_outline(text, str(target))
    else:
        return _generic_outline(text, str(target))


def _python_outline(text: str, filename: str) -> str:
    try:
        tree = ast.parse(text, filename=filename)
    except SyntaxError as e:
        fallback = _generic_outline(text, filename)
        return (
            f"Note: Python syntax error on line {e.lineno} ({e.msg}); displaying regex outline:\n"
            f"{fallback}"
        )

    lines: list[str] = []
    symbol_count = 0

    for node in tree.body:
        if isinstance(node, ast.Import):
            names = ", ".join(alias.name for alias in node.names)
            lines.append(f"L{node.lineno:4d}: import {names}")
            symbol_count += 1
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            dots = "." * (node.level or 0)
            names = ", ".join(alias.name for alias in node.names)
            lines.append(f"L{node.lineno:4d}: from {dots}{mod} import {names}")
            symbol_count += 1
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    val_str = _format_ast_expr(node.value)
                    lines.append(f"L{node.lineno:4d}: {target.id} = {val_str}")
                    symbol_count += 1
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and (
                node.target.id.isupper() or not isinstance(node.value, (ast.FunctionDef, ast.AsyncFunctionDef))
            ):
                ann = _format_ast_expr(node.annotation)
                val_part = f" = {_format_ast_expr(node.value)}" if node.value else ""
                lines.append(f"L{node.lineno:4d}: {node.target.id}: {ann}{val_part}")
                symbol_count += 1
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            prefix = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
            sig = _format_python_func_sig(node)
            lines.append(f"L{node.lineno:4d}: {prefix}{sig}")
            symbol_count += 1
        elif isinstance(node, ast.ClassDef):
            bases_str = ""
            if node.bases:
                bases = [_format_ast_expr(b) for b in node.bases]
                bases_str = f"({', '.join(bases)})"
            lines.append(f"L{node.lineno:4d}: class {node.name}{bases_str}:")
            symbol_count += 1

            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    prefix = "async def " if isinstance(item, ast.AsyncFunctionDef) else "def "
                    decorators = [_format_ast_expr(d) for d in item.decorator_list]
                    dec_str = f" [@{', @'.join(decorators)}]" if decorators else ""
                    sig = _format_python_func_sig(item)
                    lines.append(f"  L{item.lineno:4d}: {prefix}{sig}{dec_str}")
                    symbol_count += 1
                elif isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name) and target.id.isupper():
                            val_str = _format_ast_expr(item.value)
                            lines.append(f"  L{item.lineno:4d}: {target.id} = {val_str}")
                            symbol_count += 1
                elif isinstance(item, ast.AnnAssign):
                    if isinstance(item.target, ast.Name):
                        ann = _format_ast_expr(item.annotation)
                        val_part = f" = {_format_ast_expr(item.value)}" if item.value else ""
                        lines.append(f"  L{item.lineno:4d}: {item.target.id}: {ann}{val_part}")
                        symbol_count += 1
                elif isinstance(item, ast.ClassDef):
                    lines.append(f"  L{item.lineno:4d}: class {item.name}:")
                    symbol_count += 1

    header = f"Outline for {filename} ({symbol_count} symbols):"
    if not lines:
        return f"{header}\n(no top-level symbols found)"
    return f"{header}\n" + "\n".join(lines)


def _format_ast_expr(node: Optional[ast.AST]) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Constant):
            return repr(node.value)
        return type(node).__name__


def _format_python_func_sig(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = node.args
    arg_strs: list[str] = []

    for a in getattr(args, "posonlyargs", []):
        ann = f": {_format_ast_expr(a.annotation)}" if a.annotation else ""
        arg_strs.append(f"{a.arg}{ann}")
    if getattr(args, "posonlyargs", []):
        arg_strs.append("/")

    defaults_offset = len(args.args) - len(args.defaults)
    for i, a in enumerate(args.args):
        ann = f": {_format_ast_expr(a.annotation)}" if a.annotation else ""
        default_idx = i - defaults_offset
        if default_idx >= 0:
            def_val = _format_ast_expr(args.defaults[default_idx])
            arg_strs.append(f"{a.arg}{ann}={def_val}")
        else:
            arg_strs.append(f"{a.arg}{ann}")

    if args.vararg:
        ann = f": {_format_ast_expr(args.vararg.annotation)}" if args.vararg.annotation else ""
        arg_strs.append(f"*{args.vararg.arg}{ann}")
    elif args.kwonlyargs:
        arg_strs.append("*")

    for i, a in enumerate(args.kwonlyargs):
        ann = f": {_format_ast_expr(a.annotation)}" if a.annotation else ""
        if i < len(args.kw_defaults) and args.kw_defaults[i] is not None:
            def_val = _format_ast_expr(args.kw_defaults[i])
            arg_strs.append(f"{a.arg}{ann}={def_val}")
        else:
            arg_strs.append(f"{a.arg}{ann}")

    if args.kwarg:
        ann = f": {_format_ast_expr(args.kwarg.annotation)}" if args.kwarg.annotation else ""
        arg_strs.append(f"**{args.kwarg.arg}{ann}")

    ret = f" -> {_format_ast_expr(node.returns)}" if node.returns else ""
    return f"{node.name}({', '.join(arg_strs)}){ret}"


def _js_ts_outline(text: str, filename: str) -> str:
    lines: list[str] = []
    symbol_count = 0

    patterns = [
        (re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(class|interface|type|enum)\s+([A-Za-z0-9_$]+)(\s+extends|\s+implements|\s*=)?"), "type"),
        (re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s*(\*?\s*[A-Za-z0-9_$]+)\s*\((.*?)\)"), "func"),
        (re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s+)?\((.*?)\)\s*=>"), "arrow"),
        (re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Z0-9_$]{2,})\b"), "const"),
        (re.compile(r"^\s*import\s+(?:.+?\s+from\s+)?['\"]([^'\"]+)['\"]"), "import"),
    ]

    for lineno, line in enumerate(text.splitlines(), start=1):
        clean = line.strip()
        if not clean or clean.startswith("//") or clean.startswith("/*"):
            continue

        for pat, kind in patterns:
            m = pat.match(line)
            if m:
                if kind == "type":
                    lines.append(f"L{lineno:4d}: {clean[:80]}")
                elif kind == "func":
                    lines.append(f"L{lineno:4d}: function {m.group(1)}({m.group(2)})")
                elif kind == "arrow":
                    lines.append(f"L{lineno:4d}: const {m.group(1)} = ({m.group(2)}) => ...")
                elif kind == "const":
                    lines.append(f"L{lineno:4d}: {clean[:80]}")
                elif kind == "import":
                    lines.append(f"L{lineno:4d}: {clean[:80]}")
                symbol_count += 1
                break

    header = f"Outline for {filename} ({symbol_count} symbols):"
    if not lines:
        return f"{header}\n(no symbols found)"
    return f"{header}\n" + "\n".join(lines)


def _go_outline(text: str, filename: str) -> str:
    lines: list[str] = []
    symbol_count = 0
    patterns = [
        re.compile(r"^\s*package\s+([A-Za-z0-9_]+)"),
        re.compile(r"^\s*import\s+(?:\((.*?)\)|([^\s]+))"),
        re.compile(r"^\s*type\s+([A-Za-z0-9_]+)\s+(struct|interface|func|[A-Za-z0-9_]+)"),
        re.compile(r"^\s*func\s+(?:\((.*?)\)\s*)?([A-Za-z0-9_]+)\s*\((.*?)\)(.*)"),
        re.compile(r"^\s*const\s+([A-Za-z0-9_]+)"),
    ]

    for lineno, line in enumerate(text.splitlines(), start=1):
        clean = line.strip()
        if not clean or clean.startswith("//"):
            continue

        for pat in patterns:
            m = pat.match(line)
            if m:
                lines.append(f"L{lineno:4d}: {clean[:90]}")
                symbol_count += 1
                break

    header = f"Outline for {filename} ({symbol_count} symbols):"
    if not lines:
        return f"{header}\n(no symbols found)"
    return f"{header}\n" + "\n".join(lines)


def _rust_outline(text: str, filename: str) -> str:
    lines: list[str] = []
    symbol_count = 0
    patterns = [
        re.compile(r"^\s*(?:pub(?:\([^\)]+\))?\s+)?(struct|enum|trait|type|union)\s+([A-Za-z0-9_]+)"),
        re.compile(r"^\s*impl(?:\s*<[^>]+>)?\s+(?:([A-Za-z0-9_:]+)\s+for\s+)?([A-Za-z0-9_:]+)"),
        re.compile(r"^\s*(?:pub(?:\([^\)]+\))?\s+)?(?:async\s+)?fn\s+([A-Za-z0-9_]+)\s*(?:<[^>]+>)?\s*\((.*?)\)(.*)"),
        re.compile(r"^\s*(?:pub(?:\([^\)]+\))?\s+)?const\s+([A-Za-z0-9_]+)"),
        re.compile(r"^\s*use\s+(.+);"),
    ]

    for lineno, line in enumerate(text.splitlines(), start=1):
        clean = line.strip()
        if not clean or clean.startswith("//"):
            continue

        for pat in patterns:
            m = pat.match(line)
            if m:
                lines.append(f"L{lineno:4d}: {clean[:90]}")
                symbol_count += 1
                break

    header = f"Outline for {filename} ({symbol_count} symbols):"
    if not lines:
        return f"{header}\n(no symbols found)"
    return f"{header}\n" + "\n".join(lines)


def _c_cpp_outline(text: str, filename: str) -> str:
    lines: list[str] = []
    symbol_count = 0
    patterns = [
        re.compile(r"^\s*#(?:include|define)\s+(.+)"),
        re.compile(r"^\s*(?:typedef\s+)?(struct|class|enum|union)\s+([A-Za-z0-9_]+)"),
        re.compile(r"^\s*(?:template\s*<[^>]*>\s*)?(?:[A-Za-z0-9_:<>&*]+\s+)+([A-Za-z0-9_~]+)\s*\((.*?)\)\s*(?:const)?\s*(?:;|{|$)"),
    ]

    for lineno, line in enumerate(text.splitlines(), start=1):
        clean = line.strip()
        if not clean or clean.startswith("//") or clean.startswith("/*"):
            continue

        for pat in patterns:
            m = pat.match(line)
            if m:
                lines.append(f"L{lineno:4d}: {clean[:90]}")
                symbol_count += 1
                break

    header = f"Outline for {filename} ({symbol_count} symbols):"
    if not lines:
        return f"{header}\n(no symbols found)"
    return f"{header}\n" + "\n".join(lines)


def _java_outline(text: str, filename: str) -> str:
    lines: list[str] = []
    symbol_count = 0
    patterns = [
        re.compile(r"^\s*(?:package|import)\s+(.+)"),
        re.compile(r"^\s*(?:public|protected|private|static|final|abstract|\s)*\s*(class|interface|enum|record)\s+([A-Za-z0-9_]+)"),
        re.compile(r"^\s*(?:public|protected|private|static|final|synchronized|abstract|\s)+[A-Za-z0-9_<>,\[\]]+\s+([A-Za-z0-9_]+)\s*\((.*?)\)"),
    ]

    for lineno, line in enumerate(text.splitlines(), start=1):
        clean = line.strip()
        if not clean or clean.startswith("//") or clean.startswith("/*"):
            continue

        for pat in patterns:
            m = pat.match(line)
            if m:
                lines.append(f"L{lineno:4d}: {clean[:90]}")
                symbol_count += 1
                break

    header = f"Outline for {filename} ({symbol_count} symbols):"
    if not lines:
        return f"{header}\n(no symbols found)"
    return f"{header}\n" + "\n".join(lines)


def _ruby_outline(text: str, filename: str) -> str:
    lines: list[str] = []
    symbol_count = 0
    patterns = [
        re.compile(r"^\s*(?:require|require_relative)\s+['\"](.+)['\"]"),
        re.compile(r"^\s*(?:class|module)\s+([A-Za-z0-9_:]+)"),
        re.compile(r"^\s*def\s+([A-Za-z0-9_.:?!]+)(?:\s*\((.*?)\))?"),
        re.compile(r"^\s*attr_(?:accessor|reader|writer)\s+(.+)"),
    ]

    for lineno, line in enumerate(text.splitlines(), start=1):
        clean = line.strip()
        if not clean or clean.startswith("#"):
            continue

        for pat in patterns:
            m = pat.match(line)
            if m:
                lines.append(f"L{lineno:4d}: {clean[:90]}")
                symbol_count += 1
                break

    header = f"Outline for {filename} ({symbol_count} symbols):"
    if not lines:
        return f"{header}\n(no symbols found)"
    return f"{header}\n" + "\n".join(lines)


def _generic_outline(text: str, filename: str) -> str:
    lines: list[str] = []
    symbol_count = 0
    pat = re.compile(r"^\s*(def|function|class|fn|struct|interface|type|sub|#\s*[A-Za-z0-9])\s+(.+)")

    for lineno, line in enumerate(text.splitlines(), start=1):
        clean = line.strip()
        if not clean:
            continue
        m = pat.match(line)
        if m:
            lines.append(f"L{lineno:4d}: {clean[:80]}")
            symbol_count += 1

    header = f"Outline for {filename} ({symbol_count} symbols):"
    if not lines:
        return f"{header}\n(no outline symbols detected)"
    return f"{header}\n" + "\n".join(lines)
