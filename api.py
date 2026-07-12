from googleapiclient.discovery import build
from datetime import datetime, timedelta
import os
import threading
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('YOUTUBE_API_KEY')
if not api_key:
    raise EnvironmentError("YOUTUBE_API_KEY not found. Add it to a .env file or set it in your shell.")

_thread_local = threading.local()
_video_cache: dict = {}
_video_cache_lock = threading.Lock()


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
    import re
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


def search_videos(query: str = 'firearms', max_results: int = 50,
                  order: str = 'viewCount', region_code: str = 'US') -> dict:
    return _get_youtube().search().list(
        part='snippet',
        q=query,
        type='video',
        maxResults=max_results,
        order=order,
        regionCode=region_code
    ).execute()


def search_videos_by_period(query: str, time_period: str,
                             max_results: int, region_code: str) -> list[dict]:
    now = datetime.utcnow()
    offsets = {'week': 7, 'month': 30, 'year': 365}
    published_after = None
    if time_period in offsets:
        published_after = (now - timedelta(days=offsets[time_period])).isoformat() + 'Z'

    kwargs = dict(
        part='snippet',
        q=query,
        type='video',
        maxResults=max_results,
        order='viewCount',
        regionCode=region_code,
    )
    if published_after:
        kwargs['publishedAfter'] = published_after

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
