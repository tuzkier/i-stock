import {
  AreaChart,
  Archive,
  CandlestickChart,
  LineChart,
  Plus,
  RotateCcw,
  Search
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { marketHints, marketLabels } from "./data/markets";
import { buildNormalizationPreview } from "./domain/market-normalization";
import {
  archiveWatchSymbol,
  restoreWatchSymbol,
} from "./domain/watchlist-state";
import {
  acknowledgeAlertRule,
  evaluateAlertRules,
  restoreAlertRulesForActiveSymbol,
  suspendAlertRulesForArchivedSymbol
} from "./domain/alert";
import {
  createWorkspaceSnapshot,
  defaultWorkspaceLayout,
  getLayoutForSymbol,
  withSymbolLayout
} from "./domain/workspace";
import { AlertRulePanel } from "./features/alerts/AlertRulePanel";
import { HoldingsPanel } from "./features/holdings/HoldingsPanel";
import { LayoutController } from "./features/layout/LayoutController";
import { humanizeReason, humanizeTradeStatus, humanizeTrendState } from "./features/presentation/humanize";
import { ScoreBar } from "./features/presentation/ScoreBar";
import { resolveScoreTone, resolveSourceTone } from "./features/presentation/tone";
import { RestoreStatus } from "./features/restore/RestoreStatus";
import { SourceHealthPanel } from "./features/source/SourceHealthPanel";
import { buildObservation } from "./domain/observation";
import {
  buildFanTState,
  buildTradeSignalState,
  resolveTradeStrategy,
  runTradeBacktest,
  type TradeSignalState
} from "./domain/trade-signals";
import { buildSignal } from "./lib/signals";
import { readWorkspace, writeWorkspace } from "./lib/storage";
import type {
  AlertRule,
  ChartPayload,
  MarketCode,
  MtsExplanation,
  RangeKey,
  SourceStatus,
  WatchSymbol,
  WorkspaceLayout
} from "./types";

const markets = Object.keys(marketLabels) as MarketCode[];

type WatchlistQuoteSummary = {
  sourceStatus: SourceStatus;
  latestPrice?: number;
  changeValue?: number;
  changePercent?: number;
};

type DetailTab = "explain" | "alerts" | "source" | "holdings";

function formatNumber(value?: number, digits = 2) {
  if (!Number.isFinite(value)) return "--";
  return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(value as number);
}

function getChange(payload?: ChartPayload) {
  const bars = payload?.bars ?? [];
  const latest = bars.at(-1);
  const previous = payload?.meta.previousClose || bars.at(-2)?.close;
  if (!latest || !previous) return { value: 0, percent: 0 };
  const value = latest.close - previous;
  return { value, percent: (value / previous) * 100 };
}

function getSourceStatus(payload?: ChartPayload, hasError = false): SourceStatus {
  if (hasError && !payload) return "unavailable";
  if (!payload) return "not_loaded";
  if (payload.sourceHealth?.status) return payload.sourceHealth.status;
  return "unavailable";
}

function sourceStatusLabel(status: SourceStatus) {
  if (status === "formal") return "正式";
  if (status === "demo_fallback") return "演示";
  if (status === "stale") return "过期";
  if (status === "unavailable") return "不可用";
  return "未加载";
}

function mtsCardToneClass(mts: MtsExplanation) {
  const tone = resolveScoreTone(mts);
  // signal-card 既有极性类：caution（市场看空）映射到既有 .risk 边框，与 .notice--warning 物理分离（INV-03）
  if (tone === "caution") return "risk";
  if (tone === "positive") return "positive";
  return "neutral";
}

function tradeSignalTone(state: TradeSignalState) {
  if (state.status !== "ready") return "neutral";
  if (state.stance === "buy" || state.stance === "hold") return "positive";
  if (state.stance === "sell") return "risk";
  return "neutral";
}

function quoteSummaryFromPayload(payload: ChartPayload): WatchlistQuoteSummary {
  const latestBar = payload.bars.at(-1);
  const payloadChange = getChange(payload);
  return {
    sourceStatus: getSourceStatus(payload),
    latestPrice: latestBar?.close,
    changeValue: payloadChange.value,
    changePercent: payloadChange.percent
  };
}

function isActiveSymbol(item: WatchSymbol) {
  return item.status !== "archived";
}

export function App() {
  const initialWorkspace = useMemo(() => readWorkspace(), []);
  const initialSnapshot = initialWorkspace.snapshot;
  const initialSelected = initialSnapshot.watchlist.find((item) => item.symbol === initialSnapshot.selectedSymbol)
    ?? initialSnapshot.watchlist.find(isActiveSymbol)
    ?? initialSnapshot.watchlist[0];
  const [watchlist, setWatchlist] = useState<WatchSymbol[]>(() => initialSnapshot.watchlist);
  const [alerts, setAlerts] = useState<AlertRule[]>(() => initialSnapshot.alerts);
  const [selected, setSelected] = useState<WatchSymbol>(() => initialSelected);
  const [range, setRange] = useState<RangeKey>(initialSnapshot.range ?? "6mo");
  const [layoutBySymbol, setLayoutBySymbol] = useState(initialSnapshot.layoutBySymbol);
  const [globalLayoutFallback] = useState<WorkspaceLayout>(initialSnapshot.globalLayoutFallback ?? defaultWorkspaceLayout);
  const [restoreMetadata] = useState(initialWorkspace.restoreMetadata);
  const [market, setMarket] = useState<MarketCode>("US");
  const [inputSymbol, setInputSymbol] = useState("");
  const [inputName, setInputName] = useState("");
  const [payload, setPayload] = useState<ChartPayload>();
  const [quoteSummaries, setQuoteSummaries] = useState<Record<string, WatchlistQuoteSummary>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [refreshTick, setRefreshTick] = useState(0);
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [detailTab, setDetailTab] = useState<DetailTab>("explain");
  const [mtsDetailsOpen, setMtsDetailsOpen] = useState(false);

  // 选中标的行情每 60 秒自动刷新（日线口径），无需手动点刷新。
  useEffect(() => {
    const id = setInterval(() => setRefreshTick((current) => current + 1), 60_000);
    return () => clearInterval(id);
  }, []);
  const [mtsReasonDetailsOpen, setMtsReasonDetailsOpen] = useState(false);
  const selectedFetchesRef = useRef(new Map<string, Promise<ChartPayload>>());
  const selectedRequestTokenRef = useRef(0);
  const summaryRequestKeysRef = useRef(new Set<string>());

  useEffect(() => {
    writeWorkspace(
      createWorkspaceSnapshot({
        watchlist,
        alerts,
        selectedSymbol: selected.symbol,
        range,
        layoutBySymbol,
        globalLayoutFallback
      })
    );
  }, [alerts, globalLayoutFallback, layoutBySymbol, range, selected.symbol, watchlist]);

  const activeWatchlist = useMemo(() => watchlist.filter(isActiveSymbol), [watchlist]);
  const archivedWatchlist = useMemo(() => watchlist.filter((item) => item.status === "archived"), [watchlist]);
  const normalizationPreview = useMemo(
    () => buildNormalizationPreview(inputSymbol, market, watchlist),
    [inputSymbol, market, watchlist]
  );
  const activePayload = useMemo(
    () => (payload && payload.symbol === selected.symbol && payload.range === range ? payload : undefined),
    [payload, range, selected.symbol]
  );
  const selectedLayout = useMemo(
    () => getLayoutForSymbol(createWorkspaceSnapshot({ watchlist, alerts, selectedSymbol: selected.symbol, range, layoutBySymbol, globalLayoutFallback }), selected.symbol),
    [alerts, globalLayoutFallback, layoutBySymbol, range, selected.symbol, watchlist]
  );

  useEffect(() => {
    const requestToken = selectedRequestTokenRef.current + 1;
    selectedRequestTokenRef.current = requestToken;
    const requestKey = `${selected.symbol}:${range}:${refreshTick}`;
    setLoading(true);
    setError("");

    let request = selectedFetchesRef.current.get(requestKey);
    if (!request) {
      request = fetch(`/api/chart/${encodeURIComponent(selected.symbol)}?range=${range}`).then(async (response) => {
        const data = (await response.json()) as ChartPayload | { error?: string };
        if (!response.ok || ("error" in data && data.error)) throw new Error(("error" in data && data.error) || "行情加载失败");
        return data as ChartPayload;
      });
      selectedFetchesRef.current.set(requestKey, request);
      request.then(
        () => selectedFetchesRef.current.delete(requestKey),
        () => selectedFetchesRef.current.delete(requestKey)
      );
    }

    request
      .then((data) => {
        if (selectedRequestTokenRef.current === requestToken) {
          setPayload(data);
        }
      })
      .catch((caught) => {
        if (selectedRequestTokenRef.current !== requestToken) return;
        setError(caught instanceof Error ? caught.message : "行情加载失败");
        setQuoteSummaries((current) => ({
          ...current,
          [selected.symbol]: {
            ...current[selected.symbol],
            sourceStatus: "unavailable"
          }
        }));
      })
      .finally(() => {
        if (selectedRequestTokenRef.current === requestToken) {
          setLoading(false);
        }
      });
  }, [selected.symbol, range, refreshTick]);

  useEffect(() => {
    if (!payload) return;
    setQuoteSummaries((current) => ({
      ...current,
      [payload.symbol]: quoteSummaryFromPayload(payload)
    }));
  }, [payload]);

  useEffect(() => {
    const symbolsToLoad = activeWatchlist
      .map((item) => item.symbol)
      .filter((symbol) => symbol !== selected.symbol)
      .filter((symbol) => {
        const requestKey = `${symbol}:${range}`;
        const status = quoteSummaries[symbol]?.sourceStatus;
        return (!status || status === "not_loaded") && !summaryRequestKeysRef.current.has(requestKey);
      });
    if (symbolsToLoad.length === 0) return;

    for (const symbol of symbolsToLoad) {
      const requestKey = `${symbol}:${range}`;
      summaryRequestKeysRef.current.add(requestKey);

      fetch(`/api/chart/${encodeURIComponent(symbol)}?range=${range}`)
        .then(async (response) => {
          const data = (await response.json()) as ChartPayload | { error?: string };
          if (!response.ok || ("error" in data && data.error)) throw new Error(("error" in data && data.error) || "行情加载失败");
          return data as ChartPayload;
        })
        .then((data) => {
          setQuoteSummaries((current) => ({
            ...current,
            [data.symbol]: quoteSummaryFromPayload(data)
          }));
        })
        .catch((caught) => {
          if (caught.name !== "AbortError") {
            setQuoteSummaries((current) => ({
              ...current,
              [symbol]: {
                ...current[symbol],
                sourceStatus: "unavailable"
              }
            }));
          }
        });
    }
  }, [activeWatchlist, quoteSummaries, range, selected.symbol]);

  const activeObservation = useMemo(() => buildObservation(activePayload), [activePayload]);
  const bars = activeObservation.bars;
  const latest = activeObservation.latestBar;
  const mts = useMemo(() => buildSignal(activeObservation), [activeObservation]);
  const tradeSignal = useMemo(
    () => buildTradeSignalState({ ...activeObservation, symbol: activeObservation.symbol ?? selected.symbol }),
    [activeObservation, selected.symbol]
  );
  const tradeBacktest = useMemo(
    () => (tradeSignal.status === "ready" ? runTradeBacktest(tradeSignal.symbol, bars) : undefined),
    [tradeSignal.status, tradeSignal.symbol, bars]
  );
  const fanT = useMemo(
    () => (tradeSignal.status === "ready" ? buildFanTState(tradeSignal.symbol, bars) : undefined),
    [tradeSignal.status, tradeSignal.symbol, bars]
  );
  const workspaceSourceStatus = getSourceStatus(activePayload, Boolean(error));
  const workspaceSourceTone = resolveSourceTone(workspaceSourceStatus);
  const sourceAuthorityClass =
    workspaceSourceTone === "warning"
      ? "notice--warning"
      : workspaceSourceTone === "info"
        ? "notice--info"
        : "source-authority--normal";

  useEffect(() => {
    if (!latest) return;
    setAlerts((current) => {
      const evaluated = evaluateAlertRules(current, {
        symbol: selected.symbol,
        latestPrice: latest.close,
        previousClose: activePayload?.meta.previousClose ?? bars.at(-2)?.close,
        mts,
        now: Date.now()
      });
      return JSON.stringify(evaluated) === JSON.stringify(current) ? current : evaluated;
    });
  }, [activePayload?.meta.previousClose, alerts, bars, latest, selected.symbol, mts]);

  function addSymbol(event: FormEvent) {
    event.preventDefault();
    if (normalizationPreview.status !== "ready") return;
    const symbol = normalizationPreview.normalizedSymbol;
    const next = {
      id: `${symbol}-${Date.now()}`,
      symbol,
      name: inputName.trim() || symbol,
      market: normalizationPreview.market,
      status: "active" as const
    };
    setWatchlist((current) => {
      const existing = current.find((item) => item.symbol === symbol);
      if (existing?.status === "archived") {
        return restoreWatchSymbol(current, symbol, inputName);
      }
      return [next, ...current.filter((item) => item.symbol !== symbol)];
    });
    if (normalizationPreview.restoresArchived) {
      setAlerts((current) => restoreAlertRulesForActiveSymbol(current, symbol));
    }
    setSelected(next);
    setInputSymbol("");
    setInputName("");
    setIsAddOpen(false);
  }

  function archiveSymbol(symbol: string) {
    const archivedAt = Date.now();
    const nextActive = watchlist.find((item) => item.symbol !== symbol && isActiveSymbol(item));
    setWatchlist((current) => archiveWatchSymbol(current, symbol, archivedAt));
    setAlerts((current) => suspendAlertRulesForArchivedSymbol(current, symbol, archivedAt));
    if (selected.symbol === symbol && nextActive) setSelected(nextActive);
  }

  function restoreSymbol(symbol: string) {
    const restored = watchlist.find((item) => item.symbol === symbol);
    setWatchlist((current) => restoreWatchSymbol(current, symbol));
    setAlerts((current) => restoreAlertRulesForActiveSymbol(current, symbol));
    if (restored) setSelected(restored);
  }

  function refreshSelected() {
    setRefreshTick((current) => current + 1);
  }

  const signalSourceStatus = activePayload?.sourceHealth?.status;
  const signalSourceTone = signalSourceStatus ? resolveSourceTone(signalSourceStatus) : "normal";

  return (
    <main className="terminal-shell">
      <aside className="watch-panel" aria-label="自选列表">
        <div className="brand-block">
          <CandlestickChart size={26} />
          <div>
            <h1>MyInvestment</h1>
            <p>多市场技术看盘</p>
          </div>
        </div>

        <button
          className="sidebar-action"
          data-testid="add-symbol-toggle"
          type="button"
          onClick={() => setIsAddOpen((current) => !current)}
          aria-expanded={isAddOpen}
        >
          <Plus size={15} />
          新增自选
        </button>

        {isAddOpen && (
          <form className="symbol-form" onSubmit={addSymbol}>
            <div className="market-tabs">
              {markets.map((item) => (
                <button
                  className={market === item ? "active" : ""}
                  key={item}
                  onClick={() => setMarket(item)}
                  type="button"
                >
                  {marketLabels[item]}
                </button>
              ))}
            </div>
            <label>
              <Search size={15} />
              <input
                placeholder={marketHints[market]}
                value={inputSymbol}
                onChange={(event) => setInputSymbol(event.target.value)}
              />
            </label>
            <label>
              <LineChart size={15} />
              <input placeholder="名称，可选" value={inputName} onChange={(event) => setInputName(event.target.value)} />
            </label>
            <div className={`normalization-preview ${normalizationPreview.status}`}>
              <span>归一预览</span>
              {normalizationPreview.status === "ready" ? (
                <strong>
                  {marketLabels[normalizationPreview.market]} · {normalizationPreview.rawInput.trim()} →{" "}
                  {normalizationPreview.normalizedSymbol}
                </strong>
              ) : (
                <strong>{normalizationPreview.message}</strong>
              )}
              {normalizationPreview.status !== "ready" && "candidates" in normalizationPreview && normalizationPreview.candidates.length > 0 && (
                <small>{normalizationPreview.candidates.map((candidate) => `${candidate.label} ${candidate.symbol}`).join(" / ")}</small>
              )}
              {normalizationPreview.status === "ready" && <small>{normalizationPreview.message}</small>}
            </div>
            <button className="primary-action" type="submit" disabled={normalizationPreview.status !== "ready"}>
              <Plus size={16} />
              确认加入
            </button>
          </form>
        )}

        <div className="watch-list">
          <div className="watch-list-header">
            <span className="section-label">自选</span>
            <span>{activeWatchlist.length}</span>
          </div>
          {activeWatchlist.map((item) => {
            const summary = quoteSummaries[item.symbol] ?? {
              sourceStatus: item.symbol === selected.symbol ? getSourceStatus(activePayload, Boolean(error)) : "not_loaded"
            };
            return (
            <div
              className={`watch-item ${selected.symbol === item.symbol ? "selected" : ""}`}
              data-testid={`watch-item-${item.symbol}`}
              key={item.id}
            >
              <button
                className="watch-item-main"
                data-testid="watch-item-main"
                onClick={() => setSelected(item)}
                type="button"
              >
                <span className="watch-item-identity" data-testid="watch-item-identity">
                  <strong>{item.name}</strong>
                  <small>{item.symbol} · {marketLabels[item.market]}</small>
                </span>
                <span className="watch-item-quote" data-testid="watch-item-quote">
                  <strong>{formatNumber(summary.latestPrice)}</strong>
                  <small className={Number(summary.changePercent ?? 0) >= 0 ? "up" : "down"}>
                    {formatNumber(summary.changePercent)}%
                  </small>
                </span>
                <span
                  className={`watch-item-source-dot tone-${resolveSourceTone(summary.sourceStatus)}`}
                  data-testid="watch-item-source-dot"
                  aria-label={`来源：${sourceStatusLabel(summary.sourceStatus)}`}
                />
              </button>
              <button
                className="row-icon-button"
                type="button"
                aria-label={`归档 ${item.name}`}
                onClick={() => archiveSymbol(item.symbol)}
              >
                <Archive size={15} />
              </button>
            </div>
            );
          })}
          {archivedWatchlist.length > 0 && (
            <div className="archive-block">
              <h3>已归档</h3>
              {archivedWatchlist.map((item) => (
                <div
                  className="watch-item archived"
                  data-testid={`watch-item-${item.symbol}`}
                  key={item.id}
                >
                  <button
                    className="watch-item-main"
                    data-testid="watch-item-main"
                    onClick={() => restoreSymbol(item.symbol)}
                    type="button"
                  >
                    <span className="watch-item-identity" data-testid="watch-item-identity">
                      <strong>{item.name}</strong>
                      <small>{item.symbol} · {marketLabels[item.market]} · 提醒已暂停</small>
                    </span>
                    <RotateCcw size={15} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </aside>

      <section className="market-workspace" style={{ display: "block" }}>
        <div className="status-strip">
          <div className={`source-authority ${sourceAuthorityClass}`} data-testid="source-authority">
            来源 {sourceStatusLabel(workspaceSourceStatus)}
            {activePayload?.sourceHealth?.degradationReason
              ? ` · ${activePayload.sourceHealth.degradationReason}`
              : ""}
          </div>
          <RestoreStatus metadata={restoreMetadata} />
        </div>
        <LayoutController
          selected={selected}
          payload={activePayload}
          loading={loading}
          error={error}
          range={range}
          layout={selectedLayout}
          onRangeChange={setRange}
          onRefresh={refreshSelected}
          onLayoutChange={(layout) => {
            const snapshot = withSymbolLayout(
              createWorkspaceSnapshot({ watchlist, alerts, selectedSymbol: selected.symbol, range, layoutBySymbol, globalLayoutFallback }),
              selected.symbol,
              layout
            );
            setLayoutBySymbol(snapshot.layoutBySymbol);
          }}
        />
      </section>

      <section className="detail-panel" aria-label="标的细节">
        <div className="detail-tabs" role="tablist" aria-label="标的细节切换">
          <button
            className={detailTab === "explain" ? "active" : ""}
            data-testid="detail-tab-explain"
            type="button"
            role="tab"
            aria-selected={detailTab === "explain"}
            onClick={() => setDetailTab("explain")}
          >
            解释
          </button>
          <button
            className={detailTab === "alerts" ? "active" : ""}
            data-testid="detail-tab-alerts"
            type="button"
            role="tab"
            aria-selected={detailTab === "alerts"}
            onClick={() => setDetailTab("alerts")}
          >
            提醒
          </button>
          <button
            className={detailTab === "source" ? "active" : ""}
            data-testid="detail-tab-source"
            type="button"
            role="tab"
            aria-selected={detailTab === "source"}
            onClick={() => setDetailTab("source")}
          >
            来源
          </button>
          <button
            className={detailTab === "holdings" ? "active" : ""}
            data-testid="detail-tab-holdings"
            type="button"
            role="tab"
            aria-selected={detailTab === "holdings"}
            onClick={() => setDetailTab("holdings")}
          >
            持仓
          </button>
        </div>

        {detailTab === "explain" && (
          <div className="detail-grid explain-grid">
            {resolveTradeStrategy(selected.symbol) && (
              <section className={`signal-card alibaba-card ${tradeSignalTone(tradeSignal)}`} data-testid="trade-signal-card">
                <div className="signal-topline">
                  <span>{tradeSignal.strategyLabel} · {tradeSignal.styleTag}</span>
                  <strong data-testid="trade-signal-status">
                    {tradeSignal.status === "ready"
                      ? tradeSignal.holding
                        ? "持仓中"
                        : "空仓"
                      : humanizeTradeStatus(tradeSignal.status, tradeSignal.stanceLabel)}
                  </strong>
                </div>
                <strong data-testid="trade-signal-stance">{tradeSignal.stanceLabel}</strong>
                {tradeSignal.status === "ready" && tradeBacktest && (
                  <p className="trade-signal-kpi" data-testid="trade-backtest-summary">
                    胜率 {tradeBacktest.winRate === null ? "--" : `${formatNumber(tradeBacktest.winRate, 0)}%`} · 策略累计{" "}
                    {tradeBacktest.strategyReturnPct === null ? "--" : `${formatNumber(tradeBacktest.strategyReturnPct, 1)}%`}
                  </p>
                )}
                {tradeSignal.status === "ready" && (
                  <div className="trade-signal-details" data-testid="trade-signal-details">
                        <div data-testid="trade-signal-levels">
                          <p className="plan-group-title">卖出侧</p>
                          <div className="level-grid">
                            {tradeSignal.holding ? (
                              <>
                                {tradeSignal.levels.takeProfit !== undefined ? (
                                  <div><span>止盈位（跌破即卖）</span><strong>{formatNumber(tradeSignal.levels.takeProfit)}</strong></div>
                                ) : (
                                  <div><span>止损位（跌破即卖）</span><strong>{formatNumber(tradeSignal.levels.stopLoss)}</strong></div>
                                )}
                                {tradeSignal.levels.sellTargetSma !== undefined && (
                                  <div><span>目标位（站上即卖）</span><strong>{formatNumber(tradeSignal.levels.sellTargetSma)}</strong></div>
                                )}
                                {tradeSignal.holdBarsMax !== undefined && (
                                  <div><span>剩余持有</span><strong>{Math.max(0, tradeSignal.holdBarsMax - (tradeSignal.holdBarsUsed ?? 0))} 根K线</strong></div>
                                )}
                                {tradeSignal.levels.sellWatchOne !== undefined && (
                                  <div className="level-secondary"><span>阶段减仓观察一*</span><strong>{formatNumber(tradeSignal.levels.sellWatchOne)}</strong></div>
                                )}
                                {tradeSignal.levels.sellWatchTwo !== undefined && (
                                  <div className="level-secondary"><span>阶段减仓观察二*</span><strong>{formatNumber(tradeSignal.levels.sellWatchTwo)}</strong></div>
                                )}
                              </>
                            ) : (
                              <div><span>离场线</span><strong>空仓，无</strong></div>
                            )}
                          </div>
                          <p className="plan-group-title">买入侧</p>
                          <div className="level-grid">
                            {tradeSignal.holding ? (
                              <>
                                {tradeSignal.levels.addPositionTrigger !== undefined && (
                                  <div><span>加仓触发位（突破）</span><strong>{formatNumber(tradeSignal.levels.addPositionTrigger)}</strong></div>
                                )}
                                {tradeSignal.levels.pullbackZoneLow !== undefined && (
                                  <div className="level-secondary">
                                    <span>回调加仓观察区*</span>
                                    <strong>{formatNumber(tradeSignal.levels.pullbackZoneLow)} ~ {formatNumber(tradeSignal.levels.pullbackZoneHigh)}</strong>
                                  </div>
                                )}
                                <div><span>信号成本参考</span><strong>{formatNumber(tradeSignal.levels.entryPrice)}</strong></div>
                              </>
                            ) : (
                              <div>
                                <span>{tradeSignal.buyTriggerDirection === "dip" ? "买入触发位（跌破即买）" : "突破买入触发位"}</span>
                                <strong>{formatNumber(tradeSignal.levels.nextBuyTrigger)}</strong>
                              </div>
                            )}
                            {tradeSignal.levels.gateLevel !== undefined && (
                              <div><span>趋势门控 SMA60</span><strong>{formatNumber(tradeSignal.levels.gateLevel)}</strong></div>
                            )}
                            <div className="level-secondary"><span>ATR20</span><strong>{formatNumber(tradeSignal.levels.latestAtr)}</strong></div>
                          </div>
                          {fanT?.enabled && (
                            <>
                              <p className="plan-group-title">反T 波段（持仓高卖低买降成本）</p>
                              <div className="level-grid" data-testid="fant-levels">
                                <div>
                                  <span>当前阶段</span>
                                  <strong>{fanT.phase === "full" ? "满仓，等高卖" : "已卖出，等买回"}</strong>
                                </div>
                                {fanT.phase === "full" ? (
                                  <div><span>高卖触发位（站上即卖）</span><strong>{formatNumber(fanT.sellTrigger)}</strong></div>
                                ) : (
                                  <>
                                    <div><span>买回触发位（跌破即买）</span><strong>{formatNumber(fanT.buyBackTrigger)}</strong></div>
                                    <div><span>追高认错位（涨过即买回）</span><strong>{formatNumber(fanT.chaseStop)}</strong></div>
                                    <div><span>卖出参考价</span><strong>{formatNumber(fanT.soldRefPrice)}</strong></div>
                                  </>
                                )}
                              </div>
                              <p className="backtest-line" data-testid="fant-backtest-summary">
                                反T 回测：{fanT.completedRounds} 回合 · 胜 {fanT.winRounds} · 累计价差 {formatNumber(fanT.totalSpreadPct, 1)}% · 最差单回合{" "}
                                {fanT.worstSpreadPct === null ? "--" : `${formatNumber(fanT.worstSpreadPct, 1)}%`}（正价差 = 摊薄成本）
                              </p>
                            </>
                          )}
                          <p className="backtest-line">
                            * 号为 ATR 投影的阶段观察位（未经回测）；正式买卖以触发位与止损/止盈/目标线为准。
                          </p>
                        </div>
                        {tradeBacktest && (
                          <p className="backtest-line secondary" data-testid="trade-backtest-detail">
                            近 {tradeBacktest.barsUsed} 根日K：信号 买{tradeBacktest.buySignals}/卖{tradeBacktest.sellSignals} · 完成 {tradeBacktest.closedTrades} 笔 · vs 买入持有{" "}
                            {tradeBacktest.buyHoldReturnPct === null ? "--" : `${formatNumber(tradeBacktest.buyHoldReturnPct, 1)}%`}
                          </p>
                        )}
                  </div>
                )}
                <p className="technical-reminder" data-testid="trade-signal-non-advice">
                  {tradeSignal.nonAdvice}
                </p>
              </section>
            )}

            <section className={`signal-card ${mtsCardToneClass(mts)}`} data-testid="mts-card">
              <div className="signal-topline">
                <span>MTS 解释卡</span>
                <AreaChart size={18} />
              </div>
              {signalSourceStatus && signalSourceTone !== "normal" && (
                <div className={signalSourceTone === "warning" ? "notice--warning" : "notice--info"} data-testid="signal-degradation-note">
                  来源状态：{signalSourceStatus} · {activePayload?.notice || activePayload?.sourceHealth?.degradationReason}
                </div>
              )}
              {error && !activePayload && (
                <div className="notice--warning" data-testid="signal-error-note">
                  来源重试失败：{error}
                </div>
              )}
              <strong data-testid="mts-display-label">{mts.displayLabel}</strong>
              <p className="mts-trend-summary">{humanizeTrendState(mts.trendState)}</p>
              <ScoreBar score={mts.mtsScore} notApplicable={mts.scoreBand === "not_applicable"} />
              <p className="technical-reminder" data-testid="mts-non-advice">
                {mts.technicalReminder}
              </p>
              <button
                type="button"
                className="linkish"
                data-testid="mts-details-toggle"
                aria-expanded={mtsDetailsOpen}
                onClick={() => setMtsDetailsOpen((open) => !open)}
              >
                {mtsDetailsOpen ? "收起技术详情" : "展开技术详情"}
              </button>
              {mtsDetailsOpen && (
                <div className="mts-details" data-testid="mts-details">
                  <div className="score-grid" data-testid="mts-state-grid">
                    <span>trend_state {mts.trendState}</span>
                    <span>mts_score {mts.mtsScore ?? "--"}</span>
                    <span>score_band {mts.scoreBand}</span>
                    <span>signal_type {mts.signalType}</span>
                    <span>alert_level {mts.alertLevel}</span>
                  </div>
                  {activePayload?.sourceHealth?.retryState && activePayload.sourceHealth.status !== "formal" && (
                    <p className="mts-retry-meta" data-testid="mts-retry-meta">
                      重试：第 {activePayload.sourceHealth.retryState.attempt} 次
                      {activePayload.sourceHealth.retryState.reason
                        ? ` · ${activePayload.sourceHealth.retryState.reason}`
                        : ""}
                    </p>
                  )}
                </div>
              )}
            </section>

            <section className="side-section reason-card">
              <h3>ReasonRegistry</h3>
              <ul className="reason-list" data-testid="mts-reason-list">
                {mts.reasons.map((item) => (
                  <li key={`${item.code}-${item.detail}`}>
                    <strong>{item.label || humanizeReason(item.code)}</strong>
                    <span>{item.detail}</span>
                  </li>
                ))}
                {mts.invalidators.map((item) => (
                  <li className="warning" key={`${item.code}-${item.detail}`}>
                    <strong>{item.label || humanizeReason(item.code)}</strong>
                    <span>{item.detail}</span>
                  </li>
                ))}
              </ul>
              <button
                type="button"
                className="linkish"
                data-testid="mts-reason-details-toggle"
                aria-expanded={mtsReasonDetailsOpen}
                onClick={() => setMtsReasonDetailsOpen((open) => !open)}
              >
                {mtsReasonDetailsOpen ? "收起原始理由码" : "展开原始理由码"}
              </button>
              {mtsReasonDetailsOpen && (
                <ul className="reason-code-list" data-testid="mts-reason-codes">
                  {[...mts.reasons, ...mts.invalidators].map((item) => (
                    <li key={`code-${item.code}-${item.detail}`}>
                      <code>{item.code}</code>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        )}

        {detailTab === "alerts" && (
          <AlertRulePanel
            alerts={alerts}
            selectedSymbol={selected.symbol}
            latestPrice={latest?.close}
            onCreate={(rule) => setAlerts((current) => [rule, ...current])}
            onToggle={(ruleId, enabled) =>
              setAlerts((current) =>
                current.map((item) =>
                  item.id === ruleId
                    ? { ...item, enabled, activationState: enabled ? "enabled" : "disabled" }
                    : item
                )
              )
            }
            onAcknowledge={(ruleId) =>
              setAlerts((current) => current.map((item) => (item.id === ruleId ? acknowledgeAlertRule(item) : item)))
            }
            onDelete={(ruleId) => setAlerts((current) => current.filter((item) => item.id !== ruleId))}
          />
        )}

        {detailTab === "source" && (
          <SourceHealthPanel
            payload={activePayload}
            loading={loading && !activePayload}
            error={error}
            onRetry={refreshSelected}
          />
        )}

        {detailTab === "holdings" && <HoldingsPanel />}
      </section>
    </main>
  );
}
