"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.readWatchlist = readWatchlist;
exports.writeWatchlist = writeWatchlist;
exports.readAlerts = readAlerts;
exports.writeAlerts = writeAlerts;
const markets_1 = require("../data/markets");
const watchlistKey = "myinvestment.watchlist";
const alertKey = "myinvestment.alerts";
function readJson(key, fallback) {
    try {
        const value = window.localStorage.getItem(key);
        return value ? JSON.parse(value) : fallback;
    }
    catch {
        return fallback;
    }
}
function normalizeWatchSymbol(item) {
    return {
        ...item,
        status: item.status ?? "active"
    };
}
function normalizeAlertRule(rule) {
    const activationState = rule.activationState ?? (rule.enabled ? "enabled" : "disabled");
    return {
        ...rule,
        activationState,
        enabled: activationState === "enabled"
    };
}
function readWatchlist() {
    const value = readJson(watchlistKey, markets_1.defaultWatchlist);
    return value.map(normalizeWatchSymbol);
}
function writeWatchlist(value) {
    window.localStorage.setItem(watchlistKey, JSON.stringify(value));
}
function readAlerts() {
    return readJson(alertKey, []).map(normalizeAlertRule);
}
function writeAlerts(value) {
    window.localStorage.setItem(alertKey, JSON.stringify(value));
}
