import type { MarketObservation } from "./observation";
import { atr, bollinger, ema, lastFinite, macd, rsi, slope, sma } from "../lib/indicators.ts";

export type TencentTradePlanStatus = "ready" | "not_target_symbol" | "data_insufficient" | "source_degraded";
export type TencentTradePlanAction = "buy_watch" | "buy_triggered" | "hold" | "sell_watch" | "risk_control" | "wait";
export type TencentTrendBias = "uptrend_pullback" | "uptrend_breakout" | "range_rotation" | "downtrend_rebound" | "risk_off";

export type TradePlanLevelRange = {
  low: number;
  high: number;
};

export type TencentTradePlan = {
  strategyId: "tencent-0700-trend-v1";
  symbol: string;
  status: TencentTradePlanStatus;
  action: TencentTradePlanAction;
  actionLabel: string;
  bias: TencentTrendBias;
  confidence: number;
  latestPrice?: number;
  trendScore: number | null;
  levels: {
    buyZone?: TradePlanLevelRange;
    buyTrigger?: number;
    sellZone?: TradePlanLevelRange;
    sellTrigger?: number;
    stopLoss?: number;
    invalidation?: number;
    firstTarget?: number;
    secondTarget?: number;
  };
  reasons: string[];
  warnings: string[];
  nonAdvice: string;
};

const STRATEGY_ID = "tencent-0700-trend-v1" as const;
const MIN_BARS = 80;
const HK_PRICE_TICK = 0.1;

function normalizeSymbol(symbol = "") {
  return symbol.trim().toUpperCase().replace(/\s+/g, "");
}

export function isTencent700Symbol(symbol = "") {
  const normalized = normalizeSymbol(symbol);
  return normalized === "0700.HK" || normalized === "700.HK" || normalized === "HK.00700" || normalized === "HK.0700";
}

function roundPrice(value: number) {
  if (!Number.isFinite(value)) return Number.NaN;
  return Math.round(value / HK_PRICE_TICK) * HK_PRICE_TICK;
}

