import { execFile } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type {
  MarketDataCacheState,
  MarketDataEnvelope,
  MarketDataRetryState,
  PriceBar,
  PriceSeries,
  RangeKey,
  SourceHealth,
  SourceHealthStatus
} from "../types";

type FutudRequest = {
  symbol: string;
  range: RangeKey;
  host: string;
  port: number;
};

type FutudPayload = {
  symbol: string;
  name?: string;
  market?: string;
  currency?: string;
  bars: PriceBar[];
};

type FutudClient = (request: FutudRequest) => Promise<FutudPayload>;

type MarketDataSourceOptions = {
  forceRefresh?: boolean;
  futudClient?: FutudClient;
  futudHost?: string;
  futudPort?: number;
  futudTimeoutMs?: number;
  pythonBin?: string;
  now?: () => number;
  cacheEnabled?: boolean;
  ttlMs?: number;
  staleMaxAgeMs?: number;
};

export type MarketDataSource = {
  fetchSeries: (
    symbol: string,
    range?: RangeKey | string,
    options?: MarketDataSourceOptions
  ) => Promise<MarketDataEnvelope>;
  clearCache: () => void;
};

type MarketDataSourceConfig = Required<
  Pick<MarketDataSourceOptions, "cacheEnabled" | "ttlMs" | "staleMaxAgeMs" | "futudHost" | "futudPort" | "futudTimeoutMs" | "pythonBin">
> &
  Pick<MarketDataSourceOptions, "futudClient" | "now">;

type CacheEntry = {
  envelope: MarketDataEnvelope;
  fetchedAt: number;
  failureCount: number;
  lastAttemptAt?: number;
};

const RANGE_TO_INTERVAL: Record<RangeKey, string> = {
  "1d": "5m",
  "5d": "15m",
  "1mo": "1d",
  "3mo": "1d",
  "6mo": "1d",
  "1y": "1d"
};

const VALID_RANGES: RangeKey[] = ["1d", "5d", "1mo", "3mo", "6mo", "1y"];
const DEGRADING_AFFECTED_OBJECTS: Array<"chart" | "mts" | "alerts"> = ["chart", "mts", "alerts"];
const FORMAL_AFFECTED_OBJECTS: Array<"chart" | "mts" | "alerts"> = [];
const DEFAULT_TTL_MS = 60_000;
const DEFAULT_STALE_MAX_AGE_MS = 15 * 60_000;
const DEFAULT_FUTUD_HOST = "127.0.0.1";
const DEFAULT_FUTUD_PORT = 11111;
const DEFAULT_FUTUD_TIMEOUT_MS = 15_000;
const DEFAULT_PYTHON_BIN = "python3";
const SOURCE_NAME = "FutuOpenD";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FUTUD_CLIENT_SCRIPT = path.resolve(__dirname, "../../server/futud-client.py");

export function normalizeMarketDataSymbol(rawSymbol = "") {
  return rawSymbol.trim().toUpperCase().replace(/\s+/g, "");
}

export function normalizeMarketDataRange(rawRange: string = "6mo"): RangeKey {
  return VALID_RANGES.includes(rawRange as RangeKey) ? (rawRange as RangeKey) : "6mo";
}

export function marketDataIntervalForRange(range: RangeKey) {
  return RANGE_TO_INTERVAL[range];
}

export function normalizeFutudSymbol(rawSymbol = "") {
  const symbol = normalizeMarketDataSymbol(rawSymbol);

  if (!symbol) return symbol;

  if (/^(US|SH|SZ|KR)\.[A-Z0-9.-]+$/.test(symbol)) return symbol;

  const hkPrefixed = symbol.match(/^HK\.(\d{1,5})$/);
  if (hkPrefixed) return `HK.${hkPrefixed[1].padStart(5, "0")}`;

  const hkSuffix = symbol.match(/^(\d{1,5})\.HK$/);
  if (hkSuffix) return `HK.${hkSuffix[1].padStart(5, "0")}`;

  const shSuffix = symbol.match(/^(\d{6})\.SS$/);
  if (shSuffix) return `SH.${shSuffix[1]}`;

  const szSuffix = symbol.match(/^(\d{6})\.SZ$/);
  if (szSuffix) return `SZ.${szSuffix[1]}`;

  const krSuffix = symbol.match(/^(\d{6})\.KS$/);
  if (krSuffix) return `KR.${krSuffix[1]}`;

  if (/^\d{6}$/.test(symbol)) {
    return symbol.startsWith("6") ? `SH.${symbol}` : `SZ.${symbol}`;
  }

  if (/^\d{1,5}$/.test(symbol)) {
    return `HK.${symbol.padStart(5, "0")}`;
  }

  return `US.${symbol}`;
}

