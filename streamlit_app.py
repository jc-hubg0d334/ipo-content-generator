import json
import streamlit as st
import streamlit.components.v1 as components
from services import generate_full_report

st.set_page_config(
    page_title="IPO Bot",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- 样式 ----------
CUSTOM_CSS = """
<style>
.main > div {
    padding-top: 1.2rem;
}
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1200px;
}
.hero-card {
    padding: 22px 24px;
    border: 1px solid #EAEAEA;
    border-radius: 18px;
    background: linear-gradient(180deg, #FFFFFF 0%, #FAFAFA 100%);
    margin-bottom: 18px;
}
.small-muted {
    color: #666;
    font-size: 14px;
}
.metric-card {
    padding: 16px;
    border: 1px solid #ECECEC;
    border-radius: 16px;
    background: #FFF;
    text-align: center;
}
.section-card {
    padding: 18px;
    border: 1px solid #ECECEC;
    border-radius: 16px;
    background: #FFF;
}
.article-box {
    padding: 18px;
    border: 1px solid #ECECEC;
    border-radius: 16px;
    background: #FFF;
    line-height: 1.75;
    font-size: 15px;
}
.tag {
    display: inline-block;
    padding: 4px 10px;
    margin: 0 8px 8px 0;
    border-radius: 999px;
    font-size: 12px;
    background: #F3F4F6;
    color: #333;
}
hr {
    margin-top: 28px !important;
    margin-bottom: 28px !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ---------- 工具函数 ----------
def score_emoji(score: int) -> str:
    if score >= 85:
        return "🟢"
    if score >= 75:
        return "🟡"
    return "🔴"


def make_markdown_report(report: dict) -> str:
    best = report["best_article"]
    ipo_card = report["ipo_card"]
    articles = report["articles"]

    parts = [
        f"# IPO Bot 生成结果",
        f"## 公司名称\n{report['company_name']}",
        f"## 推荐风格\n{best.style}",
        f"## 推荐标题\n{best.title}",
        f"## 推荐正文\n{best.content}",
    ]

    if best.score:
        parts.append(f"## 最终评分\n{best.score.total_score}")

    parts.append("## IPO Card")
    parts.append("```json")
    parts.append(json.dumps(ipo_card.model_dump(), ensure_ascii=False, indent=2))
    parts.append("```")

    parts.append("## 多风格结果")
    for a in articles:
        parts.append(f"### {a.style}")
        parts.append(f"**标题：** {a.title}")
        parts.append(a.content)
        if a.score:
            parts.append(f"**评分：** {a.score.total_score}")

    return "\n\n".join(parts)


def render_copy_button(text: str, key: str, label: str = "复制内容"):
    text_js = json.dumps(text, ensure_ascii=False)
    button_id = f"copy-btn-{key}"
    msg_id = f"copy-msg-{key}"

    html_code = f"""
    <div style="margin: 6px 0 12px 0;">
      <button id="{button_id}" style="
          background:#111827;
          color:white;
          border:none;
          border-radius:10px;
          padding:8px 14px;
          cursor:pointer;
          font-size:14px;">
          {label}
      </button>
      <span id="{msg_id}" style="margin-left:10px;color:#16a34a;font-size:13px;"></span>
    </div>

    <script>
      const btn = document.getElementById("{button_id}");
      const msg = document.getElementById("{msg_id}");
      btn.onclick = async function() {{
        try {{
          await navigator.clipboard.writeText({text_js});
          msg.innerText = "已复制";
          setTimeout(() => msg.innerText = "", 2000);
        }} catch (e) {{
          msg.innerText = "复制失败";
          setTimeout(() => msg.innerText = "", 2000);
        }}
      }}
    </script>
    """
    components.html(html_code, height=50)


def render_header():
    st.markdown(
        """
        <div class="hero-card">
            <div class="small-muted">港股打新内容生成系统</div>
            <h1 style="margin:8px 0 10px 0;">📈 IPO Bot</h1>
            <div style="font-size:15px;color:#444;">
                输入公司名称 → 抽取 IPO 信息 → 生成多风格小红书内容 → 自动评分 → 选出最佳版本
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar():
    st.sidebar.title("控制台")

    company = st.sidebar.text_input(
        "公司名称",
        placeholder="例如：翼菲机器人 / 地平线机器人 / 老铺黄金"
    )

    styles = st.sidebar.multiselect(
        "选择风格",
        options=["conflict", "rational", "story"],
        default=["conflict", "rational", "story"]
    )

    rounds = st.sidebar.slider("优化轮数", 1, 3, 2)

    st.sidebar.markdown("---")
    st.sidebar.caption("建议先用 1-2 轮，速度更稳")
    run = st.sidebar.button("开始生成", use_container_width=True)

    return company, styles, rounds, run


def render_best_article(best):
    score = best.score.total_score if best.score else 0

    st.markdown("## 🏆 最佳版本")
    st.markdown(
        f"""
        <div class="hero-card">
            <div class="small-muted">推荐风格：{best.style}</div>
            <div style="font-size:30px;font-weight:700;line-height:1.35;margin:10px 0 8px 0;">
                {best.title}
            </div>
            <div style="font-size:16px;">
                评分：{score_emoji(score)} <b>{score}</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns([5, 1])
    with col_a:
        render_copy_button(best.title, "best-title", "复制标题")
    with col_b:
        st.write("")

    render_copy_button(best.content, "best-content", "复制正文")

    st.markdown(f'<div class="article-box">{best.content.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)

    if best.score:
        with st.expander("查看评分详情"):
            st.json(best.score.model_dump())


def render_style_tabs(articles):
    st.markdown("## ✍️ 多风格版本")

    articles_sorted = sorted(
        articles,
        key=lambda x: x.score.total_score if x.score else 0,
        reverse=True
    )

    tabs = st.tabs([
        f"{a.style}｜{a.score.total_score if a.score else 0}"
        for a in articles_sorted
    ])

    for idx, (tab, article) in enumerate(zip(tabs, articles_sorted)):
        with tab:
            st.markdown(
                f"""
                <div class="section-card">
                    <div class="small-muted">风格：{article.style}</div>
                    <div style="font-size:24px;font-weight:700;line-height:1.4;margin:8px 0 14px 0;">
                        {article.title}
                    </div>
                    <div style="font-size:15px;margin-bottom:8px;">
                        评分：{score_emoji(article.score.total_score if article.score else 0)}
                        <b>{article.score.total_score if article.score else 0}</b>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            c1, c2 = st.columns(2)
            with c1:
                render_copy_button(article.title, f"title-{idx}", "复制标题")
            with c2:
                render_copy_button(article.content, f"content-{idx}", "复制正文")

            st.markdown(
                f'<div class="article-box">{article.content.replace(chr(10), "<br>")}</div>',
                unsafe_allow_html=True
            )

            if article.score:
                with st.expander("查看该版本评分详情"):
                    st.json(article.score.model_dump())


def render_ipo_card_and_sources(ipo_card, search_results):
    st.markdown("## 🧾 IPO 数据与来源")

    left, right = st.columns(2)

    with left:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("IPO Card")
        st.json(ipo_card.model_dump())
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("搜索结果")
        if search_results:
            for i, item in enumerate(search_results, start=1):
                title = item.get("title", "")
                link = item.get("link", "")
                source = item.get("source", "")
                date = item.get("date", "")
                snippet = item.get("snippet", "")

                st.markdown(
                    f"""
                    **{i}. [{title}]({link})**  
                    <span class="small-muted">来源：{source} ｜ 日期：{date}</span>  
                    {snippet}
                    """,
                    unsafe_allow_html=True
                )
                st.markdown("---")
        else:
            st.info("当前未展示搜索结果。")
        st.markdown("</div>", unsafe_allow_html=True)


# ---------- 主页面 ----------
def main():
    render_header()
    company, styles, rounds, run = render_sidebar()

    if "report" not in st.session_state:
        st.session_state.report = None

    top1, top2, top3 = st.columns(3)
    with top1:
        st.markdown('<div class="metric-card"><div class="small-muted">状态</div><div style="font-size:24px;font-weight:700;">Ready</div></div>', unsafe_allow_html=True)
    with top2:
        st.markdown('<div class="metric-card"><div class="small-muted">平台</div><div style="font-size:24px;font-weight:700;">Streamlit</div></div>', unsafe_allow_html=True)
    with top3:
        st.markdown('<div class="metric-card"><div class="small-muted">输出</div><div style="font-size:24px;font-weight:700;">XHS 内容</div></div>', unsafe_allow_html=True)

    st.markdown("")

    if run:
        if not company.strip():
            st.warning("请输入公司名称")
            st.stop()

        if not styles:
            st.warning("请至少选择一种风格")
            st.stop()

        try:
            with st.spinner("系统正在生成内容，请稍候..."):
                report = generate_full_report(
                    company_name=company.strip(),
                    styles=styles,
                    rounds=rounds
                )
                st.session_state.report = report

            st.success("生成完成")

        except Exception as e:
            st.error(str(e))
            st.stop()

    if st.session_state.report:
        report = st.session_state.report
        best = report["best_article"]
        articles = report["articles"]
        ipo_card = report["ipo_card"]
        search_results = report["search_results"]

        markdown_text = make_markdown_report(report)

        bar1, bar2, bar3 = st.columns([1, 1, 4])
        with bar1:
            st.download_button(
                label="下载 Markdown",
                data=markdown_text,
                file_name=f"{report['company_name']}_ipo_bot.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with bar2:
            render_copy_button(markdown_text, "full-report", "复制全文")

        st.markdown("---")
        render_best_article(best)

        st.markdown("---")
        render_style_tabs(articles)

        st.markdown("---")
        render_ipo_card_and_sources(ipo_card, search_results)


if __name__ == "__main__":
    main()
