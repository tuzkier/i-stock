import type { PriceBar } from "../types.ts";
import type { MarketObservation } from "./observation.ts";
import {
  buildTradeSignalState,
  computeTradeSignalEvents,
  resolveTradeStrategy,
  runTradeBacktest,
  type TradeBacktestReport,
  type TradeSignalEvent,
  type TradeSignalState
} from "./trade-signals.ts";

/**
 * 兼容层：HK.09988 定制算法已迁移到 trade-signals.ts 的通用引擎（strategy key: alibaba）。
 * 本文件保留原导出名，规则与行为完全一致。
 */

export const ALIBABA_STRATEGY_ID = "alibaba-9988-breakout-trail-v2" as const;

export type AlibabaSignalEvent = TradeSignalEvent;
export type AlibabaSignalState = TradeSignalState;
export type AlibabaBacktestReport = TradeBacktestReport;

export function isAlibaba9988Symbol(symbol = "") {
  return resolveTradeStrategy(symbol)?.key === "alibaba";
}

export function computeAlibabaSignalEvents(bars: PriceBar[]): TradeSignalEvent[] {
  return computeTradeSignalEvents("HK.09988", bars);
}

export function buildAlibabaSignalState(observation: MarketObservation): TradeSignalState {
  return buildTradeSignalState(observation);
}

export function runAlibabaBacktest(bars: PriceBar[], symbol = "HK.09988"): TradeBacktestReport {
  return runTradeBacktest(symbol, bars);
}
