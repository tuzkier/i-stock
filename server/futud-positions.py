#!/usr/bin/env python3
"""只读查询 FutuOpenD 交易账户持仓（不解锁、不下单）。输出 JSON 到 stdout。

用法: python3 server/futud-positions.py [--market HK] [--env REAL|SIMULATE] [--host 127.0.0.1] [--port 11111]

仅做 position_list_query（只读）；不调用任何下单/改单/撤单/解锁接口。
"""
import argparse
import contextlib
import io
import json
import os
import sys

# 与 futud-client.py 一致：强制纯 Python protobuf 解析，避免版本不兼容。
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")


def parse_args():
    parser = argparse.ArgumentParser(description="Read-only position query from local FutuOpenD.")
    parser.add_argument("--market", default="HK", choices=["HK", "US", "CN"])
    parser.add_argument("--env", default="REAL", choices=["REAL", "SIMULATE"])
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
                ret, data = ctx.position_list_query(trd_env=env)
            finally:
                ctx.close()
    except Exception as exc:  # noqa: BLE001 — 顶层守卫，异常转结构化输出
        print(json.dumps({"error": "trade_query_failed", "detail": str(exc)}, ensure_ascii=False))
        return 1

    if ret != RET_OK:
        print(json.dumps({"error": "position_query_failed", "detail": str(data)}, ensure_ascii=False))
        return 1

    fields = ["code", "stock_name", "qty", "can_sell_qty", "cost_price", "nominal_price", "pl_ratio", "pl_val", "market_val"]
    positions = []
    for _, row in data.iterrows():
        item = {}
        for key in fields:
            value = row[key] if key in row else None
            item[key] = value
        positions.append(item)

    print(json.dumps({"market": args.market, "env": args.env, "count": len(positions), "positions": positions}, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
