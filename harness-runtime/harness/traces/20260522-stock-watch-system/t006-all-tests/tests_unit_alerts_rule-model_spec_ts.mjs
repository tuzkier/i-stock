// tests/unit/alerts/rule-model.spec.ts
import assert from "node:assert/strict";
import { describe, it } from "node:test";

// src/domain/alert.ts
var taxonomies = ["price", "change", "technical_indicator", "mts", "scheduled"];
var levels = ["\u89C2\u5BDF", "\u786E\u8BA4", "\u5F3A\u4FE1\u53F7", "\u98CE\u63A7"];
function assertTaxonomy(taxonomy) {
  if (!taxonomies.includes(taxonomy)) {
    throw new Error(`unsupported taxonomy: ${taxonomy}`);
  }
}
function assertLevel(level) {
  if (!levels.includes(level)) {
    throw new Error(`unsupported alert level: ${level}`);
  }
}
function assertThreshold(input) {
  if (!Number.isFinite(input.threshold)) {
    throw new Error(`${input.taxonomy} alert requires numeric threshold`);
  }
}
function assertDirection(input) {
  if (input.direction !== "above" && input.direction !== "below") {
    throw new Error(`${input.taxonomy} alert requires direction`);
  }
}
function normalizeLocalTime(localTime) {
  if (!localTime || !/^\d{2}:\d{2}$/.test(localTime)) {
    throw new Error("scheduled alert requires localTime in HH:mm");
  }
  return localTime;
}
function createId(input, now) {
  return `alert-${input.taxonomy}-${input.symbol}-${now}`;
}
function labelFor(input) {
  if (input.taxonomy === "price") return `${input.symbol} \u4EF7\u683C${input.direction === "below" ? "\u4E0B\u7834" : "\u4E0A\u7A7F"} ${input.threshold}`;
  if (input.taxonomy === "change") return `${input.symbol} \u53D8\u5316${input.direction === "below" ? "\u4F4E\u4E8E" : "\u9AD8\u4E8E"} ${input.threshold}%`;
  if (input.taxonomy === "technical_indicator") {
    return `${input.symbol} ${input.indicator ?? "\u6307\u6807"} ${input.direction === "below" ? "\u4F4E\u4E8E" : "\u9AD8\u4E8E"} ${input.threshold}`;
  }
  if (input.taxonomy === "mts") return `${input.symbol} MTS \u8FBE\u5230 ${input.mtsAlertLevel ?? "elevated"}`;
  return `${input.symbol} \u5B9A\u65F6\u63D0\u9192 ${input.localTime}`;
}
function createAlertRule(input) {
  assertTaxonomy(input.taxonomy);
  assertLevel(input.level);
  const now = input.now ?? Date.now();
  const base = {
    id: createId(input, now),
    symbol: input.symbol,
    label: labelFor(input),
    taxonomy: input.taxonomy,
    level: input.level,
    enabled: true,
    activationState: "enabled",
    triggerState: "idle",
    direction: input.direction ?? "above",
    history: []
  };
  if (input.taxonomy === "price") {
    assertThreshold(input);
    assertDirection(input);
    return {
      ...base,
      price: input.threshold,
      condition: {
        kind: "price",
        direction: input.direction,
        threshold: input.threshold
      }
    };
  }
  if (input.taxonomy === "change") {
    assertThreshold(input);
    assertDirection(input);
    return {
      ...base,
      condition: {
        kind: "change_percent",
        direction: input.direction,
        threshold: input.threshold
      }
    };
  }
  if (input.taxonomy === "technical_indicator") {
    assertThreshold(input);
    assertDirection(input);
    return {
      ...base,
      condition: {
        kind: "technical_indicator",
        indicator: input.indicator ?? "RSI",
        direction: input.direction,
        threshold: input.threshold
      }
    };
  }
  if (input.taxonomy === "mts") {
    return {
      ...base,
      signal: input.mtsAlertLevel === "high" ? "strong-buy" : "buy-watch",
      condition: {
        kind: "mts",
        mtsAlertLevel: input.mtsAlertLevel ?? "elevated"
      }
    };
  }
  const localTime = normalizeLocalTime(input.localTime);
  return {
    ...base,
    condition: {
      kind: "daily_time",
      localTime,
      timezone: "local",
      daysOfWeek: input.daysOfWeek,
      skipIfMarketClosed: input.skipIfMarketClosed
    }
  };
}
function normalizeAlertRule(rule) {
  const taxonomy = rule.taxonomy ?? (rule.signal ? "mts" : "price");
  const activationState = rule.activationState ?? (rule.enabled ? "enabled" : "disabled");
  const triggerState = rule.triggerState ?? (rule.lastTriggeredAt ? "triggered" : "idle");
  return {
    ...rule,
    taxonomy,
    level: rule.level ?? (rule.signal ? "\u5F3A\u4FE1\u53F7" : "\u89C2\u5BDF"),
    condition: rule.condition ?? (rule.signal ? { kind: "mts", mtsAlertLevel: rule.signal === "strong-sell" || rule.signal === "strong-buy" ? "high" : "elevated" } : { kind: "price", direction: rule.direction, threshold: rule.price }),
    activationState,
    triggerState,
    enabled: activationState === "enabled",
    history: rule.history ?? []
  };
}
function appendHistory(rule, event) {
  return {
    ...rule,
    history: [...rule.history ?? [], event]
  };
}
function suspendAlertRulesForArchivedSymbol(alerts, symbol, now = Date.now()) {
  return alerts.map((rawRule) => {
    const rule = normalizeAlertRule(rawRule);
    if (rule.symbol !== symbol || rule.activationState === "suspended_by_archive") return rule;
    return appendHistory(
      {
        ...rule,
        enabled: false,
        activationState: "suspended_by_archive",
        suspendedReason: "suspended_by_archive",
        restoreIntent: rule.activationState === "enabled" ? "enabled" : "disabled"
      },
      { at: now, type: "suspended_by_archive", reason: "\u6807\u7684\u5F52\u6863\uFF0C\u63D0\u9192\u6682\u505C" }
    );
  });
}
function restoreAlertRulesForActiveSymbol(alerts, symbol, now = Date.now()) {
  return alerts.map((rawRule) => {
    const rule = normalizeAlertRule(rawRule);
    if (rule.symbol !== symbol || rule.activationState !== "suspended_by_archive") return rule;
    const activationState = rule.restoreIntent === "disabled" ? "disabled" : "enabled";
    return appendHistory(
      {
        ...rule,
        enabled: activationState === "enabled",
        activationState,
        suspendedReason: void 0
      },
      { at: now, type: "restored", reason: activationState === "enabled" ? "\u6807\u7684\u6062\u590D\uFF0C\u6309\u5F52\u6863\u524D\u610F\u56FE\u542F\u7528" : "\u6807\u7684\u6062\u590D\uFF0C\u4FDD\u6301\u5F52\u6863\u524D\u505C\u7528\u610F\u56FE" }
    );
  });
}
function acknowledgeAlertRule(rule, now = Date.now()) {
  const normalized = normalizeAlertRule(rule);
  return appendHistory(
    {
      ...normalized,
      triggerState: "acknowledged",
      acknowledgedAt: now
    },
    { at: now, type: "acknowledged", reason: "\u7528\u6237\u5DF2\u786E\u8BA4\u63D0\u9192" }
  );
}

