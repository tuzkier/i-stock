import type { MtsReason, MtsReasonCode } from "../types";

export const MTS_REASON_REGISTRY_VERSION = 2;
const MTS_REASON_REGISTRY_ID = "mts-registry-v2";

function entry(input: Omit<MtsReason, "introducedIn"> & { introducedIn?: string }): MtsReason {
  return {
    introducedIn: input.introducedIn ?? MTS_REASON_REGISTRY_ID,
    ...input
  };
}

const reasonRegistry: Record<MtsReasonCode, MtsReason> = {
  TREND_ABOVE_EMA: entry({
    code: "TREND_ABOVE_EMA",
    label: "趋势结构偏强",
    detail: "价格站上 EMA20，且 EMA20 位于 EMA60 上方。",
    polarity: "positive",
    kind: "reason",
    category: "trend",
    severityHint: "confirm",
    displayKey: "mts.reason.trend_above_ema"
  }),
  TREND_BELOW_EMA: entry({
    code: "TREND_BELOW_EMA",
    label: "短线趋势偏弱",
    detail: "价格低于 EMA20，短线趋势尚未恢复。",
    polarity: "negative",
    kind: "invalidator",
    category: "trend",
    severityHint: "risk",
    displayKey: "mts.reason.trend_below_ema"
  }),
  MACD_MOMENTUM_UP: entry({
    code: "MACD_MOMENTUM_UP",
    label: "MACD 动量改善",
    detail: "MACD 柱体为正且继续抬升，短线动量正在改善。",
    polarity: "positive",
    kind: "reason",
    category: "momentum",
    severityHint: "confirm",
    displayKey: "mts.reason.macd_momentum_up"
  }),
  MACD_MOMENTUM_DOWN: entry({
    code: "MACD_MOMENTUM_DOWN",
    label: "MACD 动量走弱",
    detail: "MACD 柱体为负或继续回落，短线动量不足。",
    polarity: "negative",
    kind: "invalidator",
    category: "momentum",
    severityHint: "watch",
    displayKey: "mts.reason.macd_momentum_down"
  }),
  RSI_LOW_RECOVERY: entry({
    code: "RSI_LOW_RECOVERY",
    label: "RSI 低位修复",
    detail: "RSI 从低位回升，存在超跌修复迹象。",
    polarity: "positive",
    kind: "reason",
    category: "momentum",
    severityHint: "watch",
    displayKey: "mts.reason.rsi_low_recovery"
  }),
  RSI_OVERHEATED: entry({
    code: "RSI_OVERHEATED",
    label: "RSI 过热",
    detail: "RSI 高于 72，短线追高风险上升。",
    polarity: "negative",
    kind: "invalidator",
    category: "momentum",
    severityHint: "risk",
    displayKey: "mts.reason.rsi_overheated"
  }),
  VOLUME_EXPANSION: entry({
    code: "VOLUME_EXPANSION",
    label: "量能放大",
    detail: "成交量明显高于 20 期均量，价格动作有量能确认。",
    polarity: "positive",
    kind: "reason",
    category: "volume",
    severityHint: "watch",
    displayKey: "mts.reason.volume_expansion"
  }),
  BOLLINGER_BREAKOUT: entry({
    code: "BOLLINGER_BREAKOUT",
    label: "波动向上扩张",
    detail: "布林带收窄后向上突破，可能进入波动扩张阶段。",
    polarity: "positive",
    kind: "reason",
    category: "volatility",
    severityHint: "strong_signal",
    displayKey: "mts.reason.bollinger_breakout"
  }),
  BOLLINGER_BREAKDOWN: entry({
    code: "BOLLINGER_BREAKDOWN",
    label: "跌破布林下轨",
    detail: "价格跌破布林下轨，弱势波动仍在释放。",
    polarity: "negative",
    kind: "invalidator",
    category: "risk",
    severityHint: "risk",
    displayKey: "mts.reason.bollinger_breakdown"
  }),
  HIGH_VOLATILITY: entry({
    code: "HIGH_VOLATILITY",
    label: "波动率偏高",
    detail: "ATR 占价格比例偏高，提醒阈值和仓位需要更保守。",
    polarity: "negative",
    kind: "invalidator",
    category: "risk",
    severityHint: "risk",
    displayKey: "mts.reason.high_volatility"
  }),
  NO_CONFLUENCE: entry({
    code: "NO_CONFLUENCE",
    label: "尚未共振",
    detail: "趋势、动量、波动率和成交量尚未形成明确共振。",
    polarity: "neutral",
    kind: "reason",
    category: "data_quality",
    severityHint: "info",
    displayKey: "mts.reason.no_confluence"
  }),
  DATA_INSUFFICIENT: entry({
    code: "DATA_INSUFFICIENT",
    label: "数据不足",
    detail: "需要至少 60 根 K 线来稳定计算趋势、动量和波动率。",
    polarity: "neutral",
    kind: "invalidator",
    category: "data_quality",
    severityHint: "watch",
    displayKey: "mts.reason.data_insufficient"
  }),
  SOURCE_DEGRADED: entry({
    code: "SOURCE_DEGRADED",
    label: "来源降级",
    detail: "行情来源处于降级状态，MTS 只保留解释性技术提醒。",
    polarity: "neutral",
    kind: "invalidator",
    category: "source",
    severityHint: "watch",
    displayKey: "mts.reason.source_degraded"
  }),
  UNKNOWN_CODE: entry({
    code: "UNKNOWN_CODE",
    label: "未知原因码",
    detail: "当前原因码未注册，不能作为有效解释依据。",
    polarity: "neutral",
    kind: "invalidator",
    category: "data_quality",
    severityHint: "watch",
    displayKey: "mts.reason.unknown_code"
  })
};

export function mtsReasonRegistry() {
  return reasonRegistry;
}

export function resolveMtsReason(code: string, detail?: string): MtsReason {
  const entry = reasonRegistry[code as MtsReasonCode] ?? reasonRegistry.UNKNOWN_CODE;
  return detail ? { ...entry, detail } : entry;
}

export function validateMtsReasonRegistry() {
  const entries = Object.entries(reasonRegistry);
  const unknown = reasonRegistry.UNKNOWN_CODE;
  const invalid = entries.filter(
    ([code, entry]) =>
      entry.code !== code ||
      !entry.label ||
      !entry.detail ||
      !entry.polarity ||
      !entry.kind ||
      !entry.category ||
      !entry.severityHint ||
      !entry.displayKey ||
      !entry.introducedIn
  );
  return {
    version: MTS_REASON_REGISTRY_VERSION,
    valid: invalid.length === 0 && Boolean(unknown),
    entryCount: entries.length,
    invalidCodes: invalid.map(([code]) => code),
    deprecatedCodes: [] as string[]
  };
}
