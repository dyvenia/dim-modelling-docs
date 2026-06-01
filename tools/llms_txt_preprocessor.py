#!/usr/bin/env python3
"""mdbook preprocessor that generates an `llms.txt` index from the book.

`llms.txt` (see https://llmstxt.org) is a curated, link-only index that points
an LLM or agent at the most useful pages of the site. This preprocessor mirrors
the SUMMARY.md navigation tree: part titles become `##` sections, draft entries
(e.g. "References", "Dimensions") become bold group headers, and every real
chapter becomes a `- [Title](url): one-line description` bullet.

It does not modify the book content — it emits the index as a side file and
passes the book through unchanged.

Output: written to `<src>/llms.txt` so mdbook's static-file copy ships it to the
build output (served at `/llms.txt`). The write is idempotent (skipped when the
content is unchanged) so it never triggers an `mdbook serve` rebuild loop.

Config (book.toml, all optional):

    [preprocessor.llms-txt]
    command  = "python3 tools/llms_txt_preprocessor.py"
    renderer = ["html"]
    site-url = "https://example.com/"   # absolute base for links; "" = relative
    filename = "llms.txt"               # output name under <src>
"""

import json
import os
import re
import sys


def log(msg):
    print(f"[llms-txt] {msg}", file=sys.stderr)


# --- description extraction --------------------------------------------------

_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")  # [text](url) -> text
_STAR_RE = re.compile(r"\*+")                     # **bold**, *italic*
_WS_RE = re.compile(r"\s+")

# Lines that are structure, not prose — never start a description with these.
# (Underscores are NOT treated as emphasis: identifiers like `dim_product`
# must survive intact.)
_SKIP_PREFIXES = ("#", ">", "|", "-", "*", "+", "```", "<!--", "![", "%%")


def first_paragraph(content):
    """Return the first real prose paragraph of a chapter, as a clean string.

    Skips headings, blockquotes, tables, lists, images and fenced code (incl.
    mermaid) — wherever they appear — and takes the first run of prose lines.
    Works whether or not the page opens with an H1 title.
    """
    in_code = False
    para = []
    for raw in content.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not para:
            if not line or line.startswith(_SKIP_PREFIXES):
                continue
            para.append(line)
        else:
            if not line:
                break  # paragraph ended
            para.append(line)
    return clean(" ".join(para))


def clean(text, limit=160):
    text = _LINK_RE.sub(r"\1", text)
    text = text.replace("`", "")
    text = _STAR_RE.sub("", text)
    text = _WS_RE.sub(" ", text).strip()
    if len(text) > limit:
        cut = text[:limit].rsplit(" ", 1)[0].rstrip(" ,.;:")
        text = cut + "…"
    return text


# --- url + tree rendering ----------------------------------------------------


def make_url(path, site_url):
    rel = path.replace("\\", "/").lstrip("./")
    if rel.endswith(".md"):
        rel = rel[:-3] + ".html"
    if site_url:
        return site_url.rstrip("/") + "/" + rel
    return rel


def render_chapter(ch, out, depth, site_url):
    indent = "  " * depth
    name = ch.get("name", "")
    path = ch.get("path")
    if path:
        url = make_url(path, site_url)
        desc = first_paragraph(ch.get("content", "") or "")
        line = f"{indent}- [{name}]({url})"
        if desc:
            line += f": {desc}"
        out.append(line)
    else:
        # Draft entry (no page of its own) — a grouping header in the nav.
        out.append(f"{indent}- **{name}**")
    for sub in ch.get("sub_items", []) or []:
        if "Chapter" in sub:
            render_chapter(sub["Chapter"], out, depth + 1, site_url)


def build_index(book, config):
    pre_cfg = (config.get("preprocessor") or {}).get("llms-txt") or {}
    book_cfg = config.get("book") or {}
    site_url = pre_cfg.get("site-url", "") or ""
    title = pre_cfg.get("title") or book_cfg.get("title") or "Documentation"
    summary = pre_cfg.get("summary") or book_cfg.get("description") or ""

    groups = []  # list of (heading, [lines])
    current = None

    def ensure(heading):
        nonlocal current
        current = (heading, [])
        groups.append(current)

    for item in book.get("items", []):
        if "PartTitle" in item:
            ensure(item["PartTitle"])
        elif "Chapter" in item:
            if current is None:
                ensure("Overview")  # chapters before any part title
            render_chapter(item["Chapter"], current[1], 0, site_url)
        # "Separator" items are ignored

    lines = [f"# {title}", ""]
    if summary:
        lines += [f"> {clean(summary, limit=300)}", ""]
    for heading, body in groups:
        if not body:
            continue
        lines += [f"## {heading}", ""]
        lines += body
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# --- io ----------------------------------------------------------------------


def write_if_changed(path, content):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            if fh.read() == content:
                log(f"unchanged: {path}")
                return
    except FileNotFoundError:
        pass
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    log(f"wrote: {path}")


def main():
    # mdbook asks `<cmd> supports <renderer>`; exit 0 = supported.
    if len(sys.argv) > 1 and sys.argv[1] == "supports":
        sys.exit(0 if len(sys.argv) > 2 and sys.argv[2] == "html" else 1)

    context, book = json.load(sys.stdin)
    config = context.get("config", {})
    if context.get("renderer") not in (None, "html"):
        json.dump(book, sys.stdout)
        return

    pre_cfg = (config.get("preprocessor") or {}).get("llms-txt") or {}
    src_dir = (config.get("book") or {}).get("src") or "src"
    filename = pre_cfg.get("filename") or "llms.txt"
    out_path = os.path.join(context.get("root", "."), src_dir, filename)

    try:
        write_if_changed(out_path, build_index(book, config))
    except Exception as exc:  # never break the build over the index
        log(f"ERROR generating index: {exc}")

    json.dump(book, sys.stdout)


if __name__ == "__main__":
    main()
