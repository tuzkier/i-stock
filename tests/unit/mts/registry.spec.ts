import assert from "node:assert/strict";
import test from "node:test";
import { mtsReasonRegistry, resolveMtsReason, validateMtsReasonRegistry } from "../../../src/domain/mts-registry";
import type { MtsReasonCode } from "../../../src/types";

const expectedCodes: MtsReasonCode[] = [
  "TREND_ABOVE_EMA",
  "TREND_BELOW_EMA",
  "MACD_MOMENTUM_UP",
  "MACD_MOMENTUM_DOWN",
  "RSI_LOW_RECOVERY",
  "RSI_OVERHEATED",
  "VOLUME_EXPANSION",
  "BOLLINGER_BREAKOUT",
  "BOLLINGER_BREAKDOWN",
  "HIGH_VOLATILITY",
  "NO_CONFLUENCE",
  "DATA_INSUFFICIENT",
  "SOURCE_DEGRADED",
  "UNKNOWN_CODE"
];

test("MtsReasonRegistry is keyed by stable reason code and has no free-text code drift", () => {
  const registry = mtsReasonRegistry();
  const validation = validateMtsReasonRegistry();

  assert.equal(validation.valid, true);
  assert.equal(validation.entryCount, expectedCodes.length);
  assert.deepEqual(Object.keys(registry).sort(), [...expectedCodes].sort());
  for (const code of expectedCodes) {
    assert.equal(registry[code].code, code);
    assert.ok(registry[code].detail.length > 0);
  }
});

test("unknown registry codes degrade to UNKNOWN_CODE instead of becoming free text", () => {
  const resolved = resolveMtsReason("REMOVED_REASON_ENTRY");

  assert.equal(resolved.code, "UNKNOWN_CODE");
  assert.match(resolved.detail, /未注册/);
});