export function createMarketDataSource(defaultOptions: MarketDataSourceOptions = {}): MarketDataSource {
  const cache = new Map<string, CacheEntry>();
  const inflight = new Map<string, Promise<MarketDataEnvelope>>();
  const config: MarketDataSourceConfig = {
    cacheEnabled: defaultOptions.cacheEnabled ?? true,
    ttlMs: defaultOptions.ttlMs ?? DEFAULT_TTL_MS,
    staleMaxAgeMs: defaultOptions.staleMaxAgeMs ?? DEFAULT_STALE_MAX_AGE_MS,
    futudHost: defaultOptions.futudHost ?? process.env.FUTUD_HOST ?? DEFAULT_FUTUD_HOST,
    futudPort: Number(defaultOptions.futudPort ?? process.env.FUTUD_PORT ?? DEFAULT_FUTUD_PORT),
    futudTimeoutMs: defaultOptions.futudTimeoutMs ?? DEFAULT_FUTUD_TIMEOUT_MS,
    pythonBin: defaultOptions.pythonBin ?? process.env.FUTUD_PYTHON_BIN ?? DEFAULT_PYTHON_BIN,
    futudClient: defaultOptions.futudClient,
    now: defaultOptions.now
  };

  return {
    async fetchSeries(symbol, range = "6mo", options = {}) {
      const now = options.now ?? config.now ?? Date.now;
      const nowMs = now();
      const rawSymbol = normalizeMarketDataSymbol(symbol);
      const futudSymbol = normalizeFutudSymbol(rawSymbol);
      const normalizedRange = normalizeMarketDataRange(String(range));
      const interval = marketDataIntervalForRange(normalizedRange);
      const cacheEnabled = options.cacheEnabled ?? config.cacheEnabled;
      const ttlMs = options.ttlMs ?? config.ttlMs;
      const staleMaxAgeMs = options.staleMaxAgeMs ?? config.staleMaxAgeMs;
      const forceRefresh = options.forceRefresh ?? false;
      const cacheKey = buildCacheKey(futudSymbol, normalizedRange, interval);
      const cachedEntry = cache.get(cacheKey);

      if (!rawSymbol) {
        return buildUnavailableEnvelope({
          symbol: rawSymbol,
          range: normalizedRange,
          interval,
          servedAt: nowMs,
          cacheState: cacheEnabled ? (forceRefresh ? "bypass" : "miss") : "disabled",
          reason: "缺少标的代码",
          retryState: buildRetryState(1, nowMs, "缺少标的代码", true)
        });
      }

      if (cacheEnabled && !forceRefresh && cachedEntry && nowMs - cachedEntry.fetchedAt <= ttlMs) {
        return cloneEnvelopeWithState(cachedEntry.envelope, {
          servedAt: nowMs,
          cacheState: "hit",
          sourceHealthStatus: "formal",
          lastRefreshedAt: cachedEntry.fetchedAt,
          retryState: buildRetryState(0, undefined, undefined, false),
          degradationReason: undefined,
          notice: undefined
        });
      }

      const pendingRequest = !forceRefresh ? inflight.get(cacheKey) : undefined;
      if (pendingRequest) {
        return pendingRequest;
      }

      const request = (async () => {
        try {
          const client = options.futudClient ?? config.futudClient ?? defaultFutudClient(config);
          const payload = await client({
            symbol: futudSymbol,
            range: normalizedRange,
            host: options.futudHost ?? config.futudHost,
            port: Number(options.futudPort ?? config.futudPort)
          });
          const bars = normalizeBars(payload.bars);

          if (!bars.length) {
            throw new Error("FutuOpenD 返回了没有可用行情的 payload");
          }

          const envelope = buildFormalEnvelope({
            symbol: rawSymbol,
            range: normalizedRange,
            interval,
            bars,
            meta: normalizeMeta(payload, futudSymbol, bars),
            servedAt: nowMs,
            cacheState: cacheEnabled && forceRefresh ? "bypass" : "miss"
          });

          if (cacheEnabled) {
            cache.set(cacheKey, {
              envelope,
              fetchedAt: nowMs,
              failureCount: 0,
              lastAttemptAt: nowMs
            });
          }

          return envelope;
        } catch (error) {
          const reason = error instanceof Error ? error.message : "未知错误";
          return handleFailure({
            symbol: rawSymbol,
            normalizedRange,
            interval,
            nowMs,
            cachedEntry,
            cacheEnabled,
            staleMaxAgeMs,
            forceRefresh,
            reason
          });
        }
      })();

      if (!forceRefresh) {
        inflight.set(cacheKey, request);
      }

      try {
        return await request;
      } finally {
        if (inflight.get(cacheKey) === request) {
          inflight.delete(cacheKey);
        }
      }
    },
    clearCache() {
      cache.clear();
      inflight.clear();
    }
  };

  function handleFailure({
    symbol,
    normalizedRange,
    interval,
    nowMs,
    cachedEntry,
    cacheEnabled,
    staleMaxAgeMs,
    forceRefresh,
    reason
  }: {
    symbol: string;
    normalizedRange: RangeKey;
    interval: string;
    nowMs: number;
    cachedEntry: CacheEntry | undefined;
    cacheEnabled: boolean;
    staleMaxAgeMs: number;
    forceRefresh: boolean;
    reason: string;
  }) {
    const staleEligible = Boolean(cachedEntry && nowMs - cachedEntry.fetchedAt <= staleMaxAgeMs);

    if (cacheEnabled && staleEligible && cachedEntry) {
      const failureCount = cachedEntry.failureCount + 1;
      cachedEntry.failureCount = failureCount;
      cachedEntry.lastAttemptAt = nowMs;
      return cloneEnvelopeWithState(cachedEntry.envelope, {
        servedAt: nowMs,
        cacheState: "stale_fallback",
        sourceHealthStatus: "stale",
        lastRefreshedAt: cachedEntry.fetchedAt,
        retryState: buildRetryState(failureCount, nowMs, reason, true),
        degradationReason: buildStaleReason(reason),
        notice: buildNotice("stale", reason)
      });
    }

    const cacheState: MarketDataCacheState = cacheEnabled
      ? forceRefresh
        ? "bypass"
        : "miss"
      : "disabled";

    return buildUnavailableEnvelope({
      symbol,
      range: normalizedRange,
      interval,
      servedAt: nowMs,
      cacheState,
      reason,
      retryState: buildRetryState(1, nowMs, reason, true)
    });
  }
}

