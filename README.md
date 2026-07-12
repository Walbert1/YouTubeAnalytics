# YouTube Niche Analytics

Research tool for finding what's working in a YouTube niche right now, and turning that research into ready-to-use video ideas, titles, and hashtags via Claude.

## What it does

Given a list of search queries that define a niche (e.g. firearms training channels), this tool:

1. Pulls top videos for each query from the YouTube Data API, split into Shorts and full-length videos.
2. Computes engagement rate (likes + comments / views) per video and per query.
3. Aggregates the most common tags, hashtags, and channel branding keywords across the whole niche.
4. Grabs a snapshot of YouTube's live trending Shorts chart.
5. Packages all of the above into a markdown brief (`claude_content_brief.md`) you can paste into Claude to get concrete video ideas, algorithm-optimized titles, and hashtag sets — grounded in the actual data instead of generic advice.

## Project layout

- `api.py` — thin wrapper around the YouTube Data API v3 (search, video details, trending, channel tags).
- `analysis.py` — data shaping: Shorts/full-video split, engagement calculation, tag/hashtag extraction, per-query and niche-wide aggregation, trending Shorts.
- `youtube_api_call.py` — CLI entry point. Runs the analysis once, prints a report, and writes CSVs + the Claude brief.
- `app.py` — interactive Streamlit UI for the same analysis (adjustable queries, region, time period).

## Setup

1. Create a virtualenv and install dependencies:
   ```
   pip install google-api-python-client python-dotenv pandas plotly streamlit
   ```
2. Get a YouTube Data API v3 key from the Google Cloud Console and add it to a `.env` file:
   ```
   YOUTUBE_API_KEY=your-key-here
   ```

## Usage

Run the CLI report:

```
python youtube_api_call.py
```

This prints a per-query breakdown to the terminal and writes to the project root:

- `tags_shorts.csv`, `tags_full.csv` — most common video tags
- `hashtags_shorts.csv`, `hashtags_full.csv` — most common hashtags
- `channel_tags.csv` — branding keywords of channels appearing in results
- `trending_shorts.csv` — snapshot of YouTube's current trending Shorts
- `claude_content_brief.md` — paste this into Claude for video ideas, titles, and hashtags

Or launch the interactive UI:

```
streamlit run app.py
```

## Notes

- The niche, region, and time period are hardcoded in `youtube_api_call.py` (`NICHE_QUERIES`, `NICHE_REGION`) — edit those to target a different niche. The Streamlit app exposes all of these as sidebar controls instead.
- YouTube's Data API only exposes a *live* trending chart (no historical "trending this week" endpoint), so the Trending Shorts data reflects the moment you ran the analysis, not a weekly rollup.
