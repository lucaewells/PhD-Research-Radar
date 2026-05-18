from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class Paper:
    paper_id: str
    title: str
    authors: list[str]
    abstract: str
    published: str
    url: str
    pdf_url: str
    source: str
    categories: list[str] = field(default_factory=list)
    raw_json: str = "{}"


@dataclass(slots=True)
class Focus:
    month: str
    goals: str
    required_terms: list[str]
    nice_terms: list[str]
    avoid_terms: list[str]
    notes: str = ""


@dataclass(slots=True)
class ScoredPaper:
    paper: Paper
    score: float
    reasons: list[str]
    created_at: datetime = field(default_factory=datetime.utcnow)
