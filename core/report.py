"""Reporting helpers shared by the CLI (youtube_api_call.py) and the
Streamlit app (app.py): CSV export spec, console printing, and the
Claude content-brief builder."""
import csv

# (label, combined-dict key, CSV column name, filename) — the single source of
# truth for both the CLI's file writes and the Streamlit app's download buttons.
CSV_EXPORTS = [
    ('Tags — Shorts',      'shorts_tags',     'tag',         'tags_shorts.csv'),
    ('Tags — Full Videos', 'full_tags',       'tag',         'tags_full.csv'),
    ('Hashtags — Shorts',  'shorts_hashtags', 'hashtag',     'hashtags_shorts.csv'),
    ('Hashtags — Full',    'full_hashtags',   'hashtag',     'hashtags_full.csv'),
    ('Channel Tags',       'channel_tags',    'channel_tag', 'channel_tags.csv'),
]


def write_csv(path: str, header: list, rows) -> None:
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def print_videos(videos: list[dict], limit: int = 10) -> None:
    if not videos:
        print('  No results.')
        return
    for i, v in enumerate(videos[:limit], 1):
        print(f"  {i:2d}. {v['title']}")
        print(f"      Channel : {v['channel_name']}")
        print(f"      Views   : {v['views']:,}  |  Eng: {v['engagement_rate']:.2f}%")
        print(f"      URL     : {v['url']}")


def print_query_results(query: str, data: dict) -> None:
    for format_key, label in [('shorts', 'SHORTS'), ('full_videos', 'FULL VIDEOS')]:
        section = data[format_key]
        print(f'\n{"=" * 80}')
        print(f'{label} — {query.upper()}')
        print(f'{"=" * 80}')
        print_videos(section['videos'])
        if section['videos']:
            print(f"\n  Avg engagement: {section['avg_engagement']:.2f}%")
            print(f"  Top tags      : {', '.join(t for t, _ in section['top_tags'][:5])}")
            print(f"  Top hashtags  : {', '.join(h for h, _ in section['top_hashtags'][:5])}")


def build_claude_brief(queries: list, region: str, time_period: str,
                       results: dict, combined: dict, engagement: dict) -> str:
    """Package the analysis into a markdown brief to paste into Claude for
    video ideas, titles, and hashtags optimized for the YouTube algorithm."""
    avg_s = engagement['avg_shorts']
    avg_f = engagement['avg_full']

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
