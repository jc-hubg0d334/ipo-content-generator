import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

from utils import serpapi_search_news, extract_ipo_card_from_search
from services import build_generation_payload, generate_all_articles

load_dotenv()

st.set_page_config(
    page_title="港股IPO内容生成器",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

ALL_STYLES = ["conflict", "rational", "story"]

STYLE_META = {
    "conflict": {
        "label": "情绪交易派",
        "emoji": "🧨",
        "title": "市场情绪有没有打得太满？",
        "desc": "偏冲突、预期差、热度矛盾，适合更抓眼球的表达。",
    },
    "rational": {
        "label": "冷静分析派",
        "emoji": "🧊",
        "title": "拆开看，这票最该盯什么？",
        "desc": "偏结构化、可判断，适合打新笔记和理性表达。",
    },
    "story": {
        "label": "叙事观察派",
        "emoji": "🎭",
        "title": "市场到底在买它什么故事？",
        "desc": "偏趋势、周期、行业叙事，适合更有故事感的表达。",
    },
}


def get_llm_client_and_model():
    base_url = os.getenv("GPTSAPI_BASE_URL", "").strip()
    api_key = os.getenv("GPTSAPI_API_KEY", "").strip()
    model = os.getenv("GPTSAPI_MODEL", "").strip()

    if not api_key:
        raise ValueError("未读取到 GPTSAPI_API_KEY，请检查 .env 或环境变量")

    if not model:
        raise ValueError("未读取到 GPTSAPI_MODEL，请检查 .env 或环境变量")

    client = OpenAI(
        api_key=api_key,
        base_url=base_url if base_url else None,
    )
    return client, model


st.markdown(
    """
    <style>
        .block-container {
            max-width: 1220px;
            padding-top: 1.5rem;
            padding-bottom: 4rem;
        }

        .app-shell {
            background: linear-gradient(180deg, #f8fafc 0%, #ffffff 28%);
        }

        .hero {
            background:
                radial-gradient(circle at top right, rgba(59,130,246,0.10), transparent 28%),
                radial-gradient(circle at left top, rgba(99,102,241,0.08), transparent 24%),
                linear-gradient(135deg, #0f172a 0%, #111827 55%, #172554 100%);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 28px;
            padding: 2.2rem 2rem 2rem 2rem;
            color: white;
            box-shadow: 0 18px 50px rgba(15, 23, 42, 0.18);
            margin-bottom: 1.2rem;
        }

        .hero-top {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            font-size: 0.82rem;
            color: rgba(255,255,255,0.82);
            background: rgba(255,255,255,0.08);
            padding: 0.38rem 0.72rem;
            border-radius: 999px;
            margin-bottom: 1rem;
        }

        .hero-title {
            font-size: 2.35rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            line-height: 1.15;
            margin-bottom: 0.65rem;
        }

        .hero-subtitle {
            font-size: 1rem;
            color: rgba(255,255,255,0.80);
            line-height: 1.75;
            max-width: 820px;
        }

        .hero-metrics {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.8rem;
            margin-top: 1.4rem;
        }

        .hero-metric {
            background: rgba(255,255,255,0.07);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 18px;
            padding: 0.95rem 1rem;
            backdrop-filter: blur(6px);
        }

        .hero-metric-label {
            font-size: 0.8rem;
            color: rgba(255,255,255,0.65);
            margin-bottom: 0.25rem;
        }

        .hero-metric-value {
            font-size: 1rem;
            font-weight: 700;
            color: white;
        }

        .panel {
            background: rgba(255,255,255,0.88);
            border: 1px solid #e5e7eb;
            border-radius: 24px;
            padding: 1.2rem;
            box-shadow: 0 12px 35px rgba(15, 23, 42, 0.06);
            backdrop-filter: blur(8px);
            margin-bottom: 1rem;
        }

        .panel-title {
            font-size: 1rem;
            font-weight: 700;
            color: #111827;
            margin-bottom: 0.2rem;
        }

        .panel-subtitle {
            font-size: 0.92rem;
            color: #6b7280;
            margin-bottom: 0.9rem;
        }

        .section-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: #111827;
            margin: 1rem 0 0.75rem 0;
        }

        .glass-card {
            background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
            border: 1px solid #e5e7eb;
            border-radius: 22px;
            padding: 1.1rem 1.15rem;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
            height: 100%;
        }

        .mini-label {
            font-size: 0.78rem;
            color: #6b7280;
            margin-bottom: 0.2rem;
        }

        .mini-value {
            font-size: 1rem;
            font-weight: 700;
            color: #111827;
            line-height: 1.35;
        }

        .result-wrap {
            background: linear-gradient(180deg, #ffffff 0%, #fcfcfd 100%);
            border: 1px solid #e5e7eb;
            border-radius: 24px;
            padding: 1.25rem;
            box-shadow: 0 14px 35px rgba(15, 23, 42, 0.07);
        }

        .result-head {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 1rem;
        }

        .result-title {
            font-size: 1.18rem;
            font-weight: 800;
            color: #111827;
            margin-bottom: 0.2rem;
        }

        .result-desc {
            font-size: 0.93rem;
            color: #6b7280;
            line-height: 1.6;
        }

        .pill {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.38rem 0.72rem;
            border-radius: 999px;
            background: #f3f4f6;
            color: #374151;
            font-size: 0.82rem;
            font-weight: 600;
            white-space: nowrap;
        }

        .content-box {
            border-top: 1px solid #f0f2f5;
            padding-top: 1rem;
        }

        .footer-tip {
            color: #6b7280;
            font-size: 0.88rem;
            margin-top: 0.55rem;
        }

        div[data-testid="stTextInput"] input {
            border-radius: 16px;
            border: 1px solid #dbe1ea;
            min-height: 48px;
            font-size: 0.98rem;
        }

        div[data-testid="stMultiSelect"] > div {
            border-radius: 16px;
            border: 1px solid #dbe1ea;
            min-height: 48px;
        }

        div[data-testid="stButton"] button {
            border-radius: 16px;
            min-height: 48px;
            font-weight: 700;
            width: 100%;
            box-shadow: 0 8px 20px rgba(37, 99, 235, 0.18);
        }

        div[data-testid="stDownloadButton"] button {
            border-radius: 14px;
            font-weight: 700;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.4rem;
            margin-bottom: 0.8rem;
        }

        .stTabs [data-baseweb="tab"] {
            height: 44px;
            border-radius: 14px;
            padding-left: 1rem;
            padding-right: 1rem;
            background: #f8fafc;
        }

        .stTabs [aria-selected="true"] {
            background: #111827 !important;
            color: white !important;
        }

        @media (max-width: 900px) {
            .hero-title {
                font-size: 1.9rem;
            }

            .hero-metrics {
                grid-template-columns: 1fr;
            }

            .result-head {
                flex-direction: column;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="app-shell">', unsafe_allow_html=True)

# Hero
st.markdown(
    """
    <div class="hero">
        <div class="hero-top">📈 港股IPO内容生成引擎</div>
        <div class="hero-title">把 IPO 公开信息，生成更像真人写的内容表达</div>
        <div class="hero-subtitle">
            输入公司名称，系统会自动搜索公开资料、提取 IPO 关键信号，并生成不同视角的内容版本。
            适合做打新内容试写、账号素材生产、投研表达和 Demo 展示。
        </div>
        <div class="hero-metrics">
            <div class="hero-metric">
                <div class="hero-metric-label">处理链路</div>
                <div class="hero-metric-value">搜索 → 提取 → 多风格生成</div>
            </div>
            <div class="hero-metric">
                <div class="hero-metric-label">输出形式</div>
                <div class="hero-metric-value">小红书风格内容草稿</div>
            </div>
            <div class="hero-metric">
                <div class="hero-metric-label">当前定位</div>
                <div class="hero-metric-value">产品化 Demo / 试用版本</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Control panel
st.markdown(
    """
    <div class="panel">
        <div class="panel-title">生成控制台</div>
        <div class="panel-subtitle">输入公司名，选择希望输出的表达视角，然后生成内容。</div>
    """,
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns([1.6, 1.15, 0.75])

with c1:
    company_name = st.text_input(
        "公司名称",
        value="群核科技",
        placeholder="例如：蜜雪集团、地平线机器人、群核科技",
    )

with c2:
    styles = st.multiselect(
        "文章风格",
        options=ALL_STYLES,
        default=ALL_STYLES,
        format_func=lambda x: f'{STYLE_META[x]["emoji"]} {STYLE_META[x]["label"]}',
    )

with c3:
    st.markdown("<div style='height: 1.85rem'></div>", unsafe_allow_html=True)
    run_btn = st.button("生成内容", type="primary")

st.markdown(
    '<div class="footer-tip">建议先保留三种风格，方便直接横向对比输出差异。</div></div>',
    unsafe_allow_html=True,
)

# Preview cards before generation
if not run_btn:
    p1, p2, p3 = st.columns(3)
    preview_items = [
        ("内容输入", "公司名称 + 风格选择"),
        ("生成结果", "三种视角的内容版本"),
        ("展示场景", "Demo、作品集、试写验证"),
    ]
    for col, item in zip([p1, p2, p3], preview_items):
        with col:
            st.markdown(
                f"""
                <div class="glass-card">
                    <div class="mini-label">{item[0]}</div>
                    <div class="mini-value">{item[1]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

if run_btn:
    if not company_name.strip():
        st.warning("请输入公司名称")
        st.stop()

    if not styles:
        st.warning("请至少选择一种风格")
        st.stop()

    try:
        with st.spinner("正在搜索资料并生成内容，请稍候..."):
            client, model = get_llm_client_and_model()
            company = company_name.strip()

            search_results = serpapi_search_news(company, num=10)
            ipo_card = extract_ipo_card_from_search(company, search_results)
            payload = build_generation_payload(ipo_card)
            context_packs = payload["context_packs"]

            results = generate_all_articles(
                client=client,
                model=model,
                context_pack=context_packs,
                styles=styles,
            )

        st.success("生成完成")

        # Summary strip
        st.markdown('<div class="section-title">关键信息摘要</div>', unsafe_allow_html=True)
        s1, s2, s3, s4 = st.columns(4)

        summary_data = [
            ("公司", ipo_card.get("company_name") or company),
            ("上市时间", ipo_card.get("listing_date") or "待补充"),
            ("入场费", ipo_card.get("entry_fee") or "待补充"),
            ("募资规模", ipo_card.get("fundraising_amount") or "待补充"),
        ]

        for col, (label, value) in zip([s1, s2, s3, s4], summary_data):
            with col:
                st.markdown(
                    f"""
                    <div class="glass-card">
                        <div class="mini-label">{label}</div>
                        <div class="mini-value">{value}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown('<div class="section-title">生成结果</div>', unsafe_allow_html=True)

        tab_labels = [f'{STYLE_META[s]["emoji"]} {STYLE_META[s]["label"]}' for s in styles]
        tabs = st.tabs(tab_labels)

        for tab, style in zip(tabs, styles):
            with tab:
                meta = STYLE_META[style]
                content = results.get(style, "")

                st.markdown(
                    f"""
                    <div class="result-wrap">
                        <div class="result-head">
                            <div>
                                <div class="result-title">{meta["title"]}</div>
                                <div class="result-desc">{meta["desc"]}</div>
                            </div>
                            <div class="pill">{meta["emoji"]} {meta["label"]}</div>
                        </div>
                        <div class="content-box">
                    """,
                    unsafe_allow_html=True,
                )

                if content:
                    st.markdown(content)
                    st.markdown("<div style='height: 0.65rem'></div>", unsafe_allow_html=True)
                    st.download_button(
                        label=f"下载 {meta['label']} Markdown",
                        data=content,
                        file_name=f"{company}_{style}.md",
                        mime="text/markdown",
                        key=f"download_{style}",
                    )
                else:
                    st.error(f"{style} 没有生成内容")

                st.markdown("</div></div>", unsafe_allow_html=True)

        st.markdown('<div class="section-title">调试信息</div>', unsafe_allow_html=True)
        with st.expander("查看搜索结果、IPO Card、校验信息和原始结果", expanded=False):
            st.markdown("#### 搜索结果")
            st.json(search_results)

            st.markdown("#### 提取后的 IPO Card")
            st.json(ipo_card)

            st.markdown("#### 数据校验")
            st.json(payload["validation"])

            st.markdown("#### Context Packs")
            st.json(context_packs)

            st.markdown("#### 原始结果字典")
            st.json(results)

    except Exception as e:
        st.error("生成失败")
        st.exception(e)

st.markdown("</div>", unsafe_allow_html=True)
