"""CLI entry point. For the interactive UI run: streamlit run app.py"""
import csv
import os

from analysis import run_niche_analysis, aggregate_across_queries, get_trending_shorts

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


def _write_csv(path: str, header: list, rows) -> None:
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print(f'Wrote: {path}')


def _print_query_results(query: str, data: dict) -> None:
    for format_key, label in [('shorts', 'SHORTS'), ('full_videos', 'FULL VIDEOS')]:
        section = data[format_key]
        videos = section['videos']
        print(f'\n{"="*80}')
        print(f'{label} — {query.upper()}')
        print(f'{"="*80}')
        if not videos:
            print('  No results.')
            continue
        for i, v in enumerate(videos[:10], 1):
            print(f"  {i:2d}. {v['title']}")
            print(f"      Channel : {v['channel_name']}")
            print(f"      Views   : {v['views']:,}  |  Eng: {v['engagement_rate']:.2f}%")
            print(f"      URL     : {v['url']}")
        print(f"\n  Avg engagement: {section['avg_engagement']:.2f}%")
        print(f"  Top tags      : {', '.join(t for t, _ in section['top_tags'][:5])}")
        print(f"  Top hashtags  : {', '.join(h for h, _ in section['top_hashtags'][:5])}")


def _build_claude_brief(queries: list, region: str, time_period: str,
                        results: dict, combined: dict) -> str:
    """Package the analysis into a markdown brief to paste into Claude for
    video ideas, titles, and hashtags optimized for the YouTube algorithm."""
    shorts_eng = [(q, results[q]['shorts']['avg_engagement'])
                  for q in queries if results[q]['shorts']['videos']]
    full_eng = [(q, results[q]['full_videos']['avg_engagement'])
                for q in queries if results[q]['full_videos']['videos']]
    avg_s = sum(e for _, e in shorts_eng) / len(shorts_eng) if shorts_eng else 0.0
    avg_f = sum(e for _, e in full_eng) / len(full_eng) if full_eng else 0.0

    lines = [
        '# YouTube Content Strategy Brief',
        '',
        'You are a YouTube growth strategist. Using the real trending-data '
        f'snapshot below for the "{", ".join(queries)}" niche '
        f'(region: {region}, window: {time_period}), produce:',
        '',
        '1. 10 video ideas grounded in what is actually trending in this data '
        '(not generic advice).',
        '2. For each idea, 3 alternative titles optimized for the YouTube '
        'algorithm — front-load the searchable keyword, keep it under ~60 '
        'characters, and reuse terms/patterns from the top tags and titles below.',
        '3. A hashtag set per idea (3-5 tags: a mix of the top-performing '
        'hashtags below plus niche-specific ones).',
        '4. A format recommendation (Short vs. full-length) per idea, '
        'justified by the engagement data below.',
        '',
        'Ground every recommendation in the data — cite the tag, hashtag, or '
        'video pattern that justifies it. Do not invent statistics not shown here.',
        '',
        '---',
        '',
        '## YouTube Algorithm Context (for reference)',
        '',
        '- Shorts ranking leans on completion rate and rewatches, driven by '
        'the first 2-3 second hook; long-form leans on click-through rate '
        '(CTR) and average view duration / session watch time.',
        '- Titles: front-load the searchable keyword in the first ~40-60 '
        'characters; avoid keyword stuffing.',
        '- Hashtags: YouTube displays the first 3 hashtags above the title — '
        'put the most important ones first; avoid more than ~15 total tags '
        '(spam risk). Title/description keyword match matters more than tags alone.',
        '- Consistency between thumbnail, title, and actual content avoids '
        '"clickbait" demotion.',
        '',
        '---',
        '',
        '## Niche-Wide Signals',
        '',
        f'- Avg engagement — Shorts: {avg_s:.2f}%  |  Full videos: {avg_f:.2f}%',
        '- Top Shorts tags: ' + ', '.join(t for t, _ in combined['shorts_tags'].most_common(15)),
        '- Top Shorts hashtags: ' + ', '.join(h for h, _ in combined['shorts_hashtags'].most_common(15)),
        '- Top Full-video tags: ' + ', '.join(t for t, _ in combined['full_tags'].most_common(15)),
        '- Top Full-video hashtags: ' + ', '.join(h for h, _ in combined['full_hashtags'].most_common(15)),
        '- Top channel branding keywords in this niche: '
        + ', '.join(t for t, _ in combined['channel_tags'].most_common(15)),
        '',
        '---',
        '',
        '## Per-Query Breakdown',
    ]

    for q in queries:
        if q not in results:
            continue
        data = results[q]
        lines.append('')
        lines.append(f'### "{q}"')
        for format_key, label in [('shorts', 'Shorts'), ('full_videos', 'Full videos')]:
            section = data[format_key]
            videos = section['videos']
            lines.append('')
            lines.append(f'**{label}** (avg engagement: {section["avg_engagement"]:.2f}%)')
            if videos:
                for v in videos[:5]:
                    lines.append(
                        f"- \"{v['title']}\" — {v['channel_name']} "
                        f"({v['views']:,} views, {v['engagement_rate']:.2f}% eng)"
                    )
                top_tags = ', '.join(t for t, _ in section['top_tags'][:8])
                top_hashtags = ', '.join(h for h, _ in section['top_hashtags'][:8])
                if top_tags:
                    lines.append(f'  Top tags: {top_tags}')
                if top_hashtags:
                    lines.append(f'  Top hashtags: {top_hashtags}')
            else:
                lines.append('- No results.')

    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    print('\n' + '=' * 80)
    print('YOUTUBE FIREARMS NICHE ANALYSIS - THIS WEEK')
    print('(Tip: run "streamlit run app.py" for the interactive UI)')
    print('=' * 80)

    print(f'\nRunning {len(NICHE_QUERIES)} queries in parallel...\n')
    results = run_niche_analysis(
        NICHE_QUERIES, max_results=40, time_period='week', region_code=NICHE_REGION
    )

    for query, data in results.items():
        _print_query_results(query, data)

    # Niche-wide aggregation
    combined = aggregate_across_queries(results)

    # Engagement summary
    print('\n\n' + '=' * 80)
    print('NICHE OVERVIEW')
    print('=' * 80)
    shorts_eng = [
        (q, results[q]['shorts']['avg_engagement'])
        for q in NICHE_QUERIES if results[q]['shorts']['videos']
    ]
    full_eng = [
        (q, results[q]['full_videos']['avg_engagement'])
        for q in NICHE_QUERIES if results[q]['full_videos']['videos']
    ]
    shorts_eng.sort(key=lambda x: x[1], reverse=True)
    full_eng.sort(key=lambda x: x[1], reverse=True)

    print('\nSHORTS — Top Queries by Engagement:')
    for q, eng in shorts_eng[:5]:
        print(f'  {q:30s} -> {eng:.2f}%')
    print('\nFULL VIDEOS — Top Queries by Engagement:')
    for q, eng in full_eng[:5]:
        print(f'  {q:30s} -> {eng:.2f}%')

    avg_s = sum(e for _, e in shorts_eng) / len(shorts_eng) if shorts_eng else 0
    avg_f = sum(e for _, e in full_eng) / len(full_eng) if full_eng else 0
    rec = 'SHORT-FORM' if avg_s >= avg_f else 'FULL-LENGTH'
    print(f'\nRECOMMENDATION: Prioritize {rec} content ({abs(avg_s - avg_f):.2f}% higher engagement)')

    # Write CSVs
    out = os.path.abspath('.')
    _write_csv(os.path.join(out, 'tags_shorts.csv'),    ['tag', 'count'],         combined['shorts_tags'].most_common())
    _write_csv(os.path.join(out, 'tags_full.csv'),      ['tag', 'count'],         combined['full_tags'].most_common())
    _write_csv(os.path.join(out, 'hashtags_shorts.csv'),['hashtag', 'count'],     combined['shorts_hashtags'].most_common())
    _write_csv(os.path.join(out, 'hashtags_full.csv'),  ['hashtag', 'count'],     combined['full_hashtags'].most_common())
    _write_csv(os.path.join(out, 'channel_tags.csv'),   ['channel_tag', 'count'], combined['channel_tags'].most_common())

    # Trending Shorts (YouTube's live trending chart, filtered to Shorts)
    print('\n\n' + '=' * 80)
    print('TRENDING SHORTS RIGHT NOW')
    print('=' * 80)
    try:
        trending_shorts = get_trending_shorts(region_code=NICHE_REGION, max_results=50)
        if trending_shorts:
            for i, v in enumerate(trending_shorts[:10], 1):
                print(f"  {i:2d}. {v['title']}")
                print(f"      Channel : {v['channel_name']}")
                print(f"      Views   : {v['views']:,}  |  Eng: {v['engagement_rate']:.2f}%")
                print(f"      URL     : {v['url']}")
            _write_csv(
                os.path.join(out, 'trending_shorts.csv'),
                ['title', 'channel_name', 'views', 'engagement_rate', 'url'],
                [(v['title'], v['channel_name'], v['views'], v['engagement_rate'], v['url'])
                 for v in trending_shorts],
            )
        else:
            print('  No trending Shorts found.')
    except Exception:
        print('  Skipping trending Shorts scan (quota or API error).')

    # Claude content brief — paste into Claude to get video ideas, titles, and hashtags
    brief = _build_claude_brief(NICHE_QUERIES, NICHE_REGION, 'week', results, combined)
    brief_path = os.path.join(out, 'claude_content_brief.md')
    with open(brief_path, 'w', encoding='utf-8') as f:
        f.write(brief)
    print(f'\nWrote: {brief_path}')
    print('Paste this file into Claude to get video ideas, optimized titles, and hashtags.')
