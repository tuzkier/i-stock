export type MarketCode = "US" | "HK" | "CN" | "KR";
export type SourceHealthStatus = "formal" | "demo_fallback" | "stale" | "unavailable";
export type SourceStatus = SourceHealthStatus | "not_loaded";

export type MarketDataCacheState = "miss" | "hit" | "bypass" | "stale_fallback" | "disabled";

export type MarketDataRetryState = {
  attempt: number;
  canRetry: boolean;
  lastAttemptAt?: number;
  nextRetryAt?: number;
  reason?: string;
};

export type WatchSymbol = {
  id: string;
  symbol: string;
  name: string;
  market: MarketCode;
  status?: "active" | "archived";
  archivedAt?: number;
};

export type PriceBar = {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type RangeKey = "1d" | "5d" | "1mo" | "3mo" | "6mo" | "1y";

export type ChartLayout = "dense" | "focus" | "mobile_tab";
export type MobileWorkbenchTab = "chart" | "source";

export type WorkspaceLayout = {
  mode: ChartLayout;
  selectedMobileTab: MobileWorkbenchTab;
  updatedAt?: number;
};

export type RestoreStatus = "restored" | "partial" | "default_fallback" | "failed";

export type WorkspaceRestoreMetadata = {
  status: RestoreStatus;
  migratedFromLegacy: boolean;
  reason?: string;
  discardedLayoutKeys?: string[];
  snapshotBytes: number;
};

export type WorkspaceSnapshotV2 = {
  version: 2;
  watchlist: WatchSymbol[];
  alerts: AlertRule[];
  selectedSymbol?: string;
  range?: RangeKey;
  selectedMobileTab: MobileWorkbenchTab;
  layoutBySymbol: Record<string, WorkspaceLayout>;
  globalLayoutFallback: WorkspaceLayout;
  restoreMetadata: WorkspaceRestoreMetadata;
  updatedAt: number;
};

export type PriceSeries = {
  symbol: string;
  range: RangeKey;
  interval: string;
  bars: PriceBar[];
  latestOhlc?: {
    time: number;
    open: number;
    high: number;
    low: number;
    close: number;
  };
  latestPrice?: number;
  changeSummary?: {
    absolute: number;
    percent?: number;
  };
};

export type SourceHealth = {
  status: SourceHealthStatus;
  affectedObjects: Array<"chart" | "mts" | "alerts">;
  retryState: MarketDataRetryState;
  lastRefreshedAt?: number;
  degradationReason?: string;
};

export type MarketDataEnvelope = {
  symbol: string;
  range: RangeKey;
  interval: string;
  meta: {
    currency?: string;
    exchangeName?: string;
    fullExchangeName?: string;
    shortName?: string;
    regularMarketPrice?: number;
    previousClose?: number;
    regularMarketTime?: number;
    timezone?: string;
  };
  priceSeries: PriceSeries;
  bars: PriceBar[];
  servedAt: number;
  cacheState: MarketDataCacheState;
  sourceHealth: SourceHealth;
  sourceName: string;
  degradationReason?: string;
  lastRefreshedAt?: number;
  retryState: MarketDataRetryState;
  dataSource?: "futud";
  notice?: string;
};

export type ChartPayload = MarketDataEnvelope;

export type IndicatorPoint = {
  time: number;
  value: number;
};

export type SignalKind = "strong-buy" | "buy-watch" | "hold" | "sell-watch" | "strong-sell";

export type MtsTrendState = "bullish" | "neutral" | "bearish" | "data_insufficient" | "source_degraded";
export type MtsScoreBand = "strong_positive" | "positive" | "neutral" | "negative" | "strong_negative" | "not_applicable";
export type MtsSignalType = "technical_alert" | "risk_alert" | "watch" | "data_insufficient";
export type MtsAlertLevel = "none" | "观察" | "确认" | "强信号" | "风控";
export type MtsReasonCode =
  | "TREND_ABOVE_EMA"
  | "TREND_BELOW_EMA"
  | "MACD_MOMENTUM_UP"
  | "MACD_MOMENTUM_DOWN"
  | "RSI_LOW_RECOVERY"
  | "RSI_OVERHEATED"
  | "VOLUME_EXPANSION"
  | "BOLLINGER_BREAKOUT"
  | "BOLLINGER_BREAKDOWN"
  | "HIGH_VOLATILITY"
  | "NO_CONFLUENCE"
  | "DATA_INSUFFICIENT"
  | "SOURCE_DEGRADED"
  | "UNKNOWN_CODE";

export type MtsReason = {
  code: MtsReasonCode;
  label: string;
  detail: string;
  polarity: "positive" | "neutral" | "negative";
  kind: "reason" | "invalidator";
  category: "trend" | "momentum" | "volume" | "volatility" | "data_quality" | "risk" | "source";
  severityHint: "info" | "watch" | "confirm" | "strong_signal" | "risk";
  displayKey: string;
  introducedIn: string;
  deprecated?: boolean;
};

export type MtsExplanation = {
  trendState: MtsTrendState;
  mtsScore: number | null;
  scoreBand: MtsScoreBand;
  signalType: MtsSignalType;
  alertLevel: MtsAlertLevel;
  reasonCodes: MtsReasonCode[];
  reasons: MtsReason[];
  invalidators: MtsReason[];
  displayLabel: string;
  technicalReminder: string;
  interpretability: {
    summary: string;
    reasonCount: number;
    invalidatorCount: number;
    technicalLevels: {
      upperWatch: number;
      middleWatch: number;
      riskThreshold: number;
    };
  };
  sourceHealth?: Pick<SourceHealth, "status" | "degradationReason" | "affectedObjects">;
  registryVersion: number;
};

export type AlertRule = {
  id: string;
  symbol: string;
  label: string;
  taxonomy?: "price" | "change" | "technical_indicator" | "mts" | "scheduled";
  level?: "观察" | "确认" | "强信号" | "风控";
  condition?: {
    kind: "price" | "change_percent" | "technical_indicator" | "mts" | "daily_time";
    direction?: "above" | "below";
    threshold?: number;
    indicator?: "RSI" | "MACD" | "KDJ" | "ATR";
    mtsAlertLevel?: MtsAlertLevel;
    localTime?: string;
    timezone?: "local";
    daysOfWeek?: number[];
    skipIfMarketClosed?: boolean;
  };
  direction: "above" | "below";
  price?: number;
  signal?: SignalKind;
  enabled: boolean;
  lastTriggeredAt?: number;
  lastScheduledTriggerKey?: string;
  lastScheduledMissedKey?: string;
  triggerReason?: string;
  triggerState?: "idle" | "triggered" | "acknowledged";
  acknowledgedAt?: number;
  activationState?: "enabled" | "disabled" | "suspended_by_archive";
  suspendedReason?: "suspended_by_archive";
  restoreIntent?: "enabled" | "disabled";
  history?: Array<{
    at: number;
    type: "created" | "triggered" | "acknowledged" | "suspended_by_archive" | "restored" | "missed_while_closed";
    reason: string;
  }>;
};
