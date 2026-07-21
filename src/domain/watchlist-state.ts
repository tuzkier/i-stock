import type { AlertRule, WatchSymbol } from "../types";

export function archiveWatchSymbol(watchlist: WatchSymbol[], symbol: string, archivedAt = Date.now()) {
  return watchlist.map((item) => (item.symbol === symbol ? { ...item, status: "archived" as const, archivedAt } : item));
}

export function restoreWatchSymbol(watchlist: WatchSymbol[], symbol: string, name?: string) {
  return watchlist.map((item) =>
    item.symbol === symbol
      ? {
          ...item,
          name: name?.trim() || item.name,
          status: "active" as const,
          archivedAt: undefined
        }
      : item
  );
}

export function suspendAlertsForArchivedSymbol(alerts: AlertRule[], symbol: string) {
  return alerts.map((rule) =>
    rule.symbol === symbol
      ? {
          ...rule,
          enabled: false,
          activationState: "suspended_by_archive" as const,
          suspendedReason: "suspended_by_archive" as const,
          restoreIntent: rule.enabled ? ("enabled" as const) : ("disabled" as const)
        }
      : rule
  );
}

export function restoreAlertsForActiveSymbol(alerts: AlertRule[], symbol: string) {
  return alerts.map((rule) =>
    rule.symbol === symbol && rule.activationState === "suspended_by_archive"
      ? {
          ...rule,
          enabled: rule.restoreIntent !== "disabled",
          activationState: rule.restoreIntent === "disabled" ? ("disabled" as const) : ("enabled" as const),
          suspendedReason: undefined
        }
      : rule
  );
}
