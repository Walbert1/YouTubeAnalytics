"""Shorts-specific logic: splitting a mixed video list down to Shorts, and
YouTube's live trending-Shorts chart."""
from .api import get_trending_videos
from .video import aggregate_videos, build_video, is_short


def filter_shorts(videos: list[dict]) -> list[dict]:
    return sorted((v for v in videos if v['is_short']), key=lambda v: v['views'], reverse=True)


def aggregate_shorts(videos: list[dict]) -> dict:
    return aggregate_videos(filter_shorts(videos))


def fetch_trending_shorts(region_code: str = 'US', max_results: int = 50) -> list[dict]:
    """Fetch YouTube's current trending videos and filter to Shorts.

    The Data API only exposes a live "trending now" chart (no historical/
    weekly breakdown), so this reflects trending Shorts at call time.
    """
    videos = get_trending_videos(region_code=region_code, max_results=max_results)
    return [build_video(v['id'], v) for v in videos if is_short(v)]
