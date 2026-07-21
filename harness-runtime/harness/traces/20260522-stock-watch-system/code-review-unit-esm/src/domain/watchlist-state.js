export function archiveWatchSymbol(watchlist, symbol, archivedAt = Date.now()) {
    return watchlist.map((item) => (item.symbol === symbol ? { ...item, status: "archived", archivedAt } : item));
}
export function restoreWatchSymbol(watchlist, symbol, name) {
    return watchlist.map((item) => item.symbol === symbol
        ? {
            ...item,
            name: name?.trim() || item.name,
            status: "active",
            archivedAt: undefined
        }
        : item);
}
export function suspendAlertsForArchivedSymbol(alerts, symbol) {
    return alerts.map((rule) => rule.symbol === symbol
        ? {
            ...rule,
            enabled: false,
            activationState: "suspended_by_archive",
            suspendedReason: "suspended_by_archive",
            restoreIntent: rule.enabled ? "enabled" : "disabled"
        }
        : rule);
}
export function restoreAlertsForActiveSymbol(alerts, symbol) {
    return alerts.map((rule) => rule.symbol === symbol && rule.activationState === "suspended_by_archive"
        ? {
            ...rule,
            enabled: rule.restoreIntent !== "disabled",
            activationState: rule.restoreIntent === "disabled" ? "disabled" : "enabled",
            suspendedReason: undefined
        }
        : rule);
}
