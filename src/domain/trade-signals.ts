import type { PriceBar } from "../types.ts";
import type { MarketObservation } from "./observation.ts";

/**
 * 多标的定制交易信号引擎。每个标的的规则来自对其一年日 K 的实证分析与样本内/样本外验证，
 * 不共用一套通用参数；标的注册见文件底部 STRATEGIES。
 */

export type TradeSignalSide = "buy" | "sell";

export type TradeSignalEvent = {
  index: number;
  time: number;
  side: TradeSignalSide;
  price: number;
  reasons: string[];
};

export type TradeSignalStatus = "ready" | "not_target_symbol" | "data_insufficient" | "source_degraded";
export type TradeSignalStance = "buy" | "sell" | "hold" | "watch";

export type TradeSignalLevels = {
  // 买入侧（正式信号位）
  nextBuyTrigger?: number;
  addPositionTrigger?: number;
  // 买入侧（ATR 投影观察位，未经回测）
  pullbackZoneLow?: number;
  pullbackZoneHigh?: number;
  // 卖出侧（正式信号位）
  entryPrice?: number;
  exitLine?: number;
  stopLoss?: number;
  takeProfit?: number;
  /** 均值回归策略：站上该均线即卖出（动态目标位）。 */
  sellTargetSma?: number;
  // 卖出侧（ATR 投影观察位，未经回测）
  sellWatchOne?: number;
  sellWatchTwo?: number;
  /** 防守门控策略：进场同时要求站上的长期均线。 */
  gateLevel?: number;
  peakClose?: number;
  latestAtr?: number;
};

export type TradeSignalState = {
  strategyId: string;
  strategyLabel: string;
  styleTag: string;
  /** breakout=向上突破触发买入；dip=向下触及触发买入（均值回归）。 */
  buyTriggerDirection: "breakout" | "dip";
  symbol: string;
  status: TradeSignalStatus;
  stance: TradeSignalStance;
  stanceLabel: string;
  holding: boolean;
  levels: TradeSignalLevels;
  /** 均值回归持仓的超时口径：已持有信号根数 / 上限。 */
  holdBarsUsed?: number;
  holdBarsMax?: number;
  events: TradeSignalEvent[];
  lastEvent?: TradeSignalEvent;
  barsSinceLastEvent?: number;
  reasons: string[];
  warnings: string[];
  nonAdvice: string;
};

export type TradeBacktestTrade = {
  entryTime: number;
  entryPrice: number;
  exitTime: number;
  exitPrice: number;
  returnPct: number;
  closed: boolean;
};

export type TradeBacktestReport = {
  strategyId: string;
  symbol: string;
  barsUsed: number;
  windowStart?: number;
  windowEnd?: number;
  buySignals: number;
  sellSignals: number;
  trades: TradeBacktestTrade[];
  closedTrades: number;
  winRate: number | null;
  averageReturnPct: number | null;
  strategyReturnPct: number | null;
  buyHoldReturnPct: number | null;
  /** 策略每日盯市权益曲线的最大回撤（%，≤0）。用于强单边票「回撤比持有低」验收口径。 */
  maxDrawdownPct: number | null;
  /** 同期买入持有权益曲线的最大回撤（%，≤0），作为回撤对比基准。 */
  buyHoldMaxDrawdownPct: number | null;
  note: string;
};

type BreakoutTrailConfig = {
  kind: "breakout_trail";
  lookback: number;
  trailAtrMultiple: number;
  /** 设置后，进场额外要求收盘站上该周期 SMA（防守门控）。 */
  smaGatePeriod?: number;
};

type MeanRevertConfig = {
  kind: "mean_revert";
  lowLookback: number;
  exitSmaPeriod: number;
  maxHoldBars: number;
  stopAtrMultiple: number;
};

export type FanTConfig = {
  /** 高卖触发：收盘创近 N 日收盘新高且高于 SMA(smaPeriod)。 */
  sellLookback: number;
  smaPeriod: number;
  /** 买回触发：收盘创近 N 日收盘新低。 */
  buyLookback: number;
  /** 追高认错：卖出后收盘 ≥ 卖出信号收盘 + k×ATR20，立即买回（防卖飞）。 */
  chaseAtrMultiple: number;
};

export type TradeStrategyDefinition = {
  key: string;
  strategyId: string;
  label: string;
  styleTag: string;
  matches: (symbol: string) => boolean;
  displaySymbol: string;
  config: BreakoutTrailConfig | MeanRevertConfig;
  /** 持仓反T（高卖低买降成本）子系统；仅在震荡回归型标的上启用。 */
  fanT?: FanTConfig;
  nonAdvice: string;
  dataWarning: string;
};

