import assert from "node:assert/strict";
import test from "node:test";
import { resolveSourceTone, resolveScoreTone, resolveRestoreTone } from "../../../src/features/presentation/tone.ts";
import type { MtsExplanation, SourceStatus, WorkspaceRestoreMetadata } from "../../../src/types.ts";

function mts(overrides: Partial<MtsExplanation>): MtsExplanation {
  return {
    trendState: "neutral",
    mtsScore: 0,
    scoreBand: "neutral",
    signalType: "watch",
    alertLevel: "none",
    reasonCodes: [],
    reasons: [],
    invalidators: [],
    displayLabel: "",
    technicalReminder: "",
    interpretability: {
      summary: "",
      reasonCount: 0,
      invalidatorCount: 0,
      technicalLevels: {
        upperWatch: 0,
        middleWatch: 0,
        riskThreshold: 0
      }
    },
    registryVersion: 1,
    ...overrides
  };
}

function restoreMeta(overrides: Partial<WorkspaceRestoreMetadata>): WorkspaceRestoreMetadata {
  return {
    status: "restored",
    migratedFromLegacy: false,
    snapshotBytes: 0,
    ...overrides
  };
}

// ---- resolveSourceTone：来源五态 ----

test("resolveSourceTone: formal -> normal", () => {
  assert.equal(resolveSourceTone("formal"), "normal");
});

test("resolveSourceTone: not_loaded -> normal", () => {
  assert.equal(resolveSourceTone("not_loaded"), "normal");
});

test("resolveSourceTone: demo_fallback -> info (DEC-S07 默认档，非 warning)", () => {
  assert.equal(resolveSourceTone("demo_fallback"), "info");
});

test("resolveSourceTone: stale -> warning", () => {
  assert.equal(resolveSourceTone("stale"), "warning");
});

test("resolveSourceTone: unavailable -> warning", () => {
  assert.equal(resolveSourceTone("unavailable"), "warning");
});

test("resolveSourceTone: 未知值兜底 -> normal（防御性写法）", () => {
  assert.equal(resolveSourceTone("unknown_status" as SourceStatus), "normal");
});

// ---- resolveScoreTone：评分极性 ----

test("resolveScoreTone: source_degraded -> neutral", () => {
  assert.equal(resolveScoreTone(mts({ trendState: "source_degraded", scoreBand: "strong_positive" })), "neutral");
});

test("resolveScoreTone: data_insufficient -> neutral", () => {
  assert.equal(resolveScoreTone(mts({ trendState: "data_insufficient", scoreBand: "negative" })), "neutral");
});

test("resolveScoreTone: strong_positive -> positive", () => {
  assert.equal(resolveScoreTone(mts({ scoreBand: "strong_positive" })), "positive");
});

test("resolveScoreTone: positive -> positive", () => {
  assert.equal(resolveScoreTone(mts({ scoreBand: "positive" })), "positive");
});

test("resolveScoreTone: strong_negative -> caution（INV-03：不能是 warning）", () => {
  const result = resolveScoreTone(mts({ scoreBand: "strong_negative" }));
  assert.equal(result, "caution");
  assert.notEqual(result, "warning");
});

test("resolveScoreTone: negative -> caution（INV-03：不能是 warning）", () => {
  const result = resolveScoreTone(mts({ scoreBand: "negative" }));
  assert.equal(result, "caution");
  assert.notEqual(result, "warning");
});

test("resolveScoreTone: neutral -> neutral", () => {
  assert.equal(resolveScoreTone(mts({ scoreBand: "neutral" })), "neutral");
});

test("resolveScoreTone: not_applicable -> neutral", () => {
  assert.equal(resolveScoreTone(mts({ scoreBand: "not_applicable" })), "neutral");
});

test("resolveScoreTone: scoreBand=neutral 但 alertLevel=风控 -> caution（BR-04 OR 分支，非 warning）", () => {
  const result = resolveScoreTone(mts({ scoreBand: "neutral", alertLevel: "风控" }));
  assert.equal(result, "caution");
  assert.notEqual(result, "warning");
});

test("resolveScoreTone: scoreBand=positive 且 alertLevel=风控 -> 仍为 positive（positive 优先级不被风控标记覆盖）", () => {
  assert.equal(resolveScoreTone(mts({ scoreBand: "positive", alertLevel: "风控" })), "positive");
});

test("resolveScoreTone: alertLevel 风控 -> caution（即使 scoreBand 非 negative）", () => {
  const result = resolveScoreTone(mts({ scoreBand: "neutral", alertLevel: "风控" }));
  assert.equal(result, "caution");
  assert.notEqual(result, "warning");
});

test("resolveScoreTone: fault — demo_fallback 来源态不在此函数；negative 不得映射为 warning", () => {
  assert.notEqual(resolveScoreTone(mts({ scoreBand: "negative" })), "warning");
});

// ---- resolveRestoreTone：恢复四态 ----

test("resolveRestoreTone: restored -> normal", () => {
  assert.equal(resolveRestoreTone(restoreMeta({ status: "restored" })), "normal");
});

test("resolveRestoreTone: partial -> info", () => {
  assert.equal(resolveRestoreTone(restoreMeta({ status: "partial" })), "info");
});

test("resolveRestoreTone: default_fallback -> info", () => {
  assert.equal(resolveRestoreTone(restoreMeta({ status: "default_fallback" })), "info");
});

test("resolveRestoreTone: failed -> warning", () => {
  assert.equal(resolveRestoreTone(restoreMeta({ status: "failed" })), "warning");
});

test("resolveRestoreTone: restored 但 discardedLayoutKeys 非空 -> warning", () => {
  assert.equal(
    resolveRestoreTone(restoreMeta({ status: "restored", discardedLayoutKeys: ["mobile_tab"] })),
    "warning"
  );
});

test("resolveRestoreTone: 未知 status 兜底 -> warning（保守策略：宁可多提示不可漏报）", () => {
  assert.equal(
    resolveRestoreTone(restoreMeta({ status: "unknown_status" as WorkspaceRestoreMetadata["status"] })),
    "warning"
  );
});