function defaultFutudClient(config: Pick<MarketDataSourceConfig, "pythonBin" | "futudTimeoutMs">): FutudClient {
  return (request) =>
    new Promise((resolve, reject) => {
      execFile(
        config.pythonBin,
        [
          FUTUD_CLIENT_SCRIPT,
          "--symbol",
          request.symbol,
          "--range",
          request.range,
          "--host",
          request.host,
          "--port",
          String(request.port)
        ],
        {
          env: {
            ...process.env,
            PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION: "python"
          },
          timeout: config.futudTimeoutMs,
          maxBuffer: 1024 * 1024
        },
        (error, stdout, stderr) => {
          if (error) {
            reject(new Error(stderr.trim() || error.message));
            return;
          }

          try {
            const payload = JSON.parse(stdout.trim()) as FutudPayload & { error?: string };
            if (payload.error) {
              reject(new Error(payload.error));
              return;
            }
            resolve(payload);
          } catch (parseError) {
            reject(parseError instanceof Error ? parseError : new Error("FutuOpenD 响应解析失败"));
          }
        }
      );
    });
}

function normalizeBars(bars: PriceBar[] = []) {
  return bars
    .map((bar) => ({
      time: Number(bar.time),
      open: Number(bar.open),
      high: Number(bar.high),
      low: Number(bar.low),
      close: Number(bar.close),
      volume: Number(bar.volume ?? 0)
    }))
    .filter((bar): bar is PriceBar =>
      Number.isFinite(bar.time) &&
      Number.isFinite(bar.open) &&
      Number.isFinite(bar.high) &&
      Number.isFinite(bar.low) &&
      Number.isFinite(bar.close) &&
      Number.isFinite(bar.volume)
    );
}

