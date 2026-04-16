import json
from pathlib import Path
from typing import List, Dict, Any

# 这里改成你清洗后的总文件路径
CLEANED_FILE = Path("/Users/steven/Desktop/hk_ipo/output_json/cleaned_output/all_cleaned_samples.json")

# 输出目录
OUTPUT_DIR = CLEANED_FILE.parent
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_cleaned_samples(file_path: Path) -> List[Dict[str, Any]]:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("all_cleaned_samples.json 不是 list 结构，请检查清洗结果")

    return data


def filter_good_samples(samples: List[Dict[str, Any]], min_len: int = 80) -> List[Dict[str, Any]]:
    """
    过滤太短、太碎的样本
    """
    good = []
    for item in samples:
        content = (item.get("content") or "").strip()
        if len(content) >= min_len:
            good.append(item)
    return good


def sort_samples(samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    优先按 virality_score，其次按内容长度排序
    """
    return sorted(
        samples,
        key=lambda x: (
            x.get("virality_score", 0),
            len(x.get("content", "")),
        ),
        reverse=True,
    )


def pick_examples(samples: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
    """
    选最适合做风格参考的样本
    """
    ranked = sort_samples(samples)
    return ranked[:top_k]


def summarize_sample_features(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    做一个简单的 Python 规则总结，不靠 LLM
    先生成一个基础 style profile，后面再给模型进一步提炼
    """
    total = len(samples)
    avg_len = 0
    titles = []
    keyword_counter = {}

    if total > 0:
        avg_len = sum(len(s.get("content", "")) for s in samples) // total

    for s in samples:
        title = (s.get("title") or "").strip()
        if title:
            titles.append(title)

        for kw in s.get("keywords", []):
            keyword_counter[kw] = keyword_counter.get(kw, 0) + 1

    sorted_keywords = sorted(keyword_counter.items(), key=lambda x: x[1], reverse=True)
    top_keywords = [k for k, _ in sorted_keywords[:10]]

    return {
        "sample_count": total,
        "average_length": avg_len,
        "top_keywords": top_keywords,
        "sample_titles": titles[:10],
    }


def build_style_analysis_prompt(examples: List[Dict[str, Any]], profile: Dict[str, Any]) -> str:
    """
    这个 prompt 是给模型用来“总结风格”的，不是直接写文章
    """
    example_blocks = []

    for idx, ex in enumerate(examples, start=1):
        title = ex.get("title", "")
        content = ex.get("content", "")
        block = f"""样本{idx}
标题：{title}
正文：
{content}
"""
        example_blocks.append(block)

    joined_examples = "\n\n----------------\n\n".join(example_blocks)

    prompt = f"""
你是一个专门拆解小红书港股IPO内容风格的编辑。

现在我给你一些已经清洗好的优质样本，请你不要复述原文，而是总结这些样本的共同写法。

样本基础信息：
- 样本数量：{profile.get("sample_count", 0)}
- 平均长度：{profile.get("average_length", 0)}
- 高频关键词：{", ".join(profile.get("top_keywords", []))}

样本内容如下：
{joined_examples}

请你输出一份“写作风格规则”，要求包括以下部分：

1. 人设口吻
2. 开头方式
3. 正文结构
4. 数据如何嵌入
5. 判断怎么下
6. 适合保留的表达
7. 需要避免的表达
8. 标题风格
9. 适合写港股IPO文章的统一模板

输出要求：
- 用中文
- 清晰分点
- 不要照抄样本
- 不要空泛
- 要能直接拿去做 prompt
""".strip()

    return prompt


def build_direct_style_rules(examples: List[Dict[str, Any]], profile: Dict[str, Any]) -> str:
    """
    这是不用模型，直接由 Python 拼出来的基础规则文本
    你马上就能拿去接到 prompts.py 里
    """
    top_keywords = "、".join(profile.get("top_keywords", []))
    titles = profile.get("sample_titles", [])[:5]
    title_examples = "\n".join([f"- {t}" for t in titles if t])

    rules = f"""
你要模仿的是“小红书港股IPO内容”写法，而不是新闻稿、研报或公告摘要。

【整体风格】
- 语气像长期关注港股打新的真人作者
- 有判断，但不装专家
- 会讲数据，但不是生硬堆数据
- 像发在小红书上的简评或打新分析

【内容特点】
- 常见关键词：{top_keywords}
- 平均篇幅约：{profile.get("average_length", 0)}字
- 常见主题：港股IPO、打新、招股、上市、暗盘、认购、保荐人、基石投资者

【开头写法】
- 开头先点出现象、热度、争议或值不值得看
- 不要一上来就像公告复读
- 优先用一句话把核心信息讲出来

【正文结构】
- 先写这只票是什么、值不值得关注
- 再写招股或基本面里的关键数据
- 然后写亮点、风险、市场情绪或交易角度
- 最后给一个克制判断

【数据嵌入方式】
- 数据要自然出现在分析里，不要像表格搬运
- 优先写：招股价、集资规模、招股时间、定价日、保荐人、基石、认购热度、暗盘预期
- 没有的数据不要编

【表达要求】
- 像人写的
- 允许口语化，但不要低质营销号语气
- 不要过度夸张
- 不要写成新闻播报
- 不要写成研究报告

【禁止】
- 不要编造亲身经历
- 不要说“历史数据显示”“市场一致认为”
- 不要说“封神”“炸裂”“杀疯了”“史诗级”
- 不要使用和金融场景不匹配的词

【标题风格参考】
{title_examples}

【统一写作模板】
标题：一句话点出公司/股票 + 核心看点
第一段：这只票值不值得看，现象是什么
第二段：招股核心数据和关键点
第三段：亮点、风险、市场情绪或交易逻辑
第四段：给一个克制判断，不喊单，不绝对化
""".strip()

    return rules


def main():
    if not CLEANED_FILE.exists():
        raise FileNotFoundError(f"找不到 cleaned 文件：{CLEANED_FILE}")

    samples = load_cleaned_samples(CLEANED_FILE)
    good_samples = filter_good_samples(samples, min_len=80)
    examples = pick_examples(good_samples, top_k=5)
    profile = summarize_sample_features(good_samples)

    style_analysis_prompt = build_style_analysis_prompt(examples, profile)
    direct_style_rules = build_direct_style_rules(examples, profile)

    analysis_prompt_file = OUTPUT_DIR / "style_analysis_prompt.txt"
    direct_rules_file = OUTPUT_DIR / "style_rules.txt"
    selected_examples_file = OUTPUT_DIR / "selected_style_examples.json"

    with open(analysis_prompt_file, "w", encoding="utf-8") as f:
        f.write(style_analysis_prompt)

    with open(direct_rules_file, "w", encoding="utf-8") as f:
        f.write(direct_style_rules)

    with open(selected_examples_file, "w", encoding="utf-8") as f:
        json.dump(examples, f, ensure_ascii=False, indent=2)

    print("已完成")
    print(f"风格分析 Prompt：{analysis_prompt_file}")
    print(f"直接可用风格规则：{direct_rules_file}")
    print(f"选出的样本示例：{selected_examples_file}")
    print(f"清洗后总样本数：{len(samples)}")
    print(f"可用样本数：{len(good_samples)}")
    print(f"选中示例数：{len(examples)}")


if __name__ == "__main__":
    main()
