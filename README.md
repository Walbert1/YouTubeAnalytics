# YouTube Niche Analytics

Research tool for finding what's working in a YouTube niche right now, and turning that research into ready-to-use video ideas, titles, and hashtags via Claude.

## Table of Contents

- [What It Does](#what-it-does)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Usage](#usage)
- [Output Files](#output-files)
- [API Quota Notes](#api-quota-notes)
- [Troubleshooting](#troubleshooting)
- [Limitations](#limitations)

## What It Does

Given a list of search queries that define a niche (e.g. firearms training channels), this tool:

1. Pulls top videos for each query from the YouTube Data API, split into Shorts and full-length videos.
2. Computes engagement rate (`(likes + comments) / views`) per video and per query.
3. Aggregates the most common tags, hashtags, and channel branding keywords across the whole niche.
4. Grabs a snapshot of YouTube's live trending Shorts chart.
5. Packages all of the above into a markdown brief (`claude_content_brief.md`) you can paste into Claude to get concrete video ideas, algorithm-optimized titles, and hashtag sets — grounded in the actual data instead of generic advice.

It ships with two interchangeable front ends: a one-shot CLI report and an interactive Streamlit UI. Both call the exact same `core` package, so they never drift out of sync.

## Project Structure

```text
core/
    __init__.py     - the package's public API (what you import from `core`)
    api.py          - YouTube Data API v3 wrapper (search, video details, trending, channel tags)
    video.py        - shared video shaping: normalize API responses, is_short(), aggregate_videos()
    shorts.py       - Shorts-only logic: filtering + the live trending-Shorts chart
    full_videos.py  - full-length-video-only logic: filtering
    niche.py        - runs the niche's queries in parallel, aggregates results, engagement_summary()
    report.py       - console printing, the shared CSV export spec, and the Claude brief builder
youtube_api_call.py - CLI entry point: runs the analysis once, prints a report, writes CSVs + the Claude brief
app.py              - interactive Streamlit UI for the same analysis (adjustable queries, region, time period)
requirements.txt    - pinned dependencies
.env                - local-only secrets (YOUTUBE_API_KEY) — never committed
```

`youtube_api_call.py` and `app.py` are the two entry points; both are built entirely on top of `core`, so CSV filenames, aggregation logic, and the Shorts/full-video split stay in sync between the CLI and the UI instead of being duplicated in each.

## Prerequisites

- Python 3.10 or later (the code uses modern type-hint syntax like `str | None`).
- A Google account with access to the [Google Cloud Console](https://console.cloud.google.com/) to create a YouTube Data API v3 key.

## Setup

1. Create a virtualenv and install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate      # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Get a YouTube Data API v3 key:
   - In the [Google Cloud Console](https://console.cloud.google.com/), create (or select) a project.
   - Enable the **YouTube Data API v3** for that project.
   - Create an **API key** credential and copy it.
3. Create a `.env` file in the project root with that key:

   ```env
   YOUTUBE_API_KEY=your-key-here
   ```

   `.env` is gitignored on purpose — never commit it. `core/api.py` loads it at import time via `python-dotenv` and raises `EnvironmentError` immediately if the key is missing.

### Editor setup (optional)

A `.vscode/settings.json` is included that points VS Code/Pylance at `.venv`. If imports still show as unresolved after installing dependencies, run **Python: Select Interpreter** from the Command Palette and choose `./.venv/bin/python`.

## Usage

### CLI report

```bash
python youtube_api_call.py
```

Runs all of `NICHE_QUERIES` in parallel, prints a per-query breakdown to the terminal, and writes the [output files](#output-files) listed below to the project root. To analyze a different niche, edit the constants at the top of `youtube_api_call.py`:

```python
NICHE_QUERIES = ['firearms', 'shooting', ...]  # your search queries
NICHE_REGION = 'US'                             # YouTube region code
TIME_PERIOD = 'week'                            # 'week' | 'month' | 'year' | 'all_time'
```

### Interactive UI

```bash
streamlit run app.py
```

This must be launched with `streamlit run`, **not** `python app.py` — running it as a plain script skips Streamlit's runtime (you'll see `missing ScriptRunContext` warnings and nothing will render). The sidebar lets you set the queries, region, time period, and max results per query without editing any code, then click **Run Analysis**. Results are cached per settings combination, so re-running with the same inputs reuses the previous fetch instead of hitting the API again.

## Output Files

Written to the project root by the CLI (and available as download buttons in the Streamlit app's Export tab):

| File | Contents |
| --- | --- |
| `tags_shorts.csv` / `tags_full.csv` | Most common video tags, Shorts vs. full-length |
| `hashtags_shorts.csv` / `hashtags_full.csv` | Most common hashtags extracted from titles, Shorts vs. full-length |
| `channel_tags.csv` | Branding keywords of channels appearing in the results |
| `trending_shorts.csv` | Snapshot of YouTube's current trending Shorts |
| `claude_content_brief.md` | Markdown brief — paste this into Claude to get video ideas, optimized titles, and hashtags |

All of the above (plus the virtualenv and Python cache files) are gitignored — they're generated output, not source.

## API Quota Notes

The YouTube Data API v3 enforces a daily quota (10,000 units/day by default per project). Rough costs per call, as documented by Google:

- `search().list()` — **100 units** per call. One per query, so the default 7-query niche costs ~700 units per run.
- `videos().list()` — **1 unit** per call, batched up to 50 video IDs per call (used for both video details and the trending chart).
- `channels().list()` — **1 unit** per call, used to look up each unique channel's branding keywords (cached per run, so repeated channels across queries are only fetched once).

If you hit `HttpError 403` with a `quotaExceeded` reason, you've exceeded your project's daily quota — either wait for the daily reset or request a quota increase in the Cloud Console.

## Troubleshooting

- **`EnvironmentError: YOUTUBE_API_KEY not found`** — your `.env` file is missing, misnamed, or not in the project root. Confirm it exists and contains `YOUTUBE_API_KEY=...`.
- **Streamlit prints `missing ScriptRunContext!` / "Session state does not function..."** — you ran `python app.py` instead of `streamlit run app.py`. Use the `streamlit run` command (see [Usage](#usage)).
- **Pylance shows "Import could not be resolved" in an editor** — the editor isn't using `.venv`'s interpreter. Run **Python: Select Interpreter** in VS Code and pick `./.venv/bin/python`, then reload the window if needed.
- **`quotaExceeded` errors from the API** — see [API Quota Notes](#api-quota-notes) above.

## Limitations

- YouTube's Data API only exposes a *live* trending chart (no historical "trending this week" endpoint), so the Trending Shorts data reflects the moment you ran the analysis, not a weekly rollup.
- "Engagement rate" here is `(likes + comments) / views`; YouTube doesn't expose watch time or impressions via the public API, so this is a proxy, not the full picture the platform's own algorithm uses.
- Search results are capped per query by `max_results` (CLI: hardcoded at 40; UI: a 10–50 slider), so very broad niches will only see a slice of what's out there.
