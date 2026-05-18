from __future__ import annotations

import re
from collections import Counter

STOPWORDS = {
    "about",
    "above",
    "after",
    "again",
    "against",
    "also",
    "among",
    "because",
    "been",
    "before",
    "being",
    "between",
    "both",
    "could",
    "does",
    "doing",
    "during",
    "each",
    "from",
    "further",
    "have",
    "having",
    "into",
    "itself",
    "more",
    "most",
    "other",
    "over",
    "same",
    "should",
    "some",
    "such",
    "than",
    "that",
    "their",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "under",
    "using",
    "very",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "within",
    "would",
}


def clean_term(term: str) -> str:
    return re.sub(r"\s+", " ", term.strip().lower())


def split_terms(value: str | list[str] | None) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        raw_terms = value
    else:
        raw_terms = re.split(r"[,;\n]", value)
    terms = [clean_term(term) for term in raw_terms]
    return [term for term in terms if term]


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", text.lower())
    return [word for word in words if word not in STOPWORDS]


def top_terms(texts: list[str], limit: int = 20) -> list[str]:
    counts: Counter[str] = Counter()
    for text in texts:
        counts.update(tokenize(text))
    return [term for term, _ in counts.most_common(limit)]


def contains_phrase(text: str, phrase: str) -> bool:
    return clean_term(phrase) in clean_term(text)
