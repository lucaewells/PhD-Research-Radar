# PhD Research Radar

A personalised research-tracking app for following one focused area of your PhD at a time.

## Why this is more personal than a Google Scholar alert

Google Scholar alerts are mostly keyword triggers. They are useful, but they do not know what you are doing this month, what you have already dismissed, which methods you currently care about, or why a paper is relevant to your thesis.

This app adds a more personal layer:

- Monthly focus: define what you are researching right now, not just your broad PhD topic.
- Relevance reasons: every match includes an explanation, so you can see why it surfaced.
- Feedback loop: mark papers as useful or irrelevant, and the scorer adapts future rankings.
- Negative filters: tell the app which nearby topics are distracting this month.
- Digest mode: receive a ranked summary instead of a stream of raw alerts.
- GitHub-ready automation: run a daily digest with GitHub Actions once secrets are configured.

## MVP features

- Streamlit dashboard for configuring your profile and monthly focus.
- arXiv search using the public Atom feed.
- SQLite storage for papers, settings, focus months, and feedback.
- Explainable scoring based on monthly focus terms, core PhD keywords, recency, and learned feedback.
- Optional email notification digest through SMTP.
- GitHub Actions workflow for scheduled daily checks.

## Quick start

Use Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

The app stores local data in `data/radar.sqlite`.

Add at least one core keyword or monthly focus term before fetching papers.

## Optional email setup

Copy `.env.example` to `.env` and fill in your SMTP details.

For Gmail, use an app password rather than your normal account password.

```powershell
Copy-Item .env.example .env
```

Then run a digest from the command line:

```powershell
python -m radar.notify --fetch --send
```

## GitHub Actions setup

After uploading to GitHub, add these repository secrets if you want daily emails:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_USE_TLS`
- `EMAIL_FROM`
- `EMAIL_TO`

The workflow in `.github/workflows/daily-digest.yml` runs once per weekday morning.

## Suggested next upgrades

- Add Semantic Scholar or OpenAlex as extra sources.
- Add Zotero export/import.
- Add PDF triage notes and literature-review tags.
- Add embeddings for stronger semantic matching.
- Add weekly "what changed in this subfield" summaries.
