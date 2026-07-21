"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const strict_1 = __importDefault(require("node:assert/strict"));
const node_test_1 = require("node:test");
const watchlist_state_js_1 = require("../../../src/domain/watchlist-state.js");
const watchlist = [{ id: "9988.HK", symbol: "9988.HK", name: "阿里巴巴", market: "HK", status: "active" }];
const alerts = [
    {
        id: "alert-1",
        symbol: "9988.HK",
        label: "9988.HK 触发 strong-sell",
        direction: "above",
        signal: "strong-sell",
        enabled: true,
        activationState: "enabled"
    },
    {
        id: "alert-2",
        symbol: "AAPL",
        label: "AAPL 上穿 200",
        direction: "above",
        price: 200,
        enabled: true,
        activationState: "enabled"
    }
];
(0, node_test_1.describe)("watchlist archive and restore state", () => {
    (0, node_test_1.it)("archives a symbol without physically deleting it", () => {
        const archived = (0, watchlist_state_js_1.archiveWatchSymbol)(watchlist, "9988.HK", 123);
        strict_1.default.equal(archived.length, 1);
        strict_1.default.equal(archived[0].status, "archived");
        strict_1.default.equal(archived[0].archivedAt, 123);
    });
    (0, node_test_1.it)("suspends enabled alerts when a symbol is archived", () => {
        const suspended = (0, watchlist_state_js_1.suspendAlertsForArchivedSymbol)(alerts, "9988.HK");
        strict_1.default.equal(suspended[0].enabled, false);
        strict_1.default.equal(suspended[0].activationState, "suspended_by_archive");
        strict_1.default.equal(suspended[0].restoreIntent, "enabled");
        strict_1.default.equal(suspended[1].activationState, "enabled");
    });
    (0, node_test_1.it)("restores archived symbols and alert activation intent together", () => {
        const suspended = (0, watchlist_state_js_1.suspendAlertsForArchivedSymbol)(alerts, "9988.HK");
        const restoredWatchlist = (0, watchlist_state_js_1.restoreWatchSymbol)((0, watchlist_state_js_1.archiveWatchSymbol)(watchlist, "9988.HK", 123), "9988.HK");
        const restoredAlerts = (0, watchlist_state_js_1.restoreAlertsForActiveSymbol)(suspended, "9988.HK");
        strict_1.default.equal(restoredWatchlist[0].status, "active");
        strict_1.default.equal(restoredWatchlist[0].archivedAt, undefined);
        strict_1.default.equal(restoredAlerts[0].enabled, true);
        strict_1.default.equal(restoredAlerts[0].activationState, "enabled");
        strict_1.default.equal(restoredAlerts[0].suspendedReason, undefined);
    });
    (0, node_test_1.it)("keeps disabled intent disabled after restore", () => {
        const disabledAlert = {
            ...alerts[0],
            enabled: false,
            activationState: "disabled"
        };
        const suspended = (0, watchlist_state_js_1.suspendAlertsForArchivedSymbol)([disabledAlert], "9988.HK");
        const restored = (0, watchlist_state_js_1.restoreAlertsForActiveSymbol)(suspended, "9988.HK");
        strict_1.default.equal(restored[0].enabled, false);
        strict_1.default.equal(restored[0].activationState, "disabled");
    });
});
