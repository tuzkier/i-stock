// tests/replay/workspace/migration-replay.spec.ts
import assert from "node:assert/strict";
import test from "node:test";

// fixtures/workspace/migration-cases.json
var migration_cases_default = {
  version: 1,
  cases: [
    {
      id: "legacy-watchlist-alerts-to-v2",
      legacyWatchlist: [
        { id: "AAPL", symbol: "AAPL", name: "Apple", market: "US", status: "active" }
      ],
      legacyAlerts: [
        {
          id: "alert-aapl",
          symbol: "AAPL",
          label: "AAPL \u4EF7\u683C\u63D0\u9192",
          direction: "above",
          price: 190,
          enabled: true,
          activationState: "enabled",
          triggerState: "acknowledged",
          history: [
            { at: 1783e9, type: "triggered", reason: "fixture trigger" },
            { at: 1783000001e3, type: "acknowledged", reason: "fixture ack" }
          ]
        }
      ],
      expectedStatus: "partial",
      expectedSelectedSymbol: "AAPL",
      expectedHistory: ["triggered", "acknowledged"]
    },
    {
      id: "corrupt-json-default-fallback",
      workspaceRaw: "{bad json",
      expectedStatus: "default_fallback",
      expectedLayout: "focus"
    },
    {
      id: "per-symbol-layout-normalization",
      workspace: {
        version: 2,
        watchlist: [
          { id: "AAPL", symbol: "AAPL", name: "Apple", market: "US", status: "active" },
          { id: "0700.HK", symbol: "0700.HK", name: "\u817E\u8BAF\u63A7\u80A1", market: "HK", status: "active" }
        ],
        alerts: [],
        selectedSymbol: "0700.hk",
        layoutBySymbol: {
          AAPL: { mode: "dense", selectedMobileTab: "chart" },
          "0700.hk": { mode: "mobile_tab", selectedMobileTab: "source" }
        },
        globalLayoutFallback: { mode: "focus", selectedMobileTab: "chart" },
        updatedAt: 1783e9
      },
      expectedStatus: "restored",
      expectedSelectedSymbol: "0700.HK",
      expectedLayoutBySymbol: {
        AAPL: "dense",
        "0700.HK": "mobile_tab"
      }
    }
  ]
};

// src/data/markets.ts
var defaultWatchlist = [
  { id: "AAPL", symbol: "AAPL", name: "Apple", market: "US", status: "active" },
  { id: "0700.HK", symbol: "0700.HK", name: "\u817E\u8BAF\u63A7\u80A1", market: "HK", status: "active" },
  { id: "600519.SS", symbol: "600519.SS", name: "\u8D35\u5DDE\u8305\u53F0", market: "CN", status: "active" },
  { id: "005930.KS", symbol: "005930.KS", name: "Samsung Electronics", market: "KR", status: "active" }
];

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

// src/domain/workspace.ts
var WORKSPACE_SNAPSHOT_KEY = "myinvestment.workspace.v2";
var LEGACY_WATCHLIST_KEY = "myinvestment.watchlist";
var LEGACY_ALERT_KEY = "myinvestment.alerts";
var WORKSPACE_STORAGE_LIMIT_BYTES = 45e5;
var layoutModes = ["dense", "focus", "mobile_tab"];
var mobileTabs = ["chart", "source"];
var rangeKeys = ["1d", "5d", "1mo", "3mo", "6mo", "1y"];
var defaultWorkspaceLayout = {
  mode: "focus",
  selectedMobileTab: "chart"
};
function readJson(storage, key) {
  try {
    const value = storage.getItem(key);
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
function migrateLegacy(storage) {
  const legacyWatchlist = readJson(storage, LEGACY_WATCHLIST_KEY);
  const legacyAlerts = readJson(storage, LEGACY_ALERT_KEY);
  if (!legacyWatchlist && !legacyAlerts) return void 0;
  const snapshot = createWorkspaceSnapshot({
    watchlist: legacyWatchlist,
    alerts: legacyAlerts,
    globalLayoutFallback: defaultWorkspaceLayout
  });
  writeWorkspaceSnapshot(storage, snapshot);
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
function readWorkspaceSnapshot(storage) {
  const stored = storage.getItem(WORKSPACE_SNAPSHOT_KEY);
  if (!stored) return migrateLegacy(storage) ?? fallbackSnapshot("snapshot_missing");
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
function writeWorkspaceSnapshot(storage, snapshot) {
  const normalized = createWorkspaceSnapshot(snapshot);
  const encoded = JSON.stringify(normalized);
  if (encoded.length > WORKSPACE_STORAGE_LIMIT_BYTES) {
    throw new Error("workspace snapshot exceeds storage gate");
  }
  storage.setItem(WORKSPACE_SNAPSHOT_KEY, encoded);
  storage.setItem(LEGACY_WATCHLIST_KEY, JSON.stringify(normalized.watchlist));
  storage.setItem(LEGACY_ALERT_KEY, JSON.stringify(normalized.alerts));
}

// tests/replay/workspace/migration-replay.spec.ts
var MemoryStorage = class {
  values = /* @__PURE__ */ new Map();
  length = 0;
  clear() {
    this.values.clear();
  }
  getItem(key) {
    return this.values.get(key) ?? null;
  }
  key(index) {
    return Array.from(this.values.keys())[index] ?? null;
  }
  removeItem(key) {
    this.values.delete(key);
  }
  setItem(key, value) {
    this.values.set(key, value);
  }
};
test("workspace migration replay corpus covers legacy, corrupt and per-symbol layout recovery", () => {
  for (const item of migration_cases_default.cases) {
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