function buildFormalEnvelope({
  symbol,
  range,
  interval,
  bars,
  meta,
  servedAt,
  cacheState
}: {
  symbol: string;
  range: RangeKey;
  interval: string;
  bars: PriceBar[];
  meta: MarketDataEnvelope["meta"];
  servedAt: number;
  cacheState: MarketDataCacheState;
}): MarketDataEnvelope {
  const retryState = buildRetryState(0, servedAt, undefined, false);
  const priceSeries = buildPriceSeries(symbol, range, interval, bars);
  return {
    symbol,
    range,
    interval,
    meta,
    priceSeries,
    bars: priceSeries.bars,
    servedAt,
    cacheState,
    sourceHealth: buildSourceHealth({
      status: "formal",
      lastRefreshedAt: servedAt,
      retryState,
      degradationReason: undefined,
      affectedObjects: FORMAL_AFFECTED_OBJECTS
    }),
    sourceName: SOURCE_NAME,
    degradationReason: undefined,
    lastRefreshedAt: servedAt,
    retryState,
    dataSource: "futud"
  };
}

function buildUnavailableEnvelope({
  symbol,
  range,
  interval,
  servedAt,
  cacheState,
  reason,
  retryState
}: {
  symbol: string;
  range: RangeKey;
  interval: string;
  servedAt: number;
  cacheState: MarketDataCacheState;
  reason: string;
  retryState: MarketDataRetryState;
}): MarketDataEnvelope {
  const priceSeries = buildPriceSeries(symbol, range, interval, []);
  return {
    symbol,
    range,
    interval,
    meta: buildUnavailableMeta(symbol),
    priceSeries,
    bars: [],
    servedAt,
    cacheState,
    sourceHealth: buildSourceHealth({
      status: "unavailable",
      lastRefreshedAt: undefined,
      retryState,
      degradationReason: reason,
      affectedObjects: DEGRADING_AFFECTED_OBJECTS
    }),
    sourceName: SOURCE_NAME,
    degradationReason: reason,
    lastRefreshedAt: undefined,
    retryState,
    dataSource: "futud",
    notice: buildNotice("unavailable", reason)
  };
}

function buildSourceHealth({
  status,
  retryState,
  lastRefreshedAt,
  degradationReason,
  affectedObjects
}: {
  status: SourceHealthStatus;
  retryState: MarketDataRetryState;
  lastRefreshedAt?: number;
  degradationReason?: string;
  affectedObjects: Array<"chart" | "mts" | "alerts">;
}): SourceHealth {
  return {
    status,
    affectedObjects,
    retryState,
    lastRefreshedAt,
    degradationReason
  };
}

function buildPriceSeries(symbol: string, range: RangeKey, interval: string, bars: PriceBar[]): PriceSeries {
  const latestBar = bars.at(-1);
  const previousBar = bars.at(-2);
  const latestPrice = latestBar?.close;
  const basis = previousBar?.close ?? latestBar?.open;

  return {
    symbol,
    range,
    interval,
    bars,
    latestOhlc: latestBar
      ? {
          time: latestBar.time,
          open: latestBar.open,
          high: latestBar.high,
          low: latestBar.low,
          close: latestBar.close
        }
      : undefined,
    latestPrice,
    changeSummary:
      basis && latestPrice !== undefined
        ? {
            absolute: latestPrice - basis,
            percent: basis !== 0 ? ((latestPrice - basis) / basis) * 100 : undefined
          }
        : undefined
  };
}

