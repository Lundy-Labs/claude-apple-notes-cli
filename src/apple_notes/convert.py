"""Markdown <-> Apple-Notes-flavored HTML conversion.

AGENT OWNERSHIP: Agent A implements this file + tests/test_convert.py.
This is pure Python and fully unit-testable without macOS.

Apple Notes stores bodies as HTML. Quirks to handle:
  * The FIRST line/element becomes the note's title.
  * Notes uses <div> blocks rather than <p> for paragraphs.
  * Checklists are <ul class="..."> with checked/unchecked items
    (<- -> Markdown task lists: "- [ ]" / "- [x]").
  * Strip Notes' inline style attributes on read for clean Markdown.
"""

from __future__ import annotations

import re

import markdown as _markdown
from bs4 import BeautifulSoup, Tag
from markdownify import MarkdownConverter

# ---------------------------------------------------------------------------
# Read path: Apple Notes HTML -> Markdown
# ---------------------------------------------------------------------------

# Attributes Apple Notes sprinkles around that carry no meaning for Markdown.
_NOISE_ATTRS = ("style", "class", "dir", "id", "lang", "name")

# Class / attribute hints that Apple Notes uses to mark checklist constructs.
_CHECKLIST_CLASS_HINTS = ("checklist", "apple-checklist")
_CHECKED_HINTS = ("checked",)


def _looks_checked(el: Tag) -> bool:
    """Best-effort detection of a *checked* checklist item across Notes variants."""
    # <li checked> / <li checked="checked"> / <li checked="true">
    if el.has_attr("checked"):
        val = (el.get("checked") or "").strip().lower()
        if val in ("", "checked", "true", "1", "yes"):
            return True
    # data-* flavor sometimes seen in exports
    for key in ("data-checked", "data-completed"):
        if el.has_attr(key):
            val = (el.get(key) or "").strip().lower()
            if val in ("", "true", "1", "yes", "checked"):
                return True
    # class="checked" / class contains "checked"
    classes = el.get("class") or []
    if isinstance(classes, str):
        classes = classes.split()
    for c in classes:
        if "checked" in c.lower():
            return True
    return False


def _is_checklist(el: Tag) -> bool:
    """True if a <ul> is an Apple Notes checklist (vs. a plain bullet list)."""
    classes = el.get("class") or []
    if isinstance(classes, str):
        classes = classes.split()
    for c in classes:
        cl = c.lower()
        if any(h in cl for h in _CHECKLIST_CLASS_HINTS):
            return True
    # Fall back: every <li> carries a checked-state attribute/class.
    items = el.find_all("li", recursive=False)
    if items and all(
        li.has_attr("checked")
        or _looks_checked(li)
        or (li.get("class") and any("check" in str(c).lower() for c in li.get("class")))
        for li in items
    ):
        return True
    return False


class _NotesConverter(MarkdownConverter):
    """markdownify subclass that understands Apple Notes checklists."""

    def convert_li(self, el, text, parent_tags):
        parent = el.parent
        if parent is not None and parent.name == "ul" and _is_checklist(parent):
            box = "- [x]" if _looks_checked(el) else "- [ ]"
            content = (text or "").strip()
            return "%s %s\n" % (box, content) if content else "%s\n" % box
        return super().convert_li(el, text, parent_tags)


def _strip_noise(soup: BeautifulSoup) -> None:
    """Remove Apple Notes' presentational attributes so Markdown comes out clean."""
    for tag in soup.find_all(True):
        # Preserve the class on checklist <ul>s long enough for detection;
        # detection happens during conversion, so we strip here only the
        # purely-cosmetic attributes and leave class on checklist scaffolding.
        is_checklist_ul = tag.name == "ul" and _is_checklist(tag)
        is_checklist_li = (
            tag.name == "li"
            and tag.parent is not None
            and tag.parent.name == "ul"
            and _is_checklist(tag.parent)
        )
        for attr in _NOISE_ATTRS:
            if attr == "class" and (is_checklist_ul or is_checklist_li):
                continue
            if attr in ("checked", "data-checked", "data-completed") and is_checklist_li:
                continue
            if tag.has_attr(attr):
                del tag[attr]


