"""Offline keyword matcher optimized for Raspberry Pi.

Builds an in-memory index from database entries and performs:
1) exact token-aware matching (longest phrase first)
2) fuzzy fallback matching against token windows
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, List, Optional

_NORMALIZE_RE = re.compile(r"[^a-z0-9\s]")
_SPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Lowercase and normalize punctuation/spacing for stable matching."""
    text = (text or "").lower().strip()
    text = _NORMALIZE_RE.sub(" ", text)
    text = _SPACE_RE.sub(" ", text).strip()
    return text


@dataclass
class MatchCandidate:
    entry: dict
    term: str
    confidence: float
    match_type: str


class KeywordMatcher:
    """Fast in-memory matcher for item labels, tags, and aliases."""

    def __init__(self, database: List[dict], fuzzy_threshold: float = 0.9) -> None:
        self.fuzzy_threshold = float(fuzzy_threshold)
        self.max_term_tokens = 1
        self._terms_by_token_count: Dict[int, List[str]] = {}
        self._term_to_entries: Dict[str, List[dict]] = {}
        self._primary_label_by_id: Dict[int, str] = {}

        # Build canonical item labels by item id (first-seen entry is label in adapter).
        for entry in database:
            item_id = entry.get("id")
            item_name = (entry.get("item") or "").strip()
            if (
                isinstance(item_id, int)
                and item_id not in self._primary_label_by_id
                and item_name
            ):
                self._primary_label_by_id[item_id] = item_name

        for entry in database:
            raw_term = (entry.get("item") or "").strip()
            norm_term = normalize_text(raw_term)
            if not norm_term:
                continue

            item_id = entry.get("id")
            canonical_item = self._primary_label_by_id.get(item_id, raw_term)

            normalized_entry = {
                "id": item_id,
                "item": canonical_item,
                "rack": entry.get("rack", 0),
                "location": entry.get("location", 0),
                "isCalled": bool(entry.get("isCalled", False)),
                "matched_term": raw_term,
            }

            self._term_to_entries.setdefault(norm_term, []).append(normalized_entry)

        for term in self._term_to_entries.keys():
            token_count = len(term.split())
            self.max_term_tokens = max(self.max_term_tokens, token_count)
            self._terms_by_token_count.setdefault(token_count, []).append(term)

        # Sort longest-first so exact matching prefers more specific terms.
        for token_count, terms in self._terms_by_token_count.items():
            terms.sort(key=len, reverse=True)
            self._terms_by_token_count[token_count] = terms

    @property
    def term_count(self) -> int:
        return len(self._term_to_entries)

    def _pick_entry_for_term(self, norm_term: str) -> Optional[dict]:
        entries = self._term_to_entries.get(norm_term, [])
        if not entries:
            return None
        return entries[0].copy()

    def _exact_match(self, norm_text: str) -> Optional[MatchCandidate]:
        tokens = norm_text.split()
        if not tokens:
            return None

        for token_count in sorted(self._terms_by_token_count.keys(), reverse=True):
            if token_count > len(tokens):
                continue

            for start in range(0, len(tokens) - token_count + 1):
                phrase = " ".join(tokens[start : start + token_count])
                if phrase in self._term_to_entries:
                    entry = self._pick_entry_for_term(phrase)
                    if entry:
                        conf = 1.0 + (token_count * 0.01)
                        return MatchCandidate(
                            entry=entry,
                            term=phrase,
                            confidence=conf,
                            match_type="exact",
                        )

        return None

    def _fuzzy_match(self, norm_text: str) -> Optional[MatchCandidate]:
        tokens = norm_text.split()
        if not tokens:
            return None

        best: Optional[MatchCandidate] = None

        for token_count, terms in self._terms_by_token_count.items():
            if token_count > len(tokens) + 1:
                continue

            window_sizes = {token_count}
            if token_count > 1:
                window_sizes.add(token_count - 1)
            if token_count < self.max_term_tokens:
                window_sizes.add(token_count + 1)

            windows = set()
            for win_size in window_sizes:
                if win_size <= 0 or win_size > len(tokens):
                    continue
                for start in range(0, len(tokens) - win_size + 1):
                    windows.add(" ".join(tokens[start : start + win_size]))

            for term in terms:
                for window in windows:
                    score = SequenceMatcher(None, term, window).ratio()
                    if score < self.fuzzy_threshold:
                        continue

                    entry = self._pick_entry_for_term(term)
                    if not entry:
                        continue

                    candidate = MatchCandidate(
                        entry=entry,
                        term=term,
                        confidence=score,
                        match_type="fuzzy",
                    )
                    if best is None or candidate.confidence > best.confidence:
                        best = candidate

        return best

    def match(self, text: str) -> Optional[dict]:
        norm_text = normalize_text(text)
        if not norm_text:
            return None

        exact = self._exact_match(norm_text)
        if exact:
            result = exact.entry
            result["match_type"] = exact.match_type
            result["confidence"] = round(min(exact.confidence, 1.0), 3)
            result["matched_term"] = exact.term
            return result

        fuzzy = self._fuzzy_match(norm_text)
        if fuzzy:
            result = fuzzy.entry
            result["match_type"] = fuzzy.match_type
            result["confidence"] = round(fuzzy.confidence, 3)
            result["matched_term"] = fuzzy.term
            return result

        return None


def build_keyword_matcher(
    database: List[dict], fuzzy_threshold: float = 0.9
) -> KeywordMatcher:
    """Create a reusable matcher from DB rows."""
    return KeywordMatcher(database=database, fuzzy_threshold=fuzzy_threshold)