// tests/unit/alerts/rule-model.spec.ts
describe("alert rule model", () => {
  it("creates typed price, change, technical, MTS and scheduled rules", () => {
    const base = { symbol: "AAPL", now: 17e11 };
    const price = createAlertRule({ ...base, taxonomy: "price", level: "\u89C2\u5BDF", threshold: 190, direction: "above" });
    const change = createAlertRule({ ...base, taxonomy: "change", level: "\u786E\u8BA4", threshold: 3, direction: "above" });
    const technical = createAlertRule({ ...base, taxonomy: "technical_indicator", level: "\u98CE\u63A7", indicator: "RSI", direction: "below", threshold: 30 });
    const mts = createAlertRule({ ...base, taxonomy: "mts", level: "\u5F3A\u4FE1\u53F7", mtsAlertLevel: "high" });
    const scheduled = createAlertRule({ ...base, taxonomy: "scheduled", level: "\u89C2\u5BDF", localTime: "09:30" });
    assert.equal(price.taxonomy, "price");
    assert.equal(change.taxonomy, "change");
    assert.equal(technical.taxonomy, "technical_indicator");
    assert.equal(mts.condition.mtsAlertLevel, "high");
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
      () => createAlertRule({ symbol: "AAPL", taxonomy: "unknown", level: "\u89C2\u5BDF", threshold: 1 }),
      /unsupported taxonomy/
    );
    assert.throws(
      () => createAlertRule({ symbol: "AAPL", taxonomy: "scheduled", level: "\u89C2\u5BDF" }),
      /scheduled alert requires localTime/
    );
  });
  it("keeps activation and trigger state separate through archive, restore and ack", () => {
    const rule = createAlertRule({ symbol: "AAPL", taxonomy: "price", level: "\u89C2\u5BDF", threshold: 190, direction: "above", now: 1 });
    const triggered = {
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
});
