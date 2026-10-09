"""Run the same niche-defining search queries across Shorts and full-length
videos, and aggregate the results per-query and niche-wide."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

from .api import get_channel_tags, get_video_details_batch, search_videos
from .full_videos import aggregate_full_videos
from .shorts import aggregate_shorts
from .video import build_video, extract_hashtags


def _fetch_videos(query: str, max_results: int, region_code: str,
                  time_period: str | None) -> list[dict]:
    items = search_videos(
        query=query, max_results=max_results, region_code=region_code,
        time_period=None if time_period == 'all_time' else time_period,
    )
    video_ids = [item['id']['videoId'] for item in items
                 if isinstance(item.get('id'), dict) and 'videoId' in item['id']]
    details_map = get_video_details_batch(video_ids)
    return [build_video(vid, details_map[vid]) for vid in video_ids if vid in details_map]


def analyze_query(query: str, max_results: int = 40,
                  time_period: str = 'week', region_code: str = 'US') -> dict:
    """Fetch and analyze one query. Returns {'shorts': {...}, 'full_videos': {...}}."""
    videos = _fetch_videos(query, max_results, region_code, time_period)
    return {
        'shorts': aggregate_shorts(videos),
        'full_videos': aggregate_full_videos(videos),
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

    def _accumulate(videos: list[dict], all_key: str, tags_key: str, hashtags_key: str) -> None:
        for v in videos:
            combined[all_key].append(v)
            for t in v.get('tags', []):
                combined[tags_key][t.lower()] += 1
            for h in extract_hashtags(v.get('title', '')):
                combined[hashtags_key][h.lower()] += 1
            for ct in _ch_tags(v.get('channel_id', '')):
                combined['channel_tags'][ct] += 1

    for q_data in results.values():
        _accumulate(q_data['shorts']['videos'], 'all_shorts', 'shorts_tags', 'shorts_hashtags')
        _accumulate(q_data['full_videos']['videos'], 'all_full_videos', 'full_tags', 'full_hashtags')

    return combined


def engagement_summary(queries: list[str], results: dict) -> dict:
    """Compare Shorts vs. full-length engagement across queries, ranked both ways."""
    shorts_by_query = [
        (q, results[q]['shorts']['avg_engagement'])
        for q in queries if q in results and results[q]['shorts']['videos']
    ]
    full_by_query = [
        (q, results[q]['full_videos']['avg_engagement'])
        for q in queries if q in results and results[q]['full_videos']['videos']
    ]
    shorts_by_query.sort(key=lambda x: x[1], reverse=True)
    full_by_query.sort(key=lambda x: x[1], reverse=True)
    avg_shorts = sum(e for _, e in shorts_by_query) / len(shorts_by_query) if shorts_by_query else 0.0
    avg_full = sum(e for _, e in full_by_query) / len(full_by_query) if full_by_query else 0.0
    return {
        'shorts_by_query': shorts_by_query,
        'full_by_query': full_by_query,
        'avg_shorts': avg_shorts,
        'avg_full': avg_full,
    }
