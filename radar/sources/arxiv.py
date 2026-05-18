from __future__ import annotations

import json
from urllib.parse import quote_plus

import feedparser
import requests

from radar.models import Focus, Paper
from radar.text import split_terms

ARXIV_API_URL = "https://export.arxiv.org/api/query"


def build_query(core_keywords: str, focus: Focus) -> str:
    terms = focus.required_terms + focus.nice_terms + split_terms(core_keywords)
    unique_terms = []
    for term in terms:
        if term not in unique_terms:
            unique_terms.append(term)
    if not unique_terms:
        raise ValueError("Add at least one core keyword or monthly focus term before fetching.")
    clauses = [f'all:"{term}"' if " " in term else f"all:{term}" for term in unique_terms[:8]]
    return " OR ".join(clauses)


def fetch_arxiv_papers(query: str, max_results: int = 25, timeout: int = 45) -> list[Paper]:
    url = (
        f"{ARXIV_API_URL}?search_query={quote_plus(query)}"
        f"&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    )
    headers = {"User-Agent": "phd-research-radar/0.1 (personal research digest)"}
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(
            "arXiv did not respond in time. Try again in a minute, or reduce the fetch count."
        ) from exc

    parsed = feedparser.parse(response.text)

    papers: list[Paper] = []
    for entry in parsed.entries:
        pdf_url = ""
        for link in entry.get("links", []):
            if link.get("type") == "application/pdf":
                pdf_url = link.get("href", "")

        paper_id = entry.get("id", "").rsplit("/", 1)[-1]
        authors = [author.get("name", "") for author in entry.get("authors", [])]
        categories = [tag.get("term", "") for tag in entry.get("tags", [])]

        papers.append(
            Paper(
                paper_id=f"arxiv:{paper_id}",
                title=_squash(entry.get("title", "")),
                authors=[author for author in authors if author],
                abstract=_squash(entry.get("summary", "")),
                published=entry.get("published", ""),
                url=entry.get("id", ""),
                pdf_url=pdf_url,
                source="arXiv",
                categories=[category for category in categories if category],
                raw_json=json.dumps(entry, default=str),
            )
        )
    return papers


def _squash(value: str) -> str:
    return " ".join(value.replace("\n", " ").split())
