#!/usr/bin/env node
// 用 FutuOpenD 真实历史 K 线对已注册标的的定制信号规则做长仓回测。
// 用法: node scripts/backtest.mjs <symbol> [range] [--json]
//   symbol: HK.09988 | HK.00700 | HK.03690（或 9988/700/3690 简写）
//   range: 1mo | 3mo | 6mo | 1y (默认 1y)
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { computeTradeSignalEvents, resolveTradeStrategy, runTradeBacktest } from "../src/domain/trade-signals.ts";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2).filter((arg) => !arg.startsWith("--"));
const asJson = process.argv.includes("--json");
const aliases = { "9988": "HK.09988", "700": "HK.00700", "0700": "HK.00700", "3690": "HK.03690" };
const rawSymbol = args[0] ?? "HK.09988";
const symbol = aliases[rawSymbol] ?? rawSymbol.toUpperCase();
const range = args[1] ?? "1y";

const strategy = resolveTradeStrategy(symbol);
if (!strategy) {
  console.error(`未注册的标的: ${symbol}（已注册: HK.09988 / HK.00700 / HK.03690）`);
  process.exit(1);
}

const raw = execFileSync(
  "python3",
  [path.join(root, "server", "futud-client.py"), "--symbol", symbol, "--range", range, "--host", "127.0.0.1", "--port", "11111"],
  { encoding: "utf8", timeout: 120000 }
);

const payload = JSON.parse(raw);
if (payload.error) {
  console.error(`行情获取失败: ${payload.error}`);
  process.exit(1);
}
const bars = payload.bars ?? [];
if (bars.length === 0) {
  console.error("FutuOpenD 返回 0 根 K 线，无法回测。");
  process.exit(1);
}

const report = runTradeBacktest(symbol, bars);
const events = computeTradeSignalEvents(symbol, bars);
const day = (time) => new Date(time * 1000).toISOString().slice(0, 10);
const pct = (value) => (value === null ? "--" : `${value.toFixed(2)}%`);

if (asJson) {
  console.log(JSON.stringify({ range, report, events }, null, 2));
  process.exit(0);
}

console.log(`# ${symbol} ${payload.name ?? ""} 组合信号回测（${report.strategyId} · ${strategy.styleTag}）`);
console.log(`数据: range=${range} · ${report.barsUsed} 根日K · ${day(report.windowStart)} ~ ${day(report.windowEnd)} · 复权=QFQ`);
console.log(`信号: 买入 ${report.buySignals} 次 / 卖出 ${report.sellSignals} 次`);
console.log("");
console.log("信号明细:");
for (const event of events) {
  console.log(`  ${day(event.time)}  ${event.side === "buy" ? "买入" : "卖出"}  @ ${event.price.toFixed(2)}  (${event.reasons.join("；")})`);
}
console.log("");
console.log("交易明细（信号次日开盘成交）:");
for (const trade of report.trades) {
  const tag = trade.closed ? "" : "（未平仓，按期末收盘估值）";
  console.log(`  ${day(trade.entryTime)} 进 ${trade.entryPrice.toFixed(2)} → ${day(trade.exitTime)} 出 ${trade.exitPrice.toFixed(2)}  收益 ${trade.returnPct.toFixed(2)}%${tag}`);
}
console.log("");
console.log(`完成交易: ${report.closedTrades} 笔 | 胜率: ${pct(report.winRate)} | 单笔均益: ${pct(report.averageReturnPct)}`);
console.log(`策略累计: ${pct(report.strategyReturnPct)} | 同期买入持有: ${pct(report.buyHoldReturnPct)}`);
console.log("");
console.log(report.note);
