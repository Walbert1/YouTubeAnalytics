import streamlit as st
import pandas as pd
import plotly.express as px

from core import CSV_EXPORTS, aggregate_across_queries, fetch_trending_shorts, run_niche_analysis

st.set_page_config(
    page_title="YouTube Niche Analytics",
    page_icon="▶",
    layout="wide",
)

DEFAULT_QUERIES = [
    'firearms',
    'shooting',
    'firearms training',
    'practical shooting',
    'gun channel',
    'tactical training',
    'firearms review',
]

REGIONS = ['US', 'GB', 'CA', 'AU', 'DE', 'FR', 'JP', 'BR', 'IN', 'MX']
TIME_PERIODS = ['week', 'month', 'year', 'all_time']

VIDEO_COLUMN_LABELS = {
    'title': 'Title', 'channel_name': 'Channel', 'views': 'Views',
    'likes': 'Likes', 'comments': 'Comments', 'engagement_rate': 'Eng %', 'url': 'URL',
}

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.title("Settings")

queries_raw = st.sidebar.text_area(
    "Queries (one per line)",
    value='\n'.join(DEFAULT_QUERIES),
    height=180,
)
queries = [q.strip() for q in queries_raw.strip().splitlines() if q.strip()]

region = st.sidebar.selectbox("Region", REGIONS, index=0)
time_period = st.sidebar.selectbox("Time Period", TIME_PERIODS, index=0)
max_results = st.sidebar.slider("Max Results per Query", min_value=10, max_value=50, value=40, step=10)

