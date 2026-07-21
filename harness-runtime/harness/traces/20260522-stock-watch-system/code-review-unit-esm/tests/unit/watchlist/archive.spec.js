import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { archiveWatchSymbol, restoreAlertsForActiveSymbol, restoreWatchSymbol, suspendAlertsForArchivedSymbol } from "../../../src/domain/watchlist-state.js";
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
describe("watchlist archive and restore state", () => {
    it("archives a symbol without physically deleting it", () => {
        const archived = archiveWatchSymbol(watchlist, "9988.HK", 123);
        assert.equal(archived.length, 1);
        assert.equal(archived[0].status, "archived");
        assert.equal(archived[0].archivedAt, 123);
    });
    it("suspends enabled alerts when a symbol is archived", () => {
        const suspended = suspendAlertsForArchivedSymbol(alerts, "9988.HK");
        assert.equal(suspended[0].enabled, false);
        assert.equal(suspended[0].activationState, "suspended_by_archive");
        assert.equal(suspended[0].restoreIntent, "enabled");
        assert.equal(suspended[1].activationState, "enabled");
    });
    it("restores archived symbols and alert activation intent together", () => {
        const suspended = suspendAlertsForArchivedSymbol(alerts, "9988.HK");
        const restoredWatchlist = restoreWatchSymbol(archiveWatchSymbol(watchlist, "9988.HK", 123), "9988.HK");
        const restoredAlerts = restoreAlertsForActiveSymbol(suspended, "9988.HK");
        assert.equal(restoredWatchlist[0].status, "active");
        assert.equal(restoredWatchlist[0].archivedAt, undefined);
        assert.equal(restoredAlerts[0].enabled, true);
        assert.equal(restoredAlerts[0].activationState, "enabled");
        assert.equal(restoredAlerts[0].suspendedReason, undefined);
    });
    it("keeps disabled intent disabled after restore", () => {
        const disabledAlert = {
            ...alerts[0],
            enabled: false,
            activationState: "disabled"
        };
        const suspended = suspendAlertsForArchivedSymbol([disabledAlert], "9988.HK");
        const restored = restoreAlertsForActiveSymbol(suspended, "9988.HK");
        assert.equal(restored[0].enabled, false);
        assert.equal(restored[0].activationState, "disabled");
    });
});
