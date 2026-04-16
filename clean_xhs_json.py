import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any

# ===== 1) 改成你的 JSON 文件夹路径 =====
INPUT_DIR = Path("/Users/steven/Desktop/hk_ipo/output_json")

# 清洗后的结果输出到这里
OUTPUT_DIR = INPUT_DIR / "cleaned_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """读取单个 JSON 文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_text(text: str) -> str:
    """基础清洗：统一换行、空格、去掉明显乱码"""
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u3000", " ")
    text = text.replace("\xa0", " ")

    # 去掉过多空格
    text = re.sub(r"[ \t]+", " ", text)

    # 去掉过多空行
    text = re.sub(r"\n{2,}", "\n", text)

    return text.strip()


def is_noise_line(line: str) -> bool:
    """判断一行是不是明显噪音"""
    line = line.strip()
    if not line:
        return True

    noise_patterns = [
        r"^\d{1,2}:\d{2}",                 # 5:02 / 11:03
        r"^\d+/\d+$",                      # 3/4, 4/4
        r"^关注$",
        r"^说点什么",
        r"^不喜欢$",
        r"^共\d+条评论$",
        r"^编辑于",
        r"^合集",
        r"^回复$",
        r"^到底了$",
        r"^[A-Za-z0-9._-]+$",              # 纯账号碎片
        r"^\d+$",                          # 单独数字
    ]

    for pattern in noise_patterns:
        if re.search(pattern, line):
            return True

    # 太短且没什么信息
    if len(line) <= 2:
        return True

    return False


def clean_line(line: str) -> str:
    """清洗单行文本"""
    line = line.strip()

    # 去掉明显 UI 符号和无意义字符
    line = re.sub(r"[•◆◇▲△▼▽★☆]+", "", line)
    line = re.sub(r"[ ]{2,}", " ", line)

    # 去掉行首尾杂字符
    line = re.sub(r"^[^\u4e00-\u9fa5A-Za-z0-9【\[\(（]+", "", line)
    line = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9】\]\)）%\.。！，、：:；;HK$]+$", "", line)

    return line.strip()


def merge_broken_lines(lines: List[str]) -> List[str]:
    """
    把 OCR 被拆碎的句子尽量合并。
    规则尽量简单：如果上一句不像结束，就拼到一起。
    """
    merged = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if not merged:
            merged.append(line)
            continue

        prev = merged[-1]

        # 如果上一行不像结束，且当前行像接着说
        if (
            not re.search(r"[。！？.!?：:]$", prev)
            and len(prev) < 80
        ):
            merged[-1] = prev + line
        else:
            merged.append(line)

    return merged


def extract_content_blocks(full_text: str) -> Dict[str, Any]:
    """
    从 full_text 中抽出：
    - title: 粗略标题
    - content: 清洗后的正文
    - keywords: 简单关键词
    """
    text = normalize_text(full_text)
    raw_lines = text.split("\n")

    cleaned_lines = []
    for line in raw_lines:
        line = clean_line(line)
        if is_noise_line(line):
            continue

        # 必须至少有中文或港股常见字符
        if not re.search(r"[\u4e00-\u9fa5A-Za-z0-9]", line):
            continue

        cleaned_lines.append(line)

    cleaned_lines = merge_broken_lines(cleaned_lines)

    # 再过滤一次太短的碎片
    final_lines = []
    for line in cleaned_lines:
        if len(line) >= 6:
            final_lines.append(line)

    # 尝试提取标题：优先取前 1~2 行里像标题的内容
    title = ""
    for line in final_lines[:3]:
        if "IPO" in line or "打新" in line or "招股" in line or "分析" in line:
            title = line
            break

    if not title and final_lines:
        title = final_lines[0][:30]

    content = "\n".join(final_lines).strip()

    keywords = []
    keyword_candidates = ["港股IPO", "香港IPO", "打新", "招股", "暗盘", "上市", "保荐人", "基石投资者", "认购"]
    for kw in keyword_candidates:
        if kw in content:
            keywords.append(kw)

    return {
        "title": title,
        "content": content,
        "keywords": keywords,
        "line_count": len(final_lines),
    }


def build_clean_sample(data: Dict[str, Any], file_name: str) -> Dict[str, Any]:
    """把原始 JSON 转成干净样本"""
    parsed = extract_content_blocks(data.get("full_text", ""))

    return {
        "source_file": file_name,
        "source_image": data.get("source_image", ""),
        "title": parsed["title"],
        "content": parsed["content"],
        "keywords": parsed["keywords"],
        "line_count": parsed["line_count"],
        "likes": data.get("likes", 0),
        "comments": data.get("comments", 0),
        "collections": data.get("collections", 0),
        "virality_score": data.get("virality_score", 0),
    }


def process_all_json_files():
    """处理整个文件夹"""
    if not INPUT_DIR.exists():
        raise FileNotFoundError(f"找不到输入目录：{INPUT_DIR}")

    json_files = sorted(INPUT_DIR.glob("*.json"))
    if not json_files:
        print(f"在目录里没有找到 JSON 文件：{INPUT_DIR}")
        return

    all_samples = []

    for file_path in json_files:
        try:
            data = load_json_file(file_path)
            sample = build_clean_sample(data, file_path.name)

            # 内容太短就跳过
            if len(sample["content"]) < 20:
                print(f"[跳过] 内容太短：{file_path.name}")
                continue

            # 输出单个清洗文件
            out_file = OUTPUT_DIR / file_path.name
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(sample, f, ensure_ascii=False, indent=2)

            all_samples.append(sample)
            print(f"[完成] {file_path.name}")

        except Exception as e:
            print(f"[失败] {file_path.name} -> {e}")

    # 输出总合集
    merged_file = OUTPUT_DIR / "all_cleaned_samples.json"
    with open(merged_file, "w", encoding="utf-8") as f:
        json.dump(all_samples, f, ensure_ascii=False, indent=2)

    print("\n处理完成")
    print(f"清洗后的单文件目录：{OUTPUT_DIR}")
    print(f"总样本文件：{merged_file}")
    print(f"共保留样本数：{len(all_samples)}")


if __name__ == "__main__":
    process_all_json_files()
