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
