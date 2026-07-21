import { defaultWatchlist } from "../data/markets";
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
export function readWatchlist() {
    const value = readJson(watchlistKey, defaultWatchlist);
    return value.map(normalizeWatchSymbol);
}
export function writeWatchlist(value) {
    window.localStorage.setItem(watchlistKey, JSON.stringify(value));
}
export function readAlerts() {
    return readJson(alertKey, []).map(normalizeAlertRule);
}
export function writeAlerts(value) {
    window.localStorage.setItem(alertKey, JSON.stringify(value));
}
