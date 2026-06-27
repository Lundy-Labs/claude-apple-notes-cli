"""Tests for the Markdown <-> Apple-Notes-HTML conversion layer."""

from __future__ import annotations

import re

import pytest

from apple_notes.convert import html_to_markdown, markdown_to_html


# ---------------------------------------------------------------------------
# Read path: HTML -> Markdown
# ---------------------------------------------------------------------------


def test_empty_and_whitespace_input():
    assert html_to_markdown("") == ""
    assert html_to_markdown("   \n  ") == ""
    assert html_to_markdown(None) == ""  # type: ignore[arg-type]


def test_plain_text():
    assert html_to_markdown("<div>just some text</div>") == "just some text"


def test_div_treated_as_paragraphs():
    md = html_to_markdown("<div>first line</div><div>second line</div>")
    assert md == "first line\n\nsecond line"


def test_bold_and_italic():
    assert html_to_markdown("<div><b>bold</b> and <i>italic</i></div>") == (
        "**bold** and *italic*"
    )
    assert html_to_markdown("<div><strong>x</strong> <em>y</em></div>") == "**x** *y*"


def test_headings():
    assert html_to_markdown("<h1>Title</h1>") == "# Title"
    assert html_to_markdown("<h2>Sub</h2>") == "## Sub"
    assert html_to_markdown("<h3>Deep</h3>") == "### Deep"


def test_links():
    md = html_to_markdown('<div>see <a href="https://example.com">here</a></div>')
    assert md == "see [here](https://example.com)"


def test_inline_code():
    assert html_to_markdown("<div>use <code>foo()</code></div>") == "use `foo()`"


def test_bullet_list():
    md = html_to_markdown("<ul><li>apple</li><li>banana</li></ul>")
    assert md == "- apple\n- banana"


def test_numbered_list():
    md = html_to_markdown("<ol><li>one</li><li>two</li></ol>")
    assert md == "1. one\n2. two"


def test_style_attributes_stripped():
    html = '<div style="font: 12px Helvetica"><b style="color:red">hi</b></div>'
    md = html_to_markdown(html)
    assert md == "**hi**"
    assert "style" not in md
    assert "font" not in md


def test_class_and_other_noise_attrs_stripped():
    html = '<div class="foo" dir="ltr" id="x"><i>text</i></div>'
    assert html_to_markdown(html) == "*text*"


# ---------------------------------------------------------------------------
# Checklists (read)
# ---------------------------------------------------------------------------


def test_checklist_read_checked_attribute():
    html = '<ul class="checklist"><li checked="checked">done</li><li>todo</li></ul>'
    assert html_to_markdown(html) == "- [x] done\n- [ ] todo"


def test_checklist_read_checked_class():
    html = '<ul class="checklist"><li class="checked">a</li><li>b</li></ul>'
    assert html_to_markdown(html) == "- [x] a\n- [ ] b"


def test_checklist_apple_class_variant():
    html = (
        '<ul class="Apple-checklist">'
        '<li checked="true">x</li><li>y</li></ul>'
    )
    assert html_to_markdown(html) == "- [x] x\n- [ ] y"


def test_plain_ul_is_not_a_checklist():
    md = html_to_markdown("<ul><li>a</li><li>b</li></ul>")
    assert "[ ]" not in md
    assert md == "- a\n- b"


# ---------------------------------------------------------------------------
# Write path: Markdown -> HTML
# ---------------------------------------------------------------------------


def test_write_empty():
    assert markdown_to_html("") == ""
    assert markdown_to_html("   ") == ""


def test_write_plain_text_uses_div():
    html = markdown_to_html("just text")
    assert html == "<div>just text</div>"


def test_write_paragraphs_are_divs_not_p():
    html = markdown_to_html("para one\n\npara two")
    assert "<p>" not in html
    assert "<div>para one</div>" in html
    assert "<div>para two</div>" in html


def test_write_bold_italic():
    html = markdown_to_html("**bold** and *italic*")
    assert "<strong>bold</strong>" in html
    assert "<em>italic</em>" in html


def test_write_heading():
    html = markdown_to_html("# Hello")
    assert "<h1>Hello</h1>" in html


def test_write_link():
    html = markdown_to_html("[here](https://example.com)")
    assert '<a href="https://example.com">here</a>' in html


def test_write_bullet_list():
    html = markdown_to_html("- a\n- b")
    assert "<ul>" in html
    assert "<li>a</li>" in html
    assert "<li>b</li>" in html


# ---------------------------------------------------------------------------
# Title handling (write)
# ---------------------------------------------------------------------------


def test_title_rendered_as_first_line():
    html = markdown_to_html("body text", title="My Note")
    assert html.startswith("<h1>My Note</h1>")
    assert "<div>body text</div>" in html


def test_title_none_means_no_title():
    html = markdown_to_html("body text")
    assert "<h1>" not in html


def test_blank_title_ignored():
    html = markdown_to_html("body", title="   ")
    assert "<h1>" not in html


def test_title_with_inline_markdown():
    html = markdown_to_html("body", title="Project **Alpha**")
    assert html.startswith("<h1>Project <strong>Alpha</strong></h1>")


# ---------------------------------------------------------------------------
# Checklists (write)
# ---------------------------------------------------------------------------


def test_write_checklist():
    html = markdown_to_html("- [ ] todo\n- [x] done")
    assert '<ul class="checklist">' in html
    assert '<li>todo</li>' in html
    assert '<li checked="checked">done</li>' in html


def test_write_checklist_uppercase_x():
    html = markdown_to_html("- [X] done")
    assert '<li checked="checked">done</li>' in html


def test_write_checklist_grouped_into_single_ul():
    html = markdown_to_html("- [ ] a\n- [ ] b\n- [x] c")
    # Exactly one checklist <ul> wrapping all three items.
    assert html.count('<ul class="checklist">') == 1
    assert html.count("<li") == 3


def test_checklist_and_text_keep_order():
    html = markdown_to_html("intro\n\n- [ ] task\n\noutro")
    intro_i = html.index("intro")
    list_i = html.index('class="checklist"')
    outro_i = html.index("outro")
    assert intro_i < list_i < outro_i


# ---------------------------------------------------------------------------
# Round trips
# ---------------------------------------------------------------------------


def _normalize(md: str) -> str:
    return re.sub(r"\s+", " ", md).strip()


@pytest.mark.parametrize(
    "markdown_text",
    [
        "just plain text",
        "# A Heading",
        "**bold** and *italic* words",
        "para one\n\npara two",
        "- one\n- two\n- three",
        "1. first\n2. second",
        "see [link](https://example.com)",
        "inline `code` here",
        "- [ ] open task\n- [x] closed task",
    ],
)
def test_markdown_html_roundtrip(markdown_text):
    html = markdown_to_html(markdown_text)
    back = html_to_markdown(html)
    assert _normalize(back) == _normalize(markdown_text)


def test_checklist_roundtrip_html_first():
    html = '<ul class="checklist"><li checked="checked">done</li><li>todo</li></ul>'
    md = html_to_markdown(html)
    assert md == "- [x] done\n- [ ] todo"
    regenerated = markdown_to_html(md)
    assert html_to_markdown(regenerated) == md


def test_roundtrip_with_title():
    html = markdown_to_html("the body", title="The Title")
    md = html_to_markdown(html)
    # Title comes back as the first markdown line (an h1).
    assert md.splitlines()[0] == "# The Title"
    assert "the body" in md
