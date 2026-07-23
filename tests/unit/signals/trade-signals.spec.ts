import assert from "node:assert/strict";
import test from "node:test";
import {
  buildFanTState,
  buildTradeSignalState,
  computeTradeSignalEvents,
  resolveTradeStrategy,
  runTradeBacktest
} from "../../../src/domain/trade-signals.ts";
import { buildObservationIndicators } from "../../../src/domain/observation.ts";
import type { PriceBar } from "../../../src/types.ts";

function bar(index: number, close: number): PriceBar {
  const open = close * 0.995;
  return {
    time: 1_700_000_000 + index * 86_400,
    open,
    high: Math.max(open, close) * 1.005,
    low: Math.min(open, close) * 0.995,
    close,
    volume: 1_000_000
  };
}

// 震荡回归型序列：围绕 400 宽幅震荡，周期性砸出新低再回归均线，供均值回归策略触发。
function oscillatingBars(): PriceBar[] {
  const closes: number[] = [];
  for (let i = 0; i < 220; i += 1) {
    closes.push(400 + Math.sin(i / 9) * 30 + Math.sin(i / 3.1) * 6);
  }
  return closes.map((close, index) => bar(index, close));
}

// 持续阴跌后站上长期均线再突破的序列：前段跌破 SMA60（门控应拦截所有突破），末段反转站上。
function downtrendThenRecoverBars(): PriceBar[] {
  const closes: number[] = [];
  let price = 150;
  for (let i = 0; i < 150; i += 1) {
    price += i % 5 === 4 ? 1.2 : -1.1;
    closes.push(price);
  }
  for (let i = 0; i < 70; i += 1) {
    price += i % 4 === 3 ? -0.7 : 1.6;
    closes.push(price);
  }
  return closes.map((close, index) => bar(index, close));
}

test("策略注册：六只标的各自解析到不同策略，含新增 1888", () => {
  assert.equal(resolveTradeStrategy("HK.09988")?.key, "alibaba");
  assert.equal(resolveTradeStrategy("0700.HK")?.key, "tencent");
  assert.equal(resolveTradeStrategy("HK.03690")?.key, "meituan");
  assert.equal(resolveTradeStrategy("HK.00981")?.key, "smic");
  assert.equal(resolveTradeStrategy("HK.01810")?.key, "xiaomi");
  assert.equal(resolveTradeStrategy("HK.01888")?.key, "kingboard");
  assert.equal(resolveTradeStrategy("1888.HK")?.key, "kingboard");
  assert.equal(resolveTradeStrategy("US.AAPL"), undefined);
  // 强单边票（中芯 / 建滔）实证后改用趋势跟随，不再是均值回归；口径 = breakout_trail。
  assert.equal(resolveTradeStrategy("HK.00981")?.config.kind, "breakout_trail");
  assert.equal(resolveTradeStrategy("HK.01888")?.config.kind, "breakout_trail");
});

test("腾讯均值回归：新低触发买入，站上 SMA20/止损/超时触发卖出且严格交替", () => {
  const bars = oscillatingBars();
  const events = computeTradeSignalEvents("HK.00700", bars);
  assert.ok(events.length >= 2, `震荡序列应产生信号，实际 ${events.length}`);
  assert.equal(events[0].side, "buy");
  for (let i = 1; i < events.length; i += 1) {
    assert.notEqual(events[i].side, events[i - 1].side, "相邻信号方向必须交替");
  }
  const buy = events[0];
  assert.ok(buy.reasons.some((reason) => reason.includes("新低")), "买入原因必须为超跌新低");
  const sells = events.filter((event) => event.side === "sell");
  assert.ok(
    sells.every((event) => /SMA20|止损|超时/.test(event.reasons.join())),
    "卖出原因必须是目标/止损/超时之一"
  );
});

test("腾讯均值回归：无前视偏差与回测确定性", () => {
  const bars = oscillatingBars();
  const full = computeTradeSignalEvents("HK.00700", bars);
  for (const cut of [150, 180, bars.length - 10]) {
    const prefix = computeTradeSignalEvents("HK.00700", bars.slice(0, cut));
    assert.deepEqual(prefix, full.filter((event) => event.index < cut), `截断到 ${cut} 后应为完整序列前缀`);
  }
  assert.deepEqual(runTradeBacktest("HK.00700", bars), runTradeBacktest("HK.00700", bars));
});

test("腾讯状态卡：持仓时给出目标位/止损位/剩余持有，空仓时给跌破即买触发位", () => {
  const bars = oscillatingBars();
  const indicators = buildObservationIndicators(bars);
  const state = buildTradeSignalState({ symbol: "HK.00700", bars, indicators });
  assert.equal(state.status, "ready");
  assert.equal(state.buyTriggerDirection, "dip");
  if (state.holding) {
    assert.ok(Number.isFinite(state.levels.stopLoss), "持仓必须有固定止损位");
    assert.ok(Number.isFinite(state.levels.sellTargetSma), "持仓必须有 SMA20 目标位");
    assert.ok(state.holdBarsMax !== undefined && (state.holdBarsUsed ?? 0) <= state.holdBarsMax);
  } else {
    assert.ok(Number.isFinite(state.levels.nextBuyTrigger), "空仓必须给出跌破即买触发位");
  }
  assert.ok(state.nonAdvice.includes("不构成投资建议"));
});

