import type { AlertRule, MtsAlertLevel, MtsExplanation } from "../types";

export type AlertTaxonomy = NonNullable<AlertRule["taxonomy"]>;
export type AlertLevel = NonNullable<AlertRule["level"]>;

export type CreateAlertRuleInput = {
  symbol: string;
  taxonomy: AlertTaxonomy;
  level: AlertLevel;
  now?: number;
  direction?: "above" | "below";
  threshold?: number;
  indicator?: "RSI" | "MACD" | "KDJ" | "ATR";
  mtsAlertLevel?: MtsAlertLevel;
  localTime?: string;
  daysOfWeek?: number[];
  skipIfMarketClosed?: boolean;
};

export type AlertEvaluationInput = {
  symbol: string;
  latestPrice?: number;
  previousClose?: number;
  indicators?: Partial<Record<"RSI" | "MACD" | "KDJ" | "ATR", number>>;
  mts?: MtsExplanation;
  now?: number;
};

const taxonomies: AlertTaxonomy[] = ["price", "change", "technical_indicator", "mts", "scheduled"];
const levels: AlertLevel[] = ["观察", "确认", "强信号", "风控"];
const alertLevelRank: Record<MtsAlertLevel, number> = {
  none: 0,
  观察: 1,
  确认: 2,
  强信号: 3,
  风控: 3
};

function assertTaxonomy(taxonomy: AlertTaxonomy) {
  if (!taxonomies.includes(taxonomy)) {
    throw new Error(`unsupported taxonomy: ${taxonomy}`);
  }
}

function assertLevel(level: AlertLevel) {
  if (!levels.includes(level)) {
    throw new Error(`unsupported alert level: ${level}`);
  }
}

function assertThreshold(input: CreateAlertRuleInput) {
  if (!Number.isFinite(input.threshold)) {
    throw new Error(`${input.taxonomy} alert requires numeric threshold`);
  }
}

function assertDirection(input: CreateAlertRuleInput) {
  if (input.direction !== "above" && input.direction !== "below") {
    throw new Error(`${input.taxonomy} alert requires direction`);
  }
}

function normalizeLocalTime(localTime?: string) {
  if (!localTime || !/^\d{2}:\d{2}$/.test(localTime)) {
    throw new Error("scheduled alert requires localTime in HH:mm");
  }
  return localTime;
}

function createId(input: CreateAlertRuleInput, now: number) {
  return `alert-${input.taxonomy}-${input.symbol}-${now}`;
}

function labelFor(input: CreateAlertRuleInput) {
  if (input.taxonomy === "price") return `${input.symbol} 价格${input.direction === "below" ? "下破" : "上穿"} ${input.threshold}`;
  if (input.taxonomy === "change") return `${input.symbol} 变化${input.direction === "below" ? "低于" : "高于"} ${input.threshold}%`;
  if (input.taxonomy === "technical_indicator") {
    return `${input.symbol} ${input.indicator ?? "指标"} ${input.direction === "below" ? "低于" : "高于"} ${input.threshold}`;
  }
  if (input.taxonomy === "mts") return `${input.symbol} MTS 达到 ${input.mtsAlertLevel ?? "确认"}`;
  return `${input.symbol} 定时提醒 ${input.localTime}`;
}

function normalizeMtsAlertLevel(value?: MtsAlertLevel | "watch" | "elevated" | "high"): MtsAlertLevel {
  if (value === "high") return "强信号";
  if (value === "elevated") return "确认";
  if (value === "watch") return "观察";
  return value ?? "确认";
}

function signalToMtsAlertLevel(signal?: AlertRule["signal"]): MtsAlertLevel {
  if (signal === "strong-sell") return "风控";
  if (signal === "strong-buy") return "强信号";
  if (signal === "buy-watch" || signal === "sell-watch") return "确认";
  return "观察";
}

