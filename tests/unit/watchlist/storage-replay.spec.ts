import assert from "node:assert/strict";
import { beforeEach, describe, it } from "node:test";
import type { AlertRule, WatchSymbol } from "../../../src/types.js";

function installLocalStorage() {
  const store = new Map<string, string>();
  const localStorage = {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => {
      store.set(key, value);
    },
    removeItem: (key: string) => {
      store.delete(key);
    },
    clear: () => {
      store.clear();
    }
  };
  globalThis.window = { localStorage } as unknown as Window & typeof globalThis;
  return localStorage;
}

const localStorage = installLocalStorage();
const storage = require("../../../src/lib/storage.js") as typeof import("../../../src/lib/storage");

describe("watchlist localStorage replay", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("replays archived symbols and suspended alert restore intent from localStorage", () => {
    const watchlist: WatchSymbol[] = [
      { id: "9988.HK", symbol: "9988.HK", name: "阿里巴巴", market: "HK", status: "archived", archivedAt: 123 }
    ];
    const alerts: AlertRule[] = [
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

    assert.deepEqual(storage.readWatchlist(), watchlist);
    assert.deepEqual(storage.readAlerts(), alerts);
  });

  it("migrates legacy watchlist and alert records to explicit active/enabled state", () => {
    localStorage.setItem(
      "myinvestment.watchlist",
      JSON.stringify([{ id: "AAPL", symbol: "AAPL", name: "Apple", market: "US" }])
    );
    localStorage.setItem(
      "myinvestment.alerts",
      JSON.stringify([{ id: "alert-legacy", symbol: "AAPL", label: "AAPL 上穿 200", direction: "above", price: 200, enabled: true }])
    );

    assert.equal(storage.readWatchlist()[0].status, "active");
    assert.equal(storage.readAlerts()[0].activationState, "enabled");
  });

  it("keeps legacy disabled alerts disabled during replay", () => {
    localStorage.setItem(
      "myinvestment.alerts",
      JSON.stringify([
        { id: "alert-disabled", symbol: "AAPL", label: "AAPL 上穿 200", direction: "above", price: 200, enabled: false }
      ])
    );

    const replayedAlerts = storage.readAlerts();

    assert.equal(replayedAlerts[0].enabled, false);
    assert.equal(replayedAlerts[0].activationState, "disabled");
  });
});
