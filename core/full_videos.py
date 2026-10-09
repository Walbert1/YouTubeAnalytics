"""Full-length-video-specific logic: splitting a mixed video list down to
full-length videos (anything 60 seconds or longer)."""
from .video import aggregate_videos


def filter_full_videos(videos: list[dict]) -> list[dict]:
    return sorted((v for v in videos if not v['is_short']), key=lambda v: v['views'], reverse=True)


def aggregate_full_videos(videos: list[dict]) -> dict:
    return aggregate_videos(filter_full_videos(videos))
