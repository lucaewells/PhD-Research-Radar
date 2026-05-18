from __future__ import annotations

from datetime import date

import streamlit as st

from radar.digest import build_html_digest, build_text_digest
from radar.models import Focus
from radar.notifier import send_email
from radar.scoring import score_paper
from radar.sources.arxiv import build_query, fetch_arxiv_papers
from radar.storage import (
    connect,
    get_focus,
    get_setting,
    list_papers,
    list_unsent_top_papers,
    mark_notified,
    save_feedback,
    save_focus,
    set_setting,
    upsert_paper,
)
from radar.text import split_terms

st.set_page_config(page_title="PhD Research Radar", page_icon="radar", layout="wide")


def current_month() -> str:
    return date.today().strftime("%Y-%m")


def load_or_default_focus(month: str) -> Focus:
    focus = get_focus(conn, month)
    if focus:
        return focus
    return Focus(month=month, goals="", required_terms=[], nice_terms=[], avoid_terms=[])


def fetch_and_score(month: str, max_results: int) -> int:
    focus = load_or_default_focus(month)
    core_keywords = get_setting(conn, "core_keywords", "")
    query = build_query(core_keywords, focus)
    papers = fetch_arxiv_papers(query, max_results=max_results)
    for paper in papers:
        score, reasons = score_paper(conn, paper, focus)
        upsert_paper(conn, paper, score, reasons)
    return len(papers)


conn = connect()

st.title("PhD Research Radar")
st.caption("Monthly research focus, ranked papers, and personalised digests.")

with st.sidebar:
    st.header("Profile")
    existing_profile = get_setting(conn, "research_profile", "")
    existing_keywords = get_setting(conn, "core_keywords", "")
    research_profile = st.text_area(
        "Thesis context",
        value=existing_profile,
        height=140,
        placeholder="Example: I study human-AI collaboration in qualitative research workflows...",
    )
    core_keywords = st.text_area(
        "Core keywords",
        value=existing_keywords,
        height=100,
        placeholder="human-AI collaboration, qualitative coding, research methods",
    )
    if st.button("Save profile", use_container_width=True):
        set_setting(conn, "research_profile", research_profile.strip())
        set_setting(conn, "core_keywords", ", ".join(split_terms(core_keywords)))
        st.success("Profile saved.")

    st.divider()
    month = st.text_input("Focus month", value=current_month())
    max_results = st.slider("Fetch count", min_value=5, max_value=100, value=25, step=5)

focus = load_or_default_focus(month)

focus_tab, radar_tab, digest_tab = st.tabs(["Monthly focus", "Radar", "Digest"])

with focus_tab:
    st.subheader("What matters this month?")
    goals = st.text_area(
        "Research goal",
        value=focus.goals,
        height=140,
        placeholder="Example: Find recent work on reflective AI research assistants for literature analysis.",
    )
    required_terms = st.text_area(
        "Required terms",
        value=", ".join(focus.required_terms),
        placeholder="terms that strongly signal relevance",
    )
    nice_terms = st.text_area(
        "Useful secondary terms",
        value=", ".join(focus.nice_terms),
        placeholder="terms that are helpful but not essential",
    )
    avoid_terms = st.text_area(
        "Avoid terms",
        value=", ".join(focus.avoid_terms),
        placeholder="nearby topics that are distracting this month",
    )
    notes = st.text_area("Private notes", value=focus.notes, height=100)

    if st.button("Save monthly focus"):
        save_focus(
            conn,
            Focus(
                month=month,
                goals=goals.strip(),
                required_terms=split_terms(required_terms),
                nice_terms=split_terms(nice_terms),
                avoid_terms=split_terms(avoid_terms),
                notes=notes.strip(),
            ),
        )
        st.success("Monthly focus saved.")

with radar_tab:
    left, right = st.columns([1, 3])
    with left:
        if st.button("Fetch latest papers", type="primary", use_container_width=True):
            try:
                with st.spinner("Fetching and scoring papers..."):
                    count = fetch_and_score(month, max_results)
                st.success(f"Fetched and scored {count} papers.")
            except Exception as exc:
                st.error(str(exc))

    papers = list_papers(conn, limit=80)
    if not papers:
        st.info("Add your profile and monthly focus, then fetch papers.")
    else:
        st.subheader("Ranked papers")
        for paper in papers:
            with st.container(border=True):
                cols = st.columns([5, 1])
                with cols[0]:
                    st.markdown(f"### {paper['title']}")
                    st.write(", ".join(paper["authors"][:6]))
                    st.caption(f"{paper['source']} | {paper['published']} | score {paper['score']}")
                    st.write(paper["abstract"])
                    st.markdown(f"[Open paper]({paper['url']})")
                    if paper["pdf_url"]:
                        st.markdown(f"[Open PDF]({paper['pdf_url']})")
                    st.markdown("**Why this appeared**")
                    for reason in paper["score_reasons"]:
                        st.write(f"- {reason}")
                with cols[1]:
                    if st.button("Useful", key=f"useful-{paper['paper_id']}"):
                        save_feedback(conn, paper["paper_id"], 1)
                        st.toast("Marked useful.")
                    if st.button("Dismiss", key=f"dismiss-{paper['paper_id']}"):
                        save_feedback(conn, paper["paper_id"], -1)
                        st.toast("Marked dismissed.")

with digest_tab:
    st.subheader("Notification digest")
    limit = st.slider("Digest size", min_value=3, max_value=20, value=10)
    top_papers = list_unsent_top_papers(conn, limit=limit)
    st.text_area("Preview", value=build_text_digest(top_papers), height=360)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Send email digest", use_container_width=True):
            try:
                text_body = build_text_digest(top_papers)
                html_body = build_html_digest(top_papers)
                send_email("Your PhD Research Radar digest", text_body, html_body)
                mark_notified(conn, [paper["paper_id"] for paper in top_papers], "email", "sent")
                st.success("Digest sent.")
            except Exception as exc:
                st.error(str(exc))
    with col2:
        if st.button("Mark preview as sent", use_container_width=True):
            mark_notified(conn, [paper["paper_id"] for paper in top_papers], "manual", "sent")
            st.success("Marked as sent.")
