export type MarketCode = "US" | "HK" | "CN" | "KR";
export type SourceMode = "formal" | "demo_fallback" | "unavailable";
export type WatchStatus = "active" | "archived";
export type IndicatorStatus = "ready" | "partial" | "unavailable";
export type AlertLevel = "观察" | "确认" | "强信号" | "风控";
export type AlertState = "enabled" | "disabled" | "suspended_by_archive";

export interface WatchSymbolView {
  market: MarketCode;
  rawSymbol: string;
  normalizedSymbol: string;
  displayName: string;
  status: WatchStatus;
  sourceMode: SourceMode;
  dataTestId: string;
}

export interface ChartLayoutView {
  selectedSymbol: string;
  mainPanel: "candles_with_ema_boll";
  volumePanelVisible: true;
  secondaryIndicator: "MACD" | "RSI" | "KDJ" | "ATR";
  indicatorStatus: IndicatorStatus;
  restorePolicyLabel: string;
}

export interface MtsSignalView {
  trendState: "多头" | "震荡" | "空头" | "趋势修复中" | "数据不足";
  scoreBand: string;
  signalType: "趋势回调买点" | "收敛突破买点" | "趋势破坏" | "动量衰竭" | "风控止损" | "none";
  alertLevel: AlertLevel | "不可解释";
  reasons: string[];
  invalidators: string[];
  interpretable: boolean;
}

export interface AlertRuleView {
  id: string;
  targetSymbol: string;
  ruleType: "价格型" | "信号型";
  level: AlertLevel;
  state: AlertState;
  lastTriggeredText: string;
  triggerReason: string;
  dataTestId: string;
}

export interface SourceStatusView {
  mode: SourceMode;
  sourceName: string;
  freshnessNote: string;
  degradationReason: string;
  affectedObjects: Array<"PriceBar" | "IndicatorSet" | "MtsSignal" | "AlertRule">;
}
