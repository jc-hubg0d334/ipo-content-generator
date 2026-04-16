import yfinance as yf


import yfinance as yf


def normalize_to_yahoo_hk_symbol(stock_code: str) -> str:
    """
    支持这些输入：
    - HK.00700
    - 00700
    - 700
    - 0700.HK
    返回统一格式：
    - 0700.HK
    """
    if not stock_code:
        return ""

    code = stock_code.strip().upper()

    def to_hk_symbol(number_str: str) -> str:
        if not number_str or not number_str.isdigit():
            return ""
        # 关键：先转 int 去掉多余前导 0，再补成 4 位
        return f"{int(number_str):04d}.HK"

    if code.endswith(".HK"):
        number = code.replace(".HK", "").strip()
        symbol = to_hk_symbol(number)
        return symbol or code

    if code.startswith("HK."):
        number = code.replace("HK.", "").strip()
        symbol = to_hk_symbol(number)
        return symbol or code

    if code.isdigit():
        symbol = to_hk_symbol(code)
        return symbol or code

    return code


def to_python_number(value):
    if value is None:
        return None

    try:
        if hasattr(value, "item"):
            value = value.item()
    except Exception:
        pass

    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return float(value)

    return value


def get_market_snapshot_simple(stock_code: str) -> dict:
    symbol = normalize_to_yahoo_hk_symbol(stock_code)
    print(f"[DEBUG] Yahoo symbol = {symbol}")

    if not symbol:
        return {
            "success": False,
            "code": stock_code,
            "error": "empty stock code"
        }

    try:
        ticker = yf.Ticker(symbol)

        info = ticker.info or {}
        hist = ticker.history(period="2d", interval="1d")

        last_price = info.get("regularMarketPrice")
        previous_close = info.get("regularMarketPreviousClose")
        volume = info.get("regularMarketVolume")
        currency = info.get("currency")
        market_cap = info.get("marketCap")
        short_name = info.get("shortName") or info.get("longName")

        if last_price is None and not hist.empty and "Close" in hist.columns:
            last_price = hist["Close"].iloc[-1]

        # 如果核心字段都没有，视为失败，不要伪装 success=True
        if (
            last_price is None
            and previous_close is None
            and volume is None
            and market_cap is None
            and currency is None
        ):
            return {
                "success": False,
                "code": symbol,
                "error": "No valid market data returned from Yahoo Finance",
                "source": "Yahoo Finance via yfinance"
            }

        result = {
            "success": True,
            "code": symbol,
            "name": short_name,
            "last_price": to_python_number(last_price),
            "previous_close": to_python_number(previous_close),
            "volume": to_python_number(volume),
            "market_cap": to_python_number(market_cap),
            "currency": currency,
            "source": "Yahoo Finance via yfinance"
        }

        print("[DEBUG] Yahoo market_data =", result)
        return result

    except Exception as e:
        print("[DEBUG] Yahoo error =", e)
        return {
            "success": False,
            "code": symbol,
            "error": str(e),
            "source": "Yahoo Finance via yfinance"
        }

def to_python_number(value):
    if value is None:
        return None
    try:
        if hasattr(value, "item"):
            value = value.item()
    except Exception:
        pass

    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return float(value)
    return value


def get_market_snapshot_simple(stock_code: str) -> dict:
    symbol = normalize_to_yahoo_hk_symbol(stock_code)
    print(f"[DEBUG] Yahoo symbol = {symbol}")

    if not symbol:
        return {
            "success": False,
            "code": stock_code,
            "error": "empty stock code"
        }

    try:
        ticker = yf.Ticker(symbol)

        info = ticker.info or {}
        hist = ticker.history(period="2d", interval="1d")

        last_price = info.get("regularMarketPrice")
        previous_close = info.get("regularMarketPreviousClose")
        volume = info.get("regularMarketVolume")
        currency = info.get("currency")
        market_cap = info.get("marketCap")
        short_name = info.get("shortName") or info.get("longName")

        if last_price is None and not hist.empty and "Close" in hist.columns:
            last_price = hist["Close"].iloc[-1]

        result = {
            "success": True,
            "code": symbol,
            "name": short_name,
            "last_price": to_python_number(last_price),
            "previous_close": to_python_number(previous_close),
            "volume": to_python_number(volume),
            "market_cap": to_python_number(market_cap),
            "currency": currency,
            "source": "Yahoo Finance via yfinance"
        }

        print("[DEBUG] Yahoo market_data =", result)
        return result

    except Exception as e:
        print("[DEBUG] Yahoo Finance error =", e)
        return {
            "success": False,
            "code": symbol,
            "error": str(e),
            "source": "Yahoo Finance via yfinance"
        }
