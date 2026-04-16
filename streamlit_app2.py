# streamlit_app2.py

import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

from utils import serpapi_search_news, extract_ipo_card_from_search
from services import build_generation_payload, generate_all_articles

load_dotenv()

st.set_page_config(page_title="IPO Bot", layout="wide")

st.title("🚀 IPO Bot")
st.caption("AI港股打新内容引擎")

ALL_STYLES = ["conflict", "rational", "story"]


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


with st.container():
    company_name = st.text_input("请输入公司名称", value="群核科技")

    styles = st.multiselect(
        "选择文章风格",
        ALL_STYLES,
        default=ALL_STYLES
    )

    run_btn = st.button("开始生成", type="primary")


if run_btn:
    if not company_name.strip():
        st.warning("请输入公司名称")
        st.stop()

    if not styles:
        st.warning("请至少选择一种风格")
        st.stop()

    try:
        with st.spinner("正在生成内容，请稍候..."):
            client, model = get_llm_client_and_model()

            company = company_name.strip()

            # 1. 搜索 IPO 相关信息
            search_results = serpapi_search_news(company, num=10)

            # 2. 从搜索结果提取 IPO card
            ipo_card = extract_ipo_card_from_search(company, search_results)

            # 3. 构建上下文
            payload = build_generation_payload(ipo_card)
            context_pack = payload["context_pack"]

            # 4. 生成多风格文章
            results = generate_all_articles(
                client=client,
                model=model,
                context_pack=context_pack,
                styles=styles,
            )

        st.success("生成完成")

        # 调试信息：方便看搜索和抽取是否正常
        st.subheader("📰 搜索结果")
        st.json(search_results)

        st.subheader("🧾 提取后的 IPO Card")
        st.json(ipo_card)

        st.subheader("🔍 数据校验")
        st.json(payload["validation"])

        st.subheader("🧾 Context Pack")
        st.code(context_pack)

        st.subheader("✍️ 全部风格结果")
        tabs = st.tabs(styles)

        for tab, style in zip(tabs, styles):
            with tab:
                content = results.get(style, "")
                if content:
                    st.write(content)

                    st.download_button(
                        label=f"下载 {style} Markdown",
                        data=content,
                        file_name=f"{company}_{style}.md",
                        mime="text/markdown",
                        key=f"download_{style}",
                    )
                else:
                    st.error(f"{style} 没有生成内容")

        st.subheader("🧪 原始结果字典")
        st.json(results)

    except Exception as e:
        st.error("生成失败")
        st.exception(e)
