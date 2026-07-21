import assert from "node:assert/strict";
import test from "node:test";
import corpus from "../../../fixtures/mts/replay-corpus.json";
import { resolveMtsReason } from "../../../src/domain/mts-registry";
import { buildSignal } from "../../../src/lib/signals";
import type { PriceBar, SourceHealth } from "../../../src/types";

function bars(count: number, startClose: number, step: number): PriceBar[] {
  return Array.from({ length: count }, (_, index) => {
    const close = startClose + index * step;
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

test("MTS replay corpus stays deterministic and covers valid, insufficient and degraded states", () => {
  for (const item of corpus.cases) {
    const mts = buildSignal(
      bars(item.barCount, item.startClose, item.step),
      sourceHealth(item.sourceStatus as SourceHealth["status"])
    );

    for (const code of item.expectedReasonCodes ?? []) {
      assert.ok(mts.reasonCodes.includes(code as never), `${item.id} missing ${code}`);
    }
    if (item.expectedTrendState) assert.equal(mts.trendState, item.expectedTrendState);
    if (item.expectedAlertLevel) assert.equal(mts.alertLevel, item.expectedAlertLevel);
    for (const forbidden of item.forbiddenCopy ?? []) {
      assert.equal(mts.displayLabel.includes(forbidden), false, `${item.id} contains ${forbidden}`);
      assert.equal(mts.technicalReminder.includes(forbidden), false, `${item.id} contains ${forbidden}`);
    }
  }
});

test("registry mutation replay proves removed entries degrade instead of passing silently", () => {
  const resolved = resolveMtsReason(corpus.registryMutation.unknownCode);

  assert.equal(resolved.code, corpus.registryMutation.expectedFallback);
});
