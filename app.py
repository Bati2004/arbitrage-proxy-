from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import concurrent.futures

app = Flask(__name__)
CORS(app)  # разрешаем запросы с GitHub Pages

EXCHANGES = {
    "bybit": {
        "url": lambda base: f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={base}USDT",
        "parse": lambda j: {
            "last": float(j["result"]["list"][0]["lastPrice"]),
            "bid": float(j["result"]["list"][0]["bid1Price"]),
            "ask": float(j["result"]["list"][0]["ask1Price"]),
        },
    },
    "okx": {
        "url": lambda base: f"https://www.okx.com/api/v5/market/ticker?instId={base}-USDT",
        "parse": lambda j: {
            "last": float(j["data"][0]["last"]),
            "bid": float(j["data"][0]["bidPx"]),
            "ask": float(j["data"][0]["askPx"]),
        },
    },
    "gateio": {
        "url": lambda base: f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={base}_USDT",
        "parse": lambda j: {
            "last": float(j[0]["last"]),
            "bid": float(j[0]["highest_bid"]),
            "ask": float(j[0]["lowest_ask"]),
        },
    },
    "mexc": {
        "url": lambda base: f"https://api.mexc.com/api/v3/ticker/bookTicker?symbol={base}USDT",
        "parse": lambda j: {
            "last": (float(j["bidPrice"]) + float(j["askPrice"])) / 2,
            "bid": float(j["bidPrice"]),
            "ask": float(j["askPrice"]),
        },
    },
    "htx": {
        "url": lambda base: f"https://api.huobi.pro/market/detail/merged?symbol={base.lower()}usdt",
        "parse": lambda j: {
            "last": float(j["tick"]["close"]),
            "bid": float(j["tick"]["bid"][0]),
            "ask": float(j["tick"]["ask"][0]),
        },
    },
    "bitget": {
        "url": lambda base: f"https://api.bitget.com/api/v2/spot/market/tickers?symbol={base}USDT",
        "parse": lambda j: {
            "last": float(j["data"][0]["lastPr"]),
            "bid": float(j["data"][0]["bidPr"]),
            "ask": float(j["data"][0]["askPr"]),
        },
    },
    "bingx": {
        "url": lambda base: f"https://open-api.bingx.com/openApi/spot/v1/ticker/24hr?symbol={base}-USDT",
        "parse": lambda j: {
            "last": float((j["data"][0] if isinstance(j["data"], list) else j["data"])["lastPrice"]),
            "bid": float((j["data"][0] if isinstance(j["data"], list) else j["data"])["bidPrice"]),
            "ask": float((j["data"][0] if isinstance(j["data"], list) else j["data"])["askPrice"]),
        },
    },
}


def fetch_one(exchange_id, cfg, base):
    try:
        r = requests.get(cfg["url"](base), timeout=6)
        r.raise_for_status()
        parsed = cfg["parse"](r.json())
        return exchange_id, {"ok": True, **parsed}
    except Exception as e:
        return exchange_id, {"ok": False, "error": str(e)}


@app.route("/api/prices")
def prices():
    base = request.args.get("coin", "BTC").upper()

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
        futures = [pool.submit(fetch_one, ex_id, cfg, base) for ex_id, cfg in EXCHANGES.items()]
        for future in concurrent.futures.as_completed(futures):
            ex_id, data = future.result()
            results[ex_id] = data

    return jsonify({"coin": base, "exchanges": results})


@app.route("/")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
