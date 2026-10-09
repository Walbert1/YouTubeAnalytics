"""CLI entry point. For the interactive UI run: streamlit run app.py"""
import os

from core import (
    CSV_EXPORTS,
    aggregate_across_queries,
    build_claude_brief,
    engagement_summary,
    fetch_trending_shorts,
    print_query_results,
    print_videos,
    run_niche_analysis,
    write_csv,
)

NICHE_QUERIES = [
    'firearms',
    'shooting',
    'firearms training',
    'practical shooting',
    'gun channel',
    'tactical training',
    'firearms review',
]

NICHE_REGION = 'US'
TIME_PERIOD = 'week'


def _print_overview(engagement: dict) -> None:
    print('\n\n' + '=' * 80)
    print('NICHE OVERVIEW')
    print('=' * 80)

    print('\nSHORTS — Top Queries by Engagement:')
    for q, eng in engagement['shorts_by_query'][:5]:
        print(f'  {q:30s} -> {eng:.2f}%')
    print('\nFULL VIDEOS — Top Queries by Engagement:')
    for q, eng in engagement['full_by_query'][:5]:
        print(f'  {q:30s} -> {eng:.2f}%')

    rec = 'SHORT-FORM' if engagement['avg_shorts'] >= engagement['avg_full'] else 'FULL-LENGTH'
    diff = abs(engagement['avg_shorts'] - engagement['avg_full'])
    print(f'\nRECOMMENDATION: Prioritize {rec} content ({diff:.2f}% higher engagement)')


def _write_niche_csvs(out_dir: str, combined: dict) -> None:
    for _, key, col_name, filename in CSV_EXPORTS:
        path = os.path.join(out_dir, filename)
        write_csv(path, [col_name, 'count'], combined[key].most_common())
        print(f'Wrote: {path}')


def _report_trending_shorts(out_dir: str) -> None:
    print('\n\n' + '=' * 80)
    print('TRENDING SHORTS RIGHT NOW')
    print('=' * 80)
    try:
        trending_shorts = fetch_trending_shorts(region_code=NICHE_REGION, max_results=50)
        print_videos(trending_shorts)
        if trending_shorts:
            path = os.path.join(out_dir, 'trending_shorts.csv')
            write_csv(
                path,
                ['title', 'channel_name', 'views', 'engagement_rate', 'url'],
                [(v['title'], v['channel_name'], v['views'], v['engagement_rate'], v['url'])
                 for v in trending_shorts],
            )
            print(f'Wrote: {path}')
    except Exception:
        print('  Skipping trending Shorts scan (quota or API error).')


def _write_claude_brief(out_dir: str, results: dict, combined: dict, engagement: dict) -> None:
    brief = build_claude_brief(NICHE_QUERIES, NICHE_REGION, TIME_PERIOD, results, combined, engagement)
    brief_path = os.path.join(out_dir, 'claude_content_brief.md')
    with open(brief_path, 'w', encoding='utf-8') as f:
        f.write(brief)
    print(f'\nWrote: {brief_path}')
    print('Paste this file into Claude to get video ideas, optimized titles, and hashtags.')


def main() -> None:
    print('\n' + '=' * 80)
    print('YOUTUBE FIREARMS NICHE ANALYSIS - THIS WEEK')
    print('(Tip: run "streamlit run app.py" for the interactive UI)')
    print('=' * 80)

    print(f'\nRunning {len(NICHE_QUERIES)} queries in parallel...\n')
    results = run_niche_analysis(
        NICHE_QUERIES, max_results=40, time_period=TIME_PERIOD, region_code=NICHE_REGION
    )
    for query, data in results.items():
        print_query_results(query, data)

    combined = aggregate_across_queries(results)
    engagement = engagement_summary(NICHE_QUERIES, results)
    _print_overview(engagement)

    out_dir = os.path.abspath('.')
    _write_niche_csvs(out_dir, combined)
    _report_trending_shorts(out_dir)
    _write_claude_brief(out_dir, results, combined, engagement)


if __name__ == '__main__':
    main()
