import {
  CandlestickSeries,
  ColorType,
  createChart,
  createSeriesMarkers,
  HistogramSeries,
  LineSeries,
  type CandlestickData,
  type HistogramData,
  type IChartApi,
  type LineData,
  type SeriesMarker,
  type Time
} from "lightweight-charts";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { ChartPayload, PriceBar, SourceHealthStatus } from "../../types";
import { lastFinite } from "../../lib/indicators";
import {
  buildObservation,
  buildSecondaryIndicator,
  seriesToPoints,
  type SecondaryIndicator
} from "../../domain/observation";
import { computeTradeSignalEvents, resolveTradeStrategy } from "../../domain/trade-signals";

type ChartSurfaceProps = {
  payload?: ChartPayload;
  loading?: boolean;
  error?: string;
};

function formatNumber(value?: number, digits = 2) {
  if (!Number.isFinite(value)) return "--";
  return new Intl.NumberFormat("zh-CN", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits
  }).format(value as number);
}

function formatCompact(value?: number) {
  if (!Number.isFinite(value)) return "--";
  return new Intl.NumberFormat("zh-CN", {
    notation: "compact",
    maximumFractionDigits: 1
  }).format(value as number);
}

function formatOhlcText(bar?: Pick<PriceBar, "open" | "high" | "low" | "close">) {
  if (!bar) return "O -- / H -- / L -- / C --";
  return `O ${formatNumber(bar.open)} / H ${formatNumber(bar.high)} / L ${formatNumber(bar.low)} / C ${formatNumber(bar.close)}`;
}

function formatStatus(status: SourceHealthStatus) {
  return status;
}

function PanelShell({
  testId,
  title,
  subtitle,
  bodyHeight,
  children
}: {
  testId: string;
  title: string;
  subtitle?: string;
  bodyHeight: number;
  children?: ReactNode;
}) {
  return (
    <section className="side-section" data-testid={testId} style={{ gap: 10 }}>
      <div className="signal-topline">
        <span>{title}</span>
        {subtitle ? <strong>{subtitle}</strong> : <strong>&nbsp;</strong>}
      </div>
      <div style={{ height: bodyHeight, minHeight: bodyHeight }}>{children}</div>
    </section>
  );
}

function ChartPane({
  testId,
  bars,
  height,
  renderChart
}: {
  testId: string;
  bars: PriceBar[];
  height: number;
  renderChart: (chart: IChartApi) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!containerRef.current || bars.length === 0) return;

    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "#101215" },
        textColor: "#aeb6c2",
        fontFamily: "Avenir Next, Helvetica Neue, sans-serif"
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.04)" },
        horzLines: { color: "rgba(255,255,255,0.05)" }
      },
      rightPriceScale: {
        borderColor: "rgba(255,255,255,0.08)"
      },
      timeScale: {
        borderColor: "rgba(255,255,255,0.08)",
        timeVisible: true
      },
      crosshair: {
        mode: 1
      }
    });

    renderChart(chart);
    chart.timeScale().fitContent();

    return () => {
      chart.remove();
    };
  }, [bars, renderChart]);

  return <div ref={containerRef} style={{ width: "100%", height }} />;
}

