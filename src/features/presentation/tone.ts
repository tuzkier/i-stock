import type { MtsExplanation, SourceStatus, Tone, WorkspaceRestoreMetadata } from "../../types.ts";

/**
 * 来源状态 -> Tone 映射（来源五态）。
 * - formal / not_loaded：正常展示，无需提示 -> normal
 * - demo_fallback：非正式来源但可用 -> info（DEC-S07 默认档）
 * - stale / unavailable：数据质量或可用性问题 -> warning
 * - 未知值：防御性兜底 -> normal
 */
export function resolveSourceTone(status: SourceStatus): Tone {
  if (status === "formal" || status === "not_loaded") return "normal";
  if (status === "demo_fallback") return "info";
  if (status === "stale" || status === "unavailable") return "warning";
  return "normal";
}

/**
 * MTS 评分 -> Tone 映射（评分极性）。
 * 由 App.tsx 原 mtsTone 重构迁入：语义不变，但负向评分色从旧命名的 "risk"
 * 改为 "caution"（INV-03：负向评分表达"技术面看空"，与来源/恢复故障的
 * "warning" 物理区分，不能合并）。
 *
 * 按 tech-design.md §2 SUC-02-OP-01 / BR-04：
 * strong_positive/positive -> positive；neutral/not_applicable -> neutral；
 * negative/strong_negative 或 alertLevel=风控 -> caution。
 * positive 判断固定排在 negative-or-风控 判断之前（tech-design §2 文本顺序），
 * 因此一个积极评分即使伴随 alertLevel=风控 标记也不会被降级为 caution。
 */
export function resolveScoreTone(mts: MtsExplanation): Tone {
  if (mts.trendState === "source_degraded" || mts.trendState === "data_insufficient") return "neutral";
  if (mts.scoreBand === "strong_positive" || mts.scoreBand === "positive") return "positive";
  if (mts.scoreBand === "strong_negative" || mts.scoreBand === "negative" || mts.alertLevel === "风控") return "caution";
  return "neutral";
}

/**
 * 工作区恢复元数据 -> Tone 映射（恢复四态）。
 * - restored（且无丢弃项）：正常 -> normal
 * - partial / default_fallback：部分降级但已恢复 -> info
 * - failed，或存在 discardedLayoutKeys：需要用户注意 -> warning
 * - 未知 status：保守兜底，宁可多提示不可漏报 -> warning
 */
export function resolveRestoreTone(metadata: WorkspaceRestoreMetadata): Tone {
  if (metadata.status === "failed") return "warning";
  if (metadata.discardedLayoutKeys && metadata.discardedLayoutKeys.length > 0) return "warning";
  if (metadata.status === "restored") return "normal";
  if (metadata.status === "partial" || metadata.status === "default_fallback") return "info";
  return "warning";
}
