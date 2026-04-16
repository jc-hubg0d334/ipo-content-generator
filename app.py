# app.py
# -*- coding: utf-8 -*-

import os
import re
import json
import requests
from typing import Any, Dict, List, Tuple

from bs4 import BeautifulSoup
import fitz  # pymupdf

from prompts import (
    EXTRACT_JSON_PROMPT,
    GENERATE_XHS_PROMPT,
    EVAL_PROMPT,
    REWRITE_PROMPT,
)

# ======================
# Config
# ======================
GPTSAPI_BASE = "https://api.gptsapi.net/v1"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari"

DEFAULT_MODEL = os.getenv("GPTSAPI_MODEL", "claude-haiku-4-5-20251001")
EXTRACT_MODEL = os.getenv("GPTSAPI_EXTRACT_MODEL", DEFAULT_MODEL)
EVAL_MODEL = os.getenv("GPTSAPI_EVAL_MODEL", DEFAULT_MODEL)
WRITE_MODEL = os.getenv("GPTSAPI_WRITE_MODEL", DEFAULT_MODEL)

DEBUG = os.getenv("DEBUG", "1").strip() == "1"   # 默认开 debug，方便你定位问题
USE_SERPAPI = os.getenv("USE_SERPAPI", "0").strip() == "1"  # 默认先跑手工闭环


# ======================
# LLM helpers
# ======================
def strip_code_fences(text: str) -> str:
    """
    Remove markdown fences like:
    ```json
    {...}
    ```
    """
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
        t = t.strip()
    return t


def call_llm(prompt: str, model: str, temperature: float = 0.2, timeout: int = 120) -> str:
    key = os.getenv("GPTSAPI_KEY")
    if not key:
        raise RuntimeError("Missing GPTSAPI_KEY env var")

    url = f"{GPTSAPI_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    # 发生拥堵时自动降级模型（你 models 列表里有这些；不一定全有就会跳过）
    fallback_models = [
        model,
        os.getenv("GPTSAPI_FALLBACK_1", "claude-haiku-4-5-20251001"),
        os.getenv("GPTSAPI_FALLBACK_2", "claude-opus-4-6"),
        os.getenv("GPTSAPI_FALLBACK_3", "claude-opus-4-5-20251101"),
    ]

    # 去重
    fallback_models = list(dict.fromkeys([m for m in fallback_models if m]))

    last_err = None

    for m in fallback_models:
        # 每个模型最多重试3次
        for attempt in range(3):
            payload = {
                "model": m,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
            }

            try:
                r = requests.post(url, headers=headers, json=payload, timeout=timeout)
            except Exception as e:
                last_err = f"Request exception: {e}"
                continue

            if r.status_code == 200:
                data = r.json()
                content = data["choices"][0]["message"]["content"]
                return strip_code_fences(content)

            # 500/503 常见是拥堵 → 退避重试
            if r.status_code in (429, 500, 502, 503, 504):
                last_err = f"{r.status_code}: {r.text[:300]}"
                # 简单退避：1s, 2s, 4s
                import time
                time.sleep(1 * (2 ** attempt))
                continue

            # 其他错误直接抛出
            raise RuntimeError(f"LLM API Error {r.status_code}: {r.text[:800]}")

    raise RuntimeError(f"LLM failed after retries/fallbacks. Last error: {last_err}")

def strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
        t = t.strip()
    return t