run_btn = st.sidebar.button("Run Analysis", type="primary", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.caption("Results are cached — same settings reuse the previous fetch.")


# ── Cache wrappers ─────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _fetch(queries_tuple: tuple, region: str, time_period: str, max_results: int) -> dict:
    return run_niche_analysis(list(queries_tuple), max_results, time_period, region)


@st.cache_data(show_spinner=False)
def _fetch_trending_shorts(region: str, max_results: int) -> list[dict]:
    return fetch_trending_shorts(region_code=region, max_results=max_results)


# ── Helpers ────────────────────────────────────────────────────────────────────
def counter_df(data: list[tuple], col_name: str) -> pd.DataFrame:
    return pd.DataFrame(data, columns=[col_name, 'Count'])


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode('utf-8')


def bar_chart(data: list[tuple], col_name: str, title: str) -> None:
    df = counter_df(data[:20], col_name)
    fig = px.bar(df, x='Count', y=col_name, orientation='h', title=title,
                 color='Count', color_continuous_scale='Blues')
    fig.update_layout(yaxis={'categoryorder': 'total ascending'},
                      coloraxis_showscale=False, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig, use_container_width=True)


def video_table(videos: list[dict], sort_by_views: bool = True, limit: int | None = 50) -> pd.DataFrame:
    """Shared table shape for the Shorts, Full Videos, and Trending Shorts tabs."""
    if not videos:
        return pd.DataFrame(columns=list(VIDEO_COLUMN_LABELS.values()))
    df = pd.DataFrame(videos)[list(VIDEO_COLUMN_LABELS)].drop_duplicates('url')
    if sort_by_views:
        df = df.sort_values('views', ascending=False)
    if limit is not None:
        df = df.head(limit)
    df = df.rename(columns=VIDEO_COLUMN_LABELS)
    df['Eng %'] = df['Eng %'].round(2)
    return df


def render_video_section(videos: list[dict], tags: list[tuple], hashtags: list[tuple],
                         empty_message: str, tag_label: str) -> None:
    """Shared body for the Shorts and Full Videos tabs: table + tag/hashtag charts."""
    if videos:
        st.dataframe(video_table(videos), use_container_width=True, hide_index=True)
    else:
        st.info(empty_message)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        bar_chart(tags, 'Tag', f'Top Tags ({tag_label})')
    with col2:
        bar_chart(hashtags, 'Hashtag', f'Top Hashtags ({tag_label})')


# ── Main ───────────────────────────────────────────────────────────────────────
st.title("YouTube Niche Analytics")

if run_btn:
    if not queries:
        st.warning("Add at least one query in the sidebar.")
    else:
        with st.spinner(f"Fetching data for {len(queries)} quer{'y' if len(queries)==1 else 'ies'} in parallel…"):
            st.session_state['results'] = _fetch(tuple(queries), region, time_period, max_results)
            st.session_state['trending_shorts'] = _fetch_trending_shorts(region, 50)

if 'results' not in st.session_state:
    st.info("Configure your settings in the sidebar and click **Run Analysis**.")
else:
    results: dict = st.session_state['results']
    combined: dict = aggregate_across_queries(results)
    trending_shorts: list = st.session_state.get('trending_shorts', [])

    # ── Tabs ─────────────────────────────────────────────────────────────────────
    tab_overview, tab_shorts, tab_full, tab_trending, tab_export = st.tabs([
        "Overview", "Shorts", "Full Videos", "Trending Shorts", "Export"
    ])

    # ── Overview ─────────────────────────────────────────────────────────────────
    with tab_overview:
        st.subheader("Engagement by Query")

        rows = [
            {
                'Query': q,
                'Shorts Engagement %': round(data['shorts']['avg_engagement'], 2),
                'Full Video Engagement %': round(data['full_videos']['avg_engagement'], 2),
                'Shorts Count': len(data['shorts']['videos']),
                'Full Video Count': len(data['full_videos']['videos']),
            }
            for q, data in results.items()
        ]
        df_eng = pd.DataFrame(rows).sort_values('Shorts Engagement %', ascending=False)

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(df_eng, x='Query', y='Shorts Engagement %',
                         title='Shorts — Avg Engagement Rate',
                         color='Shorts Engagement %', color_continuous_scale='Teal')
            fig.update_layout(coloraxis_showscale=False, xaxis_tickangle=-30)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.bar(df_eng, x='Query', y='Full Video Engagement %',
                         title='Full Videos — Avg Engagement Rate',
                         color='Full Video Engagement %', color_continuous_scale='Oranges')
            fig.update_layout(coloraxis_showscale=False, xaxis_tickangle=-30)
            st.plotly_chart(fig, use_container_width=True)

        avg_shorts = df_eng['Shorts Engagement %'].mean()
        avg_full = df_eng['Full Video Engagement %'].mean()
        rec = "Short-form" if avg_shorts >= avg_full else "Full-length"
        diff = abs(avg_shorts - avg_full)
        st.info(
            f"**Recommendation:** Prioritize **{rec}** content — "
            f"{diff:.2f}% higher average engagement across all queries."
        )

        st.markdown("---")
        st.subheader("Query Summary Table")
        st.dataframe(df_eng, use_container_width=True, hide_index=True)

    # ── Shorts ───────────────────────────────────────────────────────────────────
    with tab_shorts:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("Top Shorts (All Queries Combined)")
        with col2:
            shorts_query_filter = st.selectbox(
                "Filter by query", ['All'] + list(results.keys()), key='shorts_filter'
            )

        if shorts_query_filter == 'All':
            shorts_list = combined['all_shorts']
            s_tags = combined['shorts_tags'].most_common(20)
            s_hashtags = combined['shorts_hashtags'].most_common(20)
        else:
            shorts_section = results[shorts_query_filter]['shorts']
            shorts_list = shorts_section['videos']
            s_tags = shorts_section['top_tags']
            s_hashtags = shorts_section['top_hashtags']

        render_video_section(shorts_list, s_tags, s_hashtags, "No shorts found for this selection.", "Shorts")

    # ── Full Videos ──────────────────────────────────────────────────────────────
    with tab_full:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("Top Full Videos (All Queries Combined)")
        with col2:
            full_query_filter = st.selectbox(
                "Filter by query", ['All'] + list(results.keys()), key='full_filter'
            )

        if full_query_filter == 'All':
            full_list = combined['all_full_videos']
            f_tags = combined['full_tags'].most_common(20)
            f_hashtags = combined['full_hashtags'].most_common(20)
        else:
            full_section = results[full_query_filter]['full_videos']
            full_list = full_section['videos']
            f_tags = full_section['top_tags']
            f_hashtags = full_section['top_hashtags']

        render_video_section(full_list, f_tags, f_hashtags, "No full videos found for this selection.", "Full Videos")

    # ── Trending Shorts ──────────────────────────────────────────────────────────
    with tab_trending:
        st.subheader(f"Trending Shorts Right Now ({region})")
        st.caption(
            "YouTube's Data API only exposes a live trending chart (no weekly "
            "history), so this is a snapshot from when you last clicked Run Analysis."
        )

        if trending_shorts:
            df_trending = video_table(trending_shorts, sort_by_views=False, limit=None)
            st.dataframe(df_trending, use_container_width=True, hide_index=True)
        else:
            st.info("No trending Shorts found.")

    # ── Export ───────────────────────────────────────────────────────────────────
    with tab_export:
        st.subheader("Download CSVs")
        st.caption("All downloads reflect the current query/filter selection.")

        cols = st.columns(3)
        for i, (label, key, col_name, filename) in enumerate(CSV_EXPORTS):
            df = pd.DataFrame(combined[key].most_common(), columns=[col_name, 'count'])
            cols[i % 3].download_button(
                label=f"Download: {label}",
                data=to_csv_bytes(df),
                file_name=filename,
                mime='text/csv',
                use_container_width=True,
            )

        st.markdown("---")
        st.subheader("Download All Videos")
        video_exports = [
            ("Download All Shorts Data", combined['all_shorts'], 'all_shorts.csv'),
            ("Download All Full Videos Data", combined['all_full_videos'], 'all_full_videos.csv'),
            ("Download Trending Shorts Data", trending_shorts, 'trending_shorts.csv'),
        ]
        for label, videos, filename in video_exports:
            if videos:
                st.download_button(
                    label,
                    data=to_csv_bytes(pd.DataFrame(videos).drop_duplicates('url')),
                    file_name=filename,
                    mime='text/csv',
                )
