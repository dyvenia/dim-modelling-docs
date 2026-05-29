# Dimensional Modelling Docs — MCP server

A [FastMCP](https://gofastmcp.com) server that exposes the docs in `../src` to
LLMs through tool calls. It reads the Markdown sources directly (parsing
`SUMMARY.md` for titles, ordering, and sections) — no build step required.

## Tools

Pages (prose) and definitions (glossary) have parallel `list` / `read` tools:

| Tool | Purpose | Returns |
|------|---------|---------|
| `list_docs()` | Compact index of every prose page — slug, title, section, summary, headings. | `DocIndex` |
| `search_docs(query, limit=5)` | Keyword search across **all** content (pages + definitions); ranked snippets. | `SearchResponse` |
| `read_doc(slug, section=None)` | Full page Markdown, or just one section. | `PageContent` |
| `list_definitions()` | Compact glossary — every term, its aliases, and a one-line definition. | `Glossary` |
| `read_definition(term)` | Full definition for a term, resolved by name/alias (case- & plural-insensitive). | `Definition` |

Definitions are the atomic, one-term-per-file pages under `src/definitions/`.
They are exposed through the dedicated definition tools and are **excluded from
`list_docs`** (to keep the page index focused) but **included in `search_docs`**.

**Designed for LLMs:** every page has a stable `slug` returned everywhere and
accepted as input (no path guessing); `read_definition` resolves human terms
(plurals, acronyms via an `Also known as:` line) so the model needn't know slugs;
the indexes ship summaries/one-liners and search ships snippets, so the model
reads a full page only when it needs to; and every tool returns a typed Pydantic
model, so FastMCP advertises an output schema the model can rely on. Unknown
slugs/sections/terms raise a `ToolError` that lists the valid options.

## Authoring definitions

One term per file in `src/definitions/`, following `src/definitions/_template.md`
(files prefixed with `_` are templates — ignored by the tools and the book). The
first paragraph after the H1 becomes the `list_definitions` one-liner; an optional
`> **Also known as:** SCD, DD` line registers aliases that `read_definition` will
resolve.

## Run

Uses [`uv`](https://docs.astral.sh/uv/). From this directory — `uv run` creates
the environment and installs the dependencies in `pyproject.toml` on first use:

```bash
uv run server.py           # stdio transport (for Claude Desktop / Claude Code)
```

Point it at a different docs tree with the `DOCS_SRC` env var:

```bash
DOCS_SRC=/path/to/other/src uv run server.py
```

### Inspect interactively

```bash
uv run fastmcp dev server.py   # opens the MCP Inspector in the browser
```

## Connect a client

### Claude Code

```bash
claude mcp add dim-modelling-docs -- uv --directory /abs/path/to/mcp-server run server.py
```

### Claude Desktop / generic `mcpServers` config

```json
{
  "mcpServers": {
    "dim-modelling-docs": {
      "command": "uv",
      "args": ["--directory", "/abs/path/to/mcp-server", "run", "server.py"]
    }
  }
}
```

On Windows, either use the WSL path (`/mnt/c/Users/.../mcp-server`) when launching
through WSL, or wrap the command with `wsl.exe -d Ubuntu -- ...` so the server runs
in the same environment where `uv` and the docs live.
