import { defaultWatchlist } from "../data/markets";
import { normalizeAlertRule } from "./alert";
import type {
  AlertRule,
  ChartLayout,
  MobileWorkbenchTab,
  RangeKey,
  WatchSymbol,
  WorkspaceLayout,
  WorkspaceRestoreMetadata,
  WorkspaceSnapshotV2
} from "../types";

export const WORKSPACE_SNAPSHOT_KEY = "myinvestment.workspace.v2";
export const LEGACY_WATCHLIST_KEY = "myinvestment.watchlist";
export const LEGACY_ALERT_KEY = "myinvestment.alerts";
export const WORKSPACE_STORAGE_LIMIT_BYTES = 2_000_000;

export type WorkspaceStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;

export type WorkspaceRestoreResult = {
  snapshot: WorkspaceSnapshotV2;
  restoreMetadata: WorkspaceRestoreMetadata;
};

type CreateWorkspaceSnapshotInput = {
  watchlist?: WatchSymbol[];
  alerts?: AlertRule[];
  selectedSymbol?: string;
  range?: RangeKey;
  selectedMobileTab?: MobileWorkbenchTab;
  layoutBySymbol?: Record<string, unknown>;
  globalLayoutFallback?: unknown;
  restoreMetadata?: WorkspaceRestoreMetadata;
  updatedAt?: number;
};

const layoutModes: ChartLayout[] = ["dense", "focus", "mobile_tab"];
const mobileTabs: MobileWorkbenchTab[] = ["chart", "source"];
const rangeKeys: RangeKey[] = ["1d", "5d", "1mo", "3mo", "6mo", "1y"];

export const defaultWorkspaceLayout: WorkspaceLayout = {
  mode: "focus",
  selectedMobileTab: "chart"
};

function readJson<T>(storage: WorkspaceStorage, key: string): T | undefined {
  try {
    const value = storage.getItem(key);
    return value ? (JSON.parse(value) as T) : undefined;
  } catch {
    return undefined;
  }
}

export function normalizeWorkspaceSymbol(symbol?: string) {
  return typeof symbol === "string" ? symbol.trim().toUpperCase() : "";
}

