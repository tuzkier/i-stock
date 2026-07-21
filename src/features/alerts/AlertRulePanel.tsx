import { Bell, BellRing, Trash2 } from "lucide-react";
import { useState } from "react";
import { createAlertRule, normalizeAlertRule } from "../../domain/alert";
import type { AlertRule } from "../../types";

type AlertRulePanelProps = {
  alerts: AlertRule[];
  selectedSymbol: string;
  latestPrice?: number;
  onCreate: (rule: AlertRule) => void;
  onToggle: (ruleId: string, enabled: boolean) => void;
  onAcknowledge: (ruleId: string) => void;
  onDelete: (ruleId: string) => void;
};

const taxonomyLabels: Record<NonNullable<AlertRule["taxonomy"]>, string> = {
  price: "价格型",
  change: "变化型",
  technical_indicator: "技术指标型",
  mts: "MTS 型",
  scheduled: "定时提醒"
};

const levelLabels: Array<NonNullable<AlertRule["level"]>> = ["观察", "确认", "强信号", "风控"];

function formatTime(value?: number) {
  if (!Number.isFinite(value)) return "未触发";
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "short", timeStyle: "short" }).format(new Date(value as number));
}

function latestHistory(rule: AlertRule) {
  return rule.history?.at(-1);
}

function rowTestId(rule: AlertRule) {
  if (rule.activationState === "suspended_by_archive") return "alert-rule-row-archive";
  if (rule.level === "风控") return "alert-rule-row-risk";
  return "alert-rule-row-watch";
}

function conditionHint(taxonomy: NonNullable<AlertRule["taxonomy"]>) {
  if (taxonomy === "scheduled") return "09:30";
  if (taxonomy === "mts") return "观察 / 确认 / 强信号 / 风控";
  if (taxonomy === "technical_indicator") return "RSI 阈值，如 30";
  if (taxonomy === "change") return "变化百分比，如 3";
  return "目标价";
}

export function AlertRulePanel({
  alerts,
  selectedSymbol,
  latestPrice,
  onCreate,
  onToggle,
  onAcknowledge,
  onDelete
}: AlertRulePanelProps) {
  const [taxonomy, setTaxonomy] = useState<NonNullable<AlertRule["taxonomy"]>>("price");
  const [level, setLevel] = useState<NonNullable<AlertRule["level"]>>("观察");
  const [direction, setDirection] = useState<"above" | "below">("above");
  const [conditionValue, setConditionValue] = useState("");
  const visibleAlerts = alerts
    .map(normalizeAlertRule)
    .sort((left, right) => Number(right.symbol === selectedSymbol) - Number(left.symbol === selectedSymbol));
  const triggeredCount = visibleAlerts.filter((rule) => rule.triggerState === "triggered").length;

  function saveRule() {
    const threshold = Number(conditionValue);
    const rule = createAlertRule({
      symbol: selectedSymbol,
      taxonomy,
      level,
      direction,
      threshold: Number.isFinite(threshold) ? threshold : undefined,
      indicator: "RSI",
      mtsAlertLevel: level,
      localTime: taxonomy === "scheduled" ? conditionValue || "09:30" : undefined
    });
    onCreate(rule);
    setConditionValue("");
  }

  return (
    <section className="side-section" data-testid="alerts-panel">
      <h3>买卖提醒</h3>
      {triggeredCount > 0 && (
        <div className="triggered" data-testid="alert-trigger-summary">
          <BellRing size={16} />
          {triggeredCount} 条提醒已触发
        </div>
      )}

      <div className="alert-create-form" data-testid="alert-create-form">
        <select
          aria-label="提醒类型"
          data-testid="alert-taxonomy-select"
          value={taxonomy}
          onChange={(event) => setTaxonomy(event.target.value as NonNullable<AlertRule["taxonomy"]>)}
        >
          {Object.entries(taxonomyLabels).map(([value, label]) => (
            <option value={value} key={value}>
              {label}
            </option>
          ))}
        </select>
        <select
          aria-label="提醒等级"
          data-testid="alert-level-select"
          value={level}
          onChange={(event) => setLevel(event.target.value as NonNullable<AlertRule["level"]>)}
        >
          {levelLabels.map((item) => (
            <option value={item} key={item}>
              {item}
            </option>
          ))}
        </select>
        {taxonomy !== "mts" && taxonomy !== "scheduled" && (
          <select aria-label="提醒方向" value={direction} onChange={(event) => setDirection(event.target.value as "above" | "below")}>
            <option value="above">上穿 / 高于</option>
            <option value="below">下破 / 低于</option>
          </select>
        )}
        <input
          data-testid="alert-condition-input"
          value={conditionValue}
          onChange={(event) => setConditionValue(event.target.value)}
          placeholder={conditionHint(taxonomy)}
        />
        <button data-testid="alert-save-button" type="button" onClick={saveRule}>
          <Bell size={14} /> 保存提醒
        </button>
      </div>

      <div className="alert-list">
        {visibleAlerts.length === 0 && <div className="data-notice">当前标的暂无本地提醒规则</div>}
        {visibleAlerts.map((rule) => {
          const latest = latestHistory(rule);
          const hasMissedWhileClosed = rule.history?.some((event) => event.type === "missed_while_closed");
          return (
            <label className={rule.activationState === "suspended_by_archive" ? "suspended" : ""} data-testid={rowTestId(rule)} key={rule.id}>
              <input
                type="checkbox"
                checked={rule.activationState === "enabled"}
                disabled={rule.activationState === "suspended_by_archive"}
                onChange={(event) => onToggle(rule.id, event.target.checked)}
              />
              <span>
                <strong>
                  {rule.level} · {taxonomyLabels[rule.taxonomy ?? "price"]} · {rule.label}
                </strong>
                <small>
                  {rule.activationState} / {rule.triggerState} · {formatTime(rule.lastTriggeredAt)} · {rule.triggerReason ?? "未命中"}
                </small>
                {hasMissedWhileClosed && <small>浏览器重开：missed_while_closed</small>}
                {latest && <small>历史：{latest.type} · {latest.reason}</small>}
                {rule.activationState === "suspended_by_archive" && <small>归档暂停，恢复标的后按原启停意图继续</small>}
              </span>
              {rule.triggerState === "triggered" ? (
                <button className="row-icon-button" data-testid="alert-ack-button" type="button" onClick={() => onAcknowledge(rule.id)}>
                  确认
                </button>
              ) : (
                <Trash2 size={14} onClick={() => onDelete(rule.id)} />
              )}
            </label>
          );
        })}
      </div>
      {Number.isFinite(latestPrice) && <small>当前观察价：{latestPrice}</small>}
    </section>
  );
}
