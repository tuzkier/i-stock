import type {
  MtsAlertLevel,
  MtsExplanation,
  MtsReason,
  MtsReasonCode,
  MtsScoreBand,
  MtsSignalType,
  MtsTrendState,
  PriceBar,
  SourceHealth
} from "../types";
import { atr, bollinger, ema, lastFinite, macd, obv, rsi, slope, sma } from "./indicators";
import { MTS_REASON_REGISTRY_VERSION, mtsReasonRegistry as getMtsReasonRegistry, resolveMtsReason } from "../domain/mts-registry";
import type { MarketObservation } from "../domain/observation";

function reason(code: MtsReasonCode, detail?: string): MtsReason {
  return resolveMtsReason(code, detail);
}

function scoreBand(score: number | null): MtsScoreBand {
  if (score === null) return "not_applicable";
  if (score >= 60) return "strong_positive";
  if (score >= 30) return "positive";
  if (score <= -60) return "strong_negative";
  if (score <= -30) return "negative";
  return "neutral";
}

function trendStateFor(score: number | null, invalidators: MtsReason[]): MtsTrendState {
  if (invalidators.some((item) => item.code === "DATA_INSUFFICIENT")) return "data_insufficient";
  if (invalidators.some((item) => item.code === "SOURCE_DEGRADED")) return "source_degraded";
  if (score === null) return "neutral";
  if (score >= 30) return "bullish";
  if (score <= -30) return "bearish";
  return "neutral";
}

function signalTypeFor(score: number | null, invalidators: MtsReason[]): MtsSignalType {
  if (invalidators.some((item) => item.code === "DATA_INSUFFICIENT")) return "data_insufficient";
  if (score === null) return "watch";
  if (score <= -30) return "risk_alert";
  return "technical_alert";
}

function alertLevelFor(score: number | null, invalidators: MtsReason[]): MtsAlertLevel {
  if (invalidators.length > 0 || score === null) return "none";
  if (score >= 60) return "强信号";
  if (score >= 30) return "确认";
  if (score <= -30) return "风控";
  return "观察";
}

function displayLabelFor(score: number | null, invalidators: MtsReason[]) {
  if (invalidators.some((item) => item.code === "DATA_INSUFFICIENT")) return "数据不足，暂不输出 MTS";
  if (invalidators.some((item) => item.code === "SOURCE_DEGRADED")) return "来源降级，仅保留技术提醒";
  if (score === null) return "MTS 观察";
  if (score >= 60) return "强正向技术提醒";
  if (score >= 30) return "正向技术观察";
  if (score <= -60) return "高风险技术提醒";
  if (score <= -30) return "风险技术观察";
  return "中性观察";
}

function buildMtsExplanation(
  score: number | null,
  reasons: MtsReason[],
  invalidators: MtsReason[],
  sourceHealth?: SourceHealth,
  technicalLevels = { upperWatch: Number.NaN, middleWatch: Number.NaN, riskThreshold: Number.NaN }
): MtsExplanation {
  const reasonCodes = [...reasons, ...invalidators].map((item) => item.code);
  return {
    trendState: trendStateFor(score, invalidators),
    mtsScore: score,
    scoreBand: scoreBand(score),
    signalType: signalTypeFor(score, invalidators),
    alertLevel: alertLevelFor(score, invalidators),
    reasonCodes,
    reasons,
    invalidators,
    displayLabel: displayLabelFor(score, invalidators),
    technicalReminder: "MTS 仅用于技术提醒和风险观察，不构成收益承诺或确定性买卖建议。",
    interpretability: {
      summary: invalidators.length > 0 ? "存在无效化因素，提醒等级被抑制。" : "提醒等级由趋势、动量、量能和波动率共振计算。",
      reasonCount: reasons.length,
      invalidatorCount: invalidators.length,
      technicalLevels
    },
    sourceHealth: sourceHealth
      ? {
          status: sourceHealth.status,
          degradationReason: sourceHealth.degradationReason,
          affectedObjects: sourceHealth.affectedObjects
        }
      : undefined,
    registryVersion: MTS_REASON_REGISTRY_VERSION
  };
}

export function mtsReasonRegistry() {
  return getMtsReasonRegistry();
}

function normalizeSignalInput(input: PriceBar[] | MarketObservation, sourceHealth?: SourceHealth) {
  if (Array.isArray(input)) {
    return {
      bars: input,
      sourceHealth
    };
  }
  return {
    bars: input.bars,
    sourceHealth: input.sourceHealth ?? sourceHealth
  };
}

