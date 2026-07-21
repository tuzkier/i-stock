import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { buildSignal, mtsReasonRegistry } from "../../../src/lib/signals.ts";
import type { PriceBar, SourceHealth } from "../../../src/types.ts";

function bars(count = 90): PriceBar[] {
  return Array.from({ length: count }, (_, index) => {
    const close = 100 + index * 0.8;
    return {
      time: 1_700_000_000 + index * 86_400,
      open: close - 0.5,
      high: close + 1.8,
      low: close - 1.4,
      close,
      volume: 900_000 + index * 15_000
    };
  });
}

function sourceHealth(status: SourceHealth["status"]): SourceHealth {
  return {
    status,
    affectedObjects: status === "formal" ? [] : ["chart", "mts", "alerts"],
    retryState: {
      attempt: status === "formal" ? 0 : 1,
      canRetry: status !== "formal",
      reason: status === "formal" ? undefined : "fixture degradation"
    },
    degradationReason: status === "formal" ? undefined : "fixture degradation"
  };
}

describe("MTS explanation", () => {
  it("returns a structured technical alert without investment advice language", () => {
    const mts = buildSignal(bars(), sourceHealth("formal"));

    assert.equal(mts.signalType, "technical_alert");
    assert.notEqual(mts.scoreBand, "not_applicable");
    assert.ok(mts.reasonCodes.includes("TREND_ABOVE_EMA"));
    assert.ok(mts.reasonCodes.every((code) => code in mtsReasonRegistry()));
    assert.match(mts.technicalReminder, /不构成收益承诺/);
    assert.doesNotMatch(mts.displayLabel, /买点|卖点|收益|胜率/);
    assert.equal(mts.registryVersion, 2);
    assert.equal(mts.sourceHealth?.status, "formal");
    assert.equal(mts.interpretability.reasonCount, mts.reasons.length);
  });

  it("does not output a valid alert level when data is insufficient", () => {
    const mts = buildSignal(bars(8), sourceHealth("formal"));

    assert.equal(mts.trendState, "data_insufficient");
    assert.equal(mts.mtsScore, null);
    assert.equal(mts.alertLevel, "none");
    assert.deepEqual(mts.reasonCodes, ["DATA_INSUFFICIENT"]);
  });

  it("invalidates MTS when source health is degraded", () => {
    const mts = buildSignal(bars(), sourceHealth("unavailable"));

    assert.equal(mts.trendState, "source_degraded");
    assert.equal(mts.mtsScore, null);
    assert.equal(mts.alertLevel, "none");
    assert.ok(mts.reasonCodes.includes("SOURCE_DEGRADED"));
  });
});
