# services.py

from typing import Dict, List, Any, Union

from prompts import (
    get_system_prompt,
    get_user_prompt,
    build_rewrite_system_prompt,
    build_rewrite_user_prompt,
)

ALL_STYLES = ["conflict", "rational", "story"]

# =========================
# Behavior switches
# =========================
# 默认先关闭所有“会洗风格”的步骤
ENABLE_REWRITE = False
ENABLE_LIGHT_CLEANUP = False
ENABLE_NORMALIZE_FINANCE_TERMS = False
ENABLE_DIVERSIFY_OPENING = False


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def safe_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [safe_str(v) for v in value if safe_str(v)]
    if isinstance(value, str):
        value = value.strip()
        return [value] if value else []
    return [safe_str(value)] if safe_str(value) else []


def normalize_finance_terms(text: str) -> str:
    """
    现在只建议用于极少数明显不自然的金融表述修复。
    默认关闭，不主动替换有风格的口语词。
    """
    if not text:
        return ""

    replacements = {
        "最终定格在": "最终定在",
        "最后定格在": "最后定在",
        "定格在": "定在",
        "最终定格": "最终定价",
        "最后定格": "最后定价",
        "发行定格": "发行定价",
        "价格定格": "价格定在",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text.strip()


def cleanup_ai_tone_light(text: str) -> str:
    """
    轻清洗版本：
    - 只删除极明显的AI套话
    - 不改句式
    - 不改口语
    - 不改情绪词
    """
    if not text:
        return ""

    bad_phrases = [
        "综合来看",
        "总体而言",
        "毋庸置疑",
        "从某种意义上说",
        "可以预见的是",
        "值得重点关注",
    ]

    for phrase in bad_phrases:
        text = text.replace(phrase, "")

    text = text.replace("。。", "。")
    text = text.replace("，，", "，")
    text = text.replace("\n\n\n", "\n\n")

    return text.strip()


def diversify_opening(text: str, style: str) -> str:
    """
    默认关闭。
    这个函数本质上会改语气，不适合在你当前“保素材味”阶段启用。
    """
    if not text:
        return ""

    replacements = {
        "conflict": [
            ("这只票最扎眼的地方", "真正让人上头的是"),
            ("这票热度不低", "这票热得有点过头"),
        ],
        "rational": [
            ("这票确实挺卷", "这票的数据表现不差"),
        ],
        "story": [
            ("这票热度不低", "这票是慢慢被市场盯上的"),
        ],
    }

    for old, new in replacements.get(style, []):
        text = text.replace(old, new, 1)

    return text.strip()


def _infer_market_story(ipo_card: Dict[str, Any]) -> str:
    joined_facts = " ".join(safe_list(ipo_card.get("key_facts", [])))
    text = joined_facts.lower()

    if "ai" in text:
        return "市场更容易把它放进AI相关叙事里看，资金关注点不只是基本面，还包括赛道映射。"
    if "消费" in joined_facts or "品牌" in joined_facts:
        return "市场更容易从消费品牌稀缺性和渠道扩张去理解这只票。"
    if "医药" in joined_facts or "biotech" in text:
        return "市场更容易从创新药/研发兑现角度去理解这只票。"

    return "市场更关心它到底有没有一个足够清晰、足够容易被资金理解的标签。"


def _pick_key_facts(ipo_card: Dict[str, Any], limit: int = 3) -> List[str]:
    key_facts = safe_list(ipo_card.get("key_facts", []))
    return key_facts[:limit]


def _pick_risks(ipo_card: Dict[str, Any], limit: int = 2) -> List[str]:
    risk_flags = safe_list(ipo_card.get("risk_flags", []))
    return risk_flags[:limit]


def build_context_pack(ipo_card: Dict[str, Any], style: str) -> str:
    """
    保留你原本的 style-based context 思路，
    但提示词改得更偏“怎么说”，避免只有信息没有表达约束。
    """
    facts: List[str] = []
    signals: List[str] = []
    language_rules: List[str] = []
    angle = ""

    company = safe_str(ipo_card.get("company_name"))
    fundraising = safe_str(ipo_card.get("fundraising_amount"))
    entry_fee = safe_str(ipo_card.get("entry_fee"))
    listing_date = safe_str(ipo_card.get("listing_date"))
    stock_code = safe_str(ipo_card.get("stock_code"))
    offer_price_range = safe_str(ipo_card.get("offer_price_range"))
    subscription_period = safe_str(ipo_card.get("subscription_period"))
    sponsors = safe_list(ipo_card.get("sponsors"))
    cornerstone_investors = safe_list(ipo_card.get("cornerstone_investors"))

    key_facts = _pick_key_facts(ipo_card, limit=3)
    risks = _pick_risks(ipo_card, limit=2)
    market_story = _infer_market_story(ipo_card)

    if company:
        facts.append(f"公司：{company}")
    if stock_code:
        facts.append(f"股票代码：{stock_code}")
    if fundraising:
        facts.append(f"募资规模：{fundraising}")
    if entry_fee:
        facts.append(f"入场费：{entry_fee}")
    if listing_date:
        facts.append(f"上市时间：{listing_date}")
    if offer_price_range:
        facts.append(f"招股价区间：{offer_price_range}")
    if subscription_period:
        facts.append(f"招股期：{subscription_period}")
    if sponsors:
        facts.append(f"保荐人：{'、'.join(sponsors[:3])}")
    if cornerstone_investors:
        facts.append(f"基石投资者：{'、'.join(cornerstone_investors[:5])}")

    for fact in key_facts:
        facts.append(f"事实：{fact}")

    if style == "conflict":
        signals = [
            "不要全面介绍公司，只抓一个最明显的预期差、争议点或情绪矛盾。",
            "优先写热度、募资体量、入场门槛、市场预期是否已经打满。",
            "只挑2到3个最能支撑冲突感的事实，不要把资料讲全。",
        ]
        if risks:
            signals.append(f"可用于冲突判断的风险点：{risks[0]}")
        angle = "围绕一个矛盾展开，例如：热度很高，但预期是否已经被打得太满。"
        language_rules = [
            "多用短句。",
            "可以先下判断，再解释。",
            "允许更口语化，不要写成标准分析文章。",
            "允许带一点主观感，但不要空喊。",
            "不要为了完整而把语气写平。",
        ]

    elif style == "rational":
        signals = [
            "像打新拆票笔记，不是讲故事，而是回答这票现在该怎么看。",
            "优先使用业务定位、市场地位、基石背书、交易验证点这些材料。",
            "可以写亮点和风险，但要有主次，不要平均分配篇幅。",
        ]
        if risks:
            signals.append(f"当前最该提醒的风险点：{risks[0]}")
        angle = "围绕：这只票现在值不值得看，最该验证哪些点。"
        language_rules = [
            "先给结论，再拆2到3点。",
            "保持冷静，但不要写成研报。",
            "多用“拆开看”“核心就几点”这种表达。",
            "不要过度抒情。",
            "不要为了显得专业而变得书面化。",
        ]

    else:
        signals = [
            "重点不是拆估值，而是解释市场为什么会注意到它。",
            f"市场故事：{market_story}",
            "关键数据要自然嵌进叙事，不要写成资料清单。",
        ]
        if risks:
            signals.append(f"故事最后要落回兑现问题：{risks[0]}")
        angle = "围绕：这只票为什么会被市场追，市场到底在买什么故事。"
        language_rules = [
            "从行业、周期或资金关注点切入。",
            "语气可以更像观察，不要像说明书。",
            "允许有趋势感和叙事感，但不要空泛。",
            "段落之间要自然推进，不要机械列点。",
            "不要把全文写成资料复述。",
        ]

    fact_block = "\n".join(f"- {x}" for x in facts) if facts else "- 暂无明确事实资料"
    signal_block = "\n".join(f"- {x}" for x in signals)
    language_block = "\n".join(f"- {x}" for x in language_rules)

    return f"""
【事实资料】
{fact_block}

【写作信号】
{signal_block}

【语言规则】
{language_block}

【本篇角度】
{angle}
""".strip()


def validate_ipocard(ipo_card: Dict[str, Any]) -> Dict[str, Any]:
    required_fields = ["company_name", "listing_date", "entry_fee"]
    missing = []

    for field in required_fields:
        if not safe_str(ipo_card.get(field)):
            missing.append(field)

    return {
        "is_valid": len(missing) == 0,
        "missing_fields": missing,
    }


def call_llm(
    client,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.85,
) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )

    content = resp.choices[0].message.content
    return content.strip() if content else ""


