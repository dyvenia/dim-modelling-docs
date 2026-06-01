"""FastMCP server exposing the Dimensional Modelling Docs to LLMs.

The server reads the mdBook sources (``src/``) and exposes three tools designed
for efficient LLM use:

* ``list_docs``   -- a compact index of every page (title, section, summary,
                     headings) so the model can orient itself cheaply.
* ``search_docs`` -- keyword search returning ranked snippets with the heading
                     they appear under, so the model can pick what to read.
* ``read_doc``    -- the full Markdown of a page, or just one section of it.

Design notes for good LLM interactions:
* Every page has a stable ``slug`` (e.g. ``concepts/kimball-keys``). Slugs are
  returned everywhere and accepted as input -- the model never has to guess file
  paths.
* Outputs are structured and token-frugal: the index ships summaries + headings,
  not full bodies; search ships snippets, not whole files. Read the page only
  when you actually need it.
* Every tool returns a typed Pydantic model, so FastMCP advertises an output
  schema for each tool -- the model knows the exact shape of what it will get.
* Tool and parameter docstrings tell the model exactly when and how to chain the
  tools, which materially improves tool selection.

Run with ``uv run server.py`` (see README).
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

# Docs source dir: env override, else ``../src`` relative to this file.
DOCS_SRC = Path(
    os.environ.get("DOCS_SRC", Path(__file__).resolve().parent.parent / "src")
).resolve()

# Pages under src/<this>/ are treated as atomic glossary definitions and exposed
# via the dedicated `list_definitions` / `read_definition` tools.
DEFINITIONS_SUBDIR = "definitions"

mcp = FastMCP(
    name="dim-modelling-docs",
    instructions=(
        "Reference documentation for dimensional (Kimball) data modelling. "
        "Use these tools to answer questions about dimensional modelling "
        "conventions, key types, and specific facts/dimensions/measures. "
        "For a quick term lookup, call `read_definition(term)` (browse terms with "
        "`list_definitions`). For deeper material, call `search_docs` with the "
        "user's terms (or `list_docs` to browse), then `read_doc` on the most "
        "relevant slug. Quote the docs; do not invent conventions they don't state."
    ),
)


# --------------------------------------------------------------------------- #
# Internal doc model + parsing
# --------------------------------------------------------------------------- #


class Doc(BaseModel):
    """Parsed representation of one documentation page (internal)."""

    slug: str  # stable id, e.g. "concepts/kimball-keys"
    title: str  # human title from SUMMARY.md / H1
    section: str  # part/group from SUMMARY.md, e.g. "Reference" ("" if none)
    path: Path  # absolute path to the .md file
    summary: str  # first paragraph after the H1
    headings: list[str] = Field(default_factory=list)  # in-page headings
    aliases: list[str] = Field(default_factory=list)  # from "Also known as:"
    text: str = ""  # raw markdown body

    @property
    def is_definition(self) -> bool:
        return self.slug.startswith(f"{DEFINITIONS_SUBDIR}/")


# --------------------------------------------------------------------------- #
# Tool response models (these become each tool's advertised output schema)
# --------------------------------------------------------------------------- #


class DocSummary(BaseModel):
    """One entry in the documentation index."""

    slug: str = Field(description="Stable page id; pass to read_doc.")
    title: str = Field(description="Human-readable page title.")
    section: str = Field(description="Book section/part this page belongs to.")
    summary: str = Field(description="One-line description of the page.")
    headings: list[str] = Field(description="In-page headings you can target via read_doc(section=...).")


class DocIndex(BaseModel):
    """Compact index of all documentation pages."""

    doc_count: int
    docs: list[DocSummary]
    usage: str = Field(description="Hint on how to use the returned slugs.")


class SearchHit(BaseModel):
    """A single search match."""

    slug: str = Field(description="Page id; pass to read_doc.")
    title: str = Field(description="Title of the matching page.")
    section_heading: str = Field(description="Heading the match falls under; pass as read_doc(section=...).")
    snippet: str = Field(description="Short surrounding context for the match.")
    score: int = Field(description="Relevance score (higher is better).")


class SearchResponse(BaseModel):
    """Ranked search results."""

    query: str
    result_count: int
    results: list[SearchHit]
    next_step: str = Field(description="Suggested follow-up call.")


class PageContent(BaseModel):
    """Full page, or a single requested section, as Markdown."""

    slug: str
    title: str
    section: str = Field(description="Book section/part this page belongs to.")
    content: str = Field(description="Markdown content of the page or section.")
    requested_section: str | None = Field(
        default=None, description="The section filter that was applied, if any."
    )
    path: str | None = Field(default=None, description="Source path relative to the docs root.")
    headings: list[str] | None = Field(
        default=None, description="In-page headings (only when returning a full page)."
    )


class DefinitionSummary(BaseModel):
    """One glossary entry, condensed to its canonical one-liner."""

    term: str = Field(description="Canonical term; pass to read_definition.")
    slug: str = Field(description="Stable id; also readable via read_doc.")
    definition: str = Field(description="The one-line canonical definition.")
    aliases: list[str] = Field(description="Synonyms/acronyms that also resolve to this term.")


class Glossary(BaseModel):
    """Alphabetical list of all defined terms."""

    term_count: int
    definitions: list[DefinitionSummary]
    usage: str = Field(description="Hint on how to read a full definition.")


class Definition(BaseModel):
    """A full glossary definition as Markdown."""

    term: str = Field(description="Canonical term.")
    slug: str
    aliases: list[str] = Field(description="Synonyms/acronyms for this term.")
    matched_on: str = Field(description="The lookup key that resolved the request.")
    content: str = Field(description="Full Markdown of the definition.")


_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_PART_RE = re.compile(r"^#\s+(.*\S)\s*$")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$", re.MULTILINE)
_ALIAS_RE = re.compile(r"\*\*Also known as:\*\*\s*(.+)", re.IGNORECASE)


def _slug_for(rel_path: str) -> str:
    """`./concepts/kimball-keys.md` -> `concepts/kimball-keys`."""
    p = rel_path.strip().lstrip("./")
    if p.endswith(".md"):
        p = p[:-3]
    return p.replace("\\", "/")


def anchor(heading: str) -> str:
    """mdBook-style anchor slug for a heading (for `section=` matching)."""
    a = heading.strip().lower()
    a = re.sub(r"[^\w\s-]", "", a)
    a = re.sub(r"\s+", "-", a)
    return a.strip("-")


def _extract_summary(body: str) -> str:
    """First real paragraph after the H1 (skips blockquotes/headings/blanks)."""
    lines = body.splitlines()
    paras: list[str] = []
    buf: list[str] = []
    for line in lines:
        s = line.strip()
        if not s:
            if buf:
                paras.append(" ".join(buf))
                buf = []
            continue
        if s.startswith("#"):  # heading -> paragraph boundary
            if buf:
                paras.append(" ".join(buf))
                buf = []
            continue
        if s.startswith((">", "|", "```", "-", "*")):  # skip non-prose blocks
            if buf:
                paras.append(" ".join(buf))
                buf = []
            continue
        buf.append(s)
    if buf:
        paras.append(" ".join(buf))
    for p in paras:
        if len(p) > 20:  # first substantive paragraph
            return p
    return paras[0] if paras else ""


@lru_cache(maxsize=1)
def _load_docs() -> dict[str, Doc]:
    """Parse SUMMARY.md for order/titles/sections, then load each page."""
    docs: dict[str, Doc] = {}
    summary = DOCS_SRC / "SUMMARY.md"
    seen: set[str] = set()

    # 1) Walk SUMMARY.md to capture titles + section grouping in book order.
    if summary.exists():
        current_section = ""
        first_part = True
        for raw in summary.read_text(encoding="utf-8").splitlines():
            line = raw.rstrip()
            if line.strip() == "---":  # separator clears the current part
                current_section = ""
                continue
            part = _PART_RE.match(line)
            if part:
                # The first H1 in SUMMARY.md is the book title ("Summary"); skip.
                if first_part and part.group(1).lower() == "summary":
                    first_part = False
                    continue
                first_part = False
                current_section = part.group(1)
                continue
            m = _LINK_RE.search(line)
            if not m:
                continue
            title, target = m.group(1), m.group(2)
            if not target.endswith(".md"):
                continue
            slug = _slug_for(target)
            path = (DOCS_SRC / Path(target.lstrip("./"))).resolve()
            seen.add(slug)
            if path.exists() and not path.name.startswith("_"):
                docs[slug] = _build_doc(slug, title, current_section, path)

    # 2) Include any .md on disk not listed in SUMMARY (drafts, etc.).
    #    Skip `_`-prefixed files -- they are contributor templates, not content.
    for path in sorted(DOCS_SRC.rglob("*.md")):
        if path.name == "SUMMARY.md" or path.name.startswith("_"):
            continue
        slug = _slug_for(str(path.relative_to(DOCS_SRC)).replace(os.sep, "/"))
        if slug in seen:
            continue
        docs[slug] = _build_doc(slug, _title_from_file(path), "Unlisted", path)

    return docs


def _title_from_file(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#\s+(.*\S)", line)
        if m:
            return m.group(1)
    return path.stem.replace("-", " ").title()


def _parse_aliases(body: str) -> list[str]:
    """Pull synonyms from an `**Also known as:** SCD, DD` line, if present."""
    m = _ALIAS_RE.search(body)
    if not m:
        return []
    raw = re.sub(r"[*_`>]", "", m.group(1))  # strip markdown emphasis/quote marks
    raw = re.sub(r"_.*?_", "", raw)  # drop italic placeholder text
    return [a.strip() for a in re.split(r"[,/·;]", raw) if a.strip()]


def _build_doc(slug: str, title: str, section: str, path: Path) -> Doc:
    body = path.read_text(encoding="utf-8")
    # Body without the leading H1 (we already have the title).
    body_wo_h1 = re.sub(r"\A\s*#\s+.*\n", "", body, count=1)
    headings = [h.group(2) for h in _HEADING_RE.finditer(body) if h.group(1) != "#"]
    return Doc(
        slug=slug,
        title=title,
        section=section,
        path=path,
        summary=_extract_summary(body_wo_h1),
        headings=headings,
        aliases=_parse_aliases(body),
        text=body,
    )


def _extract_section(doc: Doc, wanted: str) -> str | None:
    """Return the Markdown of one heading's section (heading + body until the
    next heading of equal-or-higher level). Matches on heading text or anchor."""
    want = wanted.strip().lower()
    matches = list(_HEADING_RE.finditer(doc.text))
    for i, m in enumerate(matches):
        level, text = len(m.group(1)), m.group(2)
        if text.strip().lower() == want or anchor(text) == anchor(wanted):
            start = m.start()
            end = len(doc.text)
            for nxt in matches[i + 1 :]:
                if len(nxt.group(1)) <= level:
                    end = nxt.start()
                    break
            return doc.text[start:end].strip()
    return None


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #


@mcp.tool
def list_docs() -> DocIndex:
    """List the documentation pages with a compact, token-frugal index.

    Use this to discover what documentation exists before reading or searching.
    Each entry includes a stable `slug` (pass it to `read_doc`), the page title,
    its section, a one-line summary, and the in-page headings so you can target a
    specific section.

    Short glossary terms are NOT listed here -- get those from `list_definitions`.

    Returns:
        A `DocIndex` with `doc_count`, a `docs` list (slug, title, section,
        summary, headings), and a `usage` hint for the next step.
    """
    docs = [d for d in _load_docs().values() if not d.is_definition]
    return DocIndex(
        doc_count=len(docs),
        docs=[
            DocSummary(
                slug=d.slug,
                title=d.title,
                section=d.section,
                summary=d.summary,
                headings=d.headings,
            )
            for d in docs
        ],
        usage=(
            "Call read_doc(slug) for a full page, read_doc(slug, section=...) for "
            "one heading, or search_docs(query) to find passages by keyword. "
            "For short term definitions, use list_definitions / read_definition."
        ),
    )


@mcp.tool
def search_docs(
    query: Annotated[
        str,
        Field(description="Keywords or a phrase to find, e.g. 'surrogate key' or 'point-in-time join'."),
    ],
    limit: Annotated[
        int,
        Field(description="Maximum number of results to return.", ge=1, le=25),
    ] = 5,
) -> SearchResponse:
    """Search the documentation and return ranked snippets with their location.

    Prefer this over reading whole pages when you have specific terms. Each
    result tells you the page `slug`, the `section_heading` the match falls under,
    and a short `snippet` for context. Follow up with
    `read_doc(slug, section=section_heading)` to get the full passage.

    Matching is case-insensitive over titles, headings, and body text; results
    are scored by where and how often the terms appear (title > heading > body).

    Args:
        query: Keywords or phrase to search for.
        limit: Maximum number of results (1-25).

    Returns:
        A `SearchResponse` with `query`, `result_count`, and a `results` list.
    """
    docs = _load_docs()
    terms = [t for t in re.split(r"\s+", query.lower().strip()) if t]
    if not terms:
        return SearchResponse(
            query=query,
            result_count=0,
            results=[],
            next_step="Empty query. Provide keywords to search for.",
        )

    hits: list[SearchHit] = []
    for d in docs.values():
        title_l = d.title.lower()
        text_l = d.text.lower()
        # Score: title hits weigh most, then heading hits, then body frequency.
        score = 0
        for t in terms:
            score += 8 * title_l.count(t)
            score += 4 * sum(t in h.lower() for h in d.headings)
            score += text_l.count(t)
        # Require every term to appear somewhere (AND semantics).
        if not all((t in title_l) or (t in text_l) for t in terms):
            continue
        if score == 0:
            continue
        loc, snippet = _best_snippet(d, terms)
        hits.append(
            SearchHit(
                slug=d.slug,
                title=d.title,
                section_heading=loc,
                snippet=snippet,
                score=score,
            )
        )

    hits.sort(key=lambda h: h.score, reverse=True)
    hits = hits[:limit]
    return SearchResponse(
        query=query,
        result_count=len(hits),
        results=hits,
        next_step=(
            "Call read_doc(slug, section=section_heading) for the full passage, "
            "or read_doc(slug) for the whole page."
            if hits
            else "No matches. Try broader terms or call list_docs()."
        ),
    )


def _best_snippet(doc: Doc, terms: list[str]) -> tuple[str, str]:
    """Return (nearest_heading, snippet) for the first term occurrence."""
    text = doc.text
    lower = text.lower()
    pos = min(
        (lower.find(t) for t in terms if lower.find(t) != -1),
        default=-1,
    )
    if pos == -1:
        return ("", doc.summary[:300])

    # Nearest preceding heading => section context.
    heading = ""
    for m in _HEADING_RE.finditer(text):
        if m.start() > pos:
            break
        if len(m.group(1)) != 1:  # ignore the H1 title
            heading = m.group(2)

    start = max(0, pos - 120)
    end = min(len(text), pos + 220)
    snippet = text[start:end].strip().replace("\n", " ")
    snippet = re.sub(r"\s+", " ", snippet)
    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet = snippet + "…"
    return (heading, snippet)


@mcp.tool
def read_doc(
    slug: Annotated[
        str,
        Field(description="Page id from list_docs/search_docs, e.g. 'reference/standard-cost'."),
    ],
    section: Annotated[
        str | None,
        Field(description="Optional heading text (or its anchor) to return just that section, e.g. 'Common Pitfalls'."),
    ] = None,
) -> PageContent:
    """Return the full Markdown of a documentation page, or one section of it.

    Get the `slug` from `list_docs` or `search_docs`. Pass `section` (a heading
    title or anchor) to retrieve only that part of a long page and save tokens;
    omit it for the whole page. Invalid slugs/sections raise an error that lists
    what is available, so you can correct the call.

    Args:
        slug: The page identifier, e.g. 'concepts/kimball-keys'.
        section: Optional heading to scope the result to one section.

    Returns:
        A `PageContent` with page metadata and a `content` field of Markdown.
    """
    docs = _load_docs()
    doc = docs.get(slug)
    if doc is None:
        raise ToolError(
            f"Unknown slug {slug!r}. Call list_docs() to see valid slugs. "
            f"Available: {', '.join(sorted(docs))}"
        )

    if section:
        content = _extract_section(doc, section)
        if content is None:
            raise ToolError(
                f"Section {section!r} not found in {slug!r}. "
                f"Available headings: {', '.join(doc.headings) or '(none)'}. "
                "Retry with one of those, or omit section for the whole page."
            )
        return PageContent(
            slug=doc.slug,
            title=doc.title,
            section=doc.section,
            requested_section=section,
            content=content,
        )

    return PageContent(
        slug=doc.slug,
        title=doc.title,
        section=doc.section,
        path=str(doc.path.relative_to(DOCS_SRC)),
        headings=doc.headings,
        content=doc.text,
    )


# --------------------------------------------------------------------------- #
# Definitions (glossary) tools
# --------------------------------------------------------------------------- #


def _definitions() -> list[Doc]:
    """All glossary docs, sorted by term."""
    return sorted(
        (d for d in _load_docs().values() if d.is_definition),
        key=lambda d: d.title.lower(),
    )


def _norm(s: str) -> str:
    """Lowercase, collapse non-alphanumerics to single spaces."""
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _singularize(s: str) -> str:
    """Crude de-pluralization so 'keys'/'dimensions' match 'key'/'dimension'."""
    if s.endswith("ies"):
        return s[:-3] + "y"
    if s.endswith("ses"):
        return s[:-2]
    if s.endswith("s") and not s.endswith("ss"):
        return s[:-1]
    return s


def _lookup_keys(doc: Doc) -> set[str]:
    """Every normalized string that should resolve to this definition."""
    raw = [doc.title, doc.slug.split("/")[-1].replace("-", " "), *doc.aliases]
    keys: set[str] = set()
    for r in raw:
        n = _norm(r)
        if n:
            keys.add(n)
            keys.add(_singularize(n))
    return keys


def _resolve_definition(term: str) -> tuple[Doc, str] | None:
    """Resolve a human term to a definition. Returns (doc, matched_key) or None.

    Tries, in order: exact key match, singularized match, then unambiguous
    substring match (term contained in a key or vice versa)."""
    q = _norm(term)
    if not q:
        return None
    qs = _singularize(q)

    defs = _definitions()
    by_key: dict[str, Doc] = {}
    for d in defs:
        for k in _lookup_keys(d):
            by_key.setdefault(k, d)

    if q in by_key:
        return by_key[q], q
    if qs in by_key:
        return by_key[qs], qs

    # Fall back to a substring match, but only if it is unambiguous.
    candidates = {
        d.slug: (d, k)
        for d in defs
        for k in _lookup_keys(d)
        if qs in k or k in qs
    }
    if len(candidates) == 1:
        return next(iter(candidates.values()))
    return None


@mcp.tool
def list_definitions() -> Glossary:
    """List every defined term with its one-line definition (a compact glossary).

    Use this to see which terms have a dedicated definition before calling
    `read_definition`. Each entry carries the canonical `term`, any `aliases`
    (acronyms/synonyms that also resolve), and the one-line `definition`.

    Returns:
        A `Glossary` with `term_count` and an alphabetical `definitions` list.
    """
    defs = _definitions()
    return Glossary(
        term_count=len(defs),
        definitions=[
            DefinitionSummary(
                term=d.title,
                slug=d.slug,
                definition=d.summary,
                aliases=d.aliases,
            )
            for d in defs
        ],
        usage="Call read_definition(term) for the full entry; term-matching is case- and plural-insensitive and accepts aliases.",
    )


@mcp.tool
def read_definition(
    term: Annotated[
        str,
        Field(description="The term to define, e.g. 'degenerate dimension', 'SCD', or 'grain'."),
    ],
) -> Definition:
    """Look up a single glossary term and return its full definition as Markdown.

    Resolution is forgiving: matching is case-insensitive, tolerates plural vs
    singular ('keys' -> 'key'), and accepts known aliases ('SCD' -> 'Slowly
    Changing Dimension'). If the term is unknown or ambiguous, the error lists the
    available terms so you can retry. Use `list_definitions` to browse first.

    Args:
        term: The term, acronym, or synonym to define.

    Returns:
        A `Definition` with the canonical term, aliases, and Markdown content.
    """
    resolved = _resolve_definition(term)
    if resolved is None:
        available = ", ".join(d.title for d in _definitions()) or "(none)"
        raise ToolError(
            f"No definition matches {term!r}. Available terms: {available}. "
            "Call list_definitions() to browse, or search_docs() for prose pages."
        )
    doc, matched = resolved
    return Definition(
        term=doc.title,
        slug=doc.slug,
        aliases=doc.aliases,
        matched_on=matched,
        content=doc.text,
    )


if __name__ == "__main__":
    # Transport is chosen via env so the same file works locally and deployed:
    #   * unset / "stdio" -> stdio (Claude Desktop / Code, the default)
    #   * "http"          -> streamable HTTP service (remote deployment)
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        mcp.run()
    else:
        mcp.run(
            transport=transport,
            host=os.environ.get("MCP_HOST", "0.0.0.0"),
            port=int(os.environ.get("MCP_PORT", "8000")),
        )
