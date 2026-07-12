from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

from api import (
    get_channel_tags,
    search_videos,
    search_videos_by_period,
    get_video_details_batch,
    get_trending_videos,
)


def is_short(video: dict) -> bool:
    duration = video.get('contentDetails', {}).get('duration', 'PT0S')
    m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if m:
        h, mn, s = m.groups()
        return int(h or 0) * 3600 + int(mn or 0) * 60 + int(s or 0) < 60
    return False


def _build_video_info(video_id: str, details: dict) -> dict:
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


def extract_hashtags(title: str, description: str = '') -> list[str]:
    return list(set(re.findall(r'#\w+', f"{title} {description}")))


def _fetch_videos(query: str, time_period: str | None,
                  max_results: int, region_code: str) -> list[dict]:
    if time_period and time_period != 'all_time':
        items = search_videos_by_period(query, time_period, max_results, region_code)
    else:
        items = search_videos(query=query, max_results=max_results,
                              region_code=region_code).get('items', [])

    video_ids = [item['id']['videoId'] for item in items
                 if isinstance(item.get('id'), dict) and 'videoId' in item['id']]
    details_map = get_video_details_batch(video_ids)
    return [_build_video_info(vid, details_map[vid])
            for vid in video_ids if vid in details_map]


def _aggregate_videos(videos: list[dict]) -> dict:
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


def get_trending_shorts(region_code: str = 'US', max_results: int = 50) -> list[dict]:
    """Fetch YouTube's current trending videos and filter to Shorts.

    The Data API only exposes a live "trending now" chart (no historical/
    weekly breakdown), so this reflects trending Shorts at call time.
    """
    videos = get_trending_videos(region_code=region_code, max_results=max_results)
    return [_build_video_info(v['id'], v) for v in videos if is_short(v)]


def analyze_query(query: str, max_results: int = 40,
                  time_period: str = 'week', region_code: str = 'US') -> dict:
    """Fetch and analyze one query. Returns {'shorts': {...}, 'full_videos': {...}}."""
    videos = _fetch_videos(query, time_period, max_results, region_code)
    shorts = sorted([v for v in videos if v['is_short']],
                    key=lambda x: x['views'], reverse=True)
    full_videos = sorted([v for v in videos if not v['is_short']],
                         key=lambda x: x['views'], reverse=True)
    return {
        'shorts': _aggregate_videos(shorts),
        'full_videos': _aggregate_videos(full_videos),
    }


def run_niche_analysis(queries: list[str], max_results: int = 40,
                       time_period: str = 'week', region_code: str = 'US') -> dict:
    """Run analyze_query for all queries in parallel. Returns dict keyed by query."""
    results: dict = {}
    with ThreadPoolExecutor(max_workers=min(len(queries), 4)) as executor:
        futures = {
            executor.submit(analyze_query, q, max_results, time_period, region_code): q
            for q in queries
        }
        for future in as_completed(futures):
            q = futures[future]
            results[q] = future.result()
    return results


def aggregate_across_queries(results: dict) -> dict:
    """Merge all per-query results into niche-wide counters and video lists."""
    combined: dict = {
        'shorts_tags': Counter(),
        'shorts_hashtags': Counter(),
        'full_tags': Counter(),
        'full_hashtags': Counter(),
        'channel_tags': Counter(),
        'all_shorts': [],
        'all_full_videos': [],
    }
    channel_tags_cache: dict = {}

    def _ch_tags(ch_id: str) -> list[str]:
        if ch_id not in channel_tags_cache:
            channel_tags_cache[ch_id] = get_channel_tags(ch_id)
        return channel_tags_cache[ch_id]

    for q_data in results.values():
        for v in q_data['shorts']['videos']:
            combined['all_shorts'].append(v)
            for t in v.get('tags', []):
                combined['shorts_tags'][t.lower()] += 1
            for h in extract_hashtags(v.get('title', '')):
                combined['shorts_hashtags'][h.lower()] += 1
            for ct in _ch_tags(v.get('channel_id', '')):
                combined['channel_tags'][ct] += 1

        for v in q_data['full_videos']['videos']:
            combined['all_full_videos'].append(v)
            for t in v.get('tags', []):
                combined['full_tags'][t.lower()] += 1
            for h in extract_hashtags(v.get('title', '')):
                combined['full_hashtags'][h.lower()] += 1
            for ct in _ch_tags(v.get('channel_id', '')):
                combined['channel_tags'][ct] += 1

    return combined

