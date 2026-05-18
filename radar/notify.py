from __future__ import annotations

import argparse
import sys
from datetime import date

from radar.digest import build_html_digest, build_text_digest
from radar.models import Focus
from radar.notifier import send_email
from radar.scoring import score_paper
from radar.sources.arxiv import build_query, fetch_arxiv_papers
from radar.storage import (
    connect,
    get_focus,
    get_setting,
    list_unsent_top_papers,
    mark_notified,
    upsert_paper,
)
from radar.text import split_terms


def run_fetch(month: str, max_results: int) -> int:
    conn = connect()
    focus = get_focus(conn, month)
    if focus is None:
        focus = Focus(month=month, goals="", required_terms=[], nice_terms=[], avoid_terms=[])

    core_keywords = get_setting(conn, "core_keywords", "")
    query = build_query(core_keywords, focus)
    papers = fetch_arxiv_papers(query, max_results=max_results)

    for paper in papers:
        score, reasons = score_paper(conn, paper, focus)
        upsert_paper(conn, paper, score, reasons)
    return len(papers)


def run_send(limit: int) -> int:
    conn = connect()
    papers = list_unsent_top_papers(conn, limit=limit)
    text_body = build_text_digest(papers)
    html_body = build_html_digest(papers)
    send_email("Your PhD Research Radar digest", text_body, html_body)
    mark_notified(conn, [paper["paper_id"] for paper in papers], "email", "sent")
    return len(papers)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch papers and optionally send a digest.")
    parser.add_argument("--month", default=date.today().strftime("%Y-%m"))
    parser.add_argument("--max-results", type=int, default=25)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--fetch", action="store_true", help="Fetch and score new papers.")
    parser.add_argument("--send", action="store_true", help="Send the email digest.")
    parser.add_argument("--set-core-keywords", default="", help="Comma-separated core keywords.")
    args = parser.parse_args()

    conn = connect()
    if args.set_core_keywords:
        from radar.storage import set_setting

        set_setting(conn, "core_keywords", ", ".join(split_terms(args.set_core_keywords)))

    try:
        fetched = run_fetch(args.month, args.max_results) if args.fetch or not args.send else 0
        sent = run_send(args.limit) if args.send else 0
    except Exception as exc:
        print(f"Research Radar error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"Fetched {fetched} papers. Sent {sent} notifications.")


if __name__ == "__main__":
    main()