function normalizeWatchSymbol(item: WatchSymbol): WatchSymbol {
  return {
    ...item,
    symbol: normalizeWorkspaceSymbol(item.symbol),
    status: item.status ?? "active"
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function normalizeLayout(value: unknown): WorkspaceLayout | undefined {
  if (!isRecord(value)) return undefined;
  const mode = value.mode;
  const selectedMobileTab = value.selectedMobileTab;
  if (!layoutModes.includes(mode as ChartLayout)) return undefined;
  return {
    mode: mode as ChartLayout,
    selectedMobileTab: mobileTabs.includes(selectedMobileTab as MobileWorkbenchTab)
      ? (selectedMobileTab as MobileWorkbenchTab)
      : "chart",
    updatedAt: Number.isFinite(value.updatedAt) ? (value.updatedAt as number) : undefined
  };
}

function normalizeLayoutMap(layoutBySymbol?: Record<string, unknown>) {
  const normalized: Record<string, WorkspaceLayout> = {};
  const discardedLayoutKeys: string[] = [];
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

function normalizeRange(range?: RangeKey) {
  return range && rangeKeys.includes(range) ? range : "6mo";
}

function selectedFromWatchlist(watchlist: WatchSymbol[], selectedSymbol?: string) {
  const normalizedSelected = normalizeWorkspaceSymbol(selectedSymbol);
  const activeSymbols = watchlist.filter((item) => item.status !== "archived");
  if (activeSymbols.some((item) => item.symbol === normalizedSelected)) return normalizedSelected;
  return activeSymbols[0]?.symbol ?? watchlist[0]?.symbol;
}

function normalizeMobileTab(value?: unknown): MobileWorkbenchTab {
  return mobileTabs.includes(value as MobileWorkbenchTab) ? (value as MobileWorkbenchTab) : "chart";
}

function defaultRestoreMetadata(snapshotBytes = 0): WorkspaceRestoreMetadata {
  return {
    status: "restored",
    migratedFromLegacy: false,
    snapshotBytes
  };
}

function withSnapshotBytes(snapshot: WorkspaceSnapshotV2): WorkspaceSnapshotV2 {
  const snapshotBytes = JSON.stringify(snapshot).length;
  return {
    ...snapshot,
    restoreMetadata: {
      ...snapshot.restoreMetadata,
      snapshotBytes
    }
  };
}

function fallbackSnapshot(reason?: string): WorkspaceRestoreResult {
  const snapshot = createWorkspaceSnapshot({
    watchlist: defaultWatchlist,
    alerts: [],
    globalLayoutFallback: defaultWorkspaceLayout,
    restoreMetadata: {
      status: "default_fallback",
      migratedFromLegacy: false,
      reason,
      snapshotBytes: 0
    }
  });
  return {
    snapshot,
    restoreMetadata: snapshot.restoreMetadata
  };
}

export function createWorkspaceSnapshot(input: CreateWorkspaceSnapshotInput): WorkspaceSnapshotV2 {
  const watchlist = (input.watchlist?.length ? input.watchlist : defaultWatchlist).map(normalizeWatchSymbol);
  const alerts = (input.alerts ?? []).map(normalizeAlertRule);
  const { layoutBySymbol } = normalizeLayoutMap(input.layoutBySymbol);
  const fallbackLayout = normalizeLayout(input.globalLayoutFallback) ?? defaultWorkspaceLayout;
  const selectedSymbol = selectedFromWatchlist(watchlist, input.selectedSymbol);
  const selectedLayout = selectedSymbol ? layoutBySymbol[selectedSymbol] ?? fallbackLayout : fallbackLayout;
  const restoreMetadata = input.restoreMetadata ?? defaultRestoreMetadata();

  return withSnapshotBytes({
    version: 2,
    watchlist,
    alerts,
    selectedSymbol,
    range: normalizeRange(input.range),
    selectedMobileTab: normalizeMobileTab(input.selectedMobileTab ?? selectedLayout.selectedMobileTab),
    layoutBySymbol,
    globalLayoutFallback: fallbackLayout,
    restoreMetadata,
    updatedAt: input.updatedAt ?? Date.now()
  });
}

function restoreSnapshot(raw: unknown): WorkspaceRestoreResult {
  if (!isRecord(raw) || raw.version !== 2) return fallbackSnapshot("snapshot_version_invalid");
  const { layoutBySymbol, discardedLayoutKeys } = normalizeLayoutMap(raw.layoutBySymbol as Record<string, unknown>);
  const fallbackLayout = normalizeLayout(raw.globalLayoutFallback);
  const status =
    discardedLayoutKeys.length > 0 || !fallbackLayout
      ? "default_fallback"
      : "restored";
  const restoreMetadata: WorkspaceRestoreMetadata = {
    status,
    migratedFromLegacy: false,
    reason: status === "default_fallback" ? "invalid_layout_fallback" : undefined,
    discardedLayoutKeys,
    snapshotBytes: 0
  };
  const snapshot = createWorkspaceSnapshot({
    watchlist: Array.isArray(raw.watchlist) ? (raw.watchlist as WatchSymbol[]) : defaultWatchlist,
    alerts: Array.isArray(raw.alerts) ? (raw.alerts as AlertRule[]) : [],
    selectedSymbol: typeof raw.selectedSymbol === "string" ? raw.selectedSymbol : undefined,
    range: raw.range as RangeKey | undefined,
    selectedMobileTab: normalizeMobileTab(raw.selectedMobileTab),
    layoutBySymbol,
    globalLayoutFallback: fallbackLayout ?? defaultWorkspaceLayout,
    restoreMetadata,
    updatedAt: Number.isFinite(raw.updatedAt) ? (raw.updatedAt as number) : Date.now()
  });

  return {
    snapshot,
    restoreMetadata: snapshot.restoreMetadata
  };
}

function migrateLegacy(storage: WorkspaceStorage): WorkspaceRestoreResult | undefined {
  const legacyWatchlist = readJson<WatchSymbol[]>(storage, LEGACY_WATCHLIST_KEY);
  const legacyAlerts = readJson<AlertRule[]>(storage, LEGACY_ALERT_KEY);
  if (!legacyWatchlist && !legacyAlerts) return undefined;

  const snapshot = createWorkspaceSnapshot({
    watchlist: legacyWatchlist,
    alerts: legacyAlerts,
    globalLayoutFallback: defaultWorkspaceLayout,
    restoreMetadata: {
      status: "partial",
      migratedFromLegacy: true,
      reason: "legacy_keys_migrated",
      snapshotBytes: 0
    }
  });
  writeWorkspaceSnapshot(storage, snapshot);
  return {
    snapshot,
    restoreMetadata: snapshot.restoreMetadata
  };
}

export function readWorkspaceSnapshot(storage: WorkspaceStorage): WorkspaceRestoreResult {
  const stored = storage.getItem(WORKSPACE_SNAPSHOT_KEY);
  if (!stored) return migrateLegacy(storage) ?? fallbackSnapshot("snapshot_missing");

  let parsed: unknown;
  try {
    parsed = JSON.parse(stored);
  } catch {
    return migrateLegacy(storage) ?? fallbackSnapshot("snapshot_corrupt_json");
  }

  const restored = !isRecord(parsed) || parsed.version !== 2 ? migrateLegacy(storage) ?? restoreSnapshot(parsed) : restoreSnapshot(parsed);
  if (restored.restoreMetadata.snapshotBytes > WORKSPACE_STORAGE_LIMIT_BYTES) {
    return fallbackSnapshot("snapshot_exceeds_storage_gate");
  }
  return restored;
}

export function writeWorkspaceSnapshot(storage: WorkspaceStorage, snapshot: WorkspaceSnapshotV2) {
  const normalized = createWorkspaceSnapshot(snapshot);
  const encoded = JSON.stringify(normalized);
  if (encoded.length > WORKSPACE_STORAGE_LIMIT_BYTES) {
    throw new Error("workspace snapshot exceeds storage gate");
  }
  storage.setItem(WORKSPACE_SNAPSHOT_KEY, encoded);
  storage.setItem(LEGACY_WATCHLIST_KEY, JSON.stringify(normalized.watchlist));
  storage.setItem(LEGACY_ALERT_KEY, JSON.stringify(normalized.alerts));
}

export function getLayoutForSymbol(snapshot: WorkspaceSnapshotV2, symbol: string): WorkspaceLayout {
  return snapshot.layoutBySymbol[normalizeWorkspaceSymbol(symbol)] ?? snapshot.globalLayoutFallback ?? defaultWorkspaceLayout;
}

export function withSymbolLayout(snapshot: WorkspaceSnapshotV2, symbol: string, layout: WorkspaceLayout): WorkspaceSnapshotV2 {
  const normalizedSymbol = normalizeWorkspaceSymbol(symbol);
  return createWorkspaceSnapshot({
    ...snapshot,
    layoutBySymbol: {
      ...snapshot.layoutBySymbol,
      [normalizedSymbol]: {
        ...layout,
        updatedAt: layout.updatedAt ?? Date.now()
      }
    },
    updatedAt: Date.now()
  });
}
