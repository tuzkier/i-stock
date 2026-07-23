#!/usr/bin/env python3
"""只读查询 FutuOpenD 账户历史成交（真实买卖点）。输出 JSON 到 stdout。

用法: python3 server/futud-deals.py [--market HK] [--env REAL|SIMULATE] [--start YYYY-MM-DD] [--end YYYY-MM-DD]

仅做 history_deal_list_query（只读）；不下单、不改单、不解锁。
"""
import argparse
import contextlib
import datetime as dt
import io
import json
import os
import sys

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")


def parse_args():
    today = dt.date.today()
    parser = argparse.ArgumentParser(description="Read-only deal-history query from local FutuOpenD.")
    parser.add_argument("--market", default="HK", choices=["HK", "US", "CN"])
    parser.add_argument("--env", default="REAL", choices=["REAL", "SIMULATE"])
    # 默认拉近 2 年（FutuOpenD 历史成交约只提供近两年；再长会被券商侧截断）。
    parser.add_argument("--start", default=(today - dt.timedelta(days=730)).isoformat())
    parser.add_argument("--end", default=today.isoformat())
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=11111)
    return parser.parse_args()


def main():
    args = parse_args()
    noisy = io.StringIO()
    try:
        with contextlib.redirect_stdout(noisy), contextlib.redirect_stderr(noisy):
            from futu import OpenSecTradeContext, TrdMarket, SecurityFirm, TrdEnv, RET_OK

            market = {"HK": TrdMarket.HK, "US": TrdMarket.US, "CN": TrdMarket.CN}[args.market]
            env = {"REAL": TrdEnv.REAL, "SIMULATE": TrdEnv.SIMULATE}[args.env]
            ctx = OpenSecTradeContext(
                filter_trdmarket=market,
                host=args.host,
                port=args.port,
                security_firm=SecurityFirm.FUTUSECURITIES,
            )
            try:
                ret, data = ctx.history_deal_list_query(code="", start=args.start, end=args.end, trd_env=env)
            finally:
                ctx.close()
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": "deal_query_failed", "detail": str(exc)}, ensure_ascii=False))
        return 1

    if ret != RET_OK:
        print(json.dumps({"error": "deal_query_failed", "detail": str(data)}, ensure_ascii=False))
        return 1

    fields = ["code", "stock_name", "trd_side", "qty", "price", "create_time"]
    deals = []
    for _, row in data.iterrows():
        deals.append({key: (row[key] if key in row else None) for key in fields})

    print(json.dumps({"market": args.market, "env": args.env, "start": args.start, "end": args.end, "count": len(deals), "deals": deals}, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
