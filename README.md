# Dimensional Modelling Docs

Reference documentation for dimensional (Kimball) data modelling, built with
[mdBook](https://rust-lang.github.io/mdBook/).

## Prerequisites

You need the `mdbook` binary on your `PATH`. This project was set up under
**WSL (Ubuntu)** using the precompiled Linux binary — no Rust toolchain required.

Install (or upgrade) mdBook:

```bash
mkdir -p ~/.local/bin
curl -fsSL \
  https://github.com/rust-lang/mdBook/releases/download/v0.5.3/mdbook-v0.5.3-x86_64-unknown-linux-gnu.tar.gz \
  | tar -xz -C ~/.local/bin mdbook
chmod +x ~/.local/bin/mdbook
```

Make sure `~/.local/bin` is on your `PATH` (Ubuntu's default `~/.profile` adds it
automatically once the directory exists — open a new shell or run
`source ~/.profile`). Verify:

```bash
mdbook --version   # mdbook v0.5.3
```

> Already have Rust? `cargo install mdbook` works too.

### Mermaid diagrams

Diagrams use the [`mdbook-mermaid`](https://github.com/badboy/mdbook-mermaid)
preprocessor, so building needs that binary too:

```bash
curl -fsSL \
  https://github.com/badboy/mdbook-mermaid/releases/download/v0.17.0/mdbook-mermaid-v0.17.0-x86_64-unknown-linux-gnu.tar.gz \
  | tar -xz -C ~/.local/bin mdbook-mermaid
chmod +x ~/.local/bin/mdbook-mermaid
```

The runtime assets (`mermaid.min.js`, `mermaid-init.js`) and `book.toml` config
are already committed, so no further setup is required. Author a diagram with a
fenced ` ```mermaid ` block — see `src/concepts/kimball-keys.md` for an example.

### Image & diagram zoom

Every content image and rendered Mermaid diagram gets a hover **zoom icon** that
opens a full-screen lightbox (scroll to zoom, drag to pan, Esc to close),
implemented in [theme/zoom.js](theme/zoom.js) + [theme/zoom.css](theme/zoom.css)
and loaded via `book.toml`. No authoring needed — it applies automatically.

## Local development

From the project root:

```bash
mdbook serve --open       # build + live-reload preview at http://localhost:3000
mdbook build              # render static HTML into ./book
mdbook clean              # remove the ./book output directory
```

`mdbook serve` watches `src/` and rebuilds on save, refreshing the browser.

### WSL note

mdBook's file-watcher can miss edits when the project lives on a Windows mount
(`/mnt/c/...`) under WSL. If live-reload stops picking up changes:

- re-run `mdbook build` manually after each edit, **or**
- move the project into the Linux filesystem (e.g. `~/dim-modelling-docs`) where
  the watcher is reliable.

## Deployment

### Docs site (mdBook) → GitHub Pages

A workflow at [.github/workflows/deploy-docs.yml](.github/workflows/deploy-docs.yml)
builds the book and publishes it on every push to `main`. It installs the same
`mdbook` (0.5.3) and `mdbook-mermaid` (0.17.0) binaries used locally, runs
`mdbook build`, and deploys `book/` via GitHub Pages.

One-time setup (repo admin): **Settings → Pages → Build and deployment → Source:
GitHub Actions**. After that, pushes to `main` deploy automatically; the live URL
appears in the workflow run and under Settings → Pages.

To deploy to **any other static host** (Netlify, S3, Cloudflare Pages, nginx),
just build and upload the output directory:

```bash
mdbook build          # produces ./book
# then serve / upload the contents of ./book as static files
```

> The bump from version-pinned binaries in CI keeps deploys reproducible. If you
> upgrade mdBook/mdbook-mermaid locally, bump `MDBOOK_VERSION` /
> `MDBOOK_MERMAID_VERSION` in the workflow to match.

### MCP server (`mcp-server/server.py`)

The server picks its transport from environment variables, so the same file runs
locally over stdio or remotely over HTTP:

| Variable | Default | Purpose |
|----------|---------|---------|
| `MCP_TRANSPORT` | `stdio` | `stdio` for desktop clients, `http` for a remote service. |
| `MCP_HOST` | `0.0.0.0` | Bind address (HTTP only). |
| `MCP_PORT` | `8000` | Port (HTTP only). |
| `DOCS_SRC` | `../src` | Path to the docs the server reads. |

**Local (stdio)** — the usual case; the client launches it. See
[mcp-server/README.md](mcp-server/README.md) for client config.

**Remote (HTTP)** — run it as a long-lived service:

```bash
cd mcp-server
MCP_TRANSPORT=http MCP_PORT=8000 uv run server.py
# reachable at http://<host>:8000/mcp
```

**Docker** — build from the repo root (so the docs are included) using
[mcp-server/Dockerfile](mcp-server/Dockerfile):

```bash
docker build -f mcp-server/Dockerfile -t dim-docs-mcp .
docker run -p 8000:8000 dim-docs-mcp        # http://localhost:8000/mcp
```

**Connect a client to the deployed HTTP server:**

```bash
claude mcp add --transport http dim-modelling-docs https://<host>/mcp
```

> Keep it alive in production with your process manager of choice (systemd,
> Docker `--restart`, a PaaS, or [FastMCP Cloud](https://gofastmcp.com)). The
> server is read-only and stateless, so you can run multiple replicas behind a
> load balancer. Put it behind TLS/auth if exposed publicly.

## Project layout

```text
.
├── book.toml          # mdBook configuration
├── README.md          # this file
├── src/
│   ├── SUMMARY.md      # table of contents (controls the sidebar)
│   ├── introduction.md # landing page
│   └── concepts/
│       └── kimball-keys.md
└── book/              # generated HTML output (not committed)
```

## Adding a page

1. Create a Markdown file under `src/` (e.g. `src/concepts/scd-types.md`).
2. Add a link to it in `src/SUMMARY.md` — the sidebar is generated from that file.
3. Run `mdbook serve` to preview.
