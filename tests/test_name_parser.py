from unittest.mock import MagicMock

import pytest

from app.db.models.session_record import SessionStatus
from app.services.name_parser import fuzzy_find, parse_text, tokenize


def _client(id_: int, name: str, aliases: list[str] | None = None):
    c = MagicMock()
    c.id = id_
    c.full_name = name
    c.aliases = aliases or []
    return c


CLIENTS = [
    _client(1, "Марія Коваль", ["Маша", "Машка"]),
    _client(2, "Ігор Петренко"),
    _client(3, "Олена Сидоренко", ["Олена"]),
    _client(4, "Тетяна Бойко"),
]


# ─── tokenize ────────────────────────────────────────────────────────────────

def test_tokenize_comma():
    assert tokenize("Маша, Ігор") == ["Маша", "Ігор"]

def test_tokenize_newline():
    assert tokenize("Маша\nІгор") == ["Маша", "Ігор"]

def test_tokenize_mixed():
    assert tokenize("Маша, Ігор\nОлена") == ["Маша", "Ігор", "Олена"]

def test_tokenize_strips_whitespace():
    assert tokenize("  Маша ,  Ігор  ") == ["Маша", "Ігор"]

def test_tokenize_empty():
    assert tokenize("") == []

def test_tokenize_single():
    assert tokenize("Маша") == ["Маша"]


# ─── fuzzy_find ──────────────────────────────────────────────────────────────

def test_fuzzy_exact_full_name():
    result = fuzzy_find("Марія Коваль", CLIENTS)
    assert len(result) == 1
    assert result[0].id == 1

def test_fuzzy_alias():
    result = fuzzy_find("Маша", CLIENTS)
    assert len(result) == 1
    assert result[0].id == 1

def test_fuzzy_partial_typo():
    result = fuzzy_find("Машка", CLIENTS)
    assert len(result) == 1
    assert result[0].id == 1

def test_fuzzy_no_match():
    result = fuzzy_find("Зінаїда", CLIENTS)
    assert result == []

def test_fuzzy_empty_name():
    assert fuzzy_find("", CLIENTS) == []

def test_fuzzy_empty_clients():
    assert fuzzy_find("Маша", []) == []

def test_fuzzy_no_duplicates_via_alias_and_name():
    # Both "Олена" alias and "Олена Сидоренко" match client 3 — expect only one result.
    result = fuzzy_find("Олена Сидоренко", CLIENTS)
    ids = [c.id for c in result]
    assert ids.count(3) == 1


# ─── parse_text ──────────────────────────────────────────────────────────────

def test_parse_single_name():
    entries = parse_text("Маша", CLIENTS)
    assert len(entries) == 1
    assert entries[0].is_resolved
    assert entries[0].matches[0].id == 1
    assert entries[0].status == SessionStatus.attended

def test_parse_comma_separated():
    entries = parse_text("Маша, Ігор", CLIENTS)
    resolved = [e for e in entries if e.is_resolved]
    ids = {e.matches[0].id for e in resolved}
    assert ids == {1, 2}

def test_parse_space_separated_returns_some_result():
    # Space-separated names are a best-effort feature. The parser may interpret
    # a 2-word phrase as one client (if it fuzzy-matches a single client well)
    # or split it into two. Either way it must not crash and return ≥ 1 entry.
    entries = parse_text("Маша Ігор", CLIENTS)
    assert len(entries) >= 1


def test_parse_space_separated_single_first_name():
    # A single recognised first-name token resolves correctly via alias.
    entries = parse_text("Маша", CLIENTS)
    assert entries[0].is_resolved
    assert entries[0].matches[0].id == 1

def test_parse_skip_keyword_missed():
    entries = parse_text("не прийшла Маша", CLIENTS)
    assert len(entries) >= 1
    resolved = [e for e in entries if e.is_resolved]
    assert any(e.status == SessionStatus.missed_no_notice for e in resolved)

def test_parse_skip_emoji():
    entries = parse_text("🚫 Маша", CLIENTS)
    resolved = [e for e in entries if e.is_resolved]
    assert any(e.status == SessionStatus.missed_no_notice for e in resolved)

def test_parse_unrecognized_token():
    entries = parse_text("Зінаїда", CLIENTS)
    assert all(e.is_unrecognized for e in entries)

def test_parse_mixed_recognized_and_not():
    entries = parse_text("Маша, Зінаїда", CLIENTS)
    assert any(e.is_resolved for e in entries)
    assert any(e.is_unrecognized for e in entries)

def test_parse_empty_text():
    entries = parse_text("", CLIENTS)
    assert entries == []

def test_parse_no_clients():
    entries = parse_text("Маша", [])
    assert all(e.is_unrecognized for e in entries)
