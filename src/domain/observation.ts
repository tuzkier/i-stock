import type { ChartPayload, IndicatorPoint, PriceBar, SourceHealth } from "../types.ts";
import { atr, ema, lastFinite, macd, rsi } from "../lib/indicators.ts";

export type SecondaryIndicator = "MACD" | "RSI" | "KDJ" | "ATR";
export type IndicatorState = "ready" | "partial" | "unavailable";

export type IndicatorSeries = {
  label: string;
  state: IndicatorState;
  summary: string;
  data?: {
    main?: IndicatorPoint[];
    signal?: IndicatorPoint[];
    histogram?: Array<IndicatorPoint & { color?: string }>;
  };
};

export type ObservationIndicators = {
  ema20: number[];
  ema60: number[];
  rsi14: number[];
  macdHistogram: number[];
  atr14: number[];
};

export type MarketObservation = {
  symbol?: string;
  bars: PriceBar[];
  sourceHealth?: SourceHealth;
  latestBar?: PriceBar;
  previousBar?: PriceBar;
  changeSummary?: {
    absolute?: number;
    percent?: number;
  };
  indicators: ObservationIndicators;
};

function formatNumber(value?: number, digits = 2) {
  if (!Number.isFinite(value)) return "--";
  return new Intl.NumberFormat("zh-CN", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits
  }).format(value as number);
}

function countFinite(values: number[]) {
  return values.filter(Number.isFinite).length;
}

export function seriesToPoints(bars: PriceBar[], values: number[]): IndicatorPoint[] {
  return values.flatMap((value, index) => {
    const bar = bars[index];
    if (!bar || !Number.isFinite(value)) return [];
    return [{ time: bar.time, value }];
  });
}

export function buildKdj(bars: PriceBar[], period = 9) {
  const k = bars.map(() => Number.NaN);
  const d = bars.map(() => Number.NaN);
  const j = bars.map(() => Number.NaN);
  let prevK = 50;
  let prevD = 50;

  bars.forEach((bar, index) => {
    if (index < period - 1) return;

    const window = bars.slice(index - period + 1, index + 1);
    const high = Math.max(...window.map((item) => item.high));
    const low = Math.min(...window.map((item) => item.low));
    const rsv = high === low ? 50 : ((bar.close - low) / (high - low)) * 100;

    prevK = (2 / 3) * prevK + (1 / 3) * rsv;
    prevD = (2 / 3) * prevD + (1 / 3) * prevK;
    const nextJ = 3 * prevK - 2 * prevD;

    k[index] = prevK;
    d[index] = prevD;
    j[index] = nextJ;
  });

  return { k, d, j };
}

export function buildObservationIndicators(bars: PriceBar[]): ObservationIndicators {
  const closes = bars.map((bar) => bar.close);
  return {
    ema20: ema(closes, 20),
    ema60: ema(closes, 60),
    rsi14: rsi(closes, 14),
    macdHistogram: macd(closes).histogram,
    atr14: atr(bars, 14)
  };
}

export function buildObservation(payload?: ChartPayload): MarketObservation {
  const bars = payload?.priceSeries?.bars ?? payload?.bars ?? [];
  const latestBar = bars.at(-1);
  const previousBar = bars.at(-2);
  return {
    symbol: payload?.symbol,
    bars,
    sourceHealth: payload?.sourceHealth,
    latestBar,
    previousBar,
    changeSummary: payload?.priceSeries?.changeSummary ?? {
      absolute: latestBar && previousBar ? latestBar.close - previousBar.close : undefined,
      percent: latestBar && previousBar && previousBar.close !== 0 ? ((latestBar.close - previousBar.close) / previousBar.close) * 100 : undefined
    },
    indicators: buildObservationIndicators(bars)
  };
}

export function buildSecondaryIndicator(bars: PriceBar[], indicator: SecondaryIndicator): IndicatorSeries {
  const closes = bars.map((bar) => bar.close);

  if (indicator === "MACD") {
    const series = macd(closes);
    const finiteCount = Math.max(countFinite(series.line), countFinite(series.signal), countFinite(series.histogram));
    const state: IndicatorState = finiteCount === 0 ? "unavailable" : bars.length < 35 ? "partial" : "ready";

    return {
      label: "MACD",
      state,
      summary:
        state === "unavailable"
          ? "MACD 数据不足"
          : `MACD ${formatNumber(lastFinite(series.line), 4)} / 信号 ${formatNumber(lastFinite(series.signal), 4)} / 柱 ${formatNumber(lastFinite(series.histogram), 4)}`,
      data: {
        main: seriesToPoints(bars, series.line),
        signal: seriesToPoints(bars, series.signal),
        histogram: series.histogram
          .map((value, index) => {
            if (!Number.isFinite(value)) return null;
            return {
              time: bars[index].time,
              value,
              color: value >= 0 ? "rgba(51,196,129,0.45)" : "rgba(241,95,95,0.45)"
            };
          })
          .filter(Boolean) as Array<IndicatorPoint & { color?: string }>
      }
    };
  }

  if (indicator === "RSI") {
    const series = rsi(closes, 14);
    const state: IndicatorState = countFinite(series) === 0 ? "unavailable" : bars.length < 20 ? "partial" : "ready";
    return {
      label: "RSI",
      state,
      summary: state === "unavailable" ? "RSI 数据不足" : `RSI14 ${formatNumber(lastFinite(series), 2)}`,
      data: {
        main: seriesToPoints(bars, series)
      }
    };
  }

  if (indicator === "KDJ") {
    const series = buildKdj(bars, 9);
    const finiteCount = Math.max(countFinite(series.k), countFinite(series.d), countFinite(series.j));
    const state: IndicatorState = finiteCount === 0 ? "unavailable" : bars.length < 18 ? "partial" : "ready";
    return {
      label: "KDJ",
      state,
      summary:
        state === "unavailable"
          ? "KDJ 数据不足"
          : `K ${formatNumber(lastFinite(series.k), 2)} / D ${formatNumber(lastFinite(series.d), 2)} / J ${formatNumber(lastFinite(series.j), 2)}`,
      data: {
        main: seriesToPoints(bars, series.k),
        signal: seriesToPoints(bars, series.d)
      }
    };
  }

  const series = atr(bars, 14);
  const state: IndicatorState = countFinite(series) === 0 ? "unavailable" : bars.length < 20 ? "partial" : "ready";
  return {
    label: "ATR",
    state,
    summary: state === "unavailable" ? "ATR 数据不足" : `ATR14 ${formatNumber(lastFinite(series), 2)}`,
    data: {
      main: seriesToPoints(bars, series)
    }
  };
}
