from futu import OpenQuoteContext

quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)

ret, data = quote_ctx.get_market_snapshot(['HK.00700'])

if ret == 0:
    print(data[['code', 'last_price', 'change_rate', 'volume']])
else:
    print("获取失败:", data)

quote_ctx.close()
