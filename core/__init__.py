"""Core YouTube niche-analytics package.

Layout:
    api.py         - YouTube Data API v3 wrapper
    video.py       - shared video shaping/aggregation
    shorts.py      - Shorts-only filtering + trending-Shorts chart
    full_videos.py - full-length-video-only filtering
    niche.py        - multi-query orchestration + cross-query aggregation
    report.py       - console/CSV/markdown reporting (shared by the CLI and the app)
"""
from .full_videos import aggregate_full_videos, filter_full_videos
from .niche import aggregate_across_queries, analyze_query, engagement_summary, run_niche_analysis
from .report import CSV_EXPORTS, build_claude_brief, print_query_results, print_videos, write_csv
from .shorts import aggregate_shorts, fetch_trending_shorts, filter_shorts
from .video import aggregate_videos, build_video, extract_hashtags, is_short

__all__ = [
    'aggregate_across_queries', 'analyze_query', 'engagement_summary', 'run_niche_analysis',
    'aggregate_full_videos', 'filter_full_videos',
    'aggregate_shorts', 'fetch_trending_shorts', 'filter_shorts',
    'aggregate_videos', 'build_video', 'extract_hashtags', 'is_short',
    'CSV_EXPORTS', 'build_claude_brief', 'print_query_results', 'print_videos', 'write_csv',
]