def must_json(text: str) -> Any:
    t = strip_code_fences(text).strip()

    # direct parse
    try:
        return json.loads(t)
    except Exception:
        pass

    # try extract object
    m = re.search(r"\{.*\}", t, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass

    # try extract array
    m = re.search(r"\[.*\]", t, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass

    raise ValueError(f"Failed to parse JSON. Head:\n{t[:400]}")
# ======================
# SerpAPI (optional)
# ======================
def serp_search(query: str, num: int = 6) -> List[str]:
    key = os.getenv("SERPAPI_KEY")
    if not key:
        raise RuntimeError("Missing SERPAPI_KEY env var")

    params = {"engine": "google", "q": query, "api_key": key, "num": num}
    r = requests.get("https://serpapi.com/search.json", params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    urls = []
    for item in data.get("organic_results", [])[:num]:
        link = item.get("link")
        if link:
            urls.append(link)

    # dedupe
    return list(dict.fromkeys(urls))


# ======================
# Fetch HTML/PDF
# ======================
def fetch_html_text(url: str, max_chars: int = 20000) -> str:
    r = requests.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:max_chars]


def fetch_pdf_text(url: str, max_pages: int = 10, max_chars: int = 30000) -> str:
    r = requests.get(url, timeout=60, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    doc = fitz.open(stream=r.content, filetype="pdf")
    parts = []
    for i in range(min(max_pages, doc.page_count)):
        parts.append(doc.load_page(i).get_text("text"))
    text = "\n".join(parts)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:max_chars]


def fetch_any_text(url: str) -> str:
    u = url.lower()
    if u.endswith(".pdf") or "pdf" in u:
        return fetch_pdf_text(url)
    return fetch_html_text(url)


# ======================
# Build IPO card
# ======================
def build_card_from_sources(company_name: str, urls: List[str]) -> Dict[str, Any]:
    chunks = []
    ok_urls = []

    for u in urls:
        try:
            txt = fetch_any_text(u)
            if txt and len(txt) > 300:
                chunks.append(f"[SOURCE] {u}\n{txt}")
                ok_urls.append(u)
        except Exception:
            continue

    merged = "\n\n".join(chunks) if chunks else f"Company: {company_name}"
    prompt = EXTRACT_JSON_PROMPT.format(content=merged)

    raw = call_llm(prompt, model=EXTRACT_MODEL, temperature=0.2)
    if DEBUG:
        print("\n[RAW EXTRACT]\n", raw[:800], "\n")

    card = must_json(raw)
    card.setdefault("sources", ok_urls or urls or [])
    if not card.get("company_name"):
        card["company_name"] = company_name
    return card


def build_manual_card(company: str) -> Dict[str, Any]:
    # 让“空卡片”也能稳定生成爆款稿：给最少的亮点/风险/市场语境
    return {
        "company_name": company,
        "ticker": None,
        "offer_period": {"start": None, "end": None},
        "price_range_hkd": [None, None],
        "fundraising_hkd": None,
        "industry": "（待确认：请按抓取结果补充）",
        "cornerstone": {"exists": None, "ratio": None},
        "use_of_proceeds": [],
        "financials": {"revenue": None, "revenue_growth": None, "gross_margin": None, "net_profit": None},
        "highlights": [
            "先看市场情绪：港股新股最近更偏交易化",
            "先拆结构：招股价区间/公开发售比例/基石强弱决定首日波动",
            "先定策略：不猜长期，只做赔率"
        ],
        "risks": [
            "信息不完整，存在误判风险（需等招股书）",
            "破发风险与市场情绪风险",
            "估值过高/行业竞争/盈利不确定性"
        ],
        "market_context": "近期港股新股波动更大，情绪交易明显，不能闭眼冲。",
        "sources": ["manual"]
    }


# ======================
# Generate / Evaluate / Rewrite
# ======================
def generate_one(card: Dict[str, Any], style: str) -> Dict[str, Any]:
    p = GENERATE_XHS_PROMPT.format(
        card_json=json.dumps(card, ensure_ascii=False),
        style=style
    )
    raw = call_llm(p, model=WRITE_MODEL, temperature=0.4)  # 稳一点
    if DEBUG:
        print(f"\n[RAW GENERATE {style}]\n{raw[:900]}\n")
    return must_json(raw)


def evaluate(card: Dict[str, Any], article: Dict[str, Any]) -> Dict[str, Any]:
    p = EVAL_PROMPT.format(
        card_json=json.dumps(card, ensure_ascii=False),
        article_json=json.dumps(article, ensure_ascii=False),
    )
    raw = call_llm(p, model=EVAL_MODEL, temperature=0.2)
    if DEBUG:
        print(f"\n[RAW EVAL]\n{raw[:900]}\n")
    return must_json(raw)


def rewrite(card: Dict[str, Any], article: Dict[str, Any], rewrite_instruction: str) -> Dict[str, Any]:
    p = REWRITE_PROMPT.format(
        rewrite_instruction=rewrite_instruction,
        card_json=json.dumps(card, ensure_ascii=False),
        article_json=json.dumps(article, ensure_ascii=False),
    )
    raw = call_llm(p, model=WRITE_MODEL, temperature=0.4)
    if DEBUG:
        print(f"\n[RAW REWRITE]\n{raw[:900]}\n")
    return must_json(raw)


def generate_best(card: Dict[str, Any], threshold: int = 85, max_rewrite: int = 2) -> Tuple[int, Dict[str, Any], Dict[str, Any]]:
    styles = ["conflict", "rational", "story"]
    candidates = []

    for st in styles:
        art = generate_one(card, st)
        rep = evaluate(card, art)
        score = int(rep.get("score", 0))
        candidates.append((score, art, rep))

    score, best, report = max(candidates, key=lambda x: x[0])

    attempt = 0
    while score < threshold and attempt < max_rewrite:
        instruction = report.get(
            "rewrite_instruction",
            "把前三行改成更强冲突钩子；整体更短句更有节奏；减少说明书表达；保留关键信息；结尾策略更明确并加强互动引导。"
        )
        best = rewrite(card, best, instruction)
        report = evaluate(card, best)
        score = int(report.get("score", 0))
        attempt += 1

    return score, best, report


# ======================
# Main
# ======================
def main():
    print("=== IPO Bot (XHS爆款流水线) ===")
    company = input("输入公司名（例如：XX科技）：").strip()
    if not company:
        print("公司名不能为空")
        return

    if USE_SERPAPI:
        if not os.getenv("SERPAPI_KEY"):
            print("你没设置 SERPAPI_KEY，自动切换为手工卡片模式。")
            card = build_manual_card(company)
        else:
            query = f"{company} 港股 招股 价格区间 招股时间 基石 募资"
            urls = serp_search(query, num=6)
            print("\n[Search URLs]")
            for u in urls:
                print("-", u)
            card = build_card_from_sources(company, urls)
    else:
        card = build_manual_card(company)

    print("\n[IPO Card]")
    print(json.dumps(card, ensure_ascii=False, indent=2))

    score, best, report = generate_best(card, threshold=85, max_rewrite=2)

    print("\n=== RESULT ===")
    print("SCORE:", score)
    print("\nTITLE:\n", best.get("title", ""))
    print("\nBODY:\n", best.get("body", ""))
    tags = best.get("tags", [])
    print("\nTAGS:\n", " ".join(tags) if isinstance(tags, list) else str(tags))

    if DEBUG:
        print("\n[EVAL REPORT]")
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
