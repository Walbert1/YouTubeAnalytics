"""Thin wrapper around the YouTube Data API v3."""
import os
import re
import threading
from datetime import datetime, timedelta

from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

api_key = os.getenv('YOUTUBE_API_KEY')
if not api_key:
    raise EnvironmentError("YOUTUBE_API_KEY not found. Add it to a .env file or set it in your shell.")

_thread_local = threading.local()
_video_cache: dict = {}
_video_cache_lock = threading.Lock()

_PERIOD_OFFSET_DAYS = {'week': 7, 'month': 30, 'year': 365}


def _get_youtube():
    if not hasattr(_thread_local, 'client'):
        _thread_local.client = build('youtube', 'v3', developerKey=api_key)
    return _thread_local.client


def get_channel_stats(username: str) -> dict:
    return _get_youtube().channels().list(
        part='statistics,snippet',
        forUsername=username
    ).execute()


def get_channel_tags(channel_id: str) -> list[str]:
    try:
        resp = _get_youtube().channels().list(
            part='brandingSettings,snippet', id=channel_id
        ).execute()
        items = resp.get('items', [])
        if not items:
            return []
        ch = items[0]
        keywords = ch.get('brandingSettings', {}).get('channel', {}).get('keywords') or ''
        if keywords:
            return [k.strip().lower() for k in re.split(r',|\s{2,}', keywords) if k.strip()]
        desc = ch.get('snippet', {}).get('description', '')
        if ',' in desc:
            return [t.strip().lower() for t in desc.split(',') if t.strip()]
        return []
    except Exception:
        return []


def search_videos(query: str, max_results: int = 50, region_code: str = 'US',
                  order: str = 'viewCount', time_period: str | None = None) -> list[dict]:
    """Search for videos, optionally restricted to a recency window.

    `time_period` is one of 'week', 'month', 'year', or None/anything else for all-time.
    """
    kwargs = dict(
        part='snippet', q=query, type='video',
        maxResults=max_results, order=order, regionCode=region_code,
    )
    if time_period in _PERIOD_OFFSET_DAYS:
        published_after = datetime.utcnow() - timedelta(days=_PERIOD_OFFSET_DAYS[time_period])
        kwargs['publishedAfter'] = published_after.isoformat() + 'Z'
    return _get_youtube().search().list(**kwargs).execute().get('items', [])


def get_video_details_batch(video_ids: list[str]) -> dict:
    """Fetch video details for multiple IDs, batching 50 per call. Uses shared cache."""
    if not video_ids:
        return {}

    results: dict = {}
    to_fetch: list[str] = []

    with _video_cache_lock:
        for vid in video_ids:
            if vid in _video_cache:
                results[vid] = _video_cache[vid]
            else:
                to_fetch.append(vid)

    for i in range(0, len(to_fetch), 50):
        chunk = to_fetch[i:i + 50]
        response = _get_youtube().videos().list(
            part='snippet,statistics,contentDetails',
            id=','.join(chunk)
        ).execute()
        with _video_cache_lock:
            for item in response.get('items', []):
                _video_cache[item['id']] = item
                results[item['id']] = item

    return results


def get_trending_videos(region_code: str = 'US', max_results: int = 50) -> list[dict]:
    return _get_youtube().videos().list(
        part='snippet,statistics,contentDetails',
        chart='mostPopular',
        regionCode=region_code,
        maxResults=max_results
    ).execute().get('items', [])
