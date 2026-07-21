import type { AlertRule, WatchSymbol } from "../types";
import { defaultWatchlist } from "../data/markets";
import {
  readWorkspaceSnapshot,
  writeWorkspaceSnapshot,
  type WorkspaceRestoreResult
} from "../domain/workspace";
import type { WorkspaceSnapshotV2 } from "../types";

const watchlistKey = "myinvestment.watchlist";
const alertKey = "myinvestment.alerts";

function readJson<T>(key: string, fallback: T): T {
  try {
    const value = window.localStorage.getItem(key);
    return value ? (JSON.parse(value) as T) : fallback;
  } catch {
    return fallback;
  }
}

function normalizeWatchSymbol(item: WatchSymbol): WatchSymbol {
  return {
    ...item,
    status: item.status ?? "active"
  };
}

function normalizeAlertRule(rule: AlertRule): AlertRule {
  const activationState = rule.activationState ?? (rule.enabled ? "enabled" : "disabled");
  return {
    ...rule,
    activationState,
    enabled: activationState === "enabled"
  };
}

export function readWatchlist() {
  const value = readJson<WatchSymbol[]>(watchlistKey, defaultWatchlist);
  return value.map(normalizeWatchSymbol);
}

export function writeWatchlist(value: WatchSymbol[]) {
  window.localStorage.setItem(watchlistKey, JSON.stringify(value));
}

export function readAlerts() {
  return readJson<AlertRule[]>(alertKey, []).map(normalizeAlertRule);
}

export function writeAlerts(value: AlertRule[]) {
  window.localStorage.setItem(alertKey, JSON.stringify(value));
}

// 种子自选：确保美团在自选列表中（用户已有任一写法的 3690 时不重复添加）。
const meituanSeed: WatchSymbol = { id: "HK.03690", symbol: "HK.03690", name: "美团-W", market: "HK", status: "active" };

function ensureSeedSymbols(watchlist: WatchSymbol[]): WatchSymbol[] {
  const hasMeituan = watchlist.some((item) => {
    const normalized = item.symbol.trim().toUpperCase().replace(/\s+/g, "");
    return normalized === "HK.03690" || normalized === "HK.3690" || normalized === "03690.HK" || normalized === "3690.HK";
  });
  return hasMeituan ? watchlist : [...watchlist, meituanSeed];
}

export function readWorkspace(): WorkspaceRestoreResult {
  const result = readWorkspaceSnapshot(window.localStorage);
  return {
    ...result,
    snapshot: { ...result.snapshot, watchlist: ensureSeedSymbols(result.snapshot.watchlist) }
  };
}

export function writeWorkspace(value: WorkspaceSnapshotV2) {
  writeWorkspaceSnapshot(window.localStorage, value);
}
