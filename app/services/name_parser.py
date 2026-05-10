import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz, process

from app.db.models.client import Client
from app.db.models.session_record import SessionStatus

_SKIP_PATTERNS = [
    "не була",
    "не був",
    "не було",
    "не прийшла",
    "не прийшов",
    "не прийшло",
    "пропуск",
    "🚫",
]


@dataclass
class ParsedEntry:
    token: str
    clean_name: str
    status: SessionStatus
    matches: list[Client] = field(default_factory=list)

    @property
    def is_resolved(self) -> bool:
        return len(self.matches) == 1

    @property
    def is_ambiguous(self) -> bool:
        return len(self.matches) > 1

    @property
    def is_unrecognized(self) -> bool:
        return len(self.matches) == 0


def tokenize(text: str) -> list[str]:
    parts = re.split(r"[,\n]+", text)
    return [p.strip() for p in parts if p.strip()]


def _extract_status(token: str) -> tuple[str, SessionStatus]:
    lower = token.lower()
    for kw in _SKIP_PATTERNS:
        if kw in lower:
            clean = lower.replace(kw, "").strip()
            return clean if clean else token, SessionStatus.missed_no_notice
    return token, SessionStatus.attended


def _build_candidate_pairs(clients: list[Client]) -> list[tuple[str, Client]]:
    pairs: list[tuple[str, Client]] = []
    for c in clients:
        pairs.append((c.full_name, c))
        for alias in (c.aliases or []):
            if alias:
                pairs.append((alias, c))
    return pairs


def fuzzy_find(name: str, clients: list[Client], threshold: int = 80) -> list[Client]:
    if not name or not clients:
        return []
    pairs = _build_candidate_pairs(clients)
    strings = [s.lower() for s, _ in pairs]
    hits = process.extract(
        name.lower(), strings, scorer=fuzz.WRatio, limit=None, score_cutoff=threshold
    )
    seen: set[int] = set()
    result: list[Client] = []
    for _, _, idx in hits:
        c = pairs[idx][1]
        if c.id not in seen:
            seen.add(c.id)
            result.append(c)
    return result


def _parse_space_separated(
    text: str, status: SessionStatus, clients: list[Client]
) -> list[ParsedEntry]:
    """Greedy left-to-right: try 2-word match, then 1-word, for space-separated names."""
    words = text.split()
    if len(words) <= 1:
        return []
    entries: list[ParsedEntry] = []
    i = 0
    while i < len(words):
        matched = False
        for length in range(min(2, len(words) - i), 0, -1):
            candidate = " ".join(words[i : i + length])
            matches = fuzzy_find(candidate, clients)
            if matches:
                # Multi-word candidate that matches several clients = two separate names typed
                # side-by-side; fall through to try shorter (1-word) matching instead.
                if length > 1 and len(matches) > 1:
                    continue
                entries.append(
                    ParsedEntry(token=candidate, clean_name=candidate, status=status, matches=matches)
                )
                i += length
                matched = True
                break
        if not matched:
            entries.append(
                ParsedEntry(token=words[i], clean_name=words[i], status=status, matches=[])
            )
            i += 1
    return entries


def parse_text(text: str, clients: list[Client]) -> list[ParsedEntry]:
    entries: list[ParsedEntry] = []
    for raw_token in tokenize(text):
        clean_name, status = _extract_status(raw_token)

        # For multi-word tokens try splitting into individual names first.
        # This handles "Ігор Олег" (space-separated, no comma) as two people.
        if ' ' in clean_name:
            sub = _parse_space_separated(clean_name, status, clients)
            if sub and any(e.matches for e in sub):
                entries.extend(sub)
                continue

        matches = fuzzy_find(clean_name, clients)
        if matches:
            entries.append(
                ParsedEntry(token=raw_token, clean_name=clean_name, status=status, matches=matches)
            )
        else:
            entries.append(
                ParsedEntry(token=raw_token, clean_name=clean_name, status=status, matches=[])
            )
    return entries
