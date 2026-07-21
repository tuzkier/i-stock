#!/usr/bin/env python3
import argparse
import contextlib
import datetime as dt
import io
import json
import os
import sys

# futu 依赖的预生成 protobuf 代码与新版 protobuf runtime 不兼容，
# 强制走纯 Python 解析以避免 "Descriptors cannot be created directly"。
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")


def parse_args():
    parser = argparse.ArgumentParser(description="Fetch K-line data from local FutuOpenD.")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--range", required=True, choices=["1d", "5d", "1mo", "3mo", "6mo", "1y"])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=11111)
    return parser.parse_args()


def range_to_request(range_key):
    if range_key == "1d":
        return {"mode": "current", "ktype": "K_5M", "num": 120}
    if range_key == "5d":
        return {"mode": "current", "ktype": "K_15M", "num": 200}

    days_by_range = {
        "1mo": 45,
        "3mo": 110,
        "6mo": 220,
        "1y": 420,
    }
    max_count_by_range = {
        "1mo": 80,
        "3mo": 130,
        "6mo": 260,
        "1y": 520,
    }
    today = dt.date.today()
    start = today - dt.timedelta(days=days_by_range[range_key])
    return {
        "mode": "history",
        "ktype": "K_DAY",
        "start": start.isoformat(),
        "end": today.isoformat(),
        "max_count": max_count_by_range[range_key],
    }


def infer_market(symbol):
    return symbol.split(".", 1)[0] if "." in symbol else "US"


def infer_currency(symbol):
    market = infer_market(symbol)
    if market == "HK":
        return "HKD"
    if market in {"SH", "SZ"}:
        return "CNY"
    if market == "KR":
        return "KRW"
    return "USD"


def parse_time(value):
    text = str(value or "").strip()
    candidates = [text, text[:19], text[:10]]
    for candidate in candidates:
        for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                parsed = dt.datetime.strptime(candidate, pattern)
                return int(parsed.replace(tzinfo=dt.timezone.utc).timestamp())
            except ValueError:
                continue
    return None


def rows_to_payload(symbol, rows):
    records = rows.to_dict("records")
    bars = []
    name = None
    for row in records:
        timestamp = parse_time(row.get("time_key"))
        if timestamp is None:
            continue

        try:
            bar = {
                "time": timestamp,
                "open": float(row.get("open")),
                "high": float(row.get("high")),
                "low": float(row.get("low")),
                "close": float(row.get("close")),
                "volume": int(float(row.get("volume") or 0)),
            }
        except (TypeError, ValueError):
            continue

        if not name and row.get("name"):
            name = str(row.get("name"))
        bars.append(bar)

    return {
        "symbol": symbol,
        "name": name or symbol,
        "market": infer_market(symbol),
        "currency": infer_currency(symbol),
        "bars": bars,
    }


def fetch(args):
    from futu import AuType, KLType, OpenQuoteContext, RET_OK, SubType

    ktype_map = {
        "K_DAY": KLType.K_DAY,
        "K_5M": KLType.K_5M,
        "K_15M": KLType.K_15M,
    }
    subtype_map = {
        "K_5M": SubType.K_5M,
        "K_15M": SubType.K_15M,
    }
    request = range_to_request(args.range)
    ctx = OpenQuoteContext(host=args.host, port=args.port)
    try:
        if request["mode"] == "current":
            # 实时 K 线接口要求先订阅对应 K 线类型
            ret_sub, sub_err = ctx.subscribe([args.symbol], [subtype_map[request["ktype"]]], subscribe_push=False)
            if ret_sub != RET_OK:
                return {"error": str(sub_err)}
            ret, data = ctx.get_cur_kline(args.symbol, request["num"], ktype=ktype_map[request["ktype"]], autype=AuType.QFQ)
        else:
            ret, data, _ = ctx.request_history_kline(
                args.symbol,
                start=request["start"],
                end=request["end"],
                ktype=ktype_map[request["ktype"]],
                autype=AuType.QFQ,
                max_count=request["max_count"],
            )

        if ret != RET_OK:
            return {"error": str(data)}

        return rows_to_payload(args.symbol, data)
    finally:
        ctx.close()


def main():
    args = parse_args()
    try:
        noisy_output = io.StringIO()
        with contextlib.redirect_stdout(noisy_output), contextlib.redirect_stderr(noisy_output):
            payload = fetch(args)
    except Exception as exc:
        payload = {"error": str(exc)}

    sys.stdout.write(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
