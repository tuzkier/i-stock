import type { PriceBar } from "../types.ts";
import { buildObservationIndicators } from "./observation.ts";
import {
  buildFanTState,
  buildTradeSignalState,
  resolveTradeStrategy,
  type FanTState,
  type TradeSignalState
} from "./trade-signals.ts";

/** FutuOpenD 持仓查询返回的单条持仓（字段与 server/futud-positions.py 输出一致）。 */
export type RawPosition = {
  code: string;
  stock_name?: string;
  qty?: number;
  cost_price?: number;
  nominal_price?: number;
  pl_ratio?: number;
  pl_val?: number;
  market_val?: number;
};

export type HoldingBase = {
  code: string;
  name: string;
  qty: number;
  cost: number;
  /** 最新价（FutuOpenD nominal_price）。 */
  price: number;
  plRatio: number;
};

export type CoveredHolding = HoldingBase & {
  strategyLabel: string;
  styleTag: string;
  /** 策略当前态势与前瞻点位（止损/止盈/下一买点等）。 */
  signal: TradeSignalState;
  /** 吊灯持仓止损参考（近 lookback 日最高收盘 − trailK×ATR20）；仅突破/趋势型有。 */
  chandelierStop?: number;
  /** 吊灯止损是否已被现价跌破（趋势止损意义上应已离场）。 */
  chandelierBreached?: boolean;
  /** 反T 降成本状态（仅震荡回归型标的启用）。 */
  fanT: FanTState;
};

export type HoldingsPanel = {
  holdings: CoveredHolding[];
  uncovered: HoldingBase[];
};

const ATR_PERIOD = 20;

function latestAtr(bars: PriceBar[], period = ATR_PERIOD): number | undefined {
  if (bars.length < period + 1) return undefined;
  const trueRanges = bars.map((bar, index) => {
    if (index === 0) return bar.high - bar.low;
    const previousClose = bars[index - 1].close;
    return Math.max(bar.high - bar.low, Math.abs(bar.high - previousClose), Math.abs(bar.low - previousClose));
  });
  let sum = 0;
  for (let i = trueRanges.length - period; i < trueRanges.length; i += 1) sum += trueRanges[i];
  return sum / period;
}

function highestClose(bars: PriceBar[], lookback: number): number {
  let max = Number.NEGATIVE_INFINITY;
  for (let i = Math.max(0, bars.length - lookback); i < bars.length; i += 1) {
    if (bars[i].close > max) max = bars[i].close;
  }
  return max;
}

/** 吊灯止损：近 lookback 日最高收盘 − trailK×ATR20。对任何持仓者有效，与策略是否模拟在场无关。 */
export function chandelierStop(bars: PriceBar[], lookback: number, trailK: number): number | undefined {
  const atr = latestAtr(bars);
  if (atr === undefined || bars.length === 0) return undefined;
  return highestClose(bars, lookback) - trailK * atr;
}

function toBase(position: RawPosition): HoldingBase {
  return {
    code: String(position.code ?? ""),
    name: String(position.stock_name ?? ""),
    qty: Number(position.qty ?? 0),
    cost: Number(position.cost_price ?? 0),
    price: Number(position.nominal_price ?? 0),
    plRatio: Number(position.pl_ratio ?? 0)
  };
}

/**
 * 把 FutuOpenD 真实持仓与各标的定制策略组装成持仓操作面板。纯函数：不做 I/O。
 * @param positions 持仓列表（来自 futud-positions.py）
 * @param barsBySymbol 每个已注册标的的日线 K 线（键为 position.code 的原始写法）
 */
export function buildHoldingsPanel(positions: RawPosition[], barsBySymbol: Record<string, PriceBar[]>): HoldingsPanel {
  const holdings: CoveredHolding[] = [];
  const uncovered: HoldingBase[] = [];

  for (const position of positions) {
    const base = toBase(position);
    const strategy = resolveTradeStrategy(base.code);
    const bars = barsBySymbol[base.code] ?? barsBySymbol[position.code] ?? [];
    if (!strategy || bars.length === 0) {
      uncovered.push(base);
      continue;
    }
    const indicators = buildObservationIndicators(bars);
    const signal = buildTradeSignalState({ symbol: base.code, bars, indicators });
    const fanT = buildFanTState(base.code, bars);

    let stop: number | undefined;
    let breached: boolean | undefined;
    if (strategy.config.kind === "breakout_trail") {
      stop = chandelierStop(bars, strategy.config.lookback, strategy.config.trailAtrMultiple);
      if (stop !== undefined) breached = base.price < stop;
    }

    holdings.push({
      ...base,
      strategyLabel: strategy.label,
      styleTag: strategy.styleTag,
      signal,
      chandelierStop: stop,
      chandelierBreached: breached,
      fanT
    });
  }

  return { holdings, uncovered };
}
