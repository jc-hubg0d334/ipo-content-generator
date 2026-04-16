from __future__ import annotations

from typing import Any, Dict, Optional
from futu import OpenQuoteContext

FUTU_HOST = "127.0.0.1"
FUTU_PORT = 11111


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value in (None, "", "N/A"):
            return None
        return float(value)
    except Exception:
        return None


from futu import OpenQuoteContext

def get_market_snapshot_simple(code: str):
    print(f"[DEBUG] 开始获取富途行情: {code}")

    quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
    try:
        ret, data = quote_ctx.get_market_snapshot([code])
        print("[DEBUG] ret =", ret)
        print("[DEBUG] data =", data)

        if ret != 0 or data is None or len(data) == 0:
            return {
                "success": False,
                "code": code,
                "error": str(data)
            }

        row = data.iloc[0]

        result = {
            "success": True,
            "code": str(row["code"]) if "code" in data.columns else code,
            "last_price": float(row["last_price"]) if "last_price" in data.columns and row["last_price"] is not None else None,
            "volume": int(row["volume"]) if "volume" in data.columns and row["volume"] is not None else None,
            "turnover": float(row["turnover"]) if "turnover" in data.columns and row["turnover"] is not None else None,
        }

        print("[DEBUG] result =", result)
        return result

    except Exception as e:
        print("[DEBUG] 富途报错 =", e)
        return {
            "success": False,
            "code": code,
            "error": str(e)
        }
    finally:
        quote_ctx.close()
