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


def html_to_markdown(html: str) -> str:
    """Convert an Apple Notes HTML body to clean Markdown."""
    raise NotImplementedError  # Agent A


def markdown_to_html(markdown_text: str, title: str | None = None) -> str:
    """Convert Markdown to Notes-flavored HTML.

    If ``title`` is given, it is rendered as the first line so Notes uses it as
    the note name.
    """
    raise NotImplementedError  # Agent A
