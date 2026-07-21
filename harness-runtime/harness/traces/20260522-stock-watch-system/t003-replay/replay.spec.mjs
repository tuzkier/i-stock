// tests/replay/mts/replay.spec.ts
import assert from "node:assert/strict";
import test from "node:test";

// fixtures/mts/replay-corpus.json
var replay_corpus_default = {
  version: 1,
  cases: [
    {
      id: "trend-up-formal",
      barCount: 90,
      startClose: 100,
      step: 0.8,
      sourceStatus: "formal",
      expectedReasonCodes: ["TREND_ABOVE_EMA"],
      forbiddenCopy: ["\u5F3A\u4E70\u70B9", "\u5F3A\u5356\u70B9", "\u80DC\u7387"]
    },
    {
      id: "data-insufficient",
      barCount: 8,
      startClose: 100,
      step: 0.2,
      sourceStatus: "formal",
      expectedTrendState: "data_insufficient",
      expectedAlertLevel: "none",
      expectedReasonCodes: ["DATA_INSUFFICIENT"]
    },
    {
      id: "source-degraded",
      barCount: 90,
      startClose: 100,
      step: 0.8,
      sourceStatus: "unavailable",
      expectedTrendState: "source_degraded",
      expectedAlertLevel: "none",
      expectedReasonCodes: ["SOURCE_DEGRADED"]
    }
  ],
  registryMutation: {
    unknownCode: "REMOVED_REASON_ENTRY",
    expectedFallback: "UNKNOWN_CODE"
  }
};

