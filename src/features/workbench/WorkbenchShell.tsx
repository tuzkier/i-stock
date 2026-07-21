import { RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ChartSurface } from "../chart/ChartSurface";
import { SourceHealthPanel } from "../source/SourceHealthPanel";
import type { ChartPayload, RangeKey, WatchSymbol } from "../../types";

type LayoutMode = "dense" | "focus" | "mobile_tab";
type MobileTab = "chart" | "source";

type WorkbenchShellProps = {
  selected: WatchSymbol;
  payload?: ChartPayload;
  loading: boolean;
  error: string;
  range: RangeKey;
  onRangeChange: (range: RangeKey) => void;
  onRefresh: () => void;
};

const ranges: RangeKey[] = ["1d", "5d", "1mo", "3mo", "6mo", "1y"];
const layoutLabels: Record<LayoutMode, string> = {
  dense: "总览",
  focus: "专注",
  mobile_tab: "单栏"
};

function formatSelected(selected: WatchSymbol) {
  return `${selected.name} · ${selected.symbol}`;
}

export function WorkbenchShell({
  selected,
  payload,
  loading,
  error,
  range,
  onRangeChange,
  onRefresh
}: WorkbenchShellProps) {
  const [layoutMode, setLayoutMode] = useState<LayoutMode>(() => (window.innerWidth <= 760 ? "mobile_tab" : "dense"));
  const [mobileTab, setMobileTab] = useState<MobileTab>("chart");

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth <= 760) {
        setLayoutMode((current) => (current === "focus" ? "focus" : "mobile_tab"));
      }
    };

    window.addEventListener("resize", handleResize);
    handleResize();
    return () => window.removeEventListener("resize", handleResize);
  }, [layoutMode]);

  useEffect(() => {
    if (layoutMode !== "mobile_tab") {
      setMobileTab("chart");
    }
  }, [layoutMode]);

  const activePayload = useMemo(
    () => (payload && payload.symbol === selected.symbol && payload.range === range ? payload : undefined),
    [payload, range, selected.symbol]
  );

  const sourceStatus = activePayload?.sourceHealth?.status ?? "unavailable";
  const chartVisible = layoutMode !== "mobile_tab" || mobileTab === "chart";
  const sourceVisible = layoutMode !== "mobile_tab" || mobileTab === "source";
  const sourcePanelCompact = layoutMode === "focus";
  const layoutLabel = layoutLabels[layoutMode];

  return (
    <section className="workbench-shell" data-testid="workbench-shell">
      <header className="workspace-header">
        <div>
          <span className="eyebrow">{selected.market}</span>
          <h2>{formatSelected(selected)}</h2>
          <div className="data-notice" data-testid="workbench-selection-summary">
            {selected.symbol} · {layoutLabel}视图 · 来源 {sourceStatus}
          </div>
        </div>
        <div className="workspace-actions">
          <div className="range-controls">
            {ranges.map((item) => (
              <button className={range === item ? "active" : ""} key={item} onClick={() => onRangeChange(item)} type="button">
                {item}
              </button>
            ))}
            <button className="icon-button" onClick={onRefresh} type="button" aria-label="刷新行情">
              <RefreshCw size={16} className={loading ? "spin" : ""} />
            </button>
          </div>
          <div className="layout-control-strip" aria-label="工作台布局切换" data-testid="layout-controller">
            <span>视图</span>
            <button
              type="button"
              className={layoutMode === "dense" ? "active" : ""}
              data-testid="layout-mode-dense"
              onClick={() => setLayoutMode("dense")}
            >
              总览
            </button>
            <button
              type="button"
              className={layoutMode === "focus" ? "active" : ""}
              data-testid="layout-mode-focus"
              onClick={() => setLayoutMode("focus")}
            >
              专注
            </button>
            <button
              type="button"
              className={layoutMode === "mobile_tab" ? "active" : ""}
              data-testid="layout-mode-mobile-tab"
              onClick={() => setLayoutMode("mobile_tab")}
            >
              单栏
            </button>
          </div>
        </div>
      </header>

      {layoutMode === "mobile_tab" && (
        <div className="market-tabs" aria-label="移动端工作台导航" data-testid="mobile-workbench-tabs">
          <button className={mobileTab === "chart" ? "active" : ""} type="button" onClick={() => setMobileTab("chart")}>
            图表
          </button>
          <button className={mobileTab === "source" ? "active" : ""} type="button" onClick={() => setMobileTab("source")}>
            来源
          </button>
        </div>
      )}

      {error && !activePayload && (
        <div className="data-notice" data-testid="workbench-error">
          {error}
        </div>
      )}

      <div
        className="workbench-body"
        style={{
          display: "grid",
          gridTemplateColumns: layoutMode === "dense" ? "minmax(0, 1fr) 280px" : "minmax(0, 1fr)",
          gap: 12,
          alignItems: "start"
        }}
      >
        {chartVisible && (
          <ChartSurface
            payload={activePayload}
            loading={loading && !activePayload}
            error={error}
          />
        )}

        {sourceVisible && (
          <SourceHealthPanel
            payload={activePayload}
            loading={loading && !activePayload}
            error={error}
            onRetry={onRefresh}
            compact={sourcePanelCompact}
          />
        )}
      </div>
    </section>
  );
}