const ATR_PERIOD = 20;
const MIN_BARS = 80;

function normalizeSymbol(symbol = "") {
  return symbol.trim().toUpperCase().replace(/\s+/g, "");
}

function matchHkSymbol(symbol: string, codes: string[]) {
  const normalized = normalizeSymbol(symbol);
  return codes.some((code) => normalized === code);
}

// ATR 口径：TR 的简单平均（与策略研究口径一致），非 EMA。
function atrSma(bars: PriceBar[], period: number) {
  const result = bars.map(() => Number.NaN);
  const trueRanges = bars.map((bar, index) => {
    if (index === 0) return bar.high - bar.low;
    const previousClose = bars[index - 1].close;
    return Math.max(bar.high - bar.low, Math.abs(bar.high - previousClose), Math.abs(bar.low - previousClose));
  });
  let sum = 0;
  trueRanges.forEach((value, index) => {
    sum += value;
    if (index >= period) sum -= trueRanges[index - period];
    if (index >= period - 1) result[index] = sum / period;
  });
  return result;
}

function smaSeries(values: number[], period: number) {
  const result = values.map(() => Number.NaN);
  let sum = 0;
  values.forEach((value, index) => {
    sum += value;
    if (index >= period) sum -= values[index - period];
    if (index >= period - 1) result[index] = sum / period;
  });
  return result;
}

function highestClose(bars: PriceBar[], endExclusive: number, lookback: number) {
  let max = Number.NEGATIVE_INFINITY;
  for (let i = Math.max(0, endExclusive - lookback); i < endExclusive; i += 1) {
    if (bars[i].close > max) max = bars[i].close;
  }
  return max;
}

function lowestClose(bars: PriceBar[], endExclusive: number, lookback: number) {
  let min = Number.POSITIVE_INFINITY;
  for (let i = Math.max(0, endExclusive - lookback); i < endExclusive; i += 1) {
    if (bars[i].close < min) min = bars[i].close;
  }
  return min;
}

/** 权益曲线最大回撤（%，返回 ≤0 的数）；空序列返回 null。 */
function maxDrawdownPct(series: number[]): number | null {
  if (series.length === 0) return null;
  let peak = series[0];
  let worst = 0;
  for (const value of series) {
    if (value > peak) peak = value;
    if (peak > 0) {
      const drawdown = ((value - peak) / peak) * 100;
      if (drawdown < worst) worst = drawdown;
    }
  }
  return worst;
}

type EngineResult = {
  events: TradeSignalEvent[];
  holding: boolean;
  levels: TradeSignalLevels;
  holdBarsUsed?: number;
  holdBarsMax?: number;
};

/**
 * 突破跟踪引擎（阿里 9988 / 美团 3690 防守门控版）：
 *  - 买入：收盘创近 N 日收盘新高；门控版额外要求收盘站上长期 SMA；
 *  - 卖出：收盘跌破 max(初始止损, 峰值收盘 − k×ATR20)；
 *  - 止损/止盈按是否越过信号成本区分（低于成本的线不称"止盈"）。
 */
