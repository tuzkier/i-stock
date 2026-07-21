#!/bin/bash
# 全局时间脚本。所有需要时间戳的地方统一使用此脚本。
# 用法: bash scripts/get_time.sh          → 2026-03-22 21:30:00 CST
#       bash scripts/get_time.sh --short   → 21:30
#       bash scripts/get_time.sh --date    → 2026-03-22
case "${1:-}" in
  --short) TZ='Asia/Shanghai' date '+%H:%M' ;;
  --date)  TZ='Asia/Shanghai' date '+%Y-%m-%d' ;;
  *)       TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M:%S CST' ;;
esac
