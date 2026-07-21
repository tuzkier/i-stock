import assert from "node:assert/strict";
import test from "node:test";
import {
  WORKSPACE_SNAPSHOT_KEY,
  createWorkspaceSnapshot,
  readWorkspaceSnapshot,
  writeWorkspaceSnapshot
} from "../../../src/domain/workspace";
import type { AlertRule, WatchSymbol } from "../../../src/types";

class MemoryStorage implements Storage {
  private values = new Map<string, string>();
  readonly length = 0;

  clear() {
    this.values.clear();
  }

  getItem(key: string) {
    return this.values.get(key) ?? null;
  }

  key(index: number) {
    return Array.from(this.values.keys())[index] ?? null;
  }

  removeItem(key: string) {
    this.values.delete(key);
  }

  setItem(key: string, value: string) {
    this.values.set(key, value);
  }
}

const watchlist: WatchSymbol[] = [
  { id: "AAPL", symbol: "AAPL", name: "Apple", market: "US", status: "active" },
  { id: "0700.HK", symbol: "0700.HK", name: "腾讯控股", market: "HK", status: "active" }
];

function alert(symbol = "AAPL"): AlertRule {
  return {
    id: `${symbol}-alert`,
    symbol,
    label: "价格提醒",
    taxonomy: "price",
    level: "观察",
    condition: { kind: "price", direction: "above", threshold: 190 },
    direction: "above",
    price: 190,
    enabled: true,
    activationState: "enabled",
    triggerState: "acknowledged",
    lastTriggeredAt: 1_783_000_000_000,
    history: [
      { at: 1_783_000_000_000, type: "triggered", reason: "AAPL close 191 >= 190" },
      { at: 1_783_000_001_000, type: "acknowledged", reason: "用户确认" }
    ]
  };
}

test("legacy watchlist and alerts keys migrate into WorkspaceSnapshotV2 without losing alert history", () => {
  const storage = new MemoryStorage();
  storage.setItem("myinvestment.watchlist", JSON.stringify(watchlist));
  storage.setItem("myinvestment.alerts", JSON.stringify([alert()]));

  const first = readWorkspaceSnapshot(storage);
  const second = readWorkspaceSnapshot(storage);

  assert.equal(first.snapshot.version, 2);
  assert.equal(first.restoreMetadata.status, "partial");
  assert.equal(first.restoreMetadata.migratedFromLegacy, true);
  assert.equal(first.snapshot.selectedSymbol, "AAPL");
  assert.equal(first.snapshot.selectedMobileTab, "chart");
  assert.equal(first.snapshot.restoreMetadata.status, "partial");
  assert.equal(first.snapshot.alerts[0]?.history?.map((item) => item.type).join(","), "triggered,acknowledged");
  assert.equal(storage.getItem(WORKSPACE_SNAPSHOT_KEY), JSON.stringify(first.snapshot));
  assert.equal(storage.getItem("myinvestment.watchlist"), JSON.stringify(first.snapshot.watchlist));
  assert.equal(storage.getItem("myinvestment.alerts"), JSON.stringify(first.snapshot.alerts));
  assert.deepEqual(second.snapshot, first.snapshot);
  assert.equal(second.restoreMetadata.migratedFromLegacy, false);
});

test("corrupt workspace snapshot falls back to a usable focus layout", () => {
  const storage = new MemoryStorage();
  storage.setItem(WORKSPACE_SNAPSHOT_KEY, "{bad json");

  const restored = readWorkspaceSnapshot(storage);

  assert.equal(restored.restoreMetadata.status, "default_fallback");
  assert.equal(restored.snapshot.globalLayoutFallback.mode, "focus");
  assert.equal(restored.snapshot.layoutBySymbol.AAPL, undefined);
});

test("corrupt workspace snapshot recovers readable legacy keys before default fallback", () => {
  const storage = new MemoryStorage();
  storage.setItem(WORKSPACE_SNAPSHOT_KEY, "{bad json");
  storage.setItem("myinvestment.watchlist", JSON.stringify(watchlist));
  storage.setItem("myinvestment.alerts", JSON.stringify([alert("0700.HK")]));

  const restored = readWorkspaceSnapshot(storage);

  assert.equal(restored.restoreMetadata.status, "partial");
  assert.equal(restored.restoreMetadata.migratedFromLegacy, true);
  assert.equal(restored.snapshot.watchlist.length, 2);
  assert.equal(restored.snapshot.alerts[0]?.symbol, "0700.HK");
});

test("per-symbol layouts are normalized by symbol and stay independent from global fallback", () => {
  const storage = new MemoryStorage();
  writeWorkspaceSnapshot(
    storage,
    createWorkspaceSnapshot({
      watchlist,
      alerts: [],
      selectedSymbol: "0700.hk",
      layoutBySymbol: {
        AAPL: { mode: "dense", selectedMobileTab: "chart" },
        "0700.hk": { mode: "mobile_tab", selectedMobileTab: "source" },
        MSFT: { mode: "not-valid", selectedMobileTab: "source" } as never
      },
      globalLayoutFallback: { mode: "focus", selectedMobileTab: "chart" }
    })
  );

  const restored = readWorkspaceSnapshot(storage);

  assert.equal(restored.restoreMetadata.status, "restored");
  assert.equal(restored.snapshot.selectedSymbol, "0700.HK");
  assert.equal(restored.snapshot.selectedMobileTab, "source");
  assert.equal(restored.snapshot.layoutBySymbol.AAPL.mode, "dense");
  assert.equal(restored.snapshot.layoutBySymbol["0700.HK"].mode, "mobile_tab");
  assert.equal(restored.snapshot.layoutBySymbol.MSFT, undefined);
  assert.equal(restored.snapshot.globalLayoutFallback.mode, "focus");
});

test("large workspace snapshot remains under storage gate and preserves alert history", () => {
  const symbols = Array.from({ length: 500 }, (_, index): WatchSymbol => ({
    id: `SYM${index}`,
    symbol: `SYM${index}`,
    name: `Symbol ${index}`,
    market: "US",
    status: "active"
  }));
  const history = Array.from({ length: 2000 }, (_, index) => ({
    at: 1_783_000_000_000 + index,
    type: "triggered" as const,
    reason: `large-history-${index}`
  }));
  const snapshot = createWorkspaceSnapshot({
    watchlist: symbols,
    alerts: [{ ...alert("SYM10"), history }],
    selectedSymbol: "SYM10",
    layoutBySymbol: { SYM10: { mode: "dense", selectedMobileTab: "chart" } },
    globalLayoutFallback: { mode: "focus", selectedMobileTab: "chart" }
  });

  const encoded = JSON.stringify(snapshot);

  assert.ok(encoded.length < 2_000_000);
  assert.equal(snapshot.alerts[0]?.history?.length, 2000);
  assert.equal(snapshot.layoutBySymbol.SYM10.mode, "dense");
});