function runBreakoutTrailEngine(bars: PriceBar[], cfg: BreakoutTrailConfig): EngineResult {
  const events: TradeSignalEvent[] = [];
  const levels: TradeSignalLevels = {};
  if (bars.length < MIN_BARS) return { events, holding: false, levels };

  const atr20 = atrSma(bars, ATR_PERIOD);
  const closes = bars.map((bar) => bar.close);
  const gate = cfg.smaGatePeriod ? smaSeries(closes, cfg.smaGatePeriod) : undefined;
  let holding = false;
  let peak: number | undefined;
  let entryPrice: number | undefined;
  let initialStop: number | undefined;

  for (let i = cfg.lookback; i < bars.length; i += 1) {
    if (!Number.isFinite(atr20[i])) continue;
    if (gate && !Number.isFinite(gate[i])) continue;
    const close = bars[i].close;

    if (!holding) {
      const priorHigh = highestClose(bars, i, cfg.lookback);
      const gateOk = !gate || close > gate[i];
      if (close >= priorHigh && gateOk) {
        entryPrice = close;
        initialStop = close - cfg.trailAtrMultiple * atr20[i];
        events.push({
          index: i,
          time: bars[i].time,
          side: "buy",
          price: close,
          reasons: [
            `收盘 ${close.toFixed(2)} 创近 ${cfg.lookback} 日收盘新高（前高 ${priorHigh.toFixed(2)}），动量突破`,
            ...(gate ? [`收盘站上 SMA${cfg.smaGatePeriod} ${gate[i].toFixed(2)}，趋势门控通过`] : []),
            `初始止损位 ${initialStop.toFixed(2)}（信号收盘 − ${cfg.trailAtrMultiple}×ATR20）`
          ]
        });
        holding = true;
        peak = close;
      }
    } else {
      peak = Math.max(peak ?? close, close);
      const trail = peak - cfg.trailAtrMultiple * atr20[i];
      const exitLine = Math.max(initialStop ?? trail, trail);
      if (close < exitLine) {
        const lockedProfit = entryPrice !== undefined && exitLine > entryPrice;
        events.push({
          index: i,
          time: bars[i].time,
          side: "sell",
          price: close,
          reasons: [
            `收盘 ${close.toFixed(2)} 跌破离场线 ${exitLine.toFixed(2)}（峰值收盘 ${peak.toFixed(2)} − ${cfg.trailAtrMultiple}×ATR20，初始止损兜底）`,
            lockedProfit
              ? `离场线高于信号成本 ${entryPrice?.toFixed(2)}，属止盈离场`
              : `离场线低于信号成本 ${entryPrice?.toFixed(2) ?? "--"}，属止损离场`
          ]
        });
        holding = false;
        peak = undefined;
        entryPrice = undefined;
        initialStop = undefined;
      }
    }
  }

  const lastIndex = bars.length - 1;
  const atr = Number.isFinite(atr20[lastIndex]) ? atr20[lastIndex] : undefined;
  levels.latestAtr = atr;
  const lookbackHigh = highestClose(bars, bars.length, cfg.lookback);
  const lastClose = bars[lastIndex].close;
  if (gate && Number.isFinite(gate[lastIndex])) levels.gateLevel = gate[lastIndex];

  if (holding && peak !== undefined && atr !== undefined) {
    levels.peakClose = peak;
    levels.entryPrice = entryPrice;
    const trail = peak - cfg.trailAtrMultiple * atr;
    const exitLine = Math.max(initialStop ?? trail, trail);
    levels.exitLine = exitLine;
    if (entryPrice !== undefined && exitLine > entryPrice) {
      levels.takeProfit = exitLine;
    } else {
      levels.stopLoss = exitLine;
    }
    levels.addPositionTrigger = gate
      ? Math.max(lookbackHigh, gate[lastIndex])
      : lookbackHigh;
    const zoneLow = Math.max(exitLine, peak - 2 * atr);
    const zoneHigh = peak - atr;
    if (zoneHigh > zoneLow) {
      levels.pullbackZoneLow = zoneLow;
      levels.pullbackZoneHigh = zoneHigh;
    }
  } else {
    levels.nextBuyTrigger = gate && Number.isFinite(gate[lastIndex])
      ? Math.max(lookbackHigh, gate[lastIndex])
      : lookbackHigh;
  }

  if (atr !== undefined) {
    const twentyDayHigh = highestClose(bars, bars.length, 20);
    levels.sellWatchOne = Math.max(twentyDayHigh, lastClose + 1.5 * atr);
    levels.sellWatchTwo = levels.sellWatchOne + 1.5 * atr;
  }
  return { events, holding, levels };
}

/**
 * 均值回归引擎（腾讯 700）：
 *  - 买入：收盘创近 N 日收盘新低（买弱，次日开盘进场）；
 *  - 卖出（任一）：收盘回升站上 SMA20（目标位）；收盘跌破固定止损（信号收盘 − k×ATR20）；
 *    持有超过 maxHoldBars 根仍未触发前两者（超时离场，不与震荡市耗时间）。
 */