export function buildSignal(input: PriceBar[] | MarketObservation, sourceHealth?: SourceHealth): MtsExplanation {
  const normalizedInput = normalizeSignalInput(input, sourceHealth);
  const bars = normalizedInput.bars;
  const activeSourceHealth = normalizedInput.sourceHealth;
  if (bars.length < 60) {
    const invalidators = [reason("DATA_INSUFFICIENT")];
    return buildMtsExplanation(null, [], invalidators, activeSourceHealth);
  }

  const closes = bars.map((bar) => bar.close);
  const volumes = bars.map((bar) => bar.volume);
  const current = bars[bars.length - 1];
  const ema20 = ema(closes, 20);
  const ema60 = ema(closes, 60);
  const rsi14 = rsi(closes, 14);
  const macdData = macd(closes);
  const band = bollinger(closes, 20, 2);
  const atr14 = atr(bars, 14);
  const obvSeries = obv(bars);
  const avgVolume20 = sma(volumes, 20);

  const latestEma20 = lastFinite(ema20);
  const latestEma60 = lastFinite(ema60);
  const latestRsi = lastFinite(rsi14);
  const previousRsi = lastFinite(rsi14, 1);
  const latestMacdHist = lastFinite(macdData.histogram);
  const previousMacdHist = lastFinite(macdData.histogram, 1);
  const latestAtr = lastFinite(atr14);
  const latestUpper = lastFinite(band.upper);
  const latestLower = lastFinite(band.lower);
  const latestMiddle = lastFinite(band.middle);
  const latestBandWidth = lastFinite(band.width);
  const latestAverageVolume = lastFinite(avgVolume20);

  const trendScore =
    (current.close > latestEma20 ? 12 : -12) +
    (latestEma20 > latestEma60 ? 18 : -18) +
    (slope(ema20, 5) > 0 ? 10 : -10);

  const momentumScore =
    (latestRsi > 50 ? 10 : -8) +
    (latestRsi < 35 && latestRsi > previousRsi ? 10 : 0) +
    (latestRsi > 72 ? -12 : 0) +
    (latestMacdHist > 0 ? 12 : -12) +
    (latestMacdHist > previousMacdHist ? 8 : -8);

  const volumeRatio = latestAverageVolume > 0 ? current.volume / latestAverageVolume : 1;
  const volumeScore = (volumeRatio > 1.25 ? 10 : volumeRatio < 0.65 ? -6 : 0) + (slope(obvSeries, 8) > 0 ? 10 : -8);

  const atrPercent = current.close > 0 ? latestAtr / current.close : 0;
  const volatilityScore =
    (latestBandWidth < 0.08 && current.close > latestUpper ? 12 : 0) +
    (current.close < latestLower ? -12 : 0) +
    (atrPercent > 0.08 ? -10 : 0);

  const rawScore = trendScore + momentumScore + volumeScore + volatilityScore;
  const score = Math.max(-100, Math.min(100, Math.round(rawScore)));
  const confidence = Math.max(0, Math.min(100, Math.round(55 + Math.abs(score) * 0.35 - atrPercent * 120)));

  const reasonCodes: MtsReasonCode[] = [];
  const invalidatorCodes: MtsReasonCode[] = [];

  if (current.close > latestEma20 && latestEma20 > latestEma60) reasonCodes.push("TREND_ABOVE_EMA");
  if (latestMacdHist > 0 && latestMacdHist > previousMacdHist) reasonCodes.push("MACD_MOMENTUM_UP");
  if (latestRsi < 35 && latestRsi > previousRsi) reasonCodes.push("RSI_LOW_RECOVERY");
  if (volumeRatio > 1.25) reasonCodes.push("VOLUME_EXPANSION");
  if (latestBandWidth < 0.08 && current.close > latestUpper) reasonCodes.push("BOLLINGER_BREAKOUT");
  if (current.close < latestEma20) invalidatorCodes.push("TREND_BELOW_EMA");
  if (latestMacdHist < 0 || latestMacdHist < previousMacdHist) invalidatorCodes.push("MACD_MOMENTUM_DOWN");
  if (latestRsi > 72) invalidatorCodes.push("RSI_OVERHEATED");
  if (atrPercent > 0.08) invalidatorCodes.push("HIGH_VOLATILITY");
  if (current.close < latestLower) invalidatorCodes.push("BOLLINGER_BREAKDOWN");

  if (reasonCodes.length === 0) {
    reasonCodes.push("NO_CONFLUENCE");
  }

  if (activeSourceHealth?.status && activeSourceHealth.status !== "formal") {
    invalidatorCodes.push("SOURCE_DEGRADED");
  }

  const mtsReasons = reasonCodes.map((code) =>
    code === "VOLUME_EXPANSION"
      ? reason(code, `成交量约为 20 期均量的 ${volumeRatio.toFixed(1)} 倍，价格动作有量能确认。`)
      : reason(code)
  );
  const invalidators = invalidatorCodes.map((code) =>
    code === "SOURCE_DEGRADED"
      ? reason(code, `来源状态为 ${activeSourceHealth?.status}，${activeSourceHealth?.degradationReason ?? "不能按正式实时行情输出有效提醒等级"}。`)
      : reason(code)
  );
  return buildMtsExplanation(
    invalidators.some((item) => item.code === "SOURCE_DEGRADED") ? null : score,
    mtsReasons,
    invalidators,
    activeSourceHealth,
    {
      upperWatch: Number.isFinite(latestUpper) ? latestUpper : latestEma20,
      middleWatch: Number.isFinite(latestMiddle) ? latestMiddle : latestEma20,
      riskThreshold: Number.isFinite(latestAtr) ? Math.max(current.close - latestAtr * 2.2, latestLower) : latestLower
    }
  );
}
