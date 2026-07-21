"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const strict_1 = __importDefault(require("node:assert/strict"));
const node_test_1 = require("node:test");
function installLocalStorage() {
    const store = new Map();
    const localStorage = {
        getItem: (key) => store.get(key) ?? null,
        setItem: (key, value) => {
            store.set(key, value);
        },
        removeItem: (key) => {
            store.delete(key);
        },
        clear: () => {
            store.clear();
        }
    };
    globalThis.window = { localStorage };
    return localStorage;
}
const localStorage = installLocalStorage();
const storage = require("../../../src/lib/storage.js");
(0, node_test_1.describe)("watchlist localStorage replay", () => {
    (0, node_test_1.beforeEach)(() => {
        localStorage.clear();
    });
    (0, node_test_1.it)("replays archived symbols and suspended alert restore intent from localStorage", () => {
        const watchlist = [
            { id: "9988.HK", symbol: "9988.HK", name: "阿里巴巴", market: "HK", status: "archived", archivedAt: 123 }
        ];
        const alerts = [
            {
                id: "alert-1",
                symbol: "9988.HK",
                label: "9988.HK 触发 strong-sell",
                direction: "above",
                signal: "strong-sell",
                enabled: false,
                activationState: "suspended_by_archive",
                suspendedReason: "suspended_by_archive",
                restoreIntent: "enabled"
            }
        ];
        storage.writeWatchlist(watchlist);
        storage.writeAlerts(alerts);
        strict_1.default.deepEqual(storage.readWatchlist(), watchlist);
        strict_1.default.deepEqual(storage.readAlerts(), alerts);
    });
    (0, node_test_1.it)("migrates legacy watchlist and alert records to explicit active/enabled state", () => {
        localStorage.setItem("myinvestment.watchlist", JSON.stringify([{ id: "AAPL", symbol: "AAPL", name: "Apple", market: "US" }]));
        localStorage.setItem("myinvestment.alerts", JSON.stringify([{ id: "alert-legacy", symbol: "AAPL", label: "AAPL 上穿 200", direction: "above", price: 200, enabled: true }]));
        strict_1.default.equal(storage.readWatchlist()[0].status, "active");
        strict_1.default.equal(storage.readAlerts()[0].activationState, "enabled");
    });
});
