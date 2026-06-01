from pyagentcli.rag.chunker import chunk_text


def test_chunk_text_splits_lines_with_overlap() -> None:
    content = "\n".join(f"line {number}" for number in range(1, 8))

    chunks = chunk_text(path="app.py", content=content, max_lines=3, overlap_lines=1)

    assert [(chunk.start_line, chunk.end_line) for chunk in chunks] == [(1, 3), (3, 5), (5, 7)]
    assert chunks[1].content.splitlines()[0] == "line 3"


def test_chunk_text_handles_empty_files() -> None:
    chunks = chunk_text(path="empty.py", content="")

    assert len(chunks) == 1
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 1
    assert chunks[0].content == ""


def test_chunk_text_extracts_python_functions_classes_and_methods() -> None:
    content = "\n".join(
        [
            "def project_status():",
            "    return 'READY'",
            "",
            "class Runner:",
            "    def run(self):",
            "        return project_status()",
            "",
            "async def refresh():",
            "    return await load()",
        ]
    )

    chunks = chunk_text(path="app.py", content=content)

    assert [(chunk.symbol_name, chunk.kind, chunk.start_line, chunk.end_line) for chunk in chunks] == [
        ("project_status", "function", 1, 2),
        ("Runner", "class", 4, 6),
        ("Runner.run", "method", 5, 6),
        ("refresh", "function", 8, 9),
    ]
    assert chunks[2].content == "    def run(self):\n        return project_status()"


def test_chunk_text_falls_back_for_invalid_python() -> None:
    chunks = chunk_text(path="broken.py", content="def nope(:\n", max_lines=5)

    assert len(chunks) == 1
    assert chunks[0].kind == "text"
    assert chunks[0].symbol_name is None
