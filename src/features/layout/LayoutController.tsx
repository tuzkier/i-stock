import { RefreshCw } from "lucide-react";
import { useEffect, useMemo } from "react";
import { ChartSurface } from "../chart/ChartSurface";
import type {
  ChartLayout,
  ChartPayload,
  RangeKey,
  WatchSymbol,
  WorkspaceLayout
} from "../../types";

type LayoutControllerProps = {
  selected: WatchSymbol;
  payload?: ChartPayload;
  loading: boolean;
  error: string;
  range: RangeKey;
  layout: WorkspaceLayout;
  onRangeChange: (range: RangeKey) => void;
  onRefresh: () => void;
  onLayoutChange: (layout: WorkspaceLayout) => void;
};

const ranges: RangeKey[] = ["1d", "5d", "1mo", "3mo", "6mo", "1y"];
const layoutLabels: Record<ChartLayout, string> = {
  dense: "总览",
  focus: "专注",
  mobile_tab: "单栏"
};

function formatSelected(selected: WatchSymbol) {
  return `${selected.name} · ${selected.symbol}`;
}

export function LayoutController({
  selected,
  payload,
  loading,
  error,
  range,
  layout,
  onRangeChange,
  onRefresh,
  onLayoutChange
}: LayoutControllerProps) {
  useEffect(() => {
    if (window.innerWidth <= 760 && layout.mode !== "mobile_tab") {
      onLayoutChange({ ...layout, mode: "mobile_tab", selectedMobileTab: layout.selectedMobileTab ?? "chart" });
    }
  }, [layout, onLayoutChange]);

  const activePayload = useMemo(
    () => (payload && payload.symbol === selected.symbol && payload.range === range ? payload : undefined),
    [payload, range, selected.symbol]
  );

  function setMode(mode: ChartLayout) {
    onLayoutChange({
      ...layout,
      mode,
      selectedMobileTab: mode === "mobile_tab" ? layout.selectedMobileTab : "chart",
      updatedAt: Date.now()
    });
  }

  const sourceStatus = activePayload?.sourceHealth?.status ?? "unavailable";
  const layoutLabel = layoutLabels[layout.mode];

  return (
    <section className="workbench-shell" data-testid="workbench-shell">
      <header className="workspace-header">
        <div>
          <span className="eyebrow">{selected.market}</span>
          <h2>{formatSelected(selected)}</h2>
          <div className="selection-summary" data-testid="workbench-selection-summary">
            {selected.symbol} · {layoutLabel}视图 · 来源 {sourceStatus}
          </div>
        </div>
        <div className="workspace-actions">
          <div className="range-controls" aria-label="周期切换">
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
              className={layout.mode === "dense" ? "active" : ""}
              data-testid="layout-mode-dense"
              onClick={() => setMode("dense")}
            >
              总览
            </button>
            <button
              type="button"
              className={layout.mode === "focus" ? "active" : ""}
              data-testid="layout-mode-focus"
              onClick={() => setMode("focus")}
            >
              专注
            </button>
            <button
              type="button"
              className={layout.mode === "mobile_tab" ? "active" : ""}
              data-testid="layout-mode-mobile-tab"
              onClick={() => setMode("mobile_tab")}
            >
              单栏
            </button>
          </div>
        </div>
      </header>

      {error && !activePayload && (
        <div className="data-notice" data-testid="workbench-error">
          {error}
        </div>
      )}

      <div
        className="workbench-body"
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1fr)",
          gap: 12,
          alignItems: "start"
        }}
      >
        <ChartSurface
          payload={activePayload}
          loading={loading && !activePayload}
          error={error}
        />
      </div>
    </section>
  );
}