function signalForMtsAlertLevel(level: MtsAlertLevel): AlertRule["signal"] {
  if (level === "风控") return "strong-sell";
  if (level === "强信号") return "strong-buy";
  if (level === "确认") return "buy-watch";
  return "hold";
}

export function createAlertRule(input: CreateAlertRuleInput): AlertRule {
  assertTaxonomy(input.taxonomy);
  assertLevel(input.level);
  const now = input.now ?? Date.now();

  const base = {
    id: createId(input, now),
    symbol: input.symbol,
    label: labelFor(input),
    taxonomy: input.taxonomy,
    level: input.level,
    enabled: true,
    activationState: "enabled" as const,
    triggerState: "idle" as const,
    direction: input.direction ?? "above",
    history: []
  };

  if (input.taxonomy === "price") {
    assertThreshold(input);
    assertDirection(input);
    return {
      ...base,
      price: input.threshold,
      condition: {
        kind: "price",
        direction: input.direction,
        threshold: input.threshold
      }
    };
  }

  if (input.taxonomy === "change") {
    assertThreshold(input);
    assertDirection(input);
    return {
      ...base,
      condition: {
        kind: "change_percent",
        direction: input.direction,
        threshold: input.threshold
      }
    };
  }

  if (input.taxonomy === "technical_indicator") {
    assertThreshold(input);
    assertDirection(input);
    return {
      ...base,
      condition: {
        kind: "technical_indicator",
        indicator: input.indicator ?? "RSI",
        direction: input.direction,
        threshold: input.threshold
      }
    };
  }

  if (input.taxonomy === "mts") {
    const mtsAlertLevel = normalizeMtsAlertLevel(input.mtsAlertLevel);
    return {
      ...base,
      signal: signalForMtsAlertLevel(mtsAlertLevel),
      condition: {
        kind: "mts",
        mtsAlertLevel
      }
    };
  }

  const localTime = normalizeLocalTime(input.localTime);
  return {
    ...base,
    condition: {
      kind: "daily_time",
      localTime,
      timezone: "local",
      daysOfWeek: input.daysOfWeek,
      skipIfMarketClosed: input.skipIfMarketClosed
    }
  };
}

export function normalizeAlertRule(rule: AlertRule): AlertRule {
  const taxonomy = rule.taxonomy ?? (rule.signal ? "mts" : "price");
  const activationState = rule.activationState ?? (rule.enabled ? "enabled" : "disabled");
  const triggerState = rule.triggerState ?? (rule.lastTriggeredAt ? "triggered" : "idle");
  const normalizedCondition =
    rule.condition?.kind === "mts"
      ? { ...rule.condition, mtsAlertLevel: normalizeMtsAlertLevel(rule.condition.mtsAlertLevel as MtsAlertLevel | "watch" | "elevated" | "high" | undefined) }
      : rule.condition;
  return {
    ...rule,
    taxonomy,
    level: rule.level ?? (rule.signal ? "强信号" : "观察"),
    condition:
      normalizedCondition ??
      (rule.signal
        ? { kind: "mts", mtsAlertLevel: signalToMtsAlertLevel(rule.signal) }
        : { kind: "price", direction: rule.direction, threshold: rule.price }),
    activationState,
    triggerState,
    enabled: activationState === "enabled",
    history: rule.history ?? []
  };
}

function appendHistory(rule: AlertRule, event: NonNullable<AlertRule["history"]>[number]) {
  return {
    ...rule,
    history: [...(rule.history ?? []), event]
  };
}

export function suspendAlertRulesForArchivedSymbol(alerts: AlertRule[], symbol: string, now = Date.now()) {
  return alerts.map((rawRule) => {
    const rule = normalizeAlertRule(rawRule);
    if (rule.symbol !== symbol || rule.activationState === "suspended_by_archive") return rule;
    return appendHistory(
      {
        ...rule,
        enabled: false,
        activationState: "suspended_by_archive",
        suspendedReason: "suspended_by_archive",
        restoreIntent: rule.activationState === "enabled" ? "enabled" : "disabled"
      },
      { at: now, type: "suspended_by_archive", reason: "标的归档，提醒暂停" }
    );
  });
}

