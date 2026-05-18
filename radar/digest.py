from __future__ import annotations

from html import escape


def build_text_digest(papers: list[dict], heading: str = "PhD Research Radar") -> str:
    if not papers:
        return f"{heading}\n\nNo new highly ranked papers today."

    lines = [heading, ""]
    for index, paper in enumerate(papers, start=1):
        reasons = "; ".join(paper["score_reasons"])
        authors = ", ".join(paper["authors"][:4])
        if len(paper["authors"]) > 4:
            authors += " et al."
        lines.extend(
            [
                f"{index}. {paper['title']}",
                f"Score: {paper['score']}",
                f"Authors: {authors}",
                f"Why: {reasons}",
                f"Link: {paper['url']}",
                "",
            ]
        )
    return "\n".join(lines)


def build_html_digest(papers: list[dict], heading: str = "PhD Research Radar") -> str:
    if not papers:
        return f"<h1>{escape(heading)}</h1><p>No new highly ranked papers today.</p>"

    cards = []
    for paper in papers:
        reasons = "".join(f"<li>{escape(reason)}</li>" for reason in paper["score_reasons"])
        authors = escape(", ".join(paper["authors"][:6]))
        cards.append(
            f"""
            <article style="border:1px solid #ddd;border-radius:8px;padding:16px;margin:14px 0;">
              <h2 style="margin:0 0 8px 0;font-size:18px;">{escape(paper['title'])}</h2>
              <p style="margin:0 0 8px 0;color:#555;">{authors}</p>
              <p style="margin:0 0 8px 0;"><strong>Score:</strong> {paper['score']}</p>
              <ul>{reasons}</ul>
              <p><a href="{escape(paper['url'])}">Open paper</a></p>
            </article>
            """
        )

    return f"""
    <html>
      <body style="font-family:Arial, sans-serif;line-height:1.45;color:#222;">
        <h1>{escape(heading)}</h1>
        {''.join(cards)}
      </body>
    </html>
    """
