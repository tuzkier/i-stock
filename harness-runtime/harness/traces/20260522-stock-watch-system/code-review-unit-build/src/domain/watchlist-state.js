"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.archiveWatchSymbol = archiveWatchSymbol;
exports.restoreWatchSymbol = restoreWatchSymbol;
exports.suspendAlertsForArchivedSymbol = suspendAlertsForArchivedSymbol;
exports.restoreAlertsForActiveSymbol = restoreAlertsForActiveSymbol;
function archiveWatchSymbol(watchlist, symbol, archivedAt = Date.now()) {
    return watchlist.map((item) => (item.symbol === symbol ? { ...item, status: "archived", archivedAt } : item));
}
function restoreWatchSymbol(watchlist, symbol, name) {
    return watchlist.map((item) => item.symbol === symbol
        ? {
            ...item,
            name: name?.trim() || item.name,
            status: "active",
            archivedAt: undefined
        }
        : item);
}
function suspendAlertsForArchivedSymbol(alerts, symbol) {
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
function restoreAlertsForActiveSymbol(alerts, symbol) {
    return alerts.map((rule) => rule.symbol === symbol && rule.activationState === "suspended_by_archive"
        ? {
            ...rule,
            enabled: rule.restoreIntent !== "disabled",
            activationState: rule.restoreIntent === "disabled" ? "disabled" : "enabled",
            suspendedReason: undefined
        }
        : rule);
}