// src/domain/mts-registry.ts
var reasonRegistry = {
  TREND_ABOVE_EMA: {
    code: "TREND_ABOVE_EMA",
    label: "\u8D8B\u52BF\u7ED3\u6784\u504F\u5F3A",
    detail: "\u4EF7\u683C\u7AD9\u4E0A EMA20\uFF0C\u4E14 EMA20 \u4F4D\u4E8E EMA60 \u4E0A\u65B9\u3002",
    polarity: "positive"
  },
  TREND_BELOW_EMA: {
    code: "TREND_BELOW_EMA",
    label: "\u77ED\u7EBF\u8D8B\u52BF\u504F\u5F31",
    detail: "\u4EF7\u683C\u4F4E\u4E8E EMA20\uFF0C\u77ED\u7EBF\u8D8B\u52BF\u5C1A\u672A\u6062\u590D\u3002",
    polarity: "negative"
  },
  MACD_MOMENTUM_UP: {
    code: "MACD_MOMENTUM_UP",
    label: "MACD \u52A8\u91CF\u6539\u5584",
    detail: "MACD \u67F1\u4F53\u4E3A\u6B63\u4E14\u7EE7\u7EED\u62AC\u5347\uFF0C\u77ED\u7EBF\u52A8\u91CF\u6B63\u5728\u6539\u5584\u3002",
    polarity: "positive"
  },
  MACD_MOMENTUM_DOWN: {
    code: "MACD_MOMENTUM_DOWN",
    label: "MACD \u52A8\u91CF\u8D70\u5F31",
    detail: "MACD \u67F1\u4F53\u4E3A\u8D1F\u6216\u7EE7\u7EED\u56DE\u843D\uFF0C\u77ED\u7EBF\u52A8\u91CF\u4E0D\u8DB3\u3002",
    polarity: "negative"
  },
  RSI_LOW_RECOVERY: {
    code: "RSI_LOW_RECOVERY",
    label: "RSI \u4F4E\u4F4D\u4FEE\u590D",
    detail: "RSI \u4ECE\u4F4E\u4F4D\u56DE\u5347\uFF0C\u5B58\u5728\u8D85\u8DCC\u4FEE\u590D\u8FF9\u8C61\u3002",
    polarity: "positive"
  },
  RSI_OVERHEATED: {
    code: "RSI_OVERHEATED",
    label: "RSI \u8FC7\u70ED",
    detail: "RSI \u9AD8\u4E8E 72\uFF0C\u77ED\u7EBF\u8FFD\u9AD8\u98CE\u9669\u4E0A\u5347\u3002",
    polarity: "negative"
  },
  VOLUME_EXPANSION: {
    code: "VOLUME_EXPANSION",
    label: "\u91CF\u80FD\u653E\u5927",
    detail: "\u6210\u4EA4\u91CF\u660E\u663E\u9AD8\u4E8E 20 \u671F\u5747\u91CF\uFF0C\u4EF7\u683C\u52A8\u4F5C\u6709\u91CF\u80FD\u786E\u8BA4\u3002",
    polarity: "positive"
  },
  BOLLINGER_BREAKOUT: {
    code: "BOLLINGER_BREAKOUT",
    label: "\u6CE2\u52A8\u5411\u4E0A\u6269\u5F20",
    detail: "\u5E03\u6797\u5E26\u6536\u7A84\u540E\u5411\u4E0A\u7A81\u7834\uFF0C\u53EF\u80FD\u8FDB\u5165\u6CE2\u52A8\u6269\u5F20\u9636\u6BB5\u3002",
    polarity: "positive"
  },
  BOLLINGER_BREAKDOWN: {
    code: "BOLLINGER_BREAKDOWN",
    label: "\u8DCC\u7834\u5E03\u6797\u4E0B\u8F68",
    detail: "\u4EF7\u683C\u8DCC\u7834\u5E03\u6797\u4E0B\u8F68\uFF0C\u5F31\u52BF\u6CE2\u52A8\u4ECD\u5728\u91CA\u653E\u3002",
    polarity: "negative"
  },
  HIGH_VOLATILITY: {
    code: "HIGH_VOLATILITY",
    label: "\u6CE2\u52A8\u7387\u504F\u9AD8",
    detail: "ATR \u5360\u4EF7\u683C\u6BD4\u4F8B\u504F\u9AD8\uFF0C\u63D0\u9192\u9608\u503C\u548C\u4ED3\u4F4D\u9700\u8981\u66F4\u4FDD\u5B88\u3002",
    polarity: "negative"
  },
  NO_CONFLUENCE: {
    code: "NO_CONFLUENCE",
    label: "\u5C1A\u672A\u5171\u632F",
    detail: "\u8D8B\u52BF\u3001\u52A8\u91CF\u3001\u6CE2\u52A8\u7387\u548C\u6210\u4EA4\u91CF\u5C1A\u672A\u5F62\u6210\u660E\u786E\u5171\u632F\u3002",
    polarity: "neutral"
  },
  DATA_INSUFFICIENT: {
    code: "DATA_INSUFFICIENT",
    label: "\u6570\u636E\u4E0D\u8DB3",
    detail: "\u9700\u8981\u81F3\u5C11 60 \u6839 K \u7EBF\u6765\u7A33\u5B9A\u8BA1\u7B97\u8D8B\u52BF\u3001\u52A8\u91CF\u548C\u6CE2\u52A8\u7387\u3002",
    polarity: "neutral"
  },
  SOURCE_DEGRADED: {
    code: "SOURCE_DEGRADED",
    label: "\u6765\u6E90\u964D\u7EA7",
    detail: "\u884C\u60C5\u6765\u6E90\u5904\u4E8E\u964D\u7EA7\u72B6\u6001\uFF0CMTS \u53EA\u4FDD\u7559\u89E3\u91CA\u6027\u6280\u672F\u63D0\u9192\u3002",
    polarity: "neutral"
  },
  UNKNOWN_CODE: {
    code: "UNKNOWN_CODE",
    label: "\u672A\u77E5\u539F\u56E0\u7801",
    detail: "\u5F53\u524D\u539F\u56E0\u7801\u672A\u6CE8\u518C\uFF0C\u4E0D\u80FD\u4F5C\u4E3A\u6709\u6548\u89E3\u91CA\u4F9D\u636E\u3002",
    polarity: "neutral"
  }
};
function resolveMtsReason(code, detail) {
  const entry = reasonRegistry[code] ?? reasonRegistry.UNKNOWN_CODE;
  return detail ? { ...entry, detail } : entry;
}

