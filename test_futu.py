from futu import OpenQuoteContext

quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)

ret, data = quote_ctx.get_market_snapshot(['HK.00700'])

if ret == 0:
    row = data.iloc[0]

    print("=== 所有包含 change / ratio / amplitude 的字段 ===")
    for col in data.columns:
        name = str(col).lower()
        if "change" in name or "ratio" in name or "amplitude" in name:
            print(f"{col} = {row.get(col)}")

    print("\n=== 基础字段 ===")
    print("code =", row.get("code"))
    print("last_price =", row.get("last_price"))
    print("volume =", row.get("volume"))

else:
    print("获取失败:", data)

quote_ctx.close()
