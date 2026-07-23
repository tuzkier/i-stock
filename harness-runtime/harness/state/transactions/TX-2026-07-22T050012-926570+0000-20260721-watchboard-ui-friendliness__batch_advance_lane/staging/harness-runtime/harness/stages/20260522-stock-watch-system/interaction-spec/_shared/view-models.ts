export type MarketCode = "US" | "HK" | "CN" | "KR";
export type LayoutMode = "dense" | "focus" | "mobile_tab";
export type SourceHealth = "formal" | "demo_fallback" | "stale" | "unavailable";
export type WatchStatus = "active" | "archived";
export type IndicatorState = "ready" | "partial" | "unavailable";
export type MtsInterpretability = "interpretable" | "data_insufficient";
export type AlertTaxonomy = "price" | "change" | "technical_indicator" | "mts" | "scheduled";
export type AlertLevel = "观察" | "确认" | "强信号" | "风控";
export type AlertActivationState = "enabled" | "disabled" | "suspended_by_archive";
export type AlertTriggerState = "idle" | "triggered" | "acknowledged";

export interface NormalizationPreviewView {
  market: MarketCode | "待确认";
  rawSymbol: string;
  normalizedSymbol: string;
  ambiguous: boolean;
  helperText: string;
  dataTestId: string;
}

export interface WatchSymbolRowView {
  market: MarketCode;
  rawSymbol: string;
  normalizedSymbol: string;
  displayName: string;
  status: WatchStatus;
  sourceHealth: SourceHealth;
  latestPriceText: string;
  changeText: string;
  dataTestId: string;
}

export interface WatchlistPanelView {
  selectedSymbol: string;
  preview: NormalizationPreviewView;
  rows: WatchSymbolRowView[];
  archivedCount: number;
  restoreSummary: string;
}

export interface ChartSurfaceView {
  symbol: string;
  market: MarketCode;
  mainPaneLabel: string;
  volumePaneLabel: string;
  secondaryIndicator: "MACD" | "RSI" | "KDJ" | "ATR";
  indicatorState: IndicatorState;
  ohlcText: string;
  sourceHealth: SourceHealth;
  dataTestId: string;
}

export interface MtsSignalCardView {
  trendState: string;
  scoreBand: string;
  signalType: string;
  alertLevel: AlertLevel | "不可解释";
  reasonCodes: string[];
  invalidators: string[];
  interpretability: MtsInterpretability;
  sourceHealth: SourceHealth;
  dataTestId: string;
}

export interface AlertRuleCardView {
  id: string;
  symbol: string;
  taxonomy: AlertTaxonomy;
  level: AlertLevel;
  activationState: AlertActivationState;
  triggerState: AlertTriggerState;
  lastTriggeredText: string;
  triggerReason: string;
  actionLabel: string;
  dataTestId: string;
}

export interface SourceHealthView {
  mode: SourceHealth;
  sourceName: string;
  lastRefreshedText: string;
  degradationReason: string;
  affectedObjects: Array<"PriceSeries" | "IndicatorSet" | "MtsSignal" | "AlertRule">;
  retryLabel: string;
  dataTestId: string;
}

export interface LayoutControllerView {
  mode: LayoutMode;
  selectedMobileTab: "watchlist" | "chart" | "alerts" | "source";
  denseLabel: string;
  focusLabel: string;
  mobileLabel: string;
  dataTestId: string;
}

export interface RestoreStatusView {
  restored: boolean;
  activeSymbols: number;
  archivedSymbols: number;
  alertRules: number;
  recentSymbol: string;
  fallbackToDefaultLayout: boolean;
  summaryText: string;
  dataTestId: string;
}

export interface WorkbenchShellView {
  selectedSymbol: string;
  layoutMode: LayoutMode;
  watchlist: WatchlistPanelView;
  chart: ChartSurfaceView;
  mts: MtsSignalCardView;
  alerts: AlertRuleCardView[];
  source: SourceHealthView;
  layout: LayoutControllerView;
  restore: RestoreStatusView;
}
