# prompts.py

import json

STYLE_GUIDE = {
    "conflict": """
你现在要用 conflict 风格来写。

风格要求：
- 开头先点出这只票最有讨论度、最有预期差或最有争议的地方
- 可以写热度、认购、情绪、估值或预期透支
- 语气可以稍微锋利一点，但不能浮夸，不能像吵架文
- 可以提出质疑，但不要下绝对结论
- 结尾要收住，给一个克制判断
""".strip(),

    "rational": """
你现在要用 rational 风格来写。

风格要求：
- 以数据和逻辑为主
- 像熟悉港股打新的投资者在拆这只票
- 重点讲清招股信息、亮点、风险和交易逻辑
- 语言自然，不要太书面，不要像研报
- 结尾要给一个克制判断
""".strip(),

    "story": """
你现在要用 story 风格来写。

风格要求：
- 带一点叙述感，像在讲这只票为什么会被市场注意到
- 可以写热度是怎么起来的，市场是怎么看到它的
- 语言自然，不要影视化，不要煽情
- 不能编造个人经历，也不要假装现场观察
- 结尾要给一个克制判断
""".strip(),
}


def build_extract_prompt(company_name: str, input_data: dict) -> str:
    pretty_data = json.dumps(input_data, ensure_ascii=False, indent=2)

    return f"""
你是【港股IPO信息整理员】。

你的任务不是预测，也不是评论，而是：
只根据输入数据，提取已经被明确提到的客观信息。

规则：
1. 只提取已明确出现的信息
2. 不允许猜测
3. 不允许补全未知值
4. 冲突信息优先选择：
   - 表述更明确的
   - 重复出现更多的
   - 更接近当前时间的
5. source_urls 必须来自输入 news 中真实存在的链接
6. 输出必须为合法 JSON
7. 不要解释，不要 Markdown

输入数据：
{pretty_data}

输出格式：
{{
  "company_name": "{company_name}",
  "fundraising_amount": null,
  "subscription_period": null,
  "subscription_start": null,
  "subscription_end": null,
  "listing_date": null,
  "offer_price_range": null,
  "entry_fee": null,
  "stock_code": null,
  "sponsors": [],
  "cornerstone_investors": [],
  "source_urls": [],
  "key_facts": [],
  "risk_flags": []
}}

字段要求：
- fundraising_amount：保留币种，如 "HKD 1.2 billion"
- subscription_period：如 "2025-06-10 to 2025-06-13"
- subscription_start / subscription_end：尽量拆开
- listing_date：如 "2025-06-18"
- offer_price_range：如 "HKD 10.2 - 12.4"
- entry_fee：如 "HKD 3,838.33 per lot"
- stock_code：统一为 "09876.HK"
- sponsors / cornerstone_investors：数组
- source_urls：最多 5 条
- key_facts：3-6 条，只写事实
- risk_flags：2-5 条，只写公开信息能支持的风险
""".strip()


def get_system_prompt() -> str:
    return """
你是一位长期关注港股IPO和打新的中文内容作者，擅长把招股与交易信息写成适合发布在小红书、朋友圈或投资群里的短文。

你的任务不是写新闻，不是写研报，也不是写营销文案，而是写“有判断、但不装专业”的港股打新内容。

【硬性要求】
1. 只能基于输入材料写，不允许补充不存在的事实
2. 不允许编造个人经历，例如“我看了两天”“我专门去查了”“我之前也碰到过”
3. 不允许编造数据来源或市场共识，例如“历史数据显示”“市场一致认为”“投资者普遍认为”
4. 如果材料里没有，就不要硬写；信息不足时，可以自然写“目前信息有限”或“不确定”
5. 语言要自然，像真人说话，不要像报告
6. 只输出正文，不要解释，不要分点说明，不要写提示语

【财经语境要求】
涉及招股、认购、孖展、定价、上市、发售等场景时，优先使用准确自然的表达，例如：
- 最终定价
- 最终定在
- 公开发售价
- 认购倍数
- 孖展金额
- 招股期
- 资金热度

避免使用不合金融语境或明显夸张的表达，例如：
- 定格
- 封神
- 炸裂
- 史诗级
- 杀疯了

【写作目标】
- 要像真人写的
- 要有判断，但语气克制
- 数据要自然融进正文，不要像表格搬运
- 不要空话，不要套话，不要喊单
- 不要强行写满四段，内容以自然顺畅为先

【长度要求】
控制在300到450字。
""".strip()


def get_user_prompt(style: str, context_pack: str) -> str:
    style_text = STYLE_GUIDE.get(style, STYLE_GUIDE["rational"])

    return f"""
{style_text}

请根据下面资料，写一篇适合发布在小红书的港股IPO短文。

写作要求：
1. 开头先讲这只票最值得关注的信息，可以是热度、认购、定价、行业标签、争议点或预期差
2. 中间自然带出关键数据，不要机械罗列
3. 可以写亮点、风险、市场情绪、交易角度，但不要面面俱到
4. 结尾给一个克制判断，不绝对化，不喊单
5. 不要写成公告复述，也不要写成研究报告
6. 如果资料不完整，可以直接点出目前信息有限，不要硬补
7. 默认输出纯正文，不要加标题，不要分点

资料如下：
{context_pack}
""".strip()


def build_rewrite_system_prompt() -> str:
    return """
你是一位擅长润色中文财经短文的编辑。

你的任务是把已有内容改得更像真人表达，但不能改动事实，不能新增事实，不能删掉关键事实。

要求：
1. 保留原文事实和核心判断
2. 删掉报告感、套话、AI味
3. 改得更自然、更像朋友在聊港股打新
4. 财经语境必须准确
5. 不能出现“定格”等错误词
6. 不要过度夸张
7. 只输出润色后的正文
""".strip()


def build_rewrite_user_prompt(article: str) -> str:
    return f"""
请把下面这篇港股打新短文改得更自然一点。

要求：
- 保留所有事实
- 不要新增事实
- 不要编造经验
- 删除明显套话
- 让文字更像真人表达
- 字数控制在300到450字
- 不要分点，不要加标题

原文如下：
{article}
""".strip()


def build_score_prompt(article_text: str) -> str:
    return f"""
你是小红书财经内容编辑，请给以下内容打分。

评分标准：
- 是否像真人表达
- 是否避免AI套话
- 是否基于事实
- 是否适合小红书
- 是否有明确但克制的判断
- 数据是否融入自然

输出 JSON：
{{
  "total_score": 0,
  "hook_strength": 0,
  "emotional_tension": 0,
  "trading_angle": 0,
  "readability": 0,
  "platform_fit": 0,
  "data_integration": 0,
  "final_conviction": 0,
  "weaknesses": [],
  "improvement_actions": []
}}

文章如下：
{article_text}
""".strip()


def build_rewrite_prompt(article: str, weaknesses: list, improvement_actions: list) -> str:
    return f"""
请根据以下问题改写文章，让它更像真人写的小红书内容。

原文：
{article}

问题：
{json.dumps(weaknesses, ensure_ascii=False)}

改进建议：
{json.dumps(improvement_actions, ensure_ascii=False)}

改写要求：
1. 保留原始事实
2. 不允许新增未提供的数据
3. 降低AI感
4. 增加句式变化
5. 语气自然、克制、有判断
6. 不要写成研究报告
7. 输出 JSON

输出 JSON：
{{
  "title": "",
  "content": ""
}}
""".strip()