test("美团防守门控：价格在 SMA60 下方时不产生任何买入信号", () => {
  const bars = downtrendThenRecoverBars();
  const events = computeTradeSignalEvents("HK.03690", bars);
  const closes = bars.map((item) => item.close);
  const sma60 = closes.map((_, index) => {
    if (index < 59) return Number.NaN;
    return closes.slice(index - 59, index + 1).reduce((sum, value) => sum + value, 0) / 60;
  });
  for (const event of events.filter((item) => item.side === "buy")) {
    assert.ok(
      bars[event.index].close > sma60[event.index],
      `买入信号 index=${event.index} 必须发生在 SMA60 上方（门控生效）`
    );
  }
  // 前段阴跌区（价格位于 SMA60 下方）不得出现买入
  const earlyBuys = events.filter((item) => item.side === "buy" && item.index < 140);
  assert.equal(earlyBuys.length, 0, "阴跌段（SMA60 下方）不得触发买入");
});

test("反T：仅腾讯启用；回合先卖后买、阶段与触发位互斥暴露", () => {
  const bars = oscillatingBars();
  assert.equal(buildFanTState("HK.09988", bars).enabled, false, "非注册反T标的不启用");
  const state = buildFanTState("HK.00700", bars);
  assert.equal(state.enabled, true);
  assert.ok(state.completedRounds >= 1, "震荡序列应产生反T回合");
  for (const round of state.rounds) {
    assert.ok(round.buyTime > round.sellTime, "每个回合必须先卖后买回");
    const expected = ((round.sellPrice - round.buyPrice) / round.buyPrice) * 100;
    assert.ok(Math.abs(round.spreadPct - expected) < 1e-9, "价差口径一致");
  }
  if (state.phase === "full") {
    assert.ok(Number.isFinite(state.sellTrigger), "满仓阶段必须给高卖触发位");
    assert.equal(state.buyBackTrigger, undefined);
  } else {
    assert.ok(Number.isFinite(state.buyBackTrigger), "已卖出阶段必须给买回触发位");
    assert.ok(Number.isFinite(state.chaseStop), "已卖出阶段必须给追高认错位");
    assert.ok((state.chaseStop as number) > (state.soldRefPrice as number), "认错位必须高于卖出参考价");
  }
  assert.equal(
    state.totalSpreadPct,
    state.rounds.reduce((sum, round) => sum + round.spreadPct, 0)
  );
});

test("反T：无前视偏差（前缀回合是完整回合的前缀）", () => {
  const bars = oscillatingBars();
  const full = buildFanTState("HK.00700", bars);
  for (const cut of [160, 190]) {
    const prefix = buildFanTState("HK.00700", bars.slice(0, cut));
    const expected = full.rounds.filter((round) => {
      const lastTime = bars[cut - 1].time;
      return round.buyTime <= lastTime;
    });
    assert.deepEqual(prefix.rounds, expected, `截断到 ${cut} 后回合应为完整序列前缀`);
  }
});

test("美团状态卡：空仓触发位同时约束 20 日高点与 SMA60 门控", () => {
  const bars = downtrendThenRecoverBars().slice(0, 150);
  const indicators = buildObservationIndicators(bars);
  const state = buildTradeSignalState({ symbol: "HK.03690", bars, indicators });
  assert.equal(state.status, "ready");
  assert.equal(state.holding, false, "阴跌段末尾应为空仓");
  assert.ok(Number.isFinite(state.levels.nextBuyTrigger));
  assert.ok(Number.isFinite(state.levels.gateLevel), "必须暴露 SMA60 门控值");
  assert.ok(
    (state.levels.nextBuyTrigger as number) >= (state.levels.gateLevel as number),
    "触发位必须不低于门控线（需同时满足两个条件）"
  );
});

// 阶梯式上行序列：先攀升创新高（触发趋势跟随买入），末段回落跌破跟踪线（触发离场），供 1888 趋势跟随测试。
function trendUpThenPullbackBars(): PriceBar[] {
  const closes: number[] = [];
  let price = 20;
  for (let i = 0; i < 160; i += 1) {
    price += i % 4 === 3 ? -0.8 : 1.4; // 净上行、带正常回撤
    closes.push(price);
  }
  for (let i = 0; i < 40; i += 1) {
    price -= 1.6; // 末段趋势反转，触发跟踪离场
    closes.push(price);
  }
  return closes.map((close, index) => bar(index, close));
}

test("建滔 1888 趋势跟随：创新高突破买入、跌破跟踪线卖出，且回测暴露最大回撤", () => {
  const bars = trendUpThenPullbackBars();
  const events = computeTradeSignalEvents("HK.01888", bars);
  assert.ok(events.length >= 2, "上行后反转序列应至少产生一买一卖");
  assert.equal(events[0].side, "buy", "首个信号应为突破买入");
  // 严格交替：买卖不连发同向
  for (let i = 1; i < events.length; i += 1) {
    assert.notEqual(events[i].side, events[i - 1].side, "信号必须严格交替");
  }
  const report = runTradeBacktest("HK.01888", bars);
  assert.ok(report.buySignals > 0 && report.sellSignals > 0, "1888 必须输出买卖信号，非仅观察位");
  assert.equal(typeof report.maxDrawdownPct, "number", "回测须暴露策略最大回撤");
  assert.equal(typeof report.buyHoldMaxDrawdownPct, "number", "回测须暴露买入持有回撤基准");
  assert.ok((report.maxDrawdownPct as number) <= 0, "最大回撤应为 ≤0 的口径");
});