function runMeanRevertEngine(bars: PriceBar[], cfg: MeanRevertConfig): EngineResult {
  const events: TradeSignalEvent[] = [];
  const levels: TradeSignalLevels = {};
  if (bars.length < MIN_BARS) return { events, holding: false, levels };

  const atr20 = atrSma(bars, ATR_PERIOD);
  const closes = bars.map((bar) => bar.close);
  const exitSma = smaSeries(closes, cfg.exitSmaPeriod);
  let holding = false;
  let entryPrice: number | undefined;
  let stop: number | undefined;
  let signalIndex: number | undefined;

  for (let i = Math.max(cfg.lowLookback, 61); i < bars.length; i += 1) {
    if (!Number.isFinite(atr20[i]) || !Number.isFinite(exitSma[i])) continue;
    const close = bars[i].close;

    if (!holding) {
      const priorLow = lowestClose(bars, i, cfg.lowLookback);
      if (close <= priorLow) {
        entryPrice = close;
        stop = close - cfg.stopAtrMultiple * atr20[i];
        signalIndex = i;
        events.push({
          index: i,
          time: bars[i].time,
          side: "buy",
          price: close,
          reasons: [
            `收盘 ${close.toFixed(2)} 创近 ${cfg.lowLookback} 日收盘新低（前低 ${priorLow.toFixed(2)}），超跌买入`,
            `固定止损位 ${stop.toFixed(2)}（信号收盘 − ${cfg.stopAtrMultiple}×ATR20）`,
            `目标：收盘回升站上 SMA${cfg.exitSmaPeriod}；最长持有 ${cfg.maxHoldBars} 根 K 线`
          ]
        });
        holding = true;
      }
    } else {
      const held = i - (signalIndex ?? i);
      const hitStop = stop !== undefined && close < stop;
      const hitTarget = close > exitSma[i];
      const hitTimeout = held >= cfg.maxHoldBars + 1;
      if (hitStop || hitTarget || hitTimeout) {
        events.push({
          index: i,
          time: bars[i].time,
          side: "sell",
          price: close,
          reasons: [
            hitStop
              ? `收盘 ${close.toFixed(2)} 跌破固定止损位 ${(stop ?? 0).toFixed(2)}，止损离场`
              : hitTarget
                ? `收盘 ${close.toFixed(2)} 站上 SMA${cfg.exitSmaPeriod} ${exitSma[i].toFixed(2)}，回归目标达成`
                : `持有 ${held} 根 K 线未达目标，超时离场`
          ]
        });
        holding = false;
        entryPrice = undefined;
        stop = undefined;
        signalIndex = undefined;
      }
    }
  }

  const lastIndex = bars.length - 1;
  const atr = Number.isFinite(atr20[lastIndex]) ? atr20[lastIndex] : undefined;
  levels.latestAtr = atr;
  const result: EngineResult = { events, holding, levels };

  if (holding && atr !== undefined) {
    levels.entryPrice = entryPrice;
    levels.stopLoss = stop;
    levels.exitLine = stop;
    if (Number.isFinite(exitSma[lastIndex])) {
      levels.sellTargetSma = exitSma[lastIndex];
      levels.sellWatchOne = exitSma[lastIndex] + 1.5 * atr;
    }
    result.holdBarsUsed = lastIndex - (signalIndex ?? lastIndex);
    result.holdBarsMax = cfg.maxHoldBars + 1;
  } else {
    levels.nextBuyTrigger = lowestClose(bars, bars.length, cfg.lowLookback);
    if (Number.isFinite(exitSma[lastIndex])) levels.sellTargetSma = exitSma[lastIndex];
  }
  return result;
}

export type FanTPhase = "full" | "reduced";

export type FanTRound = {
  sellTime: number;
  sellPrice: number;
  buyTime: number;
  buyPrice: number;
  spreadPct: number;
  byChase: boolean;
};

export type FanTState = {
  enabled: boolean;
  phase: FanTPhase;
  /** 满仓阶段：收盘站上该位触发高卖（近 N 日最高收盘，且需高于 SMA20）。 */
  sellTrigger?: number;
  /** 已卖出阶段：收盘跌破该位触发买回（近 N 日最低收盘）。 */
  buyBackTrigger?: number;
  /** 已卖出阶段：收盘涨过该位立即认错买回（卖出信号收盘 + k×ATR20）。 */
  chaseStop?: number;
  /** 已卖出阶段：卖出信号收盘参考。 */
  soldRefPrice?: number;
  rounds: FanTRound[];
  completedRounds: number;
  winRounds: number;
  totalSpreadPct: number;
  worstSpreadPct: number | null;
};

/**
 * 反T（持仓高卖低买降成本）引擎：满仓起步，高卖 → 买回交替。
 * 全部只用截至当根 K 线的数据；回合按信号次日开盘成交计算价差。
 */
