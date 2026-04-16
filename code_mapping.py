COMPANY_CODE_MAP = {
    "腾讯": "0700.HK",
    "腾讯控股": "0700.HK",
    "阿里巴巴": "9988.HK",
    "阿里": "9988.HK",
    "美团": "3690.HK",
    "京东": "9618.HK",
    "小米": "1810.HK",
}
def get_stock_code_by_company_name(company_name: str) -> str:
    return COMPANY_CODE_MAP.get(company_name.strip(), "")
