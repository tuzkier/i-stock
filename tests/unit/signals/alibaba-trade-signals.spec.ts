import assert from "node:assert/strict";
import test from "node:test";
import {
  buildAlibabaSignalState,
  computeAlibabaSignalEvents,
  isAlibaba9988Symbol,
  runAlibabaBacktest
} from "../../../src/domain/alibaba-trade-signals.ts";
import { buildObservationIndicators } from "../../../src/domain/observation.ts";
import type { PriceBar } from "../../../src/types.ts";

function bar(index: number, close: number, volume = 1_000_000): PriceBar {
  const open = close * 0.995;
  return {
    time: 1_700_000_000 + index * 86_400,
    open,
    high: Math.max(open, close) * 1.005,
    low: Math.min(open, close) * 0.995,
    close,
    volume
  };
}

// 先横盘建立指标基线，再阴跌、带回调地反转上涨（触发买入），随后转入下跌破位（触发卖出）。
// 上涨段采用「涨三回一」锯齿，避免 RSI 被单边行情钉死在过热区。
function trendReversalBars(): PriceBar[] {
  const closes: number[] = [];
  let price = 100;
  for (let i = 0; i < 70; i += 1) {
    price = 100 + Math.sin(i / 5) * 1.5;
    closes.push(price);
  }
  for (let i = 0; i < 25; i += 1) {
    price -= 0.9;
    closes.push(price);
  }
  for (let i = 0; i < 60; i += 1) {
    price += i % 4 === 3 ? -0.8 : 1.1;
    closes.push(price);
  }
  for (let i = 0; i < 35; i += 1) {
    price += i % 5 === 4 ? 0.5 : -1.4;
    closes.push(price);
  }
  return closes.map((close, index) => bar(index, close));
}

test("symbol 归一：仅识别阿里巴巴港股写法", () => {
  assert.equal(isAlibaba9988Symbol("HK.09988"), true);
  assert.equal(isAlibaba9988Symbol("9988.hk"), true);
  assert.equal(isAlibaba9988Symbol(" 09988.HK "), true);
  assert.equal(isAlibaba9988Symbol("BABA"), false);
  assert.equal(isAlibaba9988Symbol("HK.00700"), false);
});

test("趋势反转序列产生先买后卖的信号且方向正确", () => {
  const bars = trendReversalBars();
  const events = computeAlibabaSignalEvents(bars);

  assert.ok(events.length >= 2, `应至少产生 2 个信号，实际 ${events.length}`);
  const firstBuy = events.find((event) => event.side === "buy");
  assert.ok(firstBuy, "上涨段应触发买入信号");
  const sellAfterBuy = events.find((event) => event.side === "sell" && event.index > (firstBuy?.index ?? 0));
  assert.ok(sellAfterBuy, "回落段应在买入后触发卖出信号");
  for (const event of events) {
    assert.ok(event.reasons.length > 0, "每个信号必须携带规则原因");
    assert.equal(event.time, bars[event.index].time, "信号时间必须与对应 K 线对齐");
  }
});

test("数据不足时不产生信号", () => {
  const bars = trendReversalBars().slice(0, 60);
  assert.deepEqual(computeAlibabaSignalEvents(bars), []);
});

test("无前视偏差：前缀数据计算的信号是完整数据信号的前缀", () => {
  const bars = trendReversalBars();
  const full = computeAlibabaSignalEvents(bars);
  for (const cut of [100, 120, 140, bars.length - 10]) {
    const prefix = computeAlibabaSignalEvents(bars.slice(0, cut));
    const expected = full.filter((event) => event.index < cut);
    assert.deepEqual(prefix, expected, `截断到 ${cut} 根后信号应与完整序列前缀一致`);
  }
});

test("回测确定性：同数据同参数重复运行结果一致", () => {
  const bars = trendReversalBars();
  const first = runAlibabaBacktest(bars);
  const second = runAlibabaBacktest(bars);
  assert.deepEqual(first, second);
});