export function buildFanTState(symbol: string, bars: PriceBar[]): FanTState {
  const def = resolveTradeStrategy(symbol);
  const cfg = def?.fanT;
  const empty: FanTState = {
    enabled: false,
    phase: "full",
    rounds: [],
    completedRounds: 0,
    winRounds: 0,
    totalSpreadPct: 0,
    worstSpreadPct: null
  };
  if (!cfg || bars.length < MIN_BARS) return empty;

  const atr20 = atrSma(bars, ATR_PERIOD);
  const closes = bars.map((bar) => bar.close);
  const sma = smaSeries(closes, cfg.smaPeriod);
  const rounds: FanTRound[] = [];
  let phase: FanTPhase = "full";
  let sellRef: number | undefined;
  let sellExec: { time: number; price: number } | undefined;

  for (let i = Math.max(cfg.sellLookback, 61); i < bars.length; i += 1) {
    if (!Number.isFinite(atr20[i]) || !Number.isFinite(sma[i])) continue;
    const close = bars[i].close;

    if (phase === "full") {
      if (close >= highestClose(bars, i, cfg.sellLookback) && close > sma[i]) {
        const next = bars[i + 1];
        sellRef = close;
        sellExec = next ? { time: next.time, price: next.open } : undefined;
        phase = "reduced";
      }
    } else {
      const byBuyBack = close <= lowestClose(bars, i, cfg.buyLookback);
      const byChase = sellRef !== undefined && close >= sellRef + cfg.chaseAtrMultiple * atr20[i];
      if (byBuyBack || byChase) {
        const next = bars[i + 1];
        if (sellExec && next) {
          rounds.push({
            sellTime: sellExec.time,
            sellPrice: sellExec.price,
            buyTime: next.time,
            buyPrice: next.open,
            spreadPct: next.open === 0 ? 0 : ((sellExec.price - next.open) / next.open) * 100,
            byChase: !byBuyBack && byChase
          });
        }
        phase = "full";
        sellRef = undefined;
        sellExec = undefined;
      }
    }
  }

  const lastIndex = bars.length - 1;
  const atr = Number.isFinite(atr20[lastIndex]) ? atr20[lastIndex] : undefined;
  const wins = rounds.filter((round) => round.spreadPct > 0);
  const state: FanTState = {
    enabled: true,
    phase,
    rounds,
    completedRounds: rounds.length,
    winRounds: wins.length,
    totalSpreadPct: rounds.reduce((sum, round) => sum + round.spreadPct, 0),
    worstSpreadPct: rounds.length > 0 ? Math.min(...rounds.map((round) => round.spreadPct)) : null
  };
  if (phase === "full") {
    state.sellTrigger = highestClose(bars, bars.length, cfg.sellLookback);
  } else {
    state.buyBackTrigger = lowestClose(bars, bars.length, cfg.buyLookback);
    state.soldRefPrice = sellRef;
    if (sellRef !== undefined && atr !== undefined) state.chaseStop = sellRef + cfg.chaseAtrMultiple * atr;
  }
  return state;
}

export const STRATEGIES: TradeStrategyDefinition[] = [
  {
    key: "alibaba",
    strategyId: "alibaba-9988-breakout-trail-v2",
    label: "9988.HK 买卖信号",
    styleTag: "动量突破+跟踪",
    displaySymbol: "HK.09988",
    matches: (symbol) => matchHkSymbol(symbol, ["HK.09988", "HK.9988", "09988.HK", "9988.HK"]),
    config: { kind: "breakout_trail", lookback: 15, trailAtrMultiple: 2.5 },
    nonAdvice: "信号由「15 日收盘新高突破 + 2.5×ATR20 跟踪离场」的固定规则计算，仅作技术分析提醒，不构成投资建议或收益承诺。",
    dataWarning: "只使用 futud 日线价量数据，未纳入财报、消息面、资金流和持仓约束。"
  },
  {
    key: "tencent",
    strategyId: "tencent-0700-meanrev-v2",
    label: "0700.HK 买卖信号",
    styleTag: "均值回归",
    displaySymbol: "HK.00700",
    matches: (symbol) => matchHkSymbol(symbol, ["HK.00700", "HK.0700", "00700.HK", "0700.HK", "700.HK"]),
    config: { kind: "mean_revert", lowLookback: 15, exitSmaPeriod: 20, maxHoldBars: 15, stopAtrMultiple: 2.5 },
    fanT: { sellLookback: 15, smaPeriod: 20, buyLookback: 15, chaseAtrMultiple: 1.0 },
    nonAdvice: "信号由「15 日收盘新低买入 + 站上 SMA20 / 止损 / 超时离场」的固定规则计算，仅作技术分析提醒，不构成投资建议或收益承诺。",
    dataWarning: "只使用 futud 日线价量数据，未纳入财报、消息面、资金流和持仓约束。"
  },
  {
    key: "meituan",
    strategyId: "meituan-3690-defensive-v1",
    label: "3690.HK 买卖信号",
    styleTag: "防守门控",
    displaySymbol: "HK.03690",
    matches: (symbol) => matchHkSymbol(symbol, ["HK.03690", "HK.3690", "03690.HK", "3690.HK"]),
    config: { kind: "breakout_trail", lookback: 20, trailAtrMultiple: 3, smaGatePeriod: 60 },
    fanT: { sellLookback: 15, smaPeriod: 20, buyLookback: 10, chaseAtrMultiple: 1.0 },
    nonAdvice:
      "该标的过去一年未发现稳健正期望的做多规则；本策略为防守型（站上 SMA60 且 20 日新高才试仓，3×ATR20 跟踪离场），大部分时间输出空仓观望。仅作技术分析提醒，不构成投资建议。",
    dataWarning: "实证提示：该标的突破追涨历史胜率极低（20 日新高后 10 日胜率 9%），系统靠少交易避险，非盈利引擎。"
  }
];

