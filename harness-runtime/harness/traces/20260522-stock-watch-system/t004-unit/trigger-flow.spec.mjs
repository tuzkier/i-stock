// tests/replay/alerts/trigger-flow.spec.ts
import assert from "node:assert/strict";
import { describe, it } from "node:test";

// src/domain/alert.ts
var taxonomies = ["price", "change", "technical_indicator", "mts", "scheduled"];
var levels = ["\u89C2\u5BDF", "\u786E\u8BA4", "\u5F3A\u4FE1\u53F7", "\u98CE\u63A7"];
var alertLevelRank = {
  none: 0,
  watch: 1,
  elevated: 2,
  high: 3
};
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
function matchesDirection(value, threshold, direction) {
  if (!Number.isFinite(value) || !Number.isFinite(threshold)) return false;
  return direction === "below" ? value <= threshold : value >= threshold;
}
function timeToMinutes(value) {
  const [hour, minute] = value.split(":").map(Number);
  return hour * 60 + minute;
}
function evaluateRule(rule, input) {
  const condition = rule.condition;
  if (!condition) return "";
  if (condition.kind === "price" && matchesDirection(input.latestPrice, condition.threshold, condition.direction)) {
    return `price ${input.latestPrice} crossed ${condition.direction} ${condition.threshold}`;
  }
  if (condition.kind === "change_percent" && Number.isFinite(input.latestPrice) && Number.isFinite(input.previousClose) && input.previousClose) {
    const percent = (input.latestPrice - input.previousClose) / input.previousClose * 100;
    if (matchesDirection(percent, condition.threshold, condition.direction)) return `change ${percent.toFixed(2)}% crossed ${condition.direction} ${condition.threshold}%`;
  }
  if (condition.kind === "technical_indicator") {
    const indicatorValue = input.indicators?.[condition.indicator ?? "RSI"];
    if (matchesDirection(indicatorValue, condition.threshold, condition.direction)) {
      return `${condition.indicator} ${indicatorValue} crossed ${condition.direction} ${condition.threshold}`;
    }
  }
  if (condition.kind === "mts") {
    const required = alertLevelRank[condition.mtsAlertLevel ?? "elevated"];
    const actual = alertLevelRank[input.mts?.alertLevel ?? "none"];
    if (actual >= required) return `MTS alert level ${input.mts?.alertLevel} reached ${condition.mtsAlertLevel}`;
  }
  if (condition.kind === "daily_time" && condition.localTime) {
    const now = new Date(input.now ?? Date.now());
    const todayMinutes = now.getHours() * 60 + now.getMinutes();
    const scheduledMinutes = timeToMinutes(condition.localTime);
    if (todayMinutes >= scheduledMinutes) return `scheduled alert due at ${condition.localTime}`;
  }
  return "";
}
function shouldRecordMissedWhileClosed(rule, input) {
  if (rule.condition?.kind !== "daily_time" || !rule.condition.localTime || !rule.history || rule.history.length > 0) return false;
  const now = input.now ?? Date.now();
  const createdAt = Number(rule.id.split("-").at(-1));
  return Number.isFinite(createdAt) && now - createdAt > 12 * 60 * 60 * 1e3;
}
function evaluateAlertRules(alerts, input) {
  const now = input.now ?? Date.now();
  return alerts.map((rawRule) => {
    const rule = normalizeAlertRule(rawRule);
    if (rule.symbol !== input.symbol || rule.activationState !== "enabled") return rule;
    if (rule.triggerState !== "idle") return rule;
    const reason = evaluateRule(rule, input);
    if (!reason) return rule;
    const history = [...rule.history ?? []];
    if (shouldRecordMissedWhileClosed(rule, input)) {
      history.push({ at: now, type: "missed_while_closed", reason: "\u6D4F\u89C8\u5668\u5173\u95ED\u671F\u95F4\u9519\u8FC7\u5B9A\u65F6\u63D0\u9192\uFF0C\u672C\u6B21\u6253\u5F00\u540E\u8BB0\u5F55\u4E3A\u672C\u5730\u5386\u53F2" });
    }
    history.push({ at: now, type: "triggered", reason });
    return {
      ...rule,
      triggerState: "triggered",
      lastTriggeredAt: now,
      triggerReason: reason,
      history
    };
  });
}

// tests/replay/alerts/trigger-flow.spec.ts
var mtsHigh = {
  trendState: "bullish",
  mtsScore: 78,
  scoreBand: "strong_positive",
  signalType: "technical_alert",
  alertLevel: "high",
  reasonCodes: ["TREND_ABOVE_EMA"],
  reasons: [],
  invalidators: [],
  displayLabel: "\u5F3A\u6B63\u5411\u6280\u672F\u63D0\u9192",
  technicalReminder: "MTS \u4EC5\u7528\u4E8E\u6280\u672F\u63D0\u9192\u548C\u98CE\u9669\u89C2\u5BDF\uFF0C\u4E0D\u6784\u6210\u6536\u76CA\u627F\u8BFA\u6216\u786E\u5B9A\u6027\u4E70\u5356\u5EFA\u8BAE\u3002"
};
describe("alert trigger replay", () => {
  it("records triggered and missed scheduled history without firing disabled or archived rules", () => {
    const now = (/* @__PURE__ */ new Date("2026-06-06T10:30:00")).getTime();
    const price = createAlertRule({ symbol: "AAPL", taxonomy: "price", level: "\u89C2\u5BDF", threshold: 190, direction: "above", now: now - 1e4 });
    const mts = createAlertRule({ symbol: "AAPL", taxonomy: "mts", level: "\u5F3A\u4FE1\u53F7", mtsAlertLevel: "high", now: now - 1e4 });
    const scheduled = createAlertRule({ symbol: "AAPL", taxonomy: "scheduled", level: "\u89C2\u5BDF", localTime: "09:30", now: now - 864e5 });
    const disabled = { ...price, id: "disabled", activationState: "disabled", enabled: false };
    const archived = { ...price, id: "archived", activationState: "suspended_by_archive", enabled: false };
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
    assert.equal(evaluated[2].triggerState, "triggered");
    assert.equal(evaluated[2].history.some((event) => event.type === "missed_while_closed"), true);
    assert.equal(evaluated[3].triggerState, "idle");
    assert.equal(evaluated[4].triggerState, "idle");
  });
  it("does not duplicate triggered history for an already triggered rule", () => {
    const now = Date.now();
    const rule = createAlertRule({ symbol: "AAPL", taxonomy: "price", level: "\u89C2\u5BDF", threshold: 190, direction: "above", now });
    const first = evaluateAlertRules([rule], { symbol: "AAPL", latestPrice: 191, previousClose: 180, now })[0];
    const second = evaluateAlertRules([first], { symbol: "AAPL", latestPrice: 192, previousClose: 180, now: now + 1e3 })[0];
    assert.equal(first.history.length, 1);
    assert.equal(second.history.length, 1);
  });
});
