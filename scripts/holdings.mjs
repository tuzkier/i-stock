#!/usr/bin/env node
// 按 FutuOpenD 真实持仓 × 各标的定制策略，输出每个持仓的当前操作面板（只读，不下单）。
// 用法: node scripts/holdings.mjs [--env REAL|SIMULATE] [--range 1y]
// 说明：点位均由固定策略规则机械计算，仅作技术分析参考，不构成投资建议；买卖与否由你自行判断。
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildFanTState, buildTradeSignalState, resolveTradeStrategy } from "../src/domain/trade-signals.ts";
import { buildObservationIndicators } from "../src/domain/observation.ts";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const env = process.argv.includes("--env") ? process.argv[process.argv.indexOf("--env") + 1] : "REAL";
const range = process.argv.includes("--range") ? process.argv[process.argv.indexOf("--range") + 1] : "1y";
const host = "127.0.0.1";
const port = "11111";

const num = (value) => (value === undefined || value === null || Number.isNaN(Number(value)) ? "--" : Number(value).toFixed(2));
const pct = (value) => (value === undefined || value === null ? "--" : `${Number(value).toFixed(1)}%`);

// TR 的简单平均（与策略引擎口径一致），用于给持仓者算吊灯止损参考。
function latestAtr(bars, period = 20) {
  const tr = bars.map((bar, i) => {
    if (i === 0) return bar.high - bar.low;
    const pc = bars[i - 1].close;
    return Math.max(bar.high - bar.low, Math.abs(bar.high - pc), Math.abs(bar.low - pc));
  });
  if (tr.length < period) return undefined;
  let sum = 0;
  for (let i = tr.length - period; i < tr.length; i += 1) sum += tr[i];
  return sum / period;
}
function highestClose(bars, lookback) {
  const start = Math.max(0, bars.length - lookback);
  let max = -Infinity;
  for (let i = start; i < bars.length; i += 1) max = Math.max(max, bars[i].close);
  return max;
}
// 吊灯止损：近 lookback 日最高收盘 − k×ATR20。对任何持仓者有效，与策略是否模拟在场无关。
function chandelierStop(bars, lookback, trailK) {
  const atr = latestAtr(bars, 20);
  if (atr === undefined) return undefined;
  return highestClose(bars, lookback) - trailK * atr;
}

function fetchPositions() {
  const raw = execFileSync("python3", [path.join(root, "server", "futud-positions.py"), "--market", "HK", "--env", env, "--host", host, "--port", port], {
    encoding: "utf8",
    timeout: 60000
  });
  const payload = JSON.parse(raw);
  if (payload.error) throw new Error(`${payload.error}: ${payload.detail ?? ""}`);
  return payload.positions ?? [];
}

function fetchBars(symbol) {
  const raw = execFileSync("python3", [path.join(root, "server", "futud-client.py"), "--symbol", symbol, "--range", range, "--host", host, "--port", port], {
    encoding: "utf8",
    timeout: 120000
  });
  const payload = JSON.parse(raw);
  if (payload.error) return [];
  return payload.bars ?? [];
}

const positions = fetchPositions();
console.log(`# FutuOpenD ${env} 持仓操作面板（range=${range}）`);
console.log("点位由固定策略规则机械计算，仅作技术分析参考，非投资建议；是否操作由你自行判断。\n");

const covered = [];
const uncovered = [];
for (const pos of positions) {
  const code = String(pos.code ?? "");
  const strategy = resolveTradeStrategy(code);
  if (strategy) covered.push(pos);
  else uncovered.push(pos);
}

