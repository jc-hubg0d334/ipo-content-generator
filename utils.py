import json
import os
import re
import requests
from dotenv import load_dotenv
from pathlib import Path


# 强制从当前项目目录读取 .env
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=True)

GPTSAPI_BASE_URL = os.getenv("GPTSAPI_BASE_URL", "").strip().rstrip("/")
GPTSAPI_API_KEY = os.getenv("GPTSAPI_API_KEY", "").strip()
GPTSAPI_MODEL = os.getenv("GPTSAPI_MODEL", "").strip()

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "").strip()

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "").strip()
PERPLEXITY_MODEL = os.getenv("PERPLEXITY_MODEL", "sonar-pro").strip()

print("[DEBUG] ENV_PATH =", ENV_PATH)
print("[DEBUG] GPTSAPI_BASE_URL =", GPTSAPI_BASE_URL)
print("[DEBUG] GPTSAPI_API_KEY exists =", bool(GPTSAPI_API_KEY))
print("[DEBUG] GPTSAPI_MODEL =", GPTSAPI_MODEL)

def safe_json_loads(raw: str):
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}

    text = raw.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    raise ValueError(f"无法解析 JSON: {raw[:500]}")


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.5) -> str:
    if not GPTSAPI_BASE_URL or not GPTSAPI_API_KEY or not GPTSAPI_MODEL:
        raise RuntimeError(
            f"缺少 GPTSAPI_BASE_URL / GPTSAPI_API_KEY / GPTSAPI_MODEL。"
            f" 当前读取结果: BASE_URL={GPTSAPI_BASE_URL}, "
            f"API_KEY存在={bool(GPTSAPI_API_KEY)}, MODEL={GPTSAPI_MODEL}"
        )

    url = f"{GPTSAPI_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {GPTSAPI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GPTSAPI_MODEL,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]

def serpapi_search_news(company_name: str, num: int = 10) -> list[dict]:
    if not SERPAPI_API_KEY:
        print("[SerpAPI] Missing API key")
        return []

    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_news",
        "q": f'{company_name} (香港IPO OR 港股IPO OR 招股 OR 上市聆讯 OR 递表 OR 配售)',
        "api_key": SERPAPI_API_KEY,
        "hl": "zh-cn",
        "gl": "hk",
        "num": num,
    }

    try:
        resp = requests.get(url, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("news_results", []):
            results.append({
                "title": item.get("title"),
                "source": item.get("source"),
                "date": item.get("date"),
                "link": item.get("link"),
                "snippet": item.get("snippet"),
            })
        return results
    except Exception as e:
        print(f"[SerpAPI] search failed: {e}")
        return []


def call_perplexity_search(company_name: str) -> str | None:
    """
    只做搜索补充，不直接参与文章生成。
    """
    if not PERPLEXITY_API_KEY:
        return None

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
    }
    prompt = f"""
Find public Hong Kong IPO-related information about {company_name}.

Only summarize objective public facts if available:
- fundraising amount
- subscription period
- listing date
- stock code
- entry fee
- sponsors
- cornerstone investors

If unclear, say null.
Do not speculate.
""".strip()

    payload = {
        "model": PERPLEXITY_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": "You are a factual IPO search assistant."},
            {"role": "user", "content": prompt},
        ],
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=90)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[Perplexity] failed: {e}")
        return None

def build_ipo_extract_prompt(company_name: str, search_results: list[dict]) -> str:
    news_text = []

    for i, item in enumerate(search_results, start=1):
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        source = item.get("source", "")
        date = item.get("date", "")
        link = item.get("link", "")

        block = f"""
[{i}]
标题: {title}
摘要: {snippet}
来源: {source}
日期: {date}
链接: {link}
""".strip()
        news_text.append(block)

    joined_text = "\n\n".join(news_text)

    return f"""
你是港股IPO信息提取助手。

请只根据下面搜索结果中已经明确出现的信息，提取这家公司的IPO核心数据。
不要猜，不要补全，不要用常识脑补。
没有提到就留空字符串或空数组。

输出必须是合法 JSON，不要加解释，不要加 Markdown。

公司名称：{company_name}

搜索结果：
{joined_text}

输出格式：
{{
  "company": "{company_name}",
  "ticker": "",
  "fundraising": "",
  "ipo_date": "",
  "subscription_period": "",
  "entry_fee": "",
  "industry": "",
  "oversubscription": "",
  "margin_amount": "",
  "offer_price": "",
  "market_value": "",
  "cornerstone_investors": "",
  "sponsor": "",
  "tags": [],
  "highlights": [],
  "risks": [],
  "raw_points": []
}}
""".strip()

def extract_ipo_card_from_search(company_name: str, search_results: list[dict]) -> dict:
    prompt = build_ipo_extract_prompt(company_name, search_results)
    raw = call_llm(
        system_prompt="你是一个只做客观提取的港股IPO信息整理助手。",
        user_prompt=prompt,
        temperature=0.2,
    )
    return safe_json_loads(raw)
