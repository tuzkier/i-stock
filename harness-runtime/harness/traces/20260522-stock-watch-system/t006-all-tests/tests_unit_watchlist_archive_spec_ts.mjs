// tests/unit/watchlist/archive.spec.ts
import assert from "node:assert/strict";
import { describe, it } from "node:test";

// src/domain/watchlist-state.ts
function archiveWatchSymbol(watchlist2, symbol, archivedAt = Date.now()) {
  return watchlist2.map((item) => item.symbol === symbol ? { ...item, status: "archived", archivedAt } : item);
}
function restoreWatchSymbol(watchlist2, symbol, name) {
  return watchlist2.map(
    (item) => item.symbol === symbol ? {
      ...item,
      name: name?.trim() || item.name,
      status: "active",
      archivedAt: void 0
    } : item
  );
}
function suspendAlertsForArchivedSymbol(alerts2, symbol) {
  return alerts2.map(
    (rule) => rule.symbol === symbol ? {
      ...rule,
      enabled: false,
      activationState: "suspended_by_archive",
      suspendedReason: "suspended_by_archive",
      restoreIntent: rule.enabled ? "enabled" : "disabled"
    } : rule
  );
}
function restoreAlertsForActiveSymbol(alerts2, symbol) {
  return alerts2.map(
    (rule) => rule.symbol === symbol && rule.activationState === "suspended_by_archive" ? {
      ...rule,
      enabled: rule.restoreIntent !== "disabled",
      activationState: rule.restoreIntent === "disabled" ? "disabled" : "enabled",
      suspendedReason: void 0
    } : rule
  );
}

// tests/unit/watchlist/archive.spec.ts
var watchlist = [{ id: "9988.HK", symbol: "9988.HK", name: "\u963F\u91CC\u5DF4\u5DF4", market: "HK", status: "active" }];
var alerts = [
  {
    id: "alert-1",
    symbol: "9988.HK",
    label: "9988.HK \u89E6\u53D1 strong-sell",
    direction: "above",
    signal: "strong-sell",
    enabled: true,
    activationState: "enabled"
  },
  {
    id: "alert-2",
    symbol: "AAPL",
    label: "AAPL \u4E0A\u7A7F 200",
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
    assert.equal(restoredWatchlist[0].archivedAt, void 0);
    assert.equal(restoredAlerts[0].enabled, true);
    assert.equal(restoredAlerts[0].activationState, "enabled");
    assert.equal(restoredAlerts[0].suspendedReason, void 0);
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