export function restoreAlertRulesForActiveSymbol(alerts: AlertRule[], symbol: string, now = Date.now()) {
  return alerts.map((rawRule) => {
    const rule = normalizeAlertRule(rawRule);
    if (rule.symbol !== symbol || rule.activationState !== "suspended_by_archive") return rule;
    const activationState = rule.restoreIntent === "disabled" ? "disabled" : "enabled";
    return appendHistory(
      {
        ...rule,
        enabled: activationState === "enabled",
        activationState,
        suspendedReason: undefined
      },
      { at: now, type: "restored", reason: activationState === "enabled" ? "标的恢复，按归档前意图启用" : "标的恢复，保持归档前停用意图" }
    );
  });
}

export function acknowledgeAlertRule(rule: AlertRule, now = Date.now()): AlertRule {
  const normalized = normalizeAlertRule(rule);
  return appendHistory(
    {
      ...normalized,
      triggerState: "acknowledged",
      acknowledgedAt: now
    },
    { at: now, type: "acknowledged", reason: "用户已确认提醒" }
  );
}

function matchesDirection(value: number | undefined, threshold: number | undefined, direction: "above" | "below" | undefined) {
  if (!Number.isFinite(value) || !Number.isFinite(threshold)) return false;
  return direction === "below" ? (value as number) <= (threshold as number) : (value as number) >= (threshold as number);
}

function timeToMinutes(value: string) {
  const [hour, minute] = value.split(":").map(Number);
  return hour * 60 + minute;
}

