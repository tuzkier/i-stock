import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { MarketObservation } from "../../../src/domain/observation.ts";
import { buildTencentTradePlan, isTencent700Symbol } from "../../../src/domain/tencent-trade-plan.ts";
import type { PriceBar, SourceHealth } from "../../../src/types.ts";

function sourceHealth(status: SourceHealth["status"] = "formal"): SourceHealth {
  return {
    status,
    affectedObjects: status === "formal" ? [] : ["chart", "mts", "alerts"],
    retryState: {
      attempt: status === "formal" ? 0 : 1,
      canRetry: status !== "formal"
    },
    degradationReason: status === "formal" ? undefined : "fixture degraded"
  };
}

function trendBars({
  count = 140,
  start = 300,
  step = 1.2,
  volumeBase = 10_000_000,
  latePullback = false
}: {
  count?: number;
  start?: number;
  step?: number;
  volumeBase?: number;
  latePullback?: boolean;
} = {}): PriceBar[] {
  return Array.from({ length: count }, (_, index) => {
    const pullback = latePullback && index > count - 16 ? (index - (count - 16)) * Math.abs(step) * 1.8 : 0;
    const close = start + index * step + Math.sin(index / 5) * 2 - pullback;
    const open = close - step * 0.25;
    return {
      time: 1_700_000_000 + index * 86_400,
      open,
      high: Math.max(open, close) + 2.4,
      low: Math.min(open, close) - 2.2,
      close,
      volume: volumeBase + index * 12_000
    };
  });
}

function observation(symbol: string, bars: PriceBar[], status: SourceHealth["status"] = "formal"): MarketObservation {
  return {
    symbol,
    bars,
    sourceHealth: sourceHealth(status),
    latestBar: bars.at(-1),
    previousBar: bars.at(-2),
    indicators: {
      ema20: [],
      ema60: [],
      rsi14: [],
      macdHistogram: [],
      atr14: []
    }
  };
}

describe("Tencent 0700.HK trade plan", () => {
  it("recognizes 700.hk aliases", () => {
    assert.equal(isTencent700Symbol("700.hk"), true);
    assert.equal(isTencent700Symbol("0700.HK"), true);
    assert.equal(isTencent700Symbol("HK.00700"), true);
    assert.equal(isTencent700Symbol("AAPL"), false);
  });

  it("returns a buy-side plan in a constructive uptrend", () => {
    const plan = buildTencentTradePlan(observation("0700.HK", trendBars({ start: 360, step: 0.35, latePullback: true })));

    assert.equal(plan.status, "ready");
    assert.match(plan.action, /buy|hold/);
    assert.ok(plan.levels.buyTrigger || plan.levels.buyZone);
    assert.ok(plan.confidence > 0);
    assert.doesNotMatch(plan.nonAdvice, /收益承诺|胜率/);
  });

  it("returns a sell or risk-control plan in a downtrend", () => {
    const plan = buildTencentTradePlan(observation("700.hk", trendBars({ start: 620, step: -1.35 })));

    assert.equal(plan.status, "ready");
    assert.match(plan.action, /sell|risk/);
    assert.ok(plan.levels.sellTrigger);
    assert.ok(plan.trendScore !== null && plan.trendScore < 0);
  });

  it("does not output levels when source is degraded", () => {
    const plan = buildTencentTradePlan(observation("0700.HK", trendBars(), "unavailable"));

    assert.equal(plan.status, "source_degraded");
    assert.equal(plan.action, "wait");
    assert.deepEqual(plan.levels, {});
  });

  it("does not apply to other symbols", () => {
    const plan = buildTencentTradePlan(observation("AAPL", trendBars()));

    assert.equal(plan.status, "not_target_symbol");
    assert.equal(plan.action, "wait");
  });
});
