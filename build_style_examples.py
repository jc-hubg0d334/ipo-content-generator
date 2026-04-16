#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
import re
from collections import Counter

SAMPLES_PATH = Path("output/style_samples_compact.json")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

def load_samples() -> List[Dict[str, Any]]:
    with open(SAMPLES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    return re.sub(r"\s+", " ", text.strip())[:200]

def extract_keywords(text: str) -> List[str]:
    """提取港股打新关键词"""
    keywords = []
    if not text:
        return keywords
    
    # 港股打新核心词
    core_terms = [
        "孖展", "暗盘", "认购", "招股", "IPO", "上市", "定价", "热度", "资金", 
        "折价率", "打新", "公开发售", "国际配售", "基石", "超购"
    ]
    
    for term in core_terms:
        if term in text:
            keywords.append(term)
    
    # 行业关键词
    industry_terms = ["新能源", "科技", "生物", "消费", "金融", "地产"]
    for term in industry_terms:
        if term in text:
            keywords.append(f"industry_{term}")
    
    return keywords

def text_similarity(query: str, sample: Dict[str, Any]) -> float:
    """计算样本与查询的相似度"""
    query_norm = normalize_text(query).lower()
    sample_title = normalize_text(sample.get("title", "")).lower()
    sample_content = normalize_text(sample.get("content", "")).lower()
    
    score = 0.0
    
    # 标题匹配（权重最高）
    if sample_title and any(word in sample_title for word in query_norm.split()):
        score += 3.0
    
    # 内容关键词匹配
    sample_keywords = extract_keywords(sample_title + " " + sample_content)
    query_keywords = extract_keywords(query)
    
    for qk in query_keywords:
        if qk in sample_keywords:
            score += 1.0
    
    # 长度匹配（偏好相似长度）
    content_len = len(sample_content)
    if 50 < content_len < 800:
        score += 0.5
    
    # 有标签优先
    if sample.get("tags"):
        score += 0.3
    
    return score

def pick_examples(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """挑选最像的 K 个样本"""
    samples = load_samples()
    scored_samples = []
    
    for i, sample in enumerate(samples):
        score = text_similarity(query, sample)
        if score > 0.1:  # 过滤低分样本
            scored_samples.append((score, i, sample))
    
    # 按分数排序，取前 K 个
    scored_samples.sort(key=lambda x: x[0], reverse=True)
    top_k = scored_samples[:k]
    
    return [sample for _, _, sample in top_k]

def save_examples(query: str, examples: List[Dict[str, Any]]):
    """保存为当前查询的示例文件"""
    output_path = OUTPUT_DIR / f"examples_{query[:50].replace('/', '_').replace(' ', '_')}.json"
    result = {
        "query": query,
        "examples": examples,
        "count": len(examples)
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Saved examples to: {output_path}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 build_style_examples.py '宁德时代'")
        print("       python3 build_style_examples.py '新能源 IPO'")
        return
    
    query = sys.argv[1]
    print(f"🔍 Searching examples for: '{query}'")
    
    examples = pick_examples(query, k=5)
    
    print(f"✅ Found {len(examples)} similar examples:")
    for i, ex in enumerate(examples, 1):
        title = ex.get("title", "No title")
        print(f"  {i}. {title[:60]}...")
    
    save_examples(query, examples)
    print(f"\n📁 Ready for prompt generation!")

if __name__ == "__main__":
    main()
