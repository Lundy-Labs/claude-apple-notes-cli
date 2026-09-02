"""Guardrails that can be checked without talking to Notes.app."""

from apple_notes.notes import is_forever_notes_daily


def test_planner_daily_titles():
    assert is_forever_notes_daily("01 September", "Planner")
    assert is_forever_notes_daily("02 September", "Planner")
    assert is_forever_notes_daily("03 September", "Planner")
    assert is_forever_notes_daily("04 September", "Planner")
    assert is_forever_notes_daily("31 December", "Planner")
    assert is_forever_notes_daily("09 January", "Planner")


def test_planner_daily_rejects_non_dailies():
    assert not is_forever_notes_daily("September", "Planner")
    assert not is_forever_notes_daily("2 September", "Planner")  # needs zero-pad
    assert not is_forever_notes_daily("02 Sept", "Planner")
    assert not is_forever_notes_daily("02 September", "Claude Memory")
    assert not is_forever_notes_daily("02 September", None)
    assert not is_forever_notes_daily("Weather", "Planner")
    assert not is_forever_notes_daily("", "Planner")