function localDateKey(now: Date, localTime: string) {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}@${localTime}`;
}

function isWeekend(now: Date) {
  const day = now.getDay();
  return day === 0 || day === 6;
}

function matchesMtsAlertLevel(requiredLevel: MtsAlertLevel, actualLevel: MtsAlertLevel) {
  const required = normalizeMtsAlertLevel(requiredLevel);
  const actual = normalizeMtsAlertLevel(actualLevel);
  if (required === "风控" || required === "强信号") return actual === required;
  return alertLevelRank[actual] >= alertLevelRank[required];
}

type ScheduledEvaluation =
  | { kind: "trigger"; reason: string; key: string }
  | { kind: "missed"; reason: string; key: string }
  | { kind: "none" };

function shouldSkipScheduledDate(condition: NonNullable<AlertRule["condition"]>, now: Date) {
  if (condition.kind !== "daily_time") return false;
  if (condition.daysOfWeek?.length && !condition.daysOfWeek.includes(now.getDay())) return true;
  return Boolean(condition.skipIfMarketClosed && isWeekend(now));
}

function evaluateScheduledRule(rule: AlertRule, input: AlertEvaluationInput): ScheduledEvaluation {
  const condition = rule.condition;
  if (condition?.kind !== "daily_time" || !condition.localTime) return { kind: "none" };
  const now = new Date(input.now ?? Date.now());
  if (shouldSkipScheduledDate(condition, now)) return { kind: "none" };

  const todayMinutes = now.getHours() * 60 + now.getMinutes();
  const scheduledMinutes = timeToMinutes(condition.localTime);
  if (todayMinutes < scheduledMinutes) return { kind: "none" };

  const scheduledKey = localDateKey(now, condition.localTime);
  if (rule.lastScheduledTriggerKey === scheduledKey || rule.lastScheduledMissedKey === scheduledKey) return { kind: "none" };

  if (shouldRecordMissedWhileClosed(rule, input)) {
    return {
      kind: "missed",
      key: scheduledKey,
      reason: "浏览器关闭期间错过定时提醒，本次打开后记录为本地历史"
    };
  }

  return {
    kind: "trigger",
    key: scheduledKey,
    reason: `scheduled alert due at ${condition.localTime}`
  };
}

function evaluateRule(rule: AlertRule, input: AlertEvaluationInput) {
  const condition = rule.condition;
  if (!condition) return "";
  if (condition.kind === "price" && matchesDirection(input.latestPrice, condition.threshold, condition.direction)) {
    return `price ${input.latestPrice} crossed ${condition.direction} ${condition.threshold}`;
  }
  if (condition.kind === "change_percent" && Number.isFinite(input.latestPrice) && Number.isFinite(input.previousClose) && input.previousClose) {
    const percent = (((input.latestPrice as number) - (input.previousClose as number)) / (input.previousClose as number)) * 100;
    if (matchesDirection(percent, condition.threshold, condition.direction)) return `change ${percent.toFixed(2)}% crossed ${condition.direction} ${condition.threshold}%`;
  }
  if (condition.kind === "technical_indicator") {
    const indicatorValue = input.indicators?.[condition.indicator ?? "RSI"];
    if (matchesDirection(indicatorValue, condition.threshold, condition.direction)) {
      return `${condition.indicator} ${indicatorValue} crossed ${condition.direction} ${condition.threshold}`;
    }
  }
  if (condition.kind === "mts") {
    const required = normalizeMtsAlertLevel(condition.mtsAlertLevel);
    const actual = normalizeMtsAlertLevel(input.mts?.alertLevel ?? "none");
    if (matchesMtsAlertLevel(required, actual)) return `MTS alert level ${actual} reached ${required}`;
  }
  if (condition.kind === "daily_time" && condition.localTime) {
    const scheduled = evaluateScheduledRule(rule, input);
    if (scheduled.kind === "trigger") return scheduled.reason;
  }
  return "";
}

function shouldRecordMissedWhileClosed(rule: AlertRule, input: AlertEvaluationInput) {
  if (rule.condition?.kind !== "daily_time" || !rule.condition.localTime || rule.lastScheduledTriggerKey || rule.lastTriggeredAt) return false;
  if ((rule.history ?? []).some((event) => event.type === "missed_while_closed" || event.type === "triggered")) return false;
  const now = input.now ?? Date.now();
  const createdAtFromHistory = rule.history?.find((event) => event.type === "created")?.at;
  const createdAt = Number.isFinite(createdAtFromHistory) ? (createdAtFromHistory as number) : Number(rule.id.split("-").at(-1));
  return Number.isFinite(createdAt) && now - createdAt > 12 * 60 * 60 * 1000;
}

export function evaluateAlertRules(alerts: AlertRule[], input: AlertEvaluationInput): AlertRule[] {
  const now = input.now ?? Date.now();
  return alerts.map((rawRule) => {
    const rule = normalizeAlertRule(rawRule);
    if (rule.symbol !== input.symbol || rule.activationState !== "enabled") return rule;
    if (rule.condition?.kind === "daily_time") {
      const scheduled = evaluateScheduledRule(rule, input);
      if (scheduled.kind === "missed") {
        return {
          ...rule,
          lastScheduledMissedKey: scheduled.key,
          history: [...(rule.history ?? []), { at: now, type: "missed_while_closed", reason: scheduled.reason }]
        };
      }
      if (scheduled.kind !== "trigger") return rule;
      return {
        ...rule,
        triggerState: "triggered",
        lastTriggeredAt: now,
        lastScheduledTriggerKey: scheduled.key,
        triggerReason: scheduled.reason,
        history: [...(rule.history ?? []), { at: now, type: "triggered", reason: scheduled.reason }]
      };
    }
    if (rule.triggerState !== "idle") return rule;
    const reason = evaluateRule(rule, input);
    if (!reason) return rule;
    const history = [...(rule.history ?? [])];
    history.push({ at: now, type: "triggered", reason });
    return {
      ...rule,
      triggerState: "triggered",
      lastTriggeredAt: now,
      triggerReason: reason,
      history
    };
  });
}
