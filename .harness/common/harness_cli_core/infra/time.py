from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo


def today() -> str:
    return dt.datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")


def now_iso() -> str:
    return dt.datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
