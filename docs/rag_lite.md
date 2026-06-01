# RAG Lite and Hybrid Retrieval

RAG Lite is PyAgentCLI's first code-retrieval layer. It now sits behind a small hybrid retrieval interface, so deterministic FTS search can later be combined with vector search without changing the Agent tool contract.

The first version intentionally avoids embeddings and vector databases. It starts with two deterministic local search tools:

```text
search_files(query, path=".", max_results=20, case_sensitive=false)
search_text(query, path=".", max_results=20, case_sensitive=false)
search_index(query, max_results=20)
```

Advanced RAG v0.1 adds:

- `EmbeddingProvider` interface
- `NullEmbeddingProvider` fallback
- deterministic `HashEmbeddingProvider` for tests and future vector-store plumbing
- `HybridRetriever`
- `HybridSearchResult`
- `RetrievalHit` with source and score fields
- SQLite `chunk_vectors` table for optional vector persistence
- vector + FTS deduping in `HybridRetriever`
- Python import graph extraction into SQLite

When no embedding provider is configured, vector retrieval is disabled and `search_index` behaves like the previous SQLite FTS search.

## Why Start With Text Search

For coding agents, a lot of useful retrieval is exact:

- Function names
- Class names
- Error messages
- Config keys
- CLI commands
- TODO markers
- Test names

Exact search is predictable, cheap, local, and easy to audit.

## Tool Behavior

`search_files`:

- Searches workspace file paths and basenames.
- Returns relative file paths.
- Useful when the model knows part of a filename, module path, or extension.
- Skips generated and sensitive directories.
- Limits results with `max_results`.

`search_text`:

- Searches only inside the workspace.
- Returns `path:line:snippet` matches.
- Skips generated and sensitive directories such as `.git`, `.pyagent`, `.venv`, `node_modules`, and `.pytest_cache`.
- Skips common binary file suffixes.
- Limits results with `max_results`.

`search_index`:

- Searches through `HybridRetriever`.
- Uses the local SQLite FTS index at `.pyagent/index.sqlite`.
- Returns indexed chunk locations, symbol labels when available, and short highlighted snippets.
- Fails safely with a clear message if the index has not been built yet.
- Warns when indexed files have changed, disappeared, or new indexable files have appeared.
- Works best for symbols, config keys, error messages, and exact phrases.
- Reports metadata about whether vector retrieval is enabled.

## Example

```bash
PYTHONPATH=src python -m pyagentcli \
  "Find where project_status is defined"
```

The model can first call:

```json
{
  "query": "app",
  "path": ".",
  "max_results": 20
}
```

Then call:

```json
{
  "query": "project_status",
  "path": ".",
  "max_results": 20
}
```

## Explicit Context References

Users can attach small explicit context references directly in a task:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  "Summarize @README.md and inspect @./"
```

Supported references:

- `@path/to/file`
- `@path/to/folder/`
- `@symbol`

PyAgentCLI resolves references inside the workspace, applies the same path guardrails, and appends a bounded context block to the task. Sensitive paths such as `.env` and `.pyagent` are not injected.

For `@symbol`, PyAgentCLI first checks whether the reference is a real file or folder. If it is not, and the token looks like a code symbol, it first searches exact indexed symbols, then falls back to SQLite FTS and injects the top matching chunks.

Example:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --index

PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  "Explain @project_status"
```

## SQLite FTS Index

Build a local SQLite FTS index:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --index
```

The index is stored at:

```text
.pyagent/index.sqlite
```

The index stores both file metadata and line-based chunks. Python files are chunked with `ast` into functions, classes, and methods with `symbol_name` and `kind` metadata. Other UTF-8 files use deterministic line windows with overlap, so nearby context is preserved without forcing the Agent to read an entire file. It skips generated and sensitive paths such as `.git`, `.pyagent`, `.venv`, `node_modules`, and `.pytest_cache`.

Search results include a stale-index warning when the current workspace no longer matches the stored file metadata. PyAgentCLI does not silently rebuild the index during a task; it asks the user to run `pyagent --index` so retrieval changes remain explicit and auditable.

Once the index exists, the Agent can call:

```json
{
  "query": "project_status",
  "max_results": 20
}
```

This returns indexed snippets, then the Agent can use `read_file` for focused follow-up reading.

Example output:

```text
app.py:1-2 function project_status: def [project_status](): return 'READY'
```

## Hybrid Retrieval Shape

The retrieval layer now has this shape:

```text
search_index tool
  -> HybridRetriever
    -> SQLite FTS hits
    -> optional SQLite vector hits
    -> deduped RetrievalHit list
```

This keeps the current local behavior stable while making room for embeddings, vector stores, reranking, and import-graph signals.

## Vector Store

Vector persistence is optional.

The default `pyagent --index` path does not write embeddings because `NullEmbeddingProvider` is used. When a real or test provider is passed to `CodeIndexer`, vectors are written into:

```text
chunk_vectors
```

Each row stores:

- path
- start and end line
- symbol name
- kind
- content
- provider name
- dimensions
- embedding JSON

`HybridRetriever` can then query the vector table and merge vector hits with FTS hits.

## Python Import Graph

During indexing, PyAgentCLI extracts Python imports into:

```text
python_imports
```

Each row stores:

- path
- imported module
- imported name
- relative import level
- source line

The indexer exposes:

```python
CodeIndexer(workspace).imports_for("src/app.py")
CodeIndexer(workspace).imported_by("helpers")
```

This is the first dependency-graph signal for retrieval. It does not change default `search_index` output yet; it creates the data layer for future dependency-aware context injection.

## Embedding Config

Embedding providers can be configured in `pyagent.toml`:

```toml
[rag.embeddings]
provider = "hash"
dimensions = 16
```

Supported providers:

- `none`: default; no vector indexing.
- `hash`: deterministic local test provider.
- `openai-compatible`: calls an OpenAI-compatible `/embeddings` endpoint.

OpenAI-compatible example:

```toml
[rag.embeddings]
provider = "openai-compatible"
model = "text-embedding-3-small"
base_url = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"
```

The API key is read from the named environment variable. Do not put secrets directly in `pyagent.toml`.

If the embedding provider is not configured, missing, or fails during indexing/search, PyAgentCLI falls back to deterministic FTS behavior.

## Next Steps

1. Add symbol-aware chunking for more languages.
2. Add dependency-aware retrieval output or a dedicated dependency search tool.
3. Add multi-language symbol chunking.
4. Add automatic index refresh as an explicit approved action.
