import { resolveMtsReason } from "../../domain/mts-registry.ts";
import type { TradeSignalStatus } from "../../domain/trade-signals.ts";
import type { MtsTrendState } from "../../types.ts";

/**
 * MTS trendState -> 人话。
 * `MtsExplanation` 没有独立于 trendState 之外的既有人话字段（只有整体的
 * displayLabel/technicalReminder），因此这里保留一个小分支，但只覆盖规格要求的
 * 两个非常态值（data_insufficient / source_degraded）；其余值给出稳定的中文默认
 * 短标签，不裸露英文枚举串。
 */
export function humanizeTrendState(trendState: MtsTrendState): string {
  switch (trendState) {
    case "data_insufficient":
      return "数据不足";
    case "source_degraded":
      return "数据来源降级";
    case "bullish":
      return "偏多";
    case "bearish":
      return "偏空";
    case "neutral":
    default:
      return "中性";
  }
}

/**
 * 交易信号 status -> 人话。
 * 优先复用 `TradeSignalState.stanceLabel`（由 src/domain/trade-signals.ts 在
 * buildTradeSignalState 中针对 not_target_symbol / source_degraded / data_insufficient /
 * ready 各态已经产出的中文文案），不在呈现层重建一份 status->文案映射表。
 * 未提供 stanceLabel 时不臆造新文案，返回空串。
 */
export function humanizeTradeStatus(status: TradeSignalStatus, stanceLabel?: string): string {
  // status 参数保留在签名中用于类型约束调用方必须传入合法枚举值（并便于未来
  // 扩展），但人话文案本身完全来自 stanceLabel（不重建 status->文案映射表）。
  return stanceLabel ?? "";
}

/**
 * 理由码 -> 人话 label。
 * 等价于 resolveMtsReason(code, detail).label：直接复用既有 registry（含
 * UNKNOWN_CODE 回落），不在呈现层重建一份 code->label 映射表，未注册的 code
 * 永远经由 resolveMtsReason 的内置回落，绝不会把原始 code 字符串直呈。
 */
export function humanizeReason(code: string, detail?: string): string {
  return resolveMtsReason(code, detail).label;
}