STRATEGIES.push(
  {
    key: "smic",
    strategyId: "smic-0981-breakout-trail-v1",
    label: "0981.HK 买卖信号",
    styleTag: "趋势跟随",
    displaySymbol: "HK.00981",
    matches: (symbol) => matchHkSymbol(symbol, ["HK.00981", "HK.0981", "00981.HK", "0981.HK", "981.HK"]),
    // 实证：近1年买入持有 +79%、创新高后10日 +1.9%/创新低后10日 +4.0% 均正期望，属强单边上涨。
    // 参数由自身数据扫参：lookback=20 / 3×ATR20 跟踪，回测约 +78% 收益、-26% 最大回撤（持有 -44%），
    // 以更小回撤跟住主升段。均值回归会过早离场封住上行，故改趋势跟随。
    config: { kind: "breakout_trail", lookback: 20, trailAtrMultiple: 3 },
    nonAdvice: "信号由「20 日收盘新高突破买入 + 3×ATR20 跟踪离场」的固定规则计算，仅作技术分析提醒，不构成投资建议或收益承诺。",
    dataWarning: "该标的日波动约 5.2%（强单边高波动），趋势跟随以更小回撤跟住主升段；信号触发价与执行价可能偏差较大，未纳入财报、消息面与持仓约束。"
  },
  {
    key: "xiaomi",
    strategyId: "xiaomi-1810-defensive-v1",
    label: "1810.HK 买卖信号",
    styleTag: "防守门控",
    displaySymbol: "HK.01810",
    matches: (symbol) => matchHkSymbol(symbol, ["HK.01810", "HK.1810", "01810.HK", "1810.HK"]),
    config: { kind: "breakout_trail", lookback: 20, trailAtrMultiple: 3, smaGatePeriod: 60 },
    fanT: { sellLookback: 15, smaPeriod: 20, buyLookback: 15, chaseAtrMultiple: 1.0 },
    nonAdvice:
      "该标的过去一年抄底与追涨均为负期望；本策略为防守型（站上 SMA60 且 20 日新高才试仓，3×ATR20 跟踪离场），大部分时间输出空仓观望。仅作技术分析提醒，不构成投资建议。",
    dataWarning: "实证提示：该标的 15 日新低后 10 日均值 -2.57%（胜率 29%）、20 日新高后 10 日均值 -4.03%（胜率 25%），系统靠少交易避险，非盈利引擎。"
  },
  {
    key: "kingboard",
    strategyId: "kingboard-1888-breakout-trail-v1",
    label: "1888.HK 买卖信号",
    styleTag: "趋势跟随",
    displaySymbol: "HK.01888",
    matches: (symbol) => matchHkSymbol(symbol, ["HK.01888", "HK.1888", "01888.HK", "1888.HK"]),
    // 实证：近1年买入持有 +489%、创新高后10日均值 +11.6%（胜率67%）超强动量、66% 时间站上 SMA60。
    // 参数由自身数据扫参：lookback=15 / 3×ATR20 跟踪，回测约 +447% 收益、-33% 最大回撤（持有 -61%），
    // 以显著更小回撤跟住主升段。日振幅极高故用较宽跟踪，避免正常波动误触离场。
    config: { kind: "breakout_trail", lookback: 15, trailAtrMultiple: 3 },
    nonAdvice: "信号由「15 日收盘新高突破买入 + 3×ATR20 跟踪离场」的固定规则计算，仅作技术分析提醒，不构成投资建议或收益承诺。",
    dataWarning: "该标的日波动约 6.8%（87% 交易日振幅超 3%，自选中最高波动），触发价与执行价可能大幅偏差；趋势跟随目标是以显著更小回撤跟住主升段，未纳入财报、消息面与持仓约束。"
  }
);

