#!/usr/bin/env python3
import json
from prompts import (
    get_system_prompt,
    build_generation_direct_prompt,
    build_rewrite_system_prompt,
    build_rewrite_user_prompt
)

def load_style_profile():
    """加载风格画像，fallback 到默认"""
    try:
        with open("output/style_profile.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️  Using fallback style_profile")
        return {
            "overall_tone": "chatty",
            "common_terms": ["孖展", "暗盘", "认购倍数"],
            "trading_angle_focus": ["热度", "资金"]
        }

def test_full_pipeline():
    # 加载风格
    style_profile = load_style_profile()
    
    # 模拟 IPO 数据
    ipo_card = {
        "company_name": "宁德时代概念股",
        "fundraising_amount": "HKD 8亿",
        "listing_date": "2026-04-20",
        "offer_price_range": "HKD 12-15",
        "entry_fee": "HKD 5,000/手",
        "key_facts": ["新能源概念", "孖展超10倍", "基石投资者到位"]
    }
    
    # 模拟市场快照
    market_snapshot = {
        "latest_oversubscription": "超购15倍",
        "grey_market_signal": "+25%",
        "market_sentiment": "火热"
    }
    
    # 模拟 examples（等完善后再替换）
    examples = [
        {"title": "【港股打新】新能源概念，热度爆表，打不打？", "content": "这只票孖展很猛..."}
    ]
    
    print("=== 系统 Prompt ===")
    print(get_system_prompt())
    print("\n=== 生成 Prompt ===")
    
    prompt = build_generation_direct_prompt(
        style_profile=style_profile,
        examples=examples,
        ipo_card=ipo_card,
        market_snapshot=market_snapshot,
        fallback_style="xhs"
    )
    print(prompt[:1000] + "...")
    
    print("\n✅ Pipeline 测试通过！")
    print("下一步：接进 streamlit_app.py")

if __name__ == "__main__":
    test_full_pipeline()
