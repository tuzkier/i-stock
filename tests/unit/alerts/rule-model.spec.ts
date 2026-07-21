import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  acknowledgeAlertRule,
  createAlertRule,
  evaluateAlertRules,
  restoreAlertRulesForActiveSymbol,
  suspendAlertRulesForArchivedSymbol
} from "../../../src/domain/alert.ts";
import type { AlertRule } from "../../../src/types.ts";

describe("alert rule model", () => {
  it("creates typed price, change, technical, MTS and scheduled rules", () => {
    const base = { symbol: "AAPL", now: 1_700_000_000_000 };
    const price = createAlertRule({ ...base, taxonomy: "price", level: "观察", threshold: 190, direction: "above" });
    const change = createAlertRule({ ...base, taxonomy: "change", level: "确认", threshold: 3, direction: "above" });
    const technical = createAlertRule({ ...base, taxonomy: "technical_indicator", level: "风控", indicator: "RSI", direction: "below", threshold: 30 });
    const mts = createAlertRule({ ...base, taxonomy: "mts", level: "强信号", mtsAlertLevel: "强信号" });
    const scheduled = createAlertRule({ ...base, taxonomy: "scheduled", level: "观察", localTime: "09:30" });

    assert.equal(price.taxonomy, "price");
    assert.equal(change.taxonomy, "change");
    assert.equal(technical.taxonomy, "technical_indicator");
    assert.equal(mts.condition.mtsAlertLevel, "强信号");
    assert.equal(scheduled.condition.kind, "daily_time");
    assert.equal(scheduled.condition.timezone, "local");
    for (const rule of [price, change, technical, mts, scheduled]) {
      assert.equal(rule.activationState, "enabled");
      assert.equal(rule.triggerState, "idle");
      assert.deepEqual(rule.history, []);
    }
  });

  it("rejects invalid taxonomy and scheduled condition gaps", () => {
    assert.throws(
      () => createAlertRule({ symbol: "AAPL", taxonomy: "unknown" as AlertRule["taxonomy"], level: "观察", threshold: 1 }),
      /unsupported taxonomy/
    );
    assert.throws(
      () => createAlertRule({ symbol: "AAPL", taxonomy: "scheduled", level: "观察" }),
      /scheduled alert requires localTime/
    );
  });

  it("keeps activation and trigger state separate through archive, restore and ack", () => {
    const rule = createAlertRule({ symbol: "AAPL", taxonomy: "price", level: "观察", threshold: 190, direction: "above", now: 1 });
    const triggered: AlertRule = {
      ...rule,
      triggerState: "triggered",
      lastTriggeredAt: 2,
      triggerReason: "price 191 crossed above 190",
      history: [{ at: 2, type: "triggered", reason: "price 191 crossed above 190" }]
    };

    const suspended = suspendAlertRulesForArchivedSymbol([triggered], "AAPL", 3)[0];
    assert.equal(suspended.activationState, "suspended_by_archive");
    assert.equal(suspended.triggerState, "triggered");
    assert.equal(suspended.restoreIntent, "enabled");
    assert.equal(suspended.history.at(-1)?.type, "suspended_by_archive");

    const restored = restoreAlertRulesForActiveSymbol([suspended], "AAPL", 4)[0];
    assert.equal(restored.activationState, "enabled");
    assert.equal(restored.triggerState, "triggered");

    const acknowledged = acknowledgeAlertRule(restored, 5);
    assert.equal(acknowledged.activationState, "enabled");
    assert.equal(acknowledged.triggerState, "acknowledged");
    assert.equal(acknowledged.acknowledgedAt, 5);
    assert.equal(acknowledged.history.at(-1)?.type, "acknowledged");
  });

  it("allows scheduled rules to trigger again on the next eligible local day", () => {
    const firstNow = new Date("2026-06-05T10:00:00").getTime();
    const secondNow = new Date("2026-06-08T10:00:00").getTime();
    const rule = createAlertRule({
      symbol: "AAPL",
      taxonomy: "scheduled",
      level: "观察",
      localTime: "09:30",
      daysOfWeek: [1, 5],
      skipIfMarketClosed: true,
      now: firstNow - 60_000
    });

    const first = evaluateAlertRules([rule], { symbol: "AAPL", now: firstNow })[0];
    const acknowledged = acknowledgeAlertRule(first, firstNow + 1_000);
    const second = evaluateAlertRules([acknowledged], { symbol: "AAPL", now: secondNow })[0];

    assert.equal(first.triggerState, "triggered");
    assert.equal(second.triggerState, "triggered");
    assert.notEqual(second.lastScheduledTriggerKey, first.lastScheduledTriggerKey);
    assert.equal(second.history.filter((event) => event.type === "triggered").length, 2);
  });
});
