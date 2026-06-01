from __future__ import annotations

import ast
from dataclasses import dataclass


DEFAULT_CHUNK_LINES = 80
DEFAULT_OVERLAP_LINES = 10


@dataclass(frozen=True)
class CodeChunk:
    path: str
    start_line: int
    end_line: int
    content: str
    symbol_name: str | None = None
    kind: str = "text"


def chunk_text(
    *,
    path: str,
    content: str,
    max_lines: int = DEFAULT_CHUNK_LINES,
    overlap_lines: int = DEFAULT_OVERLAP_LINES,
    ) -> list[CodeChunk]:
    if path.endswith(".py"):
        symbol_chunks = _chunk_python_symbols(path=path, content=content)
        if symbol_chunks:
            return symbol_chunks

    lines = content.splitlines()
    if not lines:
        return [CodeChunk(path=path, start_line=1, end_line=1, content="", kind="text")]

    max_lines = max(1, max_lines)
    overlap_lines = max(0, min(overlap_lines, max_lines - 1))
    step = max_lines - overlap_lines

    chunks: list[CodeChunk] = []
    start = 0
    while start < len(lines):
        end = min(start + max_lines, len(lines))
        chunk_lines = lines[start:end]
        chunks.append(
            CodeChunk(
                path=path,
                start_line=start + 1,
                end_line=end,
                content="\n".join(chunk_lines),
                kind="text",
            )
        )
        if end == len(lines):
            break
        start += step
    return chunks


def _chunk_python_symbols(*, path: str, content: str) -> list[CodeChunk]:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    lines = content.splitlines()
    chunks: list[CodeChunk] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if not hasattr(node, "end_lineno"):
            continue

        start_line = int(node.lineno)
        end_line = int(node.end_lineno or node.lineno)
        if start_line < 1 or end_line < start_line:
            continue

        parent_class = _parent_class_name(tree, node)
        if isinstance(node, ast.ClassDef):
            kind = "class"
            symbol_name = node.name
        elif parent_class:
            kind = "method"
            symbol_name = f"{parent_class}.{node.name}"
        else:
            kind = "function"
            symbol_name = node.name

        chunks.append(
            CodeChunk(
                path=path,
                start_line=start_line,
                end_line=end_line,
                content="\n".join(lines[start_line - 1 : end_line]),
                symbol_name=symbol_name,
                kind=kind,
            )
        )

    return sorted(chunks, key=lambda chunk: (chunk.start_line, chunk.end_line, chunk.symbol_name or ""))


def _parent_class_name(tree: ast.AST, target: ast.AST) -> str | None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for child in node.body:
            if child is target:
                return node.name
    return None