// src/lib/indicators.ts
function sma(values, period) {
  const result = values.map(() => Number.NaN);
  let sum = 0;
  values.forEach((value, index) => {
    sum += value;
    if (index >= period) {
      sum -= values[index - period];
    }
    if (index >= period - 1) {
      result[index] = sum / period;
    }
  });
  return result;
}
function ema(values, period) {
  const result = values.map(() => Number.NaN);
  const multiplier = 2 / (period + 1);
  let previous = 0;
  values.forEach((value, index) => {
    if (index === period - 1) {
      previous = values.slice(0, period).reduce((sum, current) => sum + current, 0) / period;
      result[index] = previous;
      return;
    }
    if (index >= period) {
      previous = value * multiplier + previous * (1 - multiplier);
      result[index] = previous;
    }
  });
  return result;
}
function standardDeviation(values) {
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  const variance = values.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / values.length;
  return Math.sqrt(variance);
}
function rsi(values, period = 14) {
  const result = values.map(() => Number.NaN);
  let avgGain = 0;
  let avgLoss = 0;
  for (let index = 1; index <= period; index += 1) {
    const change = values[index] - values[index - 1];
    avgGain += Math.max(change, 0);
    avgLoss += Math.max(-change, 0);
  }
  avgGain /= period;
  avgLoss /= period;
  result[period] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  for (let index = period + 1; index < values.length; index += 1) {
    const change = values[index] - values[index - 1];
    avgGain = (avgGain * (period - 1) + Math.max(change, 0)) / period;
    avgLoss = (avgLoss * (period - 1) + Math.max(-change, 0)) / period;
    result[index] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  }
  return result;
}
function macd(values) {
  const fast = ema(values, 12);
  const slow = ema(values, 26);
  const line = values.map(
    (_, index) => Number.isFinite(fast[index]) && Number.isFinite(slow[index]) ? fast[index] - slow[index] : Number.NaN
  );
  const signal = ema(
    line.map((value) => Number.isFinite(value) ? value : 0),
    9
  );
  const histogram = line.map(
    (value, index) => Number.isFinite(value) && Number.isFinite(signal[index]) ? value - signal[index] : Number.NaN
  );
  return { line, signal, histogram };
}
function bollinger(values, period = 20, multiplier = 2) {
  const middle = sma(values, period);
  const upper = values.map(() => Number.NaN);
  const lower = values.map(() => Number.NaN);
  const width = values.map(() => Number.NaN);
  values.forEach((_, index) => {
    if (index < period - 1) {
      return;
    }
    const window = values.slice(index - period + 1, index + 1);
    const deviation = standardDeviation(window);
    upper[index] = middle[index] + deviation * multiplier;
    lower[index] = middle[index] - deviation * multiplier;
    width[index] = middle[index] === 0 ? Number.NaN : (upper[index] - lower[index]) / middle[index];
  });
  return { middle, upper, lower, width };
}
function atr(bars2, period = 14) {
  const trueRanges = bars2.map((bar, index) => {
    if (index === 0) {
      return bar.high - bar.low;
    }
    const previousClose = bars2[index - 1].close;
    return Math.max(bar.high - bar.low, Math.abs(bar.high - previousClose), Math.abs(bar.low - previousClose));
  });
  return ema(trueRanges, period);
}
function obv(bars2) {
  const result = bars2.map(() => 0);
  for (let index = 1; index < bars2.length; index += 1) {
    const direction = bars2[index].close > bars2[index - 1].close ? 1 : bars2[index].close < bars2[index - 1].close ? -1 : 0;
    result[index] = result[index - 1] + direction * bars2[index].volume;
  }
  return result;
}
function lastFinite(values, offset = 0) {
  let seen = 0;
  for (let index = values.length - 1; index >= 0; index -= 1) {
    if (Number.isFinite(values[index])) {
      if (seen === offset) {
        return values[index];
      }
      seen += 1;
    }
  }
  return Number.NaN;
}
function slope(values, lookback = 5) {
  const valid = values.filter(Number.isFinite);
  if (valid.length < lookback + 1) {
    return Number.NaN;
  }
  const current = valid[valid.length - 1];
  const previous = valid[valid.length - 1 - lookback];
  return previous === 0 ? Number.NaN : (current - previous) / previous;
}