def postprocess_text(text: str, style: str) -> str:
    """
    极轻后处理：
    默认什么都不做，只在开关打开时做最小修改。
    """
    if not text:
        return ""

    result = text

    if ENABLE_NORMALIZE_FINANCE_TERMS:
        result = normalize_finance_terms(result)

    if ENABLE_LIGHT_CLEANUP:
        result = cleanup_ai_tone_light(result)

    if ENABLE_DIVERSIFY_OPENING:
        result = diversify_opening(result, style)

    return result.strip()


def generate_draft_article(client, model: str, style: str, context_pack: str) -> str:
    system_prompt = get_system_prompt()
    user_prompt = get_user_prompt(style, context_pack)

    draft = call_llm(
        client=client,
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.9,
    )

    # 只做极轻后处理
    return postprocess_text(draft, style)


def rewrite_article(client, model: str, article: str, style: str) -> str:
    """
    rewrite 现在变成可选功能。
    默认关闭，避免把风格洗平。
    """
    if not article:
        return ""

    rewritten = call_llm(
        client=client,
        model=model,
        system_prompt=build_rewrite_system_prompt(),
        user_prompt=build_rewrite_user_prompt(article),
        temperature=0.7,
    )

    return postprocess_text(rewritten, style)


def generate_article_by_style(client, model: str, style: str, context_pack: str) -> str:
    draft = generate_draft_article(
        client=client,
        model=model,
        style=style,
        context_pack=context_pack,
    )

    if not draft:
        return ""

    if ENABLE_REWRITE:
        rewritten = rewrite_article(
            client=client,
            model=model,
            article=draft,
            style=style,
        )
        return (rewritten or draft).strip()

    return draft.strip()


def generate_all_articles(
    client,
    model: str,
    context_pack: Union[str, Dict[str, str]],
    styles: List[str] | None = None,
) -> Dict[str, str]:
    results: Dict[str, str] = {}
    target_styles = styles or ALL_STYLES

    for style in target_styles:
        try:
            if isinstance(context_pack, dict):
                current_context_pack = context_pack.get(style) or context_pack.get("rational") or ""
            else:
                current_context_pack = context_pack

            article = generate_article_by_style(
                client=client,
                model=model,
                style=style,
                context_pack=current_context_pack,
            )
            results[style] = article
        except Exception as e:
            results[style] = f"生成失败：{e}"

    return results


def build_generation_payload(ipo_card: Dict[str, Any]) -> Dict[str, Any]:
    validation = validate_ipocard(ipo_card)

    context_packs = {
        style: build_context_pack(ipo_card, style)
        for style in ALL_STYLES
    }

    return {
        "validation": validation,
        "context_pack": context_packs["rational"],  # 兼容旧前端展示
        "context_packs": context_packs,             # 新前端可用三种 style 独立 context
    }
