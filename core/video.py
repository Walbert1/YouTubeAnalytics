"""Shared video shaping: normalize raw API responses, classify Shorts vs.
full-length, and aggregate a list of videos into tag/hashtag/engagement stats.

Shorts-only and full-video-only behavior live in shorts.py / full_videos.py;
this module holds the logic both of those build on.
"""
from collections import Counter
import re

SHORT_MAX_SECONDS = 60


def is_short(video: dict) -> bool:
    duration = video.get('contentDetails', {}).get('duration', 'PT0S')
    m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if m:
        h, mn, s = m.groups()
        return int(h or 0) * 3600 + int(mn or 0) * 60 + int(s or 0) < SHORT_MAX_SECONDS
    return False


def extract_hashtags(title: str, description: str = '') -> list[str]:
    return list(set(re.findall(r'#\w+', f"{title} {description}")))


def build_video(video_id: str, details: dict) -> dict:
    """Normalize a raw YouTube API video resource into our video dict shape."""
    snippet = details.get('snippet', {})
    stats = details.get('statistics', {})
    views = int(stats.get('viewCount', 0))
    likes = int(stats.get('likeCount', 0))
    comments = int(stats.get('commentCount', 0))
    return {
        'id': video_id,
        'title': snippet.get('title', 'N/A'),
        'channel_name': snippet.get('channelTitle', 'N/A'),
        'channel_id': snippet.get('channelId', 'N/A'),
        'views': views,
        'likes': likes,
        'comments': comments,
        'tags': snippet.get('tags', []),
        'description': snippet.get('description', ''),
        'is_short': is_short(details),
        'url': f'https://www.youtube.com/watch?v={video_id}',
        'published_at': snippet.get('publishedAt', 'N/A'),
        'engagement_rate': (likes + comments) / views * 100 if views > 0 else 0.0,
    }


def aggregate_videos(videos: list[dict]) -> dict:
    """Roll up a list of videos into top tags/hashtags/channels and avg engagement."""
    tags_c: Counter = Counter()
    hashtags_c: Counter = Counter()
    channels_c: Counter = Counter()
    for v in videos:
        for t in v.get('tags', []):
            tags_c[t.lower()] += 1
        for h in extract_hashtags(v.get('title', '')):
            hashtags_c[h.lower()] += 1
        channels_c[v['channel_name']] += 1
    avg_eng = sum(v['engagement_rate'] for v in videos) / len(videos) if videos else 0.0
    return {
        'videos': videos,
        'top_tags': tags_c.most_common(20),
        'top_hashtags': hashtags_c.most_common(20),
        'top_channels': channels_c.most_common(10),
        'avg_engagement': avg_eng,
    }
