import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { createAlertRule, evaluateAlertRules } from "../../../src/domain/alert.ts";
import type { AlertRule, MtsExplanation } from "../../../src/types.ts";

const mtsHigh: MtsExplanation = {
  trendState: "bullish",
  mtsScore: 78,
  scoreBand: "strong_positive",
  signalType: "technical_alert",
  alertLevel: "强信号",
  reasonCodes: ["TREND_ABOVE_EMA"],
  reasons: [],
  invalidators: [],
  displayLabel: "强正向技术提醒",
  technicalReminder: "MTS 仅用于技术提醒和风险观察，不构成收益承诺或确定性买卖建议。",
  interpretability: {
    summary: "提醒等级由趋势、动量、量能和波动率共振计算。",
    reasonCount: 0,
    invalidatorCount: 0,
    technicalLevels: {
      upperWatch: 190,
      middleWatch: 180,
      riskThreshold: 170
    }
  },
  registryVersion: 2
};

describe("alert trigger replay", () => {
  it("records triggered and missed scheduled history without firing disabled or archived rules", () => {
    const now = new Date("2026-06-06T10:30:00").getTime();
    const price = createAlertRule({ symbol: "AAPL", taxonomy: "price", level: "观察", threshold: 190, direction: "above", now: now - 10_000 });
    const mts = createAlertRule({ symbol: "AAPL", taxonomy: "mts", level: "强信号", mtsAlertLevel: "强信号", now: now - 10_000 });
    const scheduled = createAlertRule({ symbol: "AAPL", taxonomy: "scheduled", level: "观察", localTime: "09:30", now: now - 86_400_000 });
    const disabled = { ...price, id: "disabled", activationState: "disabled" as const, enabled: false };
    const archived = { ...price, id: "archived", activationState: "suspended_by_archive" as const, enabled: false };

    const evaluated = evaluateAlertRules([price, mts, scheduled, disabled, archived], {
      symbol: "AAPL",
      latestPrice: 191,
      previousClose: 180,
      indicators: { RSI: 45 },
      mts: mtsHigh,
      now
    });

    assert.equal(evaluated[0].triggerState, "triggered");
    assert.match(evaluated[0].triggerReason ?? "", /price/);
    assert.equal(evaluated[1].triggerState, "triggered");
    assert.match(evaluated[1].triggerReason ?? "", /MTS/);
    assert.equal(evaluated[2].triggerState, "idle");
    assert.equal(evaluated[2].history.some((event) => event.type === "missed_while_closed"), true);
    assert.equal(evaluated[2].lastTriggeredAt, undefined);
    assert.equal(evaluated[3].triggerState, "idle");
    assert.equal(evaluated[4].triggerState, "idle");
  });

  it("does not duplicate triggered history for an already triggered rule", () => {
    const now = Date.now();
    const rule = createAlertRule({ symbol: "AAPL", taxonomy: "price", level: "观察", threshold: 190, direction: "above", now });
    const first = evaluateAlertRules([rule], { symbol: "AAPL", latestPrice: 191, previousClose: 180, now })[0];
    const second = evaluateAlertRules([first], { symbol: "AAPL", latestPrice: 192, previousClose: 180, now: now + 1000 })[0];

    assert.equal(first.history.length, 1);
    assert.equal(second.history.length, 1);
  });
});