test("回测按次日开盘成交且统计口径自洽", () => {
  const bars = trendReversalBars();
  const report = runAlibabaBacktest(bars);
  const events = computeAlibabaSignalEvents(bars);

  assert.equal(report.buySignals, events.filter((event) => event.side === "buy").length);
  assert.equal(report.sellSignals, events.filter((event) => event.side === "sell").length);
  assert.ok(report.trades.length >= 1, "趋势反转序列应产生至少一笔交易");

  const firstTrade = report.trades[0];
  const firstBuy = events.find((event) => event.side === "buy");
  assert.ok(firstBuy);
  const nextBar = bars[(firstBuy?.index ?? 0) + 1];
  assert.equal(firstTrade.entryTime, nextBar.time, "进场时间应为信号次日");
  assert.equal(firstTrade.entryPrice, nextBar.open, "进场价应为信号次日开盘价");

  for (const trade of report.trades) {
    const expected = ((trade.exitPrice - trade.entryPrice) / trade.entryPrice) * 100;
    assert.ok(Math.abs(trade.returnPct - expected) < 1e-9, "单笔收益率口径应一致");
  }

  const closed = report.trades.filter((trade) => trade.closed);
  assert.equal(report.closedTrades, closed.length);
  if (closed.length > 0) {
    const wins = closed.filter((trade) => trade.returnPct > 0).length;
    assert.equal(report.winRate, (wins / closed.length) * 100);
  }
});

test("信号严格交替：买入后才可能卖出，不连发同向信号", () => {
  const events = computeAlibabaSignalEvents(trendReversalBars());
  assert.ok(events.length >= 2);
  assert.equal(events[0].side, "buy", "首个信号必为买入");
  for (let i = 1; i < events.length; i += 1) {
    assert.notEqual(events[i].side, events[i - 1].side, "相邻信号方向必须交替");
  }
});

test("点位输出：持仓给分离的止损/止盈位，空仓给买入触发位", () => {
  const bars = trendReversalBars();
  const indicators = buildObservationIndicators(bars);
  const state = buildAlibabaSignalState({ symbol: "HK.09988", bars, indicators });
  assert.equal(state.status, "ready");
  if (state.holding) {
    assert.ok(Number.isFinite(state.levels.entryPrice), "持仓时必须给出信号成本参考");
    assert.ok(Number.isFinite(state.levels.exitLine), "持仓时必须给出当前生效离场线");
    assert.ok(Number.isFinite(state.levels.peakClose));
    const hasStop = state.levels.stopLoss !== undefined;
    const hasTake = state.levels.takeProfit !== undefined;
    assert.ok(hasStop !== hasTake, "止损位与止盈位必须互斥、有且只有一个生效");
    if (hasTake) {
      assert.ok((state.levels.takeProfit as number) > (state.levels.entryPrice as number), "止盈位必须高于信号成本，低于成本不得称止盈");
      assert.equal(state.levels.takeProfit, state.levels.exitLine);
    }
    if (hasStop) {
      assert.ok((state.levels.stopLoss as number) <= (state.levels.entryPrice as number), "止损位不得高于信号成本");
      assert.equal(state.levels.stopLoss, state.levels.exitLine);
    }
    assert.ok(Number.isFinite(state.levels.addPositionTrigger), "持仓时必须给出加仓触发位");
    if (state.levels.pullbackZoneLow !== undefined) {
      assert.ok((state.levels.pullbackZoneLow as number) < (state.levels.pullbackZoneHigh as number), "回调观察区下沿必须低于上沿");
      assert.ok((state.levels.pullbackZoneLow as number) >= (state.levels.exitLine as number), "回调观察区不得低于离场线");
    }
  } else {
    assert.ok(Number.isFinite(state.levels.nextBuyTrigger), "空仓时必须给出买入触发位");
  }
  assert.ok(Number.isFinite(state.levels.sellWatchOne), "必须给出阶段减仓观察位一");
  assert.ok((state.levels.sellWatchTwo as number) > (state.levels.sellWatchOne as number), "观察位二必须高于观察位一");
  assert.ok(Number.isFinite(state.levels.latestAtr));
});

test("信号状态卡：非目标标的 / 降级来源 / 数据不足的守卫", () => {
  const bars = trendReversalBars();
  const indicators = buildObservationIndicators(bars);

  const notTarget = buildAlibabaSignalState({ symbol: "US.AAPL", bars, indicators });
  assert.equal(notTarget.status, "not_target_symbol");

  const degraded = buildAlibabaSignalState({
    symbol: "HK.09988",
    bars,
    indicators,
    sourceHealth: { status: "stale", affectedObjects: [] } as never
  });
  assert.equal(degraded.status, "source_degraded");

  const insufficient = buildAlibabaSignalState({ symbol: "HK.09988", bars: bars.slice(0, 30), indicators });
  assert.equal(insufficient.status, "data_insufficient");

  const ready = buildAlibabaSignalState({ symbol: "HK.09988", bars, indicators });
  assert.equal(ready.status, "ready");
  assert.ok(ready.nonAdvice.includes("不构成投资建议"));
  assert.ok(ready.events.length >= 2);
  assert.ok(ready.stanceLabel.length > 0);
});
