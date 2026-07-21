import type { IndicatorPoint, PriceBar } from "../types";

const emptyPoint = (time: number): IndicatorPoint => ({ time, value: Number.NaN });

export function sma(values: number[], period: number) {
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

export function ema(values: number[], period: number) {
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

export function standardDeviation(values: number[]) {
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  const variance = values.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / values.length;
  return Math.sqrt(variance);
}

export function rsi(values: number[], period = 14) {
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

export function macd(values: number[]) {
  const fast = ema(values, 12);
  const slow = ema(values, 26);
  const line = values.map((_, index) =>
    Number.isFinite(fast[index]) && Number.isFinite(slow[index]) ? fast[index] - slow[index] : Number.NaN
  );
  const signal = ema(
    line.map((value) => (Number.isFinite(value) ? value : 0)),
    9
  );
  const histogram = line.map((value, index) =>
    Number.isFinite(value) && Number.isFinite(signal[index]) ? value - signal[index] : Number.NaN
  );

  return { line, signal, histogram };
}

export function bollinger(values: number[], period = 20, multiplier = 2) {
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

export function atr(bars: PriceBar[], period = 14) {
  const trueRanges = bars.map((bar, index) => {
    if (index === 0) {
      return bar.high - bar.low;
    }
    const previousClose = bars[index - 1].close;
    return Math.max(bar.high - bar.low, Math.abs(bar.high - previousClose), Math.abs(bar.low - previousClose));
  });

  return ema(trueRanges, period);
}

export function obv(bars: PriceBar[]) {
  const result = bars.map(() => 0);

  for (let index = 1; index < bars.length; index += 1) {
    const direction = bars[index].close > bars[index - 1].close ? 1 : bars[index].close < bars[index - 1].close ? -1 : 0;
    result[index] = result[index - 1] + direction * bars[index].volume;
  }

  return result;
}

export function toSeries(bars: PriceBar[], values: number[]) {
  return values
    .map((value, index) => (Number.isFinite(value) ? { time: bars[index].time, value } : emptyPoint(bars[index].time)))
    .filter((point) => Number.isFinite(point.value));
}

export function lastFinite(values: number[], offset = 0) {
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

export function slope(values: number[], lookback = 5) {
  const valid = values.filter(Number.isFinite);
  if (valid.length < lookback + 1) {
    return Number.NaN;
  }
  const current = valid[valid.length - 1];
  const previous = valid[valid.length - 1 - lookback];
  return previous === 0 ? Number.NaN : (current - previous) / previous;
}