export function ChartSurface({ payload, loading = false, error = "" }: ChartSurfaceProps) {
  const [secondaryIndicator, setSecondaryIndicator] = useState<SecondaryIndicator>("MACD");
  const observation = useMemo(() => buildObservation(payload), [payload]);
  const bars = observation.bars;
  const latestBar = observation.latestBar;
  const sourceHealth = payload?.sourceHealth;
  const status = sourceHealth?.status ?? "unavailable";
  const isDegraded = Boolean(sourceHealth && sourceHealth.status !== "formal");
  const indicator = useMemo(() => buildSecondaryIndicator(bars, secondaryIndicator), [bars, secondaryIndicator]);
  const ema20 = observation.indicators.ema20;
  const ema60 = observation.indicators.ema60;
  const ohlcText = formatOhlcText(payload?.priceSeries?.latestOhlc ?? latestBar);
  const changeValue = observation.changeSummary?.absolute;
  const changePercent = observation.changeSummary?.percent;
  const sourceSummary = payload?.notice ?? sourceHealth?.degradationReason ?? (error || (loading ? "加载中" : "等待可用数据"));

  const indicatorTabs: Array<{ id: SecondaryIndicator; label: string }> = [
    { id: "MACD", label: "MACD" },
    { id: "RSI", label: "RSI" },
    { id: "KDJ", label: "KDJ" },
    { id: "ATR", label: "ATR" }
  ];

  const mainChartSeries = useMemo(
    () => ({
      candles: bars.map(
        (bar) =>
          ({
            time: bar.time,
            open: bar.open,
            high: bar.high,
            low: bar.low,
            close: bar.close
          }) as CandlestickData
      ),
      ema20: seriesToPoints(bars, ema20) as LineData[],
      ema60: seriesToPoints(bars, ema60) as LineData[]
    }),
    [bars, ema20, ema60]
  );

  const signalMarkers = useMemo(() => {
    if (!resolveTradeStrategy(payload?.symbol ?? "") || sourceHealth?.status !== "formal") return [];
    return computeTradeSignalEvents(payload?.symbol ?? "", bars).map(
      (event) =>
        ({
          time: event.time as Time,
          position: event.side === "buy" ? "belowBar" : "aboveBar",
          shape: event.side === "buy" ? "arrowUp" : "arrowDown",
          color: event.side === "buy" ? "#33c481" : "#f15f5f",
          text: event.side === "buy" ? "买" : "卖"
        }) as SeriesMarker<Time>
    );
  }, [bars, payload?.symbol, sourceHealth?.status]);

  const volumeSeries = useMemo(
    () =>
      bars.map(
        (bar, index) =>
          ({
            time: bar.time,
            value: bar.volume,
            color: index === 0 || bar.close >= bars[index - 1].close ? "rgba(51,196,129,0.34)" : "rgba(241,95,95,0.34)"
          }) as HistogramData
      ),
    [bars]
  );

  return (
    <section className="side-section chart-surface" data-testid="chart-surface">
      <div className="signal-topline">
        <span>{payload?.meta.shortName || payload?.symbol || "等待行情"}</span>
        <strong data-testid="chart-source-status">{formatStatus(status)}</strong>
      </div>

      {sourceSummary && (isDegraded || error || loading || !payload) && (
        <div className="data-notice" data-testid="chart-degradation-note">
          {isDegraded ? `${status} · ${sourceSummary}` : sourceSummary}
        </div>
      )}

      <div className="chart-panels">
        <PanelShell testId="chart-main-panel" title="主图" subtitle={payload?.symbol || "—"} bodyHeight={260}>
          {bars.length === 0 ? (
            <div className="empty-state" style={{ minHeight: 260 }}>
              {loading ? "加载主图中" : error || "暂无主图数据"}
            </div>
          ) : (
            <ChartPane
              testId="chart-main-panel-canvas"
              bars={bars}
              height={260}
              renderChart={(chart) => {
                const candleSeries = chart.addSeries(CandlestickSeries, {
                  upColor: "#33c481",
                  downColor: "#f15f5f",
                  borderUpColor: "#33c481",
                  borderDownColor: "#f15f5f",
                  wickUpColor: "#33c481",
                  wickDownColor: "#f15f5f"
                });
                const ema20Series = chart.addSeries(LineSeries, { color: "#f0c75e", lineWidth: 2, title: "EMA20" });
                const ema60Series = chart.addSeries(LineSeries, { color: "#64a9ff", lineWidth: 2, title: "EMA60" });

                candleSeries.setData(mainChartSeries.candles);
                ema20Series.setData(mainChartSeries.ema20);
                ema60Series.setData(mainChartSeries.ema60);
                if (signalMarkers.length > 0) {
                  createSeriesMarkers(candleSeries, signalMarkers);
                }
              }}
            />
          )}
        </PanelShell>

        <PanelShell testId="chart-volume-panel" title="成交量" subtitle="Volume" bodyHeight={108}>
          {bars.length === 0 ? (
            <div className="empty-state" style={{ minHeight: 108 }}>
              {loading ? "加载成交量中" : "暂无成交量数据"}
            </div>
          ) : (
            <ChartPane
              testId="chart-volume-panel-canvas"
              bars={bars}
              height={108}
              renderChart={(chart) => {
                const volume = chart.addSeries(HistogramSeries, {
                  priceFormat: { type: "volume" },
                  priceScaleId: "volume"
                });

                chart.priceScale("volume").applyOptions({
                  scaleMargins: { top: 0.8, bottom: 0 }
                });
                volume.setData(volumeSeries);
              }}
            />
          )}
        </PanelShell>

        <section className="side-section" data-testid="chart-secondary-panel" style={{ gap: 10 }}>
          <div className="signal-topline">
            <span>副图指标</span>
            <strong data-testid="indicator-state-badge">{indicator.state}</strong>
          </div>
          <div className="market-tabs" role="tablist" aria-label="副图指标切换">
            {indicatorTabs.map((tab) => (
              <button
                key={tab.id}
                id={`indicator-tab-${tab.id.toLowerCase()}`}
                data-testid={`indicator-tab-${tab.id.toLowerCase()}`}
                className={secondaryIndicator === tab.id ? "active" : ""}
                onClick={() => setSecondaryIndicator(tab.id)}
                type="button"
                role="tab"
                aria-selected={secondaryIndicator === tab.id}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="source-health-notice" data-testid="indicator-summary">
            {indicator.label} · {indicator.state} · {indicator.summary}
          </div>

          <div style={{ minHeight: 168, height: 168 }}>
            {bars.length === 0 ? (
              <div className="empty-state" style={{ minHeight: 168 }}>
                {loading ? "加载副图中" : "暂无副图数据"}
              </div>
            ) : indicator.state === "unavailable" ? (
              <div className="empty-state" style={{ minHeight: 168 }}>
                {indicator.summary}
              </div>
            ) : (
              <ChartPane
                testId={`chart-secondary-panel-${secondaryIndicator.toLowerCase()}`}
                bars={bars}
                height={168}
                renderChart={(chart) => {
                  if (secondaryIndicator === "MACD") {
                    const histogram = chart.addSeries(HistogramSeries, {
                      priceScaleId: "macd",
                      priceFormat: { type: "price", precision: 4, minMove: 0.0001 }
                    });
                    const line = chart.addSeries(LineSeries, { color: "#f0c75e", lineWidth: 2, title: "MACD" });
                    const signal = chart.addSeries(LineSeries, { color: "#64a9ff", lineWidth: 2, title: "SIGNAL" });
                    chart.priceScale("macd").applyOptions({
                      scaleMargins: { top: 0.15, bottom: 0.15 }
                    });
                    histogram.setData((indicator.data?.histogram ?? []) as HistogramData[]);
                    line.setData((indicator.data?.main ?? []) as LineData[]);
                    signal.setData((indicator.data?.signal ?? []) as LineData[]);
                  } else if (secondaryIndicator === "RSI") {
                    const line = chart.addSeries(LineSeries, { color: "#f0c75e", lineWidth: 2, title: "RSI14" });
                    line.setData((indicator.data?.main ?? []) as LineData[]);
                  } else if (secondaryIndicator === "KDJ") {
                    const k = chart.addSeries(LineSeries, { color: "#f0c75e", lineWidth: 2, title: "K" });
                    const d = chart.addSeries(LineSeries, { color: "#64a9ff", lineWidth: 2, title: "D" });
                    k.setData((indicator.data?.main ?? []) as LineData[]);
                    d.setData((indicator.data?.signal ?? []) as LineData[]);
                  } else {
                    const line = chart.addSeries(LineSeries, { color: "#33c481", lineWidth: 2, title: "ATR14" });
                    line.setData((indicator.data?.main ?? []) as LineData[]);
                  }
                }}
              />
            )}
          </div>
        </section>
      </div>

      <div className="quote-line" data-testid="chart-ohlc">
        <strong>{ohlcText}</strong>
        <span className={Number(changeValue ?? 0) >= 0 ? "up" : "down"}>
          {Number(changeValue ?? 0) >= 0 ? "▲" : "▼"} {formatNumber(changeValue)} / {formatNumber(changePercent)}%
        </span>
      </div>

      <div className="metric-strip" data-testid="chart-metric-strip">
        <div>
          <span>EMA20</span>
          <strong>{formatNumber(lastFinite(ema20))}</strong>
        </div>
        <div>
          <span>EMA60</span>
          <strong>{formatNumber(lastFinite(ema60))}</strong>
        </div>
        <div>
          <span>RSI14</span>
          <strong>{formatNumber(lastFinite(observation.indicators.rsi14))}</strong>
        </div>
        <div>
          <span>MACD 柱</span>
          <strong>{formatNumber(lastFinite(observation.indicators.macdHistogram), 4)}</strong>
        </div>
        <div>
          <span>ATR14</span>
          <strong>{formatNumber(lastFinite(observation.indicators.atr14))}</strong>
        </div>
        <div>
          <span>成交量</span>
          <strong>{formatCompact(latestBar?.volume)}</strong>
        </div>
      </div>
    </section>
  );
}