function finiteOr(value: number, fallback: number) {
  return Number.isFinite(value) ? value : fallback;
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function rangeHigh(values: Array<{ high: number }>) {
  return Math.max(...values.map((item) => item.high));
}

function rangeLow(values: Array<{ low: number }>) {
  return Math.min(...values.map((item) => item.low));
}

function emptyPlan(
  symbol: string,
  status: TencentTradePlanStatus,
  actionLabel: string,
  reasons: string[],
  warnings: string[] = []
): TencentTradePlan {
  return {
    strategyId: STRATEGY_ID,
    symbol,
    status,
    action: "wait",
    actionLabel,
    bias: "range_rotation",
    confidence: 0,
    trendScore: null,
    levels: {},
    reasons,
    warnings,
    nonAdvice: "该算法只输出规则化技术触发位，不构成收益承诺或确定性买卖建议。"
  };
}

export function buildTencentTradePlan(observation: MarketObservation): TencentTradePlan {
  const symbol = normalizeSymbol(observation.symbol);

  if (!isTencent700Symbol(symbol)) {
    return emptyPlan(symbol, "not_target_symbol", "仅适用于 0700.HK", ["当前算法只针对腾讯控股 0700.HK。"]);
  }

  if (observation.sourceHealth?.status && observation.sourceHealth.status !== "formal") {
    return emptyPlan(symbol, "source_degraded", "来源不可用", [
      `来源状态为 ${observation.sourceHealth.status}，不输出 0700.HK 买卖点。`
    ]);
  }

  const bars = observation.bars;
  if (bars.length < MIN_BARS) {
    return emptyPlan(symbol, "data_insufficient", "数据不足", [`至少需要 ${MIN_BARS} 根日线 K 线，当前只有 ${bars.length} 根。`]);
  }

  const current = bars[bars.length - 1];
  const previous = bars[bars.length - 2];
  const closes = bars.map((bar) => bar.close);
  const volumes = bars.map((bar) => bar.volume);
  const ema20 = ema(closes, 20);
  const ema60 = ema(closes, 60);
  const sma120 = sma(closes, 120);
  const rsi14 = rsi(closes, 14);
  const macdData = macd(closes);
  const atr14 = atr(bars, 14);
  const volume20 = sma(volumes, 20);
  const band = bollinger(closes, 20, 2);

  const latestEma20 = lastFinite(ema20);
  const latestEma60 = lastFinite(ema60);
  const latestSma120 = lastFinite(sma120);
  const latestRsi = lastFinite(rsi14);
  const latestMacdHist = lastFinite(macdData.histogram);
  const previousMacdHist = lastFinite(macdData.histogram, 1);
  const latestAtr = lastFinite(atr14);
  const latestAverageVolume = lastFinite(volume20);
  const latestBandMiddle = lastFinite(band.middle);
  const latestBandUpper = lastFinite(band.upper);
  const latestBandLower = lastFinite(band.lower);

  if (![latestEma20, latestEma60, latestRsi, latestMacdHist, previousMacdHist, latestAtr].every(Number.isFinite)) {
    return emptyPlan(symbol, "data_insufficient", "指标不足", ["EMA、RSI、MACD 或 ATR 尚未形成完整有效序列。"]);
  }

  const recent20 = bars.slice(-20);
  const recent60 = bars.slice(-60);
  const high20 = rangeHigh(recent20);
  const low20 = rangeLow(recent20);
  const high60 = rangeHigh(recent60);
  const low60 = rangeLow(recent60);
  const ema20Slope = slope(ema20, 5);
  const ema60Slope = slope(ema60, 8);
  const volumeRatio = latestAverageVolume > 0 ? current.volume / latestAverageVolume : 1;
  const atrPercent = current.close > 0 ? latestAtr / current.close : 0;
  const longReference = finiteOr(latestSma120, latestEma60);
  const macdImproving = latestMacdHist > previousMacdHist;
  const overextended = current.close > latestEma20 + latestAtr * 1.8 || latestRsi >= 70;
  const belowTrendStack = current.close < latestEma20 && latestEma20 < latestEma60 && ema20Slope < 0;
  const trendBreak = current.close < latestEma60 - latestAtr * 0.4 || current.close <= low20;
  const strongUptrend = current.close > latestEma20 && latestEma20 > latestEma60 && latestEma60 >= longReference * 0.98 && ema20Slope > 0;
  const constructiveRange = current.close >= low60 && current.close <= high60 && Math.abs(latestEma20 - latestEma60) / current.close < 0.06;

  const trendScore = Math.round(
    (current.close > latestEma20 ? 18 : -18) +
      (latestEma20 > latestEma60 ? 24 : -24) +
      (current.close > longReference ? 12 : -12) +
      (ema20Slope > 0 ? 12 : -12) +
      (ema60Slope > 0 ? 8 : -8) +
      (latestMacdHist > 0 ? 12 : -12) +
      (macdImproving ? 8 : -8) +
      (latestRsi >= 45 && latestRsi <= 64 ? 8 : latestRsi > 72 ? -12 : latestRsi < 35 ? -8 : 0) +
      (volumeRatio >= 1.2 && current.close >= previous.close ? 8 : volumeRatio >= 1.4 && current.close < previous.close ? -8 : 0) +
      (atrPercent > 0.065 ? -10 : 0)
  );

  const confidence = clamp(Math.round(48 + Math.abs(trendScore) * 0.35 - atrPercent * 95), 20, 88);
  const buyZoneLow = roundPrice(Math.max(low20, latestEma20 - latestAtr * 0.55));
  const buyZoneHigh = roundPrice(latestEma20 + latestAtr * 0.25);
  const buyTrigger = roundPrice(Math.max(current.high + HK_PRICE_TICK, latestEma20 + latestAtr * 0.35));
  const buyStop = roundPrice(Math.min(buyZoneLow - latestAtr * 1.1, latestEma60 - latestAtr * 0.65));
  const sellZoneLow = roundPrice(Math.min(latestEma20, latestEma60) - latestAtr * 0.2);
  const sellZoneHigh = roundPrice(Math.max(latestEma20, latestEma60) + latestAtr * 0.45);
  const sellTrigger = roundPrice(Math.min(current.low, low20) - HK_PRICE_TICK);
  const sellInvalidation = roundPrice(latestEma20 + latestAtr * 0.65);
  const upperTarget = roundPrice(Math.max(high20, current.close + latestAtr * 1.8));
  const extendedTarget = roundPrice(Math.max(high60, upperTarget + latestAtr * 1.2));
  const downsideTarget = roundPrice(Math.max(low60, current.close - latestAtr * 1.7));
  const deepRiskTarget = roundPrice(Math.max(low60 - latestAtr, current.close - latestAtr * 3));

  const reasons = [
    `收盘 ${roundPrice(current.close).toFixed(1)}，EMA20 ${roundPrice(latestEma20).toFixed(1)}，EMA60 ${roundPrice(latestEma60).toFixed(1)}。`,
    `RSI14 ${latestRsi.toFixed(1)}，MACD 柱 ${latestMacdHist.toFixed(3)}，较上一期${macdImproving ? "改善" : "走弱"}。`,
    `20 日量比 ${volumeRatio.toFixed(2)}，ATR 约占股价 ${(atrPercent * 100).toFixed(1)}%。`
  ];
  const warnings = ["只使用 futud 日线价量数据，未纳入财报、消息面、资金流和持仓约束。"];

  if (strongUptrend && !overextended) {
    const inBuyZone = current.close >= buyZoneLow && current.close <= buyZoneHigh && macdImproving;
    return {
      strategyId: STRATEGY_ID,
      symbol,
      status: "ready",
      action: inBuyZone ? "buy_triggered" : "buy_watch",
      actionLabel: inBuyZone ? "买点触发观察" : "下一次买点",
      bias: high20 <= current.close + latestAtr ? "uptrend_breakout" : "uptrend_pullback",
      confidence,
      latestPrice: current.close,
      trendScore: clamp(trendScore, -100, 100),
      levels: {
        buyZone: { low: buyZoneLow, high: buyZoneHigh },
        buyTrigger,
        stopLoss: buyStop,
        invalidation: buyStop,
        firstTarget: upperTarget,
        secondTarget: extendedTarget
      },
      reasons: [...reasons, "趋势栈为多头排列，优先等回踩 EMA20 附近或放量突破确认。"],
      warnings,
      nonAdvice: "买点触发位只用于技术观察，不构成买入建议。"
    };
  }

  if (overextended || belowTrendStack || trendBreak) {
    const hardRisk = belowTrendStack || trendBreak;
    return {
      strategyId: STRATEGY_ID,
      symbol,
      status: "ready",
      action: hardRisk ? "risk_control" : "sell_watch",
      actionLabel: hardRisk ? "下一次卖点/风控位" : "下一次卖点",
      bias: hardRisk ? "risk_off" : "downtrend_rebound",
      confidence,
      latestPrice: current.close,
      trendScore: clamp(trendScore, -100, 100),
      levels: {
        sellZone: { low: sellZoneLow, high: sellZoneHigh },
        sellTrigger,
        invalidation: sellInvalidation,
        firstTarget: downsideTarget,
        secondTarget: deepRiskTarget
      },
      reasons: [
        ...reasons,
        hardRisk
          ? "价格处在短中期均线下方或跌破近 20 日支撑，反抽均线失败时优先看风控。"
          : "价格相对 EMA20 或 RSI 已偏热，优先等跌破短线支撑确认卖点。"
      ],
      warnings,
      nonAdvice: "卖点/风控位只用于技术观察，不构成卖出建议。"
    };
  }

  if (constructiveRange) {
    const closerToSupport = current.close <= finiteOr(latestBandMiddle, (high60 + low60) / 2);
    return {
      strategyId: STRATEGY_ID,
      symbol,
      status: "ready",
      action: closerToSupport ? "buy_watch" : "sell_watch",
      actionLabel: closerToSupport ? "下一次买点" : "下一次卖点",
      bias: "range_rotation",
      confidence: Math.max(25, confidence - 8),
      latestPrice: current.close,
      trendScore: clamp(trendScore, -100, 100),
      levels: closerToSupport
        ? {
            buyZone: {
              low: roundPrice(finiteOr(latestBandLower, low60)),
              high: roundPrice(Math.min(latestEma20, current.close + latestAtr * 0.5))
            },
            buyTrigger: roundPrice(Math.max(latestEma20, current.high + HK_PRICE_TICK)),
            stopLoss: roundPrice(low60 - latestAtr * 0.6),
            firstTarget: roundPrice(finiteOr(latestBandMiddle, latestEma20)),
            secondTarget: roundPrice(finiteOr(latestBandUpper, high60))
          }
        : {
            sellZone: {
              low: roundPrice(Math.max(latestEma20, current.close - latestAtr * 0.4)),
              high: roundPrice(finiteOr(latestBandUpper, high60))
            },
            sellTrigger: roundPrice(Math.min(current.low, latestEma20) - HK_PRICE_TICK),
            invalidation: roundPrice(high60 + latestAtr * 0.5),
            firstTarget: roundPrice(finiteOr(latestBandMiddle, latestEma20)),
            secondTarget: roundPrice(finiteOr(latestBandLower, low60))
          },
      reasons: [...reasons, "均线差距较小，按区间轮动处理，等待支撑或压力位触发。"],
      warnings,
      nonAdvice: "区间触发位只用于技术观察，不构成交易建议。"
    };
  }

  return {
    strategyId: STRATEGY_ID,
    symbol,
    status: "ready",
    action: "hold",
    actionLabel: "等待确认",
    bias: "range_rotation",
    confidence: Math.max(20, confidence - 12),
    latestPrice: current.close,
    trendScore: clamp(trendScore, -100, 100),
    levels: {
      buyTrigger: roundPrice(Math.max(latestEma20, current.high + HK_PRICE_TICK)),
      sellTrigger: roundPrice(Math.min(latestEma60, current.low) - HK_PRICE_TICK),
      firstTarget: roundPrice(finiteOr(latestBandUpper, high20)),
      invalidation: roundPrice(finiteOr(latestBandLower, low20))
    },
    reasons: [...reasons, "趋势、动量和量能没有形成同向共振，下一步等待突破或跌破确认。"],
    warnings,
    nonAdvice: "等待确认状态不构成买入或卖出建议。"
  };
}