// src/lib/signals.ts
function reason(code, detail) {
  return resolveMtsReason(code, detail);
}
function scoreBand(score) {
  if (score === null) return "not_applicable";
  if (score >= 60) return "strong_positive";
  if (score >= 30) return "positive";
  if (score <= -60) return "strong_negative";
  if (score <= -30) return "negative";
  return "neutral";
}
function trendStateFor(score, invalidators) {
  if (invalidators.some((item) => item.code === "DATA_INSUFFICIENT")) return "data_insufficient";
  if (invalidators.some((item) => item.code === "SOURCE_DEGRADED")) return "source_degraded";
  if (score === null) return "neutral";
  if (score >= 30) return "bullish";
  if (score <= -30) return "bearish";
  return "neutral";
}
function signalTypeFor(score, invalidators) {
  if (invalidators.some((item) => item.code === "DATA_INSUFFICIENT")) return "data_insufficient";
  if (score === null) return "watch";
  if (score <= -30) return "risk_alert";
  return "technical_alert";
}
function alertLevelFor(score, invalidators) {
  if (invalidators.length > 0 || score === null) return "none";
  if (Math.abs(score) >= 60) return "high";
  if (Math.abs(score) >= 30) return "elevated";
  return "watch";
}
function displayLabelFor(score, invalidators) {
  if (invalidators.some((item) => item.code === "DATA_INSUFFICIENT")) return "\u6570\u636E\u4E0D\u8DB3\uFF0C\u6682\u4E0D\u8F93\u51FA MTS";
  if (invalidators.some((item) => item.code === "SOURCE_DEGRADED")) return "\u6765\u6E90\u964D\u7EA7\uFF0C\u4EC5\u4FDD\u7559\u6280\u672F\u63D0\u9192";
  if (score === null) return "MTS \u89C2\u5BDF";
  if (score >= 60) return "\u5F3A\u6B63\u5411\u6280\u672F\u63D0\u9192";
  if (score >= 30) return "\u6B63\u5411\u6280\u672F\u89C2\u5BDF";
  if (score <= -60) return "\u9AD8\u98CE\u9669\u6280\u672F\u63D0\u9192";
  if (score <= -30) return "\u98CE\u9669\u6280\u672F\u89C2\u5BDF";
  return "\u4E2D\u6027\u89C2\u5BDF";
}
function buildMtsExplanation(score, reasons, invalidators) {
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
    technicalReminder: "MTS \u4EC5\u7528\u4E8E\u6280\u672F\u63D0\u9192\u548C\u98CE\u9669\u89C2\u5BDF\uFF0C\u4E0D\u6784\u6210\u6536\u76CA\u627F\u8BFA\u6216\u786E\u5B9A\u6027\u4E70\u5356\u5EFA\u8BAE\u3002"
  };
}
function buildSignal(bars2, sourceHealth2) {
  if (bars2.length < 60) {
    const invalidators2 = [reason("DATA_INSUFFICIENT")];
    const mts2 = buildMtsExplanation(null, [], invalidators2);
    return {
      kind: "hold",
      label: mts2.displayLabel,
      score: 0,
      confidence: 0,
      buyLine: Number.NaN,
      sellLine: Number.NaN,
      stopLine: Number.NaN,
      reasons: invalidators2.map((item) => item.detail),
      warnings: [],
      mts: mts2
    };
  }
  const closes = bars2.map((bar) => bar.close);
  const volumes = bars2.map((bar) => bar.volume);
  const current = bars2[bars2.length - 1];
  const ema20 = ema(closes, 20);
  const ema60 = ema(closes, 60);
  const rsi14 = rsi(closes, 14);
  const macdData = macd(closes);
  const band = bollinger(closes, 20, 2);
  const atr14 = atr(bars2, 14);
  const obvSeries = obv(bars2);
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
  const trendScore = (current.close > latestEma20 ? 12 : -12) + (latestEma20 > latestEma60 ? 18 : -18) + (slope(ema20, 5) > 0 ? 10 : -10);
  const momentumScore = (latestRsi > 50 ? 10 : -8) + (latestRsi < 35 && latestRsi > previousRsi ? 10 : 0) + (latestRsi > 72 ? -12 : 0) + (latestMacdHist > 0 ? 12 : -12) + (latestMacdHist > previousMacdHist ? 8 : -8);
  const volumeRatio = latestAverageVolume > 0 ? current.volume / latestAverageVolume : 1;
  const volumeScore = (volumeRatio > 1.25 ? 10 : volumeRatio < 0.65 ? -6 : 0) + (slope(obvSeries, 8) > 0 ? 10 : -8);
  const atrPercent = current.close > 0 ? latestAtr / current.close : 0;
  const volatilityScore = (latestBandWidth < 0.08 && current.close > latestUpper ? 12 : 0) + (current.close < latestLower ? -12 : 0) + (atrPercent > 0.08 ? -10 : 0);
  const rawScore = trendScore + momentumScore + volumeScore + volatilityScore;
  const score = Math.max(-100, Math.min(100, Math.round(rawScore)));
  const confidence = Math.max(0, Math.min(100, Math.round(55 + Math.abs(score) * 0.35 - atrPercent * 120)));
  const kind = score >= 60 ? "strong-buy" : score >= 30 ? "buy-watch" : score <= -60 ? "strong-sell" : score <= -30 ? "sell-watch" : "hold";
  const labelByKind = {
    "strong-buy": "\u5F3A\u6B63\u5411\u6280\u672F\u63D0\u9192",
    "buy-watch": "\u6B63\u5411\u6280\u672F\u89C2\u5BDF",
    hold: "\u89C2\u671B",
    "sell-watch": "\u98CE\u9669\u6280\u672F\u89C2\u5BDF",
    "strong-sell": "\u9AD8\u98CE\u9669\u6280\u672F\u63D0\u9192"
  };
  const reasonCodes = [];
  const invalidatorCodes = [];
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
  if (sourceHealth2?.status && sourceHealth2.status !== "formal") {
    invalidatorCodes.push("SOURCE_DEGRADED");
  }
  const mtsReasons = reasonCodes.map(
    (code) => code === "VOLUME_EXPANSION" ? reason(code, `\u6210\u4EA4\u91CF\u7EA6\u4E3A 20 \u671F\u5747\u91CF\u7684 ${volumeRatio.toFixed(1)} \u500D\uFF0C\u4EF7\u683C\u52A8\u4F5C\u6709\u91CF\u80FD\u786E\u8BA4\u3002`) : reason(code)
  );
  const invalidators = invalidatorCodes.map(
    (code) => code === "SOURCE_DEGRADED" ? reason(code, `\u6765\u6E90\u72B6\u6001\u4E3A ${sourceHealth2?.status}\uFF0C${sourceHealth2?.degradationReason ?? "\u4E0D\u80FD\u6309\u6B63\u5F0F\u5B9E\u65F6\u884C\u60C5\u8F93\u51FA\u6709\u6548\u63D0\u9192\u7B49\u7EA7"}\u3002`) : reason(code)
  );
  const mts = buildMtsExplanation(invalidators.some((item) => item.code === "SOURCE_DEGRADED") ? null : score, mtsReasons, invalidators);
  return {
    kind,
    label: mts.displayLabel || labelByKind[kind],
    score: mts.mtsScore ?? 0,
    confidence: invalidators.some((item) => item.code === "SOURCE_DEGRADED") ? 0 : confidence,
    buyLine: Number.isFinite(latestUpper) ? latestUpper : latestEma20,
    sellLine: Number.isFinite(latestMiddle) ? latestMiddle : latestEma20,
    stopLine: Number.isFinite(latestAtr) ? Math.max(current.close - latestAtr * 2.2, latestLower) : latestLower,
    reasons: mtsReasons.map((item) => item.detail),
    warnings: invalidators.map((item) => item.detail),
    mts
  };
}

