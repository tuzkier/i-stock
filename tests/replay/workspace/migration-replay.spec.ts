import assert from "node:assert/strict";
import test from "node:test";
import corpus from "../../../fixtures/workspace/migration-cases.json";
import {
  LEGACY_ALERT_KEY,
  LEGACY_WATCHLIST_KEY,
  WORKSPACE_SNAPSHOT_KEY,
  readWorkspaceSnapshot
} from "../../../src/domain/workspace";

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

test("workspace migration replay corpus covers legacy, corrupt and per-symbol layout recovery", () => {
  for (const item of corpus.cases) {
    const storage = new MemoryStorage();
    if ("legacyWatchlist" in item) storage.setItem(LEGACY_WATCHLIST_KEY, JSON.stringify(item.legacyWatchlist));
    if ("legacyAlerts" in item) storage.setItem(LEGACY_ALERT_KEY, JSON.stringify(item.legacyAlerts));
    if ("workspaceRaw" in item) storage.setItem(WORKSPACE_SNAPSHOT_KEY, item.workspaceRaw);
    if ("workspace" in item) storage.setItem(WORKSPACE_SNAPSHOT_KEY, JSON.stringify(item.workspace));

    const restored = readWorkspaceSnapshot(storage);

    assert.equal(restored.restoreMetadata.status, item.expectedStatus, item.id);
    if ("expectedSelectedSymbol" in item) assert.equal(restored.snapshot.selectedSymbol, item.expectedSelectedSymbol);
    if ("expectedLayout" in item) assert.equal(restored.snapshot.globalLayoutFallback.mode, item.expectedLayout);
    if ("expectedHistory" in item) {
      assert.deepEqual(restored.snapshot.alerts[0]?.history?.map((event) => event.type), item.expectedHistory);
    }
    if ("expectedLayoutBySymbol" in item) {
      for (const [symbol, mode] of Object.entries(item.expectedLayoutBySymbol)) {
        assert.equal(restored.snapshot.layoutBySymbol[symbol]?.mode, mode);
      }
    }
  }
});
