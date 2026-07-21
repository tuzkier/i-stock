import type { ChartPayload, MarketDataRetryState, SourceHealthStatus } from "../../types";

type SourceHealthPanelProps = {
  payload?: ChartPayload;
  loading?: boolean;
  error?: string;
  onRetry?: () => void;
  compact?: boolean;
};

function formatDateTime(value?: number) {
  if (!Number.isFinite(value)) {
    return "未刷新";
  }

  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value as number));
}

function formatRetryState(retryState?: MarketDataRetryState) {
  if (!retryState) {
    return "重试次数 0";
  }

  const canRetryText = retryState.canRetry ? "可重试" : "暂不可重试";
  const reasonText = retryState.reason ? ` · ${retryState.reason}` : "";

  return `重试次数 ${retryState.attempt} · ${canRetryText}${reasonText}`;
}

function statusLabel(status: SourceHealthStatus) {
  return status;
}

export function SourceHealthPanel({ payload, loading = false, error = "", onRetry, compact = false }: SourceHealthPanelProps) {
  const sourceHealth = payload?.sourceHealth;
  const status: SourceHealthStatus = sourceHealth?.status ?? "unavailable";
  const sourceName = payload?.sourceName ?? "等待加载";
  const lastRefreshedText = formatDateTime(sourceHealth?.lastRefreshedAt ?? payload?.lastRefreshedAt);
  const degradationReason =
    status === "formal"
      ? "正式来源可用"
      : sourceHealth?.degradationReason ?? payload?.degradationReason ?? (loading ? "正在加载行情" : error || "当前没有可用的行情来源");
  const retryState = sourceHealth?.retryState ?? payload?.retryState;
  const notice =
    status === "formal"
      ? ""
      : [payload?.notice, error ? `重试失败：${error}` : ""].filter(Boolean).join(" · ");
  const affectedObjects = sourceHealth?.affectedObjects ?? [];
  const affectedObjectsText = affectedObjects.length > 0 ? affectedObjects.join(" / ") : status === "formal" ? "无降级影响" : "未声明";

  return (
    <section className={`side-section source-health-panel ${compact ? "compact" : ""}`} data-testid="source-health-panel">
      <div className="signal-topline">
        <span>来源健康</span>
        <strong data-testid="source-health-status">{statusLabel(status)}</strong>
      </div>

      <div className="source-health-summary">
        <div>
          <span>来源</span>
          <strong>{sourceName}</strong>
        </div>
        <div>
          <span>最后刷新</span>
          <strong>{lastRefreshedText}</strong>
        </div>
        {compact && (
          <div>
            <span>重试</span>
            <strong>{formatRetryState(retryState)}</strong>
          </div>
        )}
      </div>

      {(notice || status !== "formal" || error || loading) && (
        <div className="source-health-notice" data-testid="source-health-notice">
          {notice || degradationReason}
        </div>
      )}

      {!compact && (
        <div className="source-health-grid">
          <div>
            <span>降级说明</span>
            <strong>{degradationReason}</strong>
          </div>
          <div>
            <span>影响对象</span>
            <strong>{affectedObjectsText}</strong>
          </div>
          <div>
            <span>重试状态</span>
            <strong>{formatRetryState(retryState)}</strong>
          </div>
        </div>
      )}

      <div className="source-health-actions">
        <button type="button" onClick={onRetry} aria-label="重试行情">
          重试来源
        </button>
      </div>
    </section>
  );
}