for (const pos of covered) {
  const code = String(pos.code);
  const cost = Number(pos.cost_price);
  const now = Number(pos.nominal_price);
  const qty = Number(pos.qty);
  const bars = fetchBars(code);
  const strategy = resolveTradeStrategy(code);
  if (bars.length === 0) {
    console.log(`== ${code} ${pos.stock_name ?? ""} ==  行情不可用，跳过\n`);
    continue;
  }
  const indicators = buildObservationIndicators(bars);
  const state = buildTradeSignalState({ symbol: code, bars, indicators, sourceHealth: { status: "formal" } });
  const L = state.levels;
  console.log(`== ${code} ${pos.stock_name ?? ""} · ${strategy.styleTag} ==`);
  console.log(`  持仓: ${qty} 股 @ 成本 ${num(cost)}｜现价 ${num(now)}｜盈亏 ${pct(pos.pl_ratio)}`);
  console.log(`  策略态势: ${state.stanceLabel}`);
  if (state.holding) {
    // 策略当前判定为持仓：离场线即是对持仓者有效的趋势止损/止盈线。
    if (L.takeProfit !== undefined) console.log(`  止盈离场线: ${num(L.takeProfit)}（收盘跌破即离场，高于策略成本）`);
    if (L.stopLoss !== undefined) console.log(`  止损离场线: ${num(L.stopLoss)}（收盘跌破即离场）`);
    if (L.sellTargetSma !== undefined) console.log(`  卖出目标（站上SMA即卖）: ${num(L.sellTargetSma)}`);
    if (L.addPositionTrigger !== undefined) console.log(`  加仓触发位: ${num(L.addPositionTrigger)}`);
    const stopVs = L.stopLoss ?? L.takeProfit ?? L.exitLine;
    if (stopVs !== undefined) console.log(`  离场线相对你成本: ${pct(((stopVs - cost) / cost) * 100)}`);
  } else if (strategy.config.kind === "mean_revert") {
    console.log(`  策略视为空仓：回归卖出目标≈${num(L.sellTargetSma)}，跌破近 ${strategy.config.lowLookback} 日低点(${num(L.nextBuyTrigger)})才是它的买点。`);
    console.log(`  提示: 你持仓成本 ${num(cost)} 远${cost > now ? "高于" : "低于"}现价，均值回归系统当前不在场，对你的仓位无活跃止损。`);
  } else {
    // 趋势跟随/防守，策略当前空仓（多为下跌中已离场）。对持仓者给出趋势再入场线与诚实说明。
    console.log(`  策略视为空仓（趋势已在下跌中离场）：再入场线=突破近 ${strategy.config.lookback} 日高点 ${num(L.nextBuyTrigger)}。`);
    console.log(`  提示: 纯趋势跟随此刻不持有本票；它对当前这波下跌不设“抄底止损”，只在重新突破 ${num(L.nextBuyTrigger)} 时才再入场。`);
  }
  // 对持仓者补一条与策略模拟无关的止损参考（突破/趋势/防守型用吊灯止损；均值回归不适用）。
  if (strategy.config.kind === "breakout_trail") {
    const stop = chandelierStop(bars, strategy.config.lookback, strategy.config.trailAtrMultiple);
    if (stop !== undefined) {
      const breached = now < stop;
      console.log(
        `  持仓者止损参考(吊灯 近${strategy.config.lookback}日高−${strategy.config.trailAtrMultiple}×ATR20): ${num(stop)}` +
          `｜相对现价 ${pct(((stop - now) / now) * 100)}` +
          (breached ? "（已跌破：趋势止损意义上应已离场）" : "（收盘跌破即触发趋势离场）")
      );
    }
  }
  // 反T 降成本决策：仅震荡回归型标的启用（实证有正价差）；趋势票实证会卖飞，显式声明不做。
  const fan = buildFanTState(code, bars);
  if (fan.enabled) {
    console.log(
      `  反T降成本: 近1年 ${fan.completedRounds} 回合(胜 ${fan.winRounds})，累计价差 ${fan.totalSpreadPct.toFixed(1)}%` +
        (fan.worstSpreadPct === null ? "" : `，最差单回合 ${fan.worstSpreadPct.toFixed(1)}%`)
    );
    if (fan.phase === "full") {
      console.log(`    当前满仓阶段：高卖触发位 ${num(fan.sellTrigger)}（收盘站上即减一档、等回落买回降成本）`);
    } else {
      console.log(
        `    当前已减仓阶段：买回触发位 ${num(fan.buyBackTrigger)}（收盘跌破即买回）｜认错追高位 ${num(fan.chaseStop)}（涨过即买回防卖飞）`
      );
    }
  } else {
    console.log(`  反T降成本: 不适用——本票实证反T为负期望（趋势票易卖飞），只做趋势持有与离场，不高抛低吸。`);
  }
  console.log("");
}

if (uncovered.length > 0) {
  console.log("== 无定制策略的持仓（不输出信号）==");
  for (const pos of uncovered) {
    console.log(`  ${pos.code} ${pos.stock_name ?? ""}｜${Number(pos.qty)} 股 @ ${num(pos.cost_price)}｜现价 ${num(pos.nominal_price)}｜盈亏 ${pct(pos.pl_ratio)}`);
  }
}