export function resolveTradeStrategy(symbol = "") {
  return STRATEGIES.find((strategy) => strategy.matches(symbol));
}

function runEngine(bars: PriceBar[], def: TradeStrategyDefinition): EngineResult {
  return def.config.kind === "breakout_trail"
    ? runBreakoutTrailEngine(bars, def.config)
    : runMeanRevertEngine(bars, def.config);
}

export function computeTradeSignalEvents(symbol: string, bars: PriceBar[]): TradeSignalEvent[] {
  const def = resolveTradeStrategy(symbol);
  if (!def) return [];
  return runEngine(bars, def).events;
}

export function buildTradeSignalState(observation: MarketObservation): TradeSignalState {
  const symbol = normalizeSymbol(observation.symbol ?? "");
  const def = resolveTradeStrategy(symbol);

  const base = {
    strategyId: def?.strategyId ?? "none",
    strategyLabel: def?.label ?? "买卖信号",
    styleTag: def?.styleTag ?? "",
    buyTriggerDirection: (def?.config.kind === "mean_revert" ? "dip" : "breakout") as "breakout" | "dip",
    symbol,
    holding: false,
    levels: {} as TradeSignalLevels,
    events: [] as TradeSignalEvent[],
    warnings: [] as string[],
    nonAdvice: def?.nonAdvice ?? ""
  };

  if (!def) {
    return {
      ...base,
      status: "not_target_symbol",
      stance: "watch",
      stanceLabel: "该标的暂无定制算法",
      reasons: ["当前只为 HK.09988 / HK.00700 / HK.03690 / HK.00981 / HK.01810 / HK.01888 提供定制信号算法。"]
    };
  }

  if (observation.sourceHealth?.status && observation.sourceHealth.status !== "formal") {
    return {
      ...base,
      status: "source_degraded",
      stance: "watch",
      stanceLabel: "来源不可用",
      reasons: [`来源状态为 ${observation.sourceHealth.status}，不输出 ${def.displaySymbol} 买卖信号。`]
    };
  }

  if (observation.bars.length < MIN_BARS) {
    return {
      ...base,
      status: "data_insufficient",
      stance: "watch",
      stanceLabel: "数据不足",
      reasons: [`至少需要 ${MIN_BARS} 根日线 K 线，当前只有 ${observation.bars.length} 根。`]
    };
  }

  const engine = runEngine(observation.bars, def);
  const lastEvent = engine.events.at(-1);
  const barsSinceLastEvent = lastEvent ? observation.bars.length - 1 - lastEvent.index : undefined;
  const warnings = [def.dataWarning];

  if (engine.holding) {
    const stance: TradeSignalStance = barsSinceLastEvent === 0 ? "buy" : "hold";
    const exitHint =
      def.config.kind === "mean_revert"
        ? `目标 SMA${def.config.exitSmaPeriod}，止损/超时离场`
        : "收盘跌破止盈/止损线即离场";
    return {
      ...base,
      status: "ready",
      stance,
      stanceLabel:
        barsSinceLastEvent === 0
          ? "买入信号（最新 K 线触发）"
          : `持有中（${barsSinceLastEvent} 根 K 线前买入），${exitHint}`,
      holding: true,
      levels: engine.levels,
      holdBarsUsed: engine.holdBarsUsed,
      holdBarsMax: engine.holdBarsMax,
      events: engine.events,
      lastEvent,
      barsSinceLastEvent,
      warnings,
      reasons: lastEvent?.reasons ?? []
    };
  }

  const stance: TradeSignalStance = lastEvent && barsSinceLastEvent === 0 ? "sell" : "watch";
  const buyHint =
    def.config.kind === "mean_revert"
      ? `收盘跌破近 ${def.config.lowLookback} 日低点即触发买入`
      : def.config.smaGatePeriod
        ? `需同时站上 SMA${def.config.smaGatePeriod} 与近 ${def.config.lookback} 日高点才触发买入`
        : `收盘突破近 ${def.config.lookback} 日高点即触发买入`;
  return {
    ...base,
    status: "ready",
    stance,
    stanceLabel: lastEvent && barsSinceLastEvent === 0 ? "卖出信号（最新 K 线触发）" : `观望（空仓），${buyHint}`,
    holding: false,
    levels: engine.levels,
    events: engine.events,
    lastEvent,
    barsSinceLastEvent,
    warnings,
    reasons:
      lastEvent && barsSinceLastEvent === 0
        ? lastEvent.reasons
        : [`下一买入触发位：${engine.levels.nextBuyTrigger?.toFixed(2) ?? "--"}（${buyHint}）。`]
  };
}

