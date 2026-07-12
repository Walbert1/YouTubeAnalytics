import streamlit as st
import pandas as pd
import plotly.express as px
from collections import Counter

from analysis import run_niche_analysis, aggregate_across_queries, get_trending_shorts

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
    return get_trending_shorts(region_code=region, max_results=max_results)


# ── Helpers ────────────────────────────────────────────────────────────────────
def counter_df(data: list[tuple], col_name: str) -> pd.DataFrame:
    return pd.DataFrame(data, columns=[col_name, 'Count'])


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode('utf-8')


def bar_chart(data: list[tuple], col_name: str, title: str):
    df = counter_df(data[:20], col_name)
    fig = px.bar(df, x='Count', y=col_name, orientation='h', title=title,
                 color='Count', color_continuous_scale='Blues')
    fig.update_layout(yaxis={'categoryorder': 'total ascending'},
                      coloraxis_showscale=False, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig, use_container_width=True)


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
            shorts_list = results[shorts_query_filter]['shorts']['videos']
            s_tags = results[shorts_query_filter]['shorts']['top_tags']
            s_hashtags = results[shorts_query_filter]['shorts']['top_hashtags']

        if shorts_list:
            df_shorts = (
                pd.DataFrame(shorts_list)[
                    ['title', 'channel_name', 'views', 'likes', 'comments', 'engagement_rate', 'url']
                ]
                .sort_values('views', ascending=False)
                .drop_duplicates('url')
                .head(50)
                .rename(columns={
                    'title': 'Title', 'channel_name': 'Channel', 'views': 'Views',
                    'likes': 'Likes', 'comments': 'Comments',
                    'engagement_rate': 'Eng %', 'url': 'URL',
                })
            )
            df_shorts['Eng %'] = df_shorts['Eng %'].round(2)
            st.dataframe(df_shorts, use_container_width=True, hide_index=True)
        else:
            st.info("No shorts found for this selection.")

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            bar_chart(s_tags, 'Tag', 'Top Tags (Shorts)')
        with col2:
            bar_chart(s_hashtags, 'Hashtag', 'Top Hashtags (Shorts)')

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
            full_list = results[full_query_filter]['full_videos']['videos']
            f_tags = results[full_query_filter]['full_videos']['top_tags']
            f_hashtags = results[full_query_filter]['full_videos']['top_hashtags']

        if full_list:
            df_full = (
                pd.DataFrame(full_list)[
                    ['title', 'channel_name', 'views', 'likes', 'comments', 'engagement_rate', 'url']
                ]
                .sort_values('views', ascending=False)
                .drop_duplicates('url')
                .head(50)
                .rename(columns={
                    'title': 'Title', 'channel_name': 'Channel', 'views': 'Views',
                    'likes': 'Likes', 'comments': 'Comments',
                    'engagement_rate': 'Eng %', 'url': 'URL',
                })
            )
            df_full['Eng %'] = df_full['Eng %'].round(2)
            st.dataframe(df_full, use_container_width=True, hide_index=True)
        else:
            st.info("No full videos found for this selection.")

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            bar_chart(f_tags, 'Tag', 'Top Tags (Full Videos)')
        with col2:
            bar_chart(f_hashtags, 'Hashtag', 'Top Hashtags (Full Videos)')

    # ── Trending Shorts ──────────────────────────────────────────────────────────
    with tab_trending:
        st.subheader(f"Trending Shorts Right Now ({region})")
        st.caption(
            "YouTube's Data API only exposes a live trending chart (no weekly "
            "history), so this is a snapshot from when you last clicked Run Analysis."
        )

        if trending_shorts:
            df_trending = (
                pd.DataFrame(trending_shorts)[
                    ['title', 'channel_name', 'views', 'likes', 'comments', 'engagement_rate', 'url']
                ]
                .drop_duplicates('url')
                .rename(columns={
                    'title': 'Title', 'channel_name': 'Channel', 'views': 'Views',
                    'likes': 'Likes', 'comments': 'Comments',
                    'engagement_rate': 'Eng %', 'url': 'URL',
                })
            )
            df_trending['Eng %'] = df_trending['Eng %'].round(2)
            st.dataframe(df_trending, use_container_width=True, hide_index=True)
        else:
            st.info("No trending Shorts found.")

    # ── Export ───────────────────────────────────────────────────────────────────
    with tab_export:
        st.subheader("Download CSVs")
        st.caption("All downloads reflect the current query/filter selection.")

        exports = [
            ("Tags — Shorts",      combined['shorts_tags'],     'tag',         'tags_shorts.csv'),
            ("Tags — Full Videos", combined['full_tags'],       'tag',         'tags_full.csv'),
            ("Hashtags — Shorts",  combined['shorts_hashtags'], 'hashtag',     'hashtags_shorts.csv'),
            ("Hashtags — Full",    combined['full_hashtags'],   'hashtag',     'hashtags_full.csv'),
            ("Channel Tags",       combined['channel_tags'],    'channel_tag', 'channel_tags.csv'),
        ]

        cols = st.columns(3)
        for i, (label, counter, col_name, filename) in enumerate(exports):
            df = pd.DataFrame(counter.most_common(), columns=[col_name, 'count'])
            cols[i % 3].download_button(
                label=f"Download: {label}",
                data=to_csv_bytes(df),
                file_name=filename,
                mime='text/csv',
                use_container_width=True,
            )

        st.markdown("---")
        st.subheader("Download All Videos")
        if combined['all_shorts']:
            df_all_shorts = pd.DataFrame(combined['all_shorts']).drop_duplicates('url')
            st.download_button(
                "Download All Shorts Data",
                data=to_csv_bytes(df_all_shorts),
                file_name='all_shorts.csv',
                mime='text/csv',
            )
        if combined['all_full_videos']:
            df_all_full = pd.DataFrame(combined['all_full_videos']).drop_duplicates('url')
            st.download_button(
                "Download All Full Videos Data",
                data=to_csv_bytes(df_all_full),
                file_name='all_full_videos.csv',
                mime='text/csv',
            )
        if trending_shorts:
            df_trending_export = pd.DataFrame(trending_shorts).drop_duplicates('url')
            st.download_button(
                "Download Trending Shorts Data",
                data=to_csv_bytes(df_trending_export),
                file_name='trending_shorts.csv',
                mime='text/csv',
            )
