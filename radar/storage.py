from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from radar.models import Focus, Paper

DEFAULT_DB_PATH = Path("data/radar.sqlite")


def connect(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS focus_months (
            month TEXT PRIMARY KEY,
            goals TEXT NOT NULL DEFAULT '',
            required_terms TEXT NOT NULL DEFAULT '[]',
            nice_terms TEXT NOT NULL DEFAULT '[]',
            avoid_terms TEXT NOT NULL DEFAULT '[]',
            notes TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS papers (
            paper_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            authors TEXT NOT NULL,
            abstract TEXT NOT NULL,
            published TEXT NOT NULL,
            url TEXT NOT NULL,
            pdf_url TEXT NOT NULL,
            source TEXT NOT NULL,
            categories TEXT NOT NULL,
            raw_json TEXT NOT NULL,
            score REAL NOT NULL DEFAULT 0,
            score_reasons TEXT NOT NULL DEFAULT '[]',
            seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_scored_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id TEXT NOT NULL,
            rating INTEGER NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (paper_id) REFERENCES papers (paper_id)
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL,
            FOREIGN KEY (paper_id) REFERENCES papers (paper_id)
        );
        """
    )
    conn.commit()


def get_setting(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()


def get_focus(conn: sqlite3.Connection, month: str) -> Focus | None:
    row = conn.execute("SELECT * FROM focus_months WHERE month = ?", (month,)).fetchone()
    if not row:
        return None
    return Focus(
        month=row["month"],
        goals=row["goals"],
        required_terms=json.loads(row["required_terms"]),
        nice_terms=json.loads(row["nice_terms"]),
        avoid_terms=json.loads(row["avoid_terms"]),
        notes=row["notes"],
    )


def save_focus(conn: sqlite3.Connection, focus: Focus) -> None:
    conn.execute(
        """
        INSERT INTO focus_months (month, goals, required_terms, nice_terms, avoid_terms, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(month) DO UPDATE SET
            goals = excluded.goals,
            required_terms = excluded.required_terms,
            nice_terms = excluded.nice_terms,
            avoid_terms = excluded.avoid_terms,
            notes = excluded.notes
        """,
        (
            focus.month,
            focus.goals,
            json.dumps(focus.required_terms),
            json.dumps(focus.nice_terms),
            json.dumps(focus.avoid_terms),
            focus.notes,
        ),
    )
    conn.commit()


def upsert_paper(
    conn: sqlite3.Connection,
    paper: Paper,
    score: float,
    reasons: list[str],
) -> None:
    conn.execute(
        """
        INSERT INTO papers (
            paper_id, title, authors, abstract, published, url, pdf_url,
            source, categories, raw_json, score, score_reasons
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(paper_id) DO UPDATE SET
            title = excluded.title,
            authors = excluded.authors,
            abstract = excluded.abstract,
            published = excluded.published,
            url = excluded.url,
            pdf_url = excluded.pdf_url,
            source = excluded.source,
            categories = excluded.categories,
            raw_json = excluded.raw_json,
            score = excluded.score,
            score_reasons = excluded.score_reasons,
            last_scored_at = CURRENT_TIMESTAMP
        """,
        (
            paper.paper_id,
            paper.title,
            json.dumps(paper.authors),
            paper.abstract,
            paper.published,
            paper.url,
            paper.pdf_url,
            paper.source,
            json.dumps(paper.categories),
            paper.raw_json,
            score,
            json.dumps(reasons),
        ),
    )
    conn.commit()


def list_papers(conn: sqlite3.Connection, limit: int = 50) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT p.*,
            COALESCE((SELECT rating FROM feedback f WHERE f.paper_id = p.paper_id ORDER BY f.created_at DESC LIMIT 1), 0) AS rating
        FROM papers p
        ORDER BY p.score DESC, p.published DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [paper_row_to_dict(row) for row in rows]


def paper_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["authors"] = json.loads(item["authors"])
    item["categories"] = json.loads(item["categories"])
    item["score_reasons"] = json.loads(item["score_reasons"])
    return item


def save_feedback(conn: sqlite3.Connection, paper_id: str, rating: int, note: str = "") -> None:
    conn.execute(
        "INSERT INTO feedback (paper_id, rating, note) VALUES (?, ?, ?)",
        (paper_id, rating, note),
    )
    conn.commit()


def feedback_texts(conn: sqlite3.Connection, rating: int) -> list[str]:
    rows = conn.execute(
        """
        SELECT p.title, p.abstract
        FROM feedback f
        JOIN papers p ON p.paper_id = f.paper_id
        WHERE f.rating = ?
        """,
        (rating,),
    ).fetchall()
    return [f"{row['title']} {row['abstract']}" for row in rows]


def list_unsent_top_papers(conn: sqlite3.Connection, limit: int = 10) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT p.*
        FROM papers p
        WHERE NOT EXISTS (
            SELECT 1 FROM notifications n
            WHERE n.paper_id = p.paper_id AND n.status = 'sent'
        )
        ORDER BY p.score DESC, p.published DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [paper_row_to_dict(row) for row in rows]


def mark_notified(conn: sqlite3.Connection, paper_ids: list[str], channel: str, status: str) -> None:
    conn.executemany(
        "INSERT INTO notifications (paper_id, channel, status) VALUES (?, ?, ?)",
        [(paper_id, channel, status) for paper_id in paper_ids],
    )
    conn.commit()
