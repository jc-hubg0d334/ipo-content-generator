import json
import re
from pathlib import Path
from collections import Counter, defaultdict

INPUT_DIR = Path("/Users/steven/Desktop/hk_ipo/output_json")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

STYLE_PROFILE_PATH = OUTPUT_DIR / "style_profile.json"
SAMPLES_COMPACT_PATH = OUTPUT_DIR / "style_samples_compact.json"

STOPWORDS = {
    "的", "了", "是", "我", "你", "他", "她", "它", "我们", "你们", "他们",
    "一个", "没有", "不是", "这个", "那个", "但是", "所以", "因为", "如果",
    "可能", "已经", "还是", "可以", "自己", "还是", "以及", "并且", "或者",
    "真的", "其实", "感觉", "就是", "比较", "非常", "有点", "现在", "目前",
    "大家", "然后", "这样", "那样", "一个", "这只", "这篇", "文章"
}

FORBIDDEN_PHRASES = ["封神", "炸裂", "史诗级", "杀疯了", "定格"]

def load_json_file(fp: Path):
    try:
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def extract_text_fields(obj):
    texts = []
    if isinstance(obj, dict):
        for k in ["title", "content", "text", "body", "summary", "description", "desc"]:
            v = obj.get(k)
            if isinstance(v, str) and v.strip():
                texts.append(v.strip())
        for k in ["items", "paragraphs", "sections", "content_list"]:
            v = obj.get(k)
            if isinstance(v, list):
                for x in v:
                    if isinstance(x, str) and x.strip():
                        texts.append(x.strip())
                    elif isinstance(x, dict):
                        for kk in ["text", "content", "body"]:
                            vv = x.get(kk)
                            if isinstance(vv, str) and vv.strip():
                                texts.append(vv.strip())
    elif isinstance(obj, list):
        for item in obj:
            texts.extend(extract_text_fields(item))
    return texts

def compact_sample(obj):
    if not isinstance(obj, dict):
        return {"raw_type": str(type(obj))}
    return {
        "title": obj.get("title", ""),
        "content": obj.get("content", obj.get("text", "")),
        "tags": obj.get("tags", []),
        "source": obj.get("source", ""),
        "company": obj.get("company", obj.get("company_name", "")),
    }

def normalize_text(text):
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def tokenize_cn(text):
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    tokens = [t for t in tokens if t not in STOPWORDS]
    return tokens

def split_sentences(text):
    parts = re.split(r"[。！？!?；;\n]+", text)
    return [p.strip() for p in parts if p.strip()]

def count_title_patterns(title):
    patterns = []
    if not title:
        return patterns
    if "【港股打新】" in title:
        patterns.append("【港股打新】前缀")
    if "打不打" in title:
        patterns.append("打不打问句")
    if "值不值" in title:
        patterns.append("值不值问句")
    if "到底" in title:
        patterns.append("到底问句")
    if "？" in title or "?" in title:
        patterns.append("问句标题")
    if len(title) <= 18:
        patterns.append("短标题")
    if any(x in title for x in ["热", "火", "疯", "冲", "博"]):
        patterns.append("情绪标题")
    return patterns

def detect_tone(text):
    score = Counter()
    if any(x in text for x in ["打不打", "值不值", "怎么看", "要不要"]):
        score["judgment"] += 1
    if any(x in text for x in ["热度", "孖展", "认购倍数", "暗盘", "资金"]):
        score["trading"] += 1
    if any(x in text for x in ["我觉得", "我看", "说白了", "其实", "直接说"]):
        score["chatty"] += 1
    if any(x in text for x in ["风险", "谨慎", "克制", "不绝对"]):
        score["calm"] += 1
    if any(x in text for x in ["研报", "逻辑", "估值", "基本面", "数据"]):
        score["rational"] += 1
    return score

def main():
    files = sorted(INPUT_DIR.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No json files found in {INPUT_DIR}")

    all_samples = []
    all_texts = []
    title_counter = Counter()
    word_counter = Counter()
    sentence_lens = []
    tone_counter = Counter()
    length_counter = Counter()
    common_terms_counter = Counter()

    for fp in files:
        obj = load_json_file(fp)
        if obj is None:
            continue

        all_samples.append(compact_sample(obj))
        texts = extract_text_fields(obj)
        texts = [normalize_text(t) for t in texts if t and normalize_text(t)]
        if not texts:
            continue

        combined = "\n".join(texts)
        all_texts.append(combined)

        title = ""
        if isinstance(obj, dict):
            title = obj.get("title", "") or obj.get("headline", "") or obj.get("name", "")
        title = normalize_text(title)
        if title:
            for p in count_title_patterns(title):
                title_counter[p] += 1

        for t in texts:
            sents = split_sentences(t)
            sentence_lens.extend([len(s) for s in sents if s])
            tone_counter.update(detect_tone(t))
            tokens = tokenize_cn(t)
            word_counter.update(tokens)

            for term in ["孖展", "暗盘", "认购倍数", "折价率", "招股期", "公开发售价", "热度", "资金", "博弈", "打不打", "值不值"]:
                if term in t:
                    common_terms_counter[term] += 1

            if len(t) < 120:
                length_counter["short"] += 1
            elif len(t) < 400:
                length_counter["medium"] += 1
            else:
                length_counter["long"] += 1

    top_words = [w for w, _ in word_counter.most_common(80) if len(w) >= 2]
    top_common_terms = [w for w, _ in common_terms_counter.most_common(30)]
    top_title_patterns = [w for w, _ in title_counter.most_common()]
    avg_sentence_len = round(sum(sentence_lens) / len(sentence_lens), 2) if sentence_lens else 0

    if tone_counter:
        dominant_tone = tone_counter.most_common(1)[0][0]
    else:
        dominant_tone = "chatty"

    if length_counter:
        dominant_length = length_counter.most_common(1)[0][0]
    else:
        dominant_length = "medium"

    style_profile = {
        "overall_tone": dominant_tone,
        "title_patterns": top_title_patterns[:12],
        "opening_patterns": [
            "先点热度",
            "先抛冲突",
            "先给判断",
            "先说数据再说观点"
        ],
        "common_terms": top_common_terms[:20],
        "top_words": top_words[:50],
        "sentence_length": {
            "avg_chars_per_sentence": avg_sentence_len,
            "dominant_length": dominant_length
        },
        "emotion_level": "medium",
        "judgment_style": "有判断但不绝对，偏克制",
        "trading_angle_focus": [
            "热度",
            "资金",
            "孖展",
            "暗盘",
            "定价",
            "招股期",
            "认购倍数",
            "情绪"
        ],
        "forbidden_phrases": FORBIDDEN_PHRASES,
        "platform_fit": "小红书港股打新内容",
        "tone_signals": dict(tone_counter.most_common()),
        "length_distribution": dict(length_counter),
        "sample_count": len(all_samples)
    }

    with open(STYLE_PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(style_profile, f, ensure_ascii=False, indent=2)

    with open(SAMPLES_COMPACT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_samples, f, ensure_ascii=False, indent=2)

    print(f"Saved: {STYLE_PROFILE_PATH}")
    print(f"Saved: {SAMPLES_COMPACT_PATH}")
    print(f"Files processed: {len(files)}")
    print(f"Samples kept: {len(all_samples)}")
    print(f"Avg sentence length: {avg_sentence_len}")

if __name__ == "__main__":
    main()
