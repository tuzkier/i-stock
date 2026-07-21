var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __esm = (fn, res) => function __init() {
  return fn && (res = (0, fn[__getOwnPropNames(fn)[0]])(fn = 0)), res;
};
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// src/domain/market-normalization.ts
var init_market_normalization = __esm({
  "src/domain/market-normalization.ts"() {
    "use strict";
  }
});

// src/data/markets.ts
var defaultWatchlist;
var init_markets = __esm({
  "src/data/markets.ts"() {
    "use strict";
    init_market_normalization();
    defaultWatchlist = [
      { id: "AAPL", symbol: "AAPL", name: "Apple", market: "US", status: "active" },
      { id: "0700.HK", symbol: "0700.HK", name: "\u817E\u8BAF\u63A7\u80A1", market: "HK", status: "active" },
      { id: "600519.SS", symbol: "600519.SS", name: "\u8D35\u5DDE\u8305\u53F0", market: "CN", status: "active" },
      { id: "005930.KS", symbol: "005930.KS", name: "Samsung Electronics", market: "KR", status: "active" }
    ];
  }
});

// src/domain/alert.ts
function normalizeAlertRule(rule) {
  const taxonomy = rule.taxonomy ?? (rule.signal ? "mts" : "price");
  const activationState = rule.activationState ?? (rule.enabled ? "enabled" : "disabled");
  const triggerState = rule.triggerState ?? (rule.lastTriggeredAt ? "triggered" : "idle");
  return {
    ...rule,
    taxonomy,
    level: rule.level ?? (rule.signal ? "\u5F3A\u4FE1\u53F7" : "\u89C2\u5BDF"),
    condition: rule.condition ?? (rule.signal ? { kind: "mts", mtsAlertLevel: rule.signal === "strong-sell" || rule.signal === "strong-buy" ? "high" : "elevated" } : { kind: "price", direction: rule.direction, threshold: rule.price }),
    activationState,
    triggerState,
    enabled: activationState === "enabled",
    history: rule.history ?? []
  };
}
var init_alert = __esm({
  "src/domain/alert.ts"() {
    "use strict";
  }
});