// tests/replay/mts/replay.spec.ts
function bars(count, startClose, step) {
  return Array.from({ length: count }, (_, index) => {
    const close = startClose + index * step;
    return {
      time: 17e8 + index * 86400,
      open: close - 0.5,
      high: close + 1.8,
      low: close - 1.4,
      close,
      volume: 9e5 + index * 15e3
    };
  });
}
function sourceHealth(status) {
  return {
    status,
    affectedObjects: status === "formal" ? [] : ["chart", "mts", "alerts"],
    retryState: {
      attempt: status === "formal" ? 0 : 1,
      canRetry: status !== "formal",
      reason: status === "formal" ? void 0 : "fixture degradation"
    },
    degradationReason: status === "formal" ? void 0 : "fixture degradation"
  };
}
test("MTS replay corpus stays deterministic and covers valid, insufficient and degraded states", () => {
  for (const item of replay_corpus_default.cases) {
    const signal = buildSignal(
      bars(item.barCount, item.startClose, item.step),
      sourceHealth(item.sourceStatus)
    );
    for (const code of item.expectedReasonCodes ?? []) {
      assert.ok(signal.mts.reasonCodes.includes(code), `${item.id} missing ${code}`);
    }
    if (item.expectedTrendState) assert.equal(signal.mts.trendState, item.expectedTrendState);
    if (item.expectedAlertLevel) assert.equal(signal.mts.alertLevel, item.expectedAlertLevel);
    for (const forbidden of item.forbiddenCopy ?? []) {
      assert.equal(signal.mts.displayLabel.includes(forbidden), false, `${item.id} contains ${forbidden}`);
      assert.equal(signal.mts.technicalReminder.includes(forbidden), false, `${item.id} contains ${forbidden}`);
    }
  }
});
test("registry mutation replay proves removed entries degrade instead of passing silently", () => {
  const resolved = resolveMtsReason(replay_corpus_default.registryMutation.unknownCode);
  assert.equal(resolved.code, replay_corpus_default.registryMutation.expectedFallback);
});
