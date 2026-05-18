from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from sqlite3 import Connection

from radar.models import Focus, Paper
from radar.storage import feedback_texts, get_setting
from radar.text import contains_phrase, split_terms, top_terms


def score_paper(conn: Connection, paper: Paper, focus: Focus) -> tuple[float, list[str]]:
    text = f"{paper.title}\n{paper.abstract}".lower()
    score = 0.0
    reasons: list[str] = []

    profile_terms = split_terms(get_setting(conn, "core_keywords", ""))
    for term in profile_terms:
        if contains_phrase(text, term):
            score += 2.0
            reasons.append(f"Matches core PhD keyword: {term}")

    for term in focus.required_terms:
        if contains_phrase(text, term):
            score += 5.0
            reasons.append(f"Matches this month's required focus: {term}")

    for term in focus.nice_terms:
        if contains_phrase(text, term):
            score += 2.5
            reasons.append(f"Matches a useful secondary term: {term}")

    for term in focus.avoid_terms:
        if contains_phrase(text, term):
            score -= 4.0
            reasons.append(f"Down-ranked because it matches avoid term: {term}")

    liked_terms = top_terms(feedback_texts(conn, 1), limit=20)
    disliked_terms = set(top_terms(feedback_texts(conn, -1), limit=20))

    for term in liked_terms:
        if contains_phrase(text, term):
            score += 0.4

    for term in disliked_terms:
        if contains_phrase(text, term):
            score -= 0.3

    if liked_terms:
        reasons.append("Adjusted using terms from papers you marked useful")

    recency_boost = _recency_boost(paper.published)
    if recency_boost:
        score += recency_boost
        reasons.append("Recent publication")

    if not reasons:
        reasons.append("Broad match from your search query")

    return round(max(score, 0.0), 2), reasons[:6]


def _recency_boost(published: str) -> float:
    try:
        dt = parsedate_to_datetime(published)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
        except ValueError:
            return 0.0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - dt).days
    if age_days <= 14:
        return 1.5
    if age_days <= 45:
        return 0.75
    return 0.0