// src/domain/workspace.ts
function readJson(storage2, key) {
  try {
    const value = storage2.getItem(key);
    return value ? JSON.parse(value) : void 0;
  } catch {
    return void 0;
  }
}
function normalizeWorkspaceSymbol(symbol) {
  return typeof symbol === "string" ? symbol.trim().toUpperCase() : "";
}
function normalizeWatchSymbol(item) {
  return {
    ...item,
    symbol: normalizeWorkspaceSymbol(item.symbol),
    status: item.status ?? "active"
  };
}
function isRecord(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
function normalizeLayout(value) {
  if (!isRecord(value)) return void 0;
  const mode = value.mode;
  const selectedMobileTab = value.selectedMobileTab;
  if (!layoutModes.includes(mode)) return void 0;
  return {
    mode,
    selectedMobileTab: mobileTabs.includes(selectedMobileTab) ? selectedMobileTab : "chart",
    updatedAt: Number.isFinite(value.updatedAt) ? value.updatedAt : void 0
  };
}
function normalizeLayoutMap(layoutBySymbol) {
  const normalized = {};
  const discardedLayoutKeys = [];
  for (const [rawSymbol, rawLayout] of Object.entries(layoutBySymbol ?? {})) {
    const symbol = normalizeWorkspaceSymbol(rawSymbol);
    const layout = normalizeLayout(rawLayout);
    if (!symbol || !layout) {
      if (rawSymbol) discardedLayoutKeys.push(rawSymbol);
      continue;
    }
    normalized[symbol] = layout;
  }
  return { layoutBySymbol: normalized, discardedLayoutKeys };
}
function normalizeRange(range) {
  return range && rangeKeys.includes(range) ? range : "6mo";
}
function selectedFromWatchlist(watchlist, selectedSymbol) {
  const normalizedSelected = normalizeWorkspaceSymbol(selectedSymbol);
  const activeSymbols = watchlist.filter((item) => item.status !== "archived");
  if (activeSymbols.some((item) => item.symbol === normalizedSelected)) return normalizedSelected;
  return activeSymbols[0]?.symbol ?? watchlist[0]?.symbol;
}
function fallbackSnapshot(reason) {
  const snapshot = createWorkspaceSnapshot({
    watchlist: defaultWatchlist,
    alerts: [],
    globalLayoutFallback: defaultWorkspaceLayout
  });
  return {
    snapshot,
    restoreMetadata: {
      status: "default_fallback",
      migratedFromLegacy: false,
      reason,
      snapshotBytes: JSON.stringify(snapshot).length
    }
  };
}
function createWorkspaceSnapshot(input) {
  const watchlist = (input.watchlist?.length ? input.watchlist : defaultWatchlist).map(normalizeWatchSymbol);
  const alerts = (input.alerts ?? []).map(normalizeAlertRule);
  const { layoutBySymbol } = normalizeLayoutMap(input.layoutBySymbol);
  const fallbackLayout = normalizeLayout(input.globalLayoutFallback) ?? defaultWorkspaceLayout;
  return {
    version: 2,
    watchlist,
    alerts,
    selectedSymbol: selectedFromWatchlist(watchlist, input.selectedSymbol),
    range: normalizeRange(input.range),
    layoutBySymbol,
    globalLayoutFallback: fallbackLayout,
    updatedAt: input.updatedAt ?? Date.now()
  };
}
function restoreSnapshot(raw) {
  if (!isRecord(raw) || raw.version !== 2) return fallbackSnapshot("snapshot_version_invalid");
  const { layoutBySymbol, discardedLayoutKeys } = normalizeLayoutMap(raw.layoutBySymbol);
  const fallbackLayout = normalizeLayout(raw.globalLayoutFallback);
  const status = discardedLayoutKeys.length > 0 || !fallbackLayout ? "default_fallback" : "restored";
  const snapshot = createWorkspaceSnapshot({
    watchlist: Array.isArray(raw.watchlist) ? raw.watchlist : defaultWatchlist,
    alerts: Array.isArray(raw.alerts) ? raw.alerts : [],
    selectedSymbol: typeof raw.selectedSymbol === "string" ? raw.selectedSymbol : void 0,
    range: raw.range,
    layoutBySymbol,
    globalLayoutFallback: fallbackLayout ?? defaultWorkspaceLayout,
    updatedAt: Number.isFinite(raw.updatedAt) ? raw.updatedAt : Date.now()
  });
  return {
    snapshot,
    restoreMetadata: {
      status,
      migratedFromLegacy: false,
      reason: status === "default_fallback" ? "invalid_layout_fallback" : void 0,
      discardedLayoutKeys,
      snapshotBytes: JSON.stringify(snapshot).length
    }
  };
}
function migrateLegacy(storage2) {
  const legacyWatchlist = readJson(storage2, LEGACY_WATCHLIST_KEY);
  const legacyAlerts = readJson(storage2, LEGACY_ALERT_KEY);
  if (!legacyWatchlist && !legacyAlerts) return void 0;
  const snapshot = createWorkspaceSnapshot({
    watchlist: legacyWatchlist,
    alerts: legacyAlerts,
    globalLayoutFallback: defaultWorkspaceLayout
  });
  writeWorkspaceSnapshot(storage2, snapshot);
  return {
    snapshot,
    restoreMetadata: {
      status: "partial",
      migratedFromLegacy: true,
      reason: "legacy_keys_migrated",
      snapshotBytes: JSON.stringify(snapshot).length
    }
  };
}
function readWorkspaceSnapshot(storage2) {
  const stored = storage2.getItem(WORKSPACE_SNAPSHOT_KEY);
  if (!stored) return migrateLegacy(storage2) ?? fallbackSnapshot("snapshot_missing");
  let parsed;
  try {
    parsed = JSON.parse(stored);
  } catch {
    return fallbackSnapshot("snapshot_corrupt_json");
  }
  const restored = restoreSnapshot(parsed);
  if (restored.restoreMetadata.snapshotBytes > WORKSPACE_STORAGE_LIMIT_BYTES) {
    return fallbackSnapshot("snapshot_exceeds_storage_gate");
  }
  return restored;
}
function writeWorkspaceSnapshot(storage2, snapshot) {
  const normalized = createWorkspaceSnapshot(snapshot);
  const encoded = JSON.stringify(normalized);
  if (encoded.length > WORKSPACE_STORAGE_LIMIT_BYTES) {
    throw new Error("workspace snapshot exceeds storage gate");
  }
  storage2.setItem(WORKSPACE_SNAPSHOT_KEY, encoded);
  storage2.setItem(LEGACY_WATCHLIST_KEY, JSON.stringify(normalized.watchlist));
  storage2.setItem(LEGACY_ALERT_KEY, JSON.stringify(normalized.alerts));
}
var WORKSPACE_SNAPSHOT_KEY, LEGACY_WATCHLIST_KEY, LEGACY_ALERT_KEY, WORKSPACE_STORAGE_LIMIT_BYTES, layoutModes, mobileTabs, rangeKeys, defaultWorkspaceLayout;
var init_workspace = __esm({
  "src/domain/workspace.ts"() {
    "use strict";
    init_markets();
    init_alert();
    WORKSPACE_SNAPSHOT_KEY = "myinvestment.workspace.v2";
    LEGACY_WATCHLIST_KEY = "myinvestment.watchlist";
    LEGACY_ALERT_KEY = "myinvestment.alerts";
    WORKSPACE_STORAGE_LIMIT_BYTES = 45e5;
    layoutModes = ["dense", "focus", "mobile_tab"];
    mobileTabs = ["chart", "source"];
    rangeKeys = ["1d", "5d", "1mo", "3mo", "6mo", "1y"];
    defaultWorkspaceLayout = {
      mode: "focus",
      selectedMobileTab: "chart"
    };
  }
});

// src/lib/storage.ts
var storage_exports = {};
__export(storage_exports, {
  readAlerts: () => readAlerts,
  readWatchlist: () => readWatchlist,
  readWorkspace: () => readWorkspace,
  writeAlerts: () => writeAlerts,
  writeWatchlist: () => writeWatchlist,
  writeWorkspace: () => writeWorkspace
});
function readJson2(key, fallback) {
  try {
    const value = window.localStorage.getItem(key);
    return value ? JSON.parse(value) : fallback;
  } catch {
    return fallback;
  }
}
function normalizeWatchSymbol2(item) {
  return {
    ...item,
    status: item.status ?? "active"
  };
}
function normalizeAlertRule2(rule) {
  const activationState = rule.activationState ?? (rule.enabled ? "enabled" : "disabled");
  return {
    ...rule,
    activationState,
    enabled: activationState === "enabled"
  };
}
function readWatchlist() {
  const value = readJson2(watchlistKey, defaultWatchlist);
  return value.map(normalizeWatchSymbol2);
}
function writeWatchlist(value) {
  window.localStorage.setItem(watchlistKey, JSON.stringify(value));
}
function readAlerts() {
  return readJson2(alertKey, []).map(normalizeAlertRule2);
}
function writeAlerts(value) {
  window.localStorage.setItem(alertKey, JSON.stringify(value));
}
function readWorkspace() {
  return readWorkspaceSnapshot(window.localStorage);
}
function writeWorkspace(value) {
  writeWorkspaceSnapshot(window.localStorage, value);
}
var watchlistKey, alertKey;
var init_storage = __esm({
  "src/lib/storage.ts"() {
    "use strict";
    init_markets();
    init_workspace();
    watchlistKey = "myinvestment.watchlist";
    alertKey = "myinvestment.alerts";
  }
});

// tests/unit/watchlist/storage-replay.spec.ts
import assert from "node:assert/strict";
import { beforeEach, describe, it } from "node:test";
function installLocalStorage() {
  const store = /* @__PURE__ */ new Map();
  const localStorage2 = {
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
  globalThis.window = { localStorage: localStorage2 };
  return localStorage2;
}
var localStorage = installLocalStorage();
var storage = (init_storage(), __toCommonJS(storage_exports));
describe("watchlist localStorage replay", () => {
  beforeEach(() => {
    localStorage.clear();
  });
  it("replays archived symbols and suspended alert restore intent from localStorage", () => {
    const watchlist = [
      { id: "9988.HK", symbol: "9988.HK", name: "\u963F\u91CC\u5DF4\u5DF4", market: "HK", status: "archived", archivedAt: 123 }
    ];
    const alerts = [
      {
        id: "alert-1",
        symbol: "9988.HK",
        label: "9988.HK \u89E6\u53D1 strong-sell",
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
      JSON.stringify([{ id: "alert-legacy", symbol: "AAPL", label: "AAPL \u4E0A\u7A7F 200", direction: "above", price: 200, enabled: true }])
    );
    assert.equal(storage.readWatchlist()[0].status, "active");
    assert.equal(storage.readAlerts()[0].activationState, "enabled");
  });
  it("keeps legacy disabled alerts disabled during replay", () => {
    localStorage.setItem(
      "myinvestment.alerts",
      JSON.stringify([
        { id: "alert-disabled", symbol: "AAPL", label: "AAPL \u4E0A\u7A7F 200", direction: "above", price: 200, enabled: false }
      ])
    );
    const replayedAlerts = storage.readAlerts();
    assert.equal(replayedAlerts[0].enabled, false);
    assert.equal(replayedAlerts[0].activationState, "disabled");
  });
});