function normalizeMeta(payload: FutudPayload, symbol: string, bars: PriceBar[]): MarketDataEnvelope["meta"] {
  return {
    currency: payload.currency ?? inferCurrency(symbol),
    exchangeName: SOURCE_NAME,
    fullExchangeName: `${SOURCE_NAME} local market data`,
    shortName: payload.name ?? payload.symbol ?? symbol,
    regularMarketPrice: bars.at(-1)?.close,
    previousClose: bars.at(-2)?.close,
    regularMarketTime: bars.at(-1)?.time,
    timezone: "UTC"
  };
}

function buildUnavailableMeta(symbol: string): MarketDataEnvelope["meta"] {
  return {
    shortName: symbol,
    currency: inferCurrency(symbol),
    exchangeName: SOURCE_NAME,
    fullExchangeName: `${SOURCE_NAME} local market data`,
    timezone: "UTC"
  };
}

function inferCurrency(symbol: string) {
  if (symbol.startsWith("HK.")) return "HKD";
  if (symbol.startsWith("SH.") || symbol.startsWith("SZ.")) return "CNY";
  if (symbol.startsWith("KR.")) return "KRW";
  return "USD";
}

function buildNotice(status: Exclude<SourceHealthStatus, "formal" | "demo_fallback">, reason: string) {
  if (status === "stale") {
    return `FutuOpenD 行情已过期，当前显示上次成功缓存：${reason}`;
  }

  return `FutuOpenD 行情不可用：${reason}`;
}

function buildStaleReason(reason: string) {
  return `FutuOpenD 请求失败，已使用上次成功缓存：${reason}`;
}

function buildRetryState(
  attempt: number,
  lastAttemptAt: number | undefined,
  reason: string | undefined,
  canRetry: boolean
): MarketDataRetryState {
  return {
    attempt,
    canRetry,
    lastAttemptAt,
    nextRetryAt: canRetry && lastAttemptAt !== undefined ? lastAttemptAt + Math.min(60_000, 15_000 * Math.max(1, attempt)) : undefined,
    reason
  };
}

function buildCacheKey(symbol: string, range: RangeKey, interval: string) {
  return `${symbol}::${range}::${interval}::futud`;
}

function cloneEnvelopeWithState(
  envelope: MarketDataEnvelope,
  patch: {
    servedAt: number;
    cacheState: MarketDataCacheState;
    sourceHealthStatus: SourceHealthStatus;
    lastRefreshedAt?: number;
    retryState: MarketDataRetryState;
    degradationReason?: string;
    notice?: string;
  }
): MarketDataEnvelope {
  const bars = cloneBars(envelope.bars);
  const priceSeries = clonePriceSeries(envelope.priceSeries, bars);
  const sourceHealth = buildSourceHealth({
    status: patch.sourceHealthStatus,
    affectedObjects:
      patch.sourceHealthStatus === "formal" ? FORMAL_AFFECTED_OBJECTS : DEGRADING_AFFECTED_OBJECTS,
    retryState: patch.retryState,
    lastRefreshedAt: patch.lastRefreshedAt,
    degradationReason: patch.degradationReason
  });

  return {
    ...envelope,
    bars,
    priceSeries,
    servedAt: patch.servedAt,
    cacheState: patch.cacheState,
    sourceHealth,
    sourceName: SOURCE_NAME,
    degradationReason: patch.degradationReason,
    lastRefreshedAt: patch.lastRefreshedAt,
    retryState: patch.retryState,
    dataSource: "futud",
    notice: patch.notice
  };
}

function clonePriceSeries(priceSeries: PriceSeries, bars: PriceBar[]): PriceSeries {
  return {
    ...priceSeries,
    bars,
    latestOhlc: priceSeries.latestOhlc ? { ...priceSeries.latestOhlc } : undefined,
    changeSummary: priceSeries.changeSummary ? { ...priceSeries.changeSummary } : undefined
  };
}

function cloneBars(bars: PriceBar[]) {
  return bars.map((bar) => ({ ...bar }));
}
