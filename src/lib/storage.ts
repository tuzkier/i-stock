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

// 种子自选：确保用户实际持仓的标的都在自选列表中（任一写法已存在则不重复添加）。
// 注：持仓中的期权（如 HK.TCH260730P430000）不种入——K 线行情接口不适用衍生品。
const seedWatchSymbols: WatchSymbol[] = [
  { id: "HK.09988", symbol: "HK.09988", name: "阿里巴巴-W", market: "HK", status: "active" },
  { id: "HK.00700", symbol: "HK.00700", name: "腾讯控股", market: "HK", status: "active" },
  { id: "HK.03690", symbol: "HK.03690", name: "美团-W", market: "HK", status: "active" },
  { id: "HK.01810", symbol: "HK.01810", name: "小米集团-W", market: "HK", status: "active" },
  { id: "HK.00981", symbol: "HK.00981", name: "中芯国际", market: "HK", status: "active" },
  { id: "HK.01888", symbol: "HK.01888", name: "建滔积层板", market: "HK", status: "active" },
  { id: "HK.07709", symbol: "HK.07709", name: "南方两倍做多海力士", market: "HK", status: "active" },
  { id: "US.SPCX", symbol: "US.SPCX", name: "SpaceX", market: "US", status: "active" }
];

// 同一标的的不同写法归一到一个 key：HK 代码取数字部分（HK.00700 / 0700.HK / 700.HK 视为同一只）。
function symbolKey(symbol: string): string {
  const normalized = symbol.trim().toUpperCase().replace(/\s+/g, "");
  const hk = normalized.match(/^HK\.(\d+)$/) ?? normalized.match(/^(\d+)\.HK$/);
  if (hk) return `HK:${Number.parseInt(hk[1], 10)}`;
  return normalized;
}

function ensureSeedSymbols(watchlist: WatchSymbol[]): WatchSymbol[] {
  const existing = new Set(watchlist.map((item) => symbolKey(item.symbol)));
  const additions = seedWatchSymbols.filter((seed) => !existing.has(symbolKey(seed.symbol)));
  return additions.length > 0 ? [...watchlist, ...additions] : watchlist;
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