/**
 * 长仓回测：买入信号在下一根 K 线开盘价进场，卖出信号在下一根 K 线开盘价离场，
 * 避免用触发当根的收盘数据成交造成前视偏差。期末未平仓头寸按最后收盘价估值并标记 closed=false。
 */
export function runTradeBacktest(symbol: string, bars: PriceBar[]): TradeBacktestReport {
  const def = resolveTradeStrategy(symbol);
  const events = def ? runEngine(bars, def).events : [];
  const trades: TradeBacktestTrade[] = [];
  let entry: { time: number; price: number } | null = null;

  for (const event of events) {
    const next = bars[event.index + 1];
    if (!next) continue;
    if (event.side === "buy" && !entry) {
      entry = { time: next.time, price: next.open };
    } else if (event.side === "sell" && entry) {
      trades.push({
        entryTime: entry.time,
        entryPrice: entry.price,
        exitTime: next.time,
        exitPrice: next.open,
        returnPct: entry.price === 0 ? 0 : ((next.open - entry.price) / entry.price) * 100,
        closed: true
      });
      entry = null;
    }
  }

  const lastBar = bars.at(-1);
  if (entry && lastBar) {
    trades.push({
      entryTime: entry.time,
      entryPrice: entry.price,
      exitTime: lastBar.time,
      exitPrice: lastBar.close,
      returnPct: entry.price === 0 ? 0 : ((lastBar.close - entry.price) / entry.price) * 100,
      closed: false
    });
  }

  const closedTrades = trades.filter((trade) => trade.closed);
  const wins = closedTrades.filter((trade) => trade.returnPct > 0);
  const strategyReturnPct =
    trades.length > 0 ? (trades.reduce((product, trade) => product * (1 + trade.returnPct / 100), 1) - 1) * 100 : null;
  const firstBar = bars[0];
  const buyHoldReturnPct =
    firstBar && lastBar && firstBar.open > 0 ? ((lastBar.close - firstBar.open) / firstBar.open) * 100 : null;

  // 每日盯市权益曲线：买入信号次日开盘进场、卖出信号次日开盘离场，持仓期间按当日收盘估值。
  // 与上面 trades 的成交口径一致，用于计算策略最大回撤（不引入前视偏差）。
  const execs: { index: number; side: TradeSignalSide }[] = [];
  for (const event of events) {
    const execIndex = event.index + 1;
    if (bars[execIndex]) execs.push({ index: execIndex, side: event.side });
  }
  const strategyCurve: number[] = [];
  let equity = 1;
  let inPosition = false;
  let heldShares = 0;
  let execCursor = 0;
  for (let i = 0; i < bars.length; i += 1) {
    while (execCursor < execs.length && execs[execCursor].index === i) {
      const exec = execs[execCursor];
      if (exec.side === "buy" && !inPosition && bars[i].open > 0) {
        heldShares = equity / bars[i].open;
        inPosition = true;
      } else if (exec.side === "sell" && inPosition) {
        equity = heldShares * bars[i].open;
        inPosition = false;
        heldShares = 0;
      }
      execCursor += 1;
    }
    strategyCurve.push(inPosition ? heldShares * bars[i].close : equity);
  }
  const maxDrawdown = maxDrawdownPct(strategyCurve);
  const buyHoldCurve = firstBar ? [firstBar.open, ...bars.map((bar) => bar.close)] : [];
  const buyHoldMaxDrawdown = maxDrawdownPct(buyHoldCurve);

  return {
    strategyId: def?.strategyId ?? "none",
    symbol: normalizeSymbol(symbol),
    barsUsed: bars.length,
    windowStart: firstBar?.time,
    windowEnd: lastBar?.time,
    buySignals: events.filter((event) => event.side === "buy").length,
    sellSignals: events.filter((event) => event.side === "sell").length,
    trades,
    closedTrades: closedTrades.length,
    winRate: closedTrades.length > 0 ? (wins.length / closedTrades.length) * 100 : null,
    averageReturnPct:
      closedTrades.length > 0 ? closedTrades.reduce((sum, trade) => sum + trade.returnPct, 0) / closedTrades.length : null,
    strategyReturnPct,
    buyHoldReturnPct,
    maxDrawdownPct: maxDrawdown,
    buyHoldMaxDrawdownPct: buyHoldMaxDrawdown,
    note: "长仓规则回测：信号次日开盘成交，未平仓头寸按期末收盘估值；结果仅用于检验规则历史表现，不构成收益承诺。"
  };
}
