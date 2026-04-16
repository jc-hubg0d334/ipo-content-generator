from pydantic import BaseModel, Field
from typing import Optional, List


class IPOCard(BaseModel):
    company_name: str

    # 仅做信息承载，不强行判断
    fundraising_amount: Optional[str] = None
    subscription_period: Optional[str] = None
    subscription_start: Optional[str] = None
    subscription_end: Optional[str] = None
    listing_date: Optional[str] = None
    offer_price_range: Optional[str] = None
    entry_fee: Optional[str] = None
    stock_code: Optional[str] = None

    sponsors: List[str] = Field(default_factory=list)
    cornerstone_investors: List[str] = Field(default_factory=list)
    source_urls: List[str] = Field(default_factory=list)

    key_facts: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)


class ArticleScore(BaseModel):
    total_score: int = 0
    hook_strength: int = 0
    emotional_tension: int = 0
    trading_angle: int = 0
    readability: int = 0
    platform_fit: int = 0
    data_integration: int = 0
    final_conviction: int = 0

    weaknesses: List[str] = Field(default_factory=list)
    improvement_actions: List[str] = Field(default_factory=list)


class GeneratedArticle(BaseModel):
    style: str
    title: str
    content: str
    score: Optional[ArticleScore] = None