def html_to_markdown(html: str) -> str:
    """Convert an Apple Notes HTML body to clean Markdown."""
    if html is None:
        return ""
    if not html.strip():
        return ""

    soup = BeautifulSoup(html, "html.parser")
    _strip_noise(soup)

    md = _NotesConverter(
        heading_style="ATX",
        bullets="-",
        # Treat <div> like a line/paragraph block (Notes' paragraph element).
        strip=[],
    ).convert_soup(soup)

    # Collapse the runs of blank lines markdownify can leave behind and trim.
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


# ---------------------------------------------------------------------------
# Write path: Markdown -> Apple Notes HTML
# ---------------------------------------------------------------------------

# Matches a Markdown task-list line: "- [ ] text" / "* [x] text" (any indent).
_TASK_LINE = re.compile(r"^(?P<indent>\s*)[-*+]\s+\[(?P<mark>[ xX])\]\s?(?P<text>.*)$")


def _render_inline(text: str) -> str:
    """Render inline Markdown (bold/italic/code/links) to HTML, no block wrapper."""
    text = text.strip()
    if not text:
        return ""
    html = _markdown.markdown(text)
    # Strip the single wrapping <p>...</p> that markdown adds for a lone line.
    m = re.match(r"^<p>(.*)</p>$", html, re.DOTALL)
    if m:
        return m.group(1).strip()
    return html.strip()


def _split_blocks(markdown_text: str):
    """Yield ('checklist', items) and ('block', text) segments in order.

    Consecutive task-list lines are grouped into a single checklist block so
    they round-trip into one Apple Notes <ul class="checklist">.
    """
    lines = markdown_text.splitlines()
    i = 0
    n = len(lines)
    while i < n:
        if _TASK_LINE.match(lines[i]):
            items = []
            while i < n and _TASK_LINE.match(lines[i]):
                m = _TASK_LINE.match(lines[i])
                checked = m.group("mark").lower() == "x"
                items.append((checked, m.group("text")))
                i += 1
            yield ("checklist", items)
        else:
            start = i
            while i < n and not _TASK_LINE.match(lines[i]):
                i += 1
            yield ("block", "\n".join(lines[start:i]))


def _render_title(title: str) -> str:
    """First line of the body — Apple Notes adopts it as the note name."""
    inner = _render_inline(title) or title.strip()
    return "<h1>%s</h1>" % inner


def markdown_to_html(markdown_text: str, title: str | None = None) -> str:
    """Convert Markdown to Notes-flavored HTML.

    If ``title`` is given, it is rendered as the first line so Notes uses it as
    the note name.
    """
    markdown_text = markdown_text or ""

    parts: list[str] = []
    if title is not None and title.strip():
        parts.append(_render_title(title))

    for kind, payload in _split_blocks(markdown_text):
        if kind == "checklist":
            lis = []
            for checked, text in payload:
                attr = ' checked="checked"' if checked else ""
                lis.append(
                    "<li%s>%s</li>" % (attr, _render_inline(text))
                )
            parts.append('<ul class="checklist">%s</ul>' % "".join(lis))
            continue

        text = payload.strip()
        if not text:
            continue
        html = _markdown.markdown(text, output_format="html")
        # Notes uses <div> for paragraphs rather than <p>; rewrite top-level
        # <p> blocks to <div> so the note reads natively in Notes.app.
        html = _paragraphs_to_divs(html)
        parts.append(html)

    if not parts:
        return ""
    return "".join(parts)


def _paragraphs_to_divs(html: str) -> str:
    """Rewrite top-level <p> elements to <div> (Apple Notes' paragraph block)."""
    soup = BeautifulSoup(html, "html.parser")
    for p in soup.find_all("p"):
        # Only rewrite paragraphs that aren't nested inside list items etc.
        if p.find_parent(["li", "blockquote", "ul", "ol", "td", "th"]):
            continue
        p.name = "div"
    return str(soup)
