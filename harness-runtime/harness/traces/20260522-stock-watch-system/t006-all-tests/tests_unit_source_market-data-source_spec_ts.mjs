// tests/unit/source/market-data-source.spec.ts
import assert from "node:assert/strict";
import { describe, it } from "node:test";

// src/domain/market-data-source.ts
var RANGE_TO_INTERVAL = {
  "1d": "5m",
  "5d": "15m",
  "1mo": "1d",
  "3mo": "1d",
  "6mo": "1d",
  "1y": "1d"
};
var VALID_RANGES = ["1d", "5d", "1mo", "3mo", "6mo", "1y"];
var DEGRADING_AFFECTED_OBJECTS = ["chart", "mts", "alerts"];
var FORMAL_AFFECTED_OBJECTS = [];
var DEFAULT_TTL_MS = 6e4;
var DEFAULT_STALE_MAX_AGE_MS = 15 * 6e4;
function normalizeMarketDataSymbol(rawSymbol = "") {
  return rawSymbol.trim().toUpperCase().replace(/\s+/g, "");
}
function normalizeMarketDataRange(rawRange = "6mo") {
  return VALID_RANGES.includes(rawRange) ? rawRange : "6mo";
}
function marketDataIntervalForRange(range) {
  return RANGE_TO_INTERVAL[range];
}
function compactBars(result) {
  const quote = result.indicators?.quote?.[0];
  if (!quote || !Array.isArray(result.timestamp)) {
    return [];
  }
  return result.timestamp.map((timestamp, index) => ({
    time: timestamp,
    open: quote.open?.[index],
    high: quote.high?.[index],
    low: quote.low?.[index],
    close: quote.close?.[index],
    volume: quote.volume?.[index] ?? 0
  })).filter(
    (bar) => Number.isFinite(bar.time) && Number.isFinite(bar.open) && Number.isFinite(bar.high) && Number.isFinite(bar.low) && Number.isFinite(bar.close) && Number.isFinite(bar.volume)
  );
}
function generateFallbackBars(symbol, range, nowMs = Date.now()) {
  const countByRange = {
    "1d": 78,
    "5d": 130,
    "1mo": 22,
    "3mo": 66,
    "6mo": 132,
    "1y": 252
  };
  const stepByRange = {
    "1d": 5 * 60,
    "5d": 15 * 60,
    "1mo": 24 * 60 * 60,
    "3mo": 24 * 60 * 60,
    "6mo": 24 * 60 * 60,
    "1y": 24 * 60 * 60
  };
  const seed = symbol.split("").reduce((sum, char) => sum + char.charCodeAt(0), 0);
  const random = seededRandom(seed || 1);
  const count = countByRange[range] ?? 132;
  const step = stepByRange[range] ?? 24 * 60 * 60;
  const nowSeconds = Math.floor(nowMs / 1e3);
  const base = symbol.includes(".HK") ? 320 : symbol.includes(".KS") ? 7e4 : symbol.includes(".SS") || symbol.includes(".SZ") ? 60 : 180;
  let close = base * (0.85 + random() * 0.3);
  return Array.from({ length: count }, (_, index) => {
    const drift = Math.sin((index + seed) / 13) * 6e-3;
    const shock = (random() - 0.5) * 0.025;
    const open = close;
    close = Math.max(0.01, close * (1 + drift + shock));
    const high = Math.max(open, close) * (1 + random() * 0.015);
    const low = Math.min(open, close) * (1 - random() * 0.015);
    const volume = Math.round((7e5 + random() * 4e6) * (1 + Math.abs(shock) * 20));
    return {
      time: nowSeconds - (count - index - 1) * step,
      open,
      high,
      low,
      close,
      volume
    };
  });
}
function createMarketDataSource(defaultOptions = {}) {
  const cache = /* @__PURE__ */ new Map();
  const config = {
    provider: normalizeProvider(defaultOptions.provider ?? "yahoo"),
    cacheEnabled: defaultOptions.cacheEnabled ?? true,
    ttlMs: defaultOptions.ttlMs ?? DEFAULT_TTL_MS,
    staleMaxAgeMs: defaultOptions.staleMaxAgeMs ?? DEFAULT_STALE_MAX_AGE_MS,
    fetchImpl: defaultOptions.fetchImpl,
    now: defaultOptions.now
  };
  return {
    async fetchSeries(symbol, range = "6mo", options = {}) {
      const now = options.now ?? config.now ?? Date.now;
      const nowMs = now();
      const rawSymbol = normalizeMarketDataSymbol(symbol);
      const normalizedRange = normalizeMarketDataRange(String(range));
      const interval = marketDataIntervalForRange(normalizedRange);
      const provider = normalizeProvider(options.provider ?? config.provider);
      const fetchImpl = options.fetchImpl ?? config.fetchImpl ?? (typeof globalThis.fetch === "function" ? globalThis.fetch.bind(globalThis) : void 0);
      const cacheEnabled = options.cacheEnabled ?? config.cacheEnabled;
      const ttlMs = options.ttlMs ?? config.ttlMs;
      const staleMaxAgeMs = options.staleMaxAgeMs ?? config.staleMaxAgeMs;
      const forceRefresh = options.forceRefresh ?? false;
      const cacheKey = buildCacheKey(rawSymbol, normalizedRange, interval, provider);
      const cachedEntry = cache.get(cacheKey);
      if (!rawSymbol) {
        return buildFallbackEnvelope({
          symbol: rawSymbol,
          range: normalizedRange,
          interval,
          provider,
          servedAt: nowMs,
          sourceHealthStatus: "unavailable",
          cacheState: cacheEnabled ? forceRefresh ? "bypass" : "miss" : "disabled",
          reason: "\u7F3A\u5C11\u6807\u7684\u4EE3\u7801",
          retryState: buildRetryState(1, nowMs, "\u7F3A\u5C11\u6807\u7684\u4EE3\u7801", true)
        });
      }
      if (cacheEnabled && !forceRefresh && cachedEntry && nowMs - cachedEntry.fetchedAt <= ttlMs) {
        return cloneEnvelopeWithState(cachedEntry.envelope, {
          servedAt: nowMs,
          cacheState: "hit",
          sourceHealthStatus: "formal",
          lastRefreshedAt: cachedEntry.fetchedAt,
          retryState: buildRetryState(0, void 0, void 0, false),
          sourceName: providerLabel(provider),
          dataSource: "yahoo"
        });
      }
      try {
        if (!fetchImpl) {
          throw new Error("\u5F53\u524D\u8FD0\u884C\u73AF\u5883\u7F3A\u5C11 fetch");
        }
        const url = new URL(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(rawSymbol)}`);
        url.searchParams.set("range", normalizedRange);
        url.searchParams.set("interval", interval);
        url.searchParams.set("includePrePost", "false");
        url.searchParams.set("events", "div,splits");
        const upstream = await fetchImpl(url, {
          headers: {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
          }
        });
        const text = await upstream.text();
        const parsed = parseYahooPayload(text);
        const result = parsed?.chart?.result?.[0];
        const upstreamReason = parsed?.chart?.error?.description ?? `\u4E0A\u6E38\u8FD4\u56DE ${upstream.status}`;
        if (!upstream.ok || parsed?.chart?.error || !result) {
          return handleFailure({
            rawSymbol,
            normalizedRange,
            interval,
            provider,
            nowMs,
            cachedEntry,
            cacheEnabled,
            staleMaxAgeMs,
            forceRefresh,
            cacheKey,
            reason: upstreamReason,
            failureKind: "payload"
          });
        }
        const bars = compactBars(result);
        if (!bars.length) {
          return handleFailure({
            rawSymbol,
            normalizedRange,
            interval,
            provider,
            nowMs,
            cachedEntry,
            cacheEnabled,
            staleMaxAgeMs,
            forceRefresh,
            cacheKey,
            reason: "\u4E0A\u6E38\u8FD4\u56DE\u4E86\u6CA1\u6709\u53EF\u7528\u884C\u60C5\u7684 payload",
            failureKind: "payload"
          });
        }
        const envelope = buildFormalEnvelope({
          symbol: rawSymbol,
          range: normalizedRange,
          interval,
          provider,
          bars,
          meta: normalizeMeta(result.meta, rawSymbol, bars, provider),
          servedAt: nowMs,
          cacheState: cacheEnabled && forceRefresh ? "bypass" : cachedEntry ? "miss" : "miss",
          dataSource: "yahoo"
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
        const reason = error instanceof Error ? error.message : "\u672A\u77E5\u9519\u8BEF";
        return handleFailure({
          rawSymbol,
          normalizedRange,
          interval,
          provider,
          nowMs,
          cachedEntry,
          cacheEnabled,
          staleMaxAgeMs,
          forceRefresh,
          cacheKey,
          reason,
          failureKind: "network"
        });
      }
    },
    clearCache() {
      cache.clear();
    }
  };
  function handleFailure({
    rawSymbol,
    normalizedRange,
    interval,
    provider,
    nowMs,
    cachedEntry,
    cacheEnabled,
    staleMaxAgeMs,
    forceRefresh,
    cacheKey,
    reason,
    failureKind
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
        sourceName: providerLabel(provider),
        degradationReason: buildStaleReason(reason),
        notice: buildNotice("stale", reason),
        dataSource: "yahoo"
      });
    }
    const sourceHealthStatus = failureKind === "payload" ? "demo_fallback" : "unavailable";
    const cacheState = cacheEnabled ? forceRefresh ? "bypass" : "miss" : "disabled";
    return buildFallbackEnvelope({
      symbol: rawSymbol,
      range: normalizedRange,
      interval,
      provider,
      servedAt: nowMs,
      sourceHealthStatus,
      cacheState,
      reason,
      retryState: buildRetryState(1, nowMs, reason, true)
    });
  }
}
function buildFormalEnvelope({
  symbol,
  range,
  interval,
  provider,
  bars,
  meta,
  servedAt,
  cacheState,
  dataSource
}) {
  const retryState = buildRetryState(0, servedAt, void 0, false);
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
      degradationReason: void 0,
      affectedObjects: FORMAL_AFFECTED_OBJECTS
    }),
    sourceName: providerLabel(provider),
    degradationReason: void 0,
    lastRefreshedAt: servedAt,
    retryState,
    dataSource
  };
}
function buildFallbackEnvelope({
  symbol,
  range,
  interval,
  provider,
  servedAt,
  sourceHealthStatus,
  cacheState,
  reason,
  retryState
}) {
  const bars = generateFallbackBars(symbol, range, servedAt);
  const meta = buildFallbackMeta(symbol, bars, provider);
  const degradationReason = buildFallbackReason(sourceHealthStatus, reason);
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
      status: sourceHealthStatus,
      lastRefreshedAt: void 0,
      retryState,
      degradationReason,
      affectedObjects: DEGRADING_AFFECTED_OBJECTS
    }),
    sourceName: "Demo",
    degradationReason,
    lastRefreshedAt: void 0,
    retryState,
    dataSource: "demo",
    notice: buildNotice(sourceHealthStatus, reason)
  };
}
function buildSourceHealth({
  status,
  retryState,
  lastRefreshedAt,
  degradationReason,
  affectedObjects
}) {
  return {
    status,
    affectedObjects,
    retryState,
    lastRefreshedAt,
    degradationReason
  };
}
function buildPriceSeries(symbol, range, interval, bars) {
  const latestBar = bars.at(-1);
  const previousBar = bars.at(-2);
  const latestPrice = latestBar?.close;
  const basis = previousBar?.close ?? latestBar?.open;
  return {
    symbol,
    range,
    interval,
    bars,
    latestOhlc: latestBar ? {
      time: latestBar.time,
      open: latestBar.open,
      high: latestBar.high,
      low: latestBar.low,
      close: latestBar.close
    } : void 0,
    latestPrice,
    changeSummary: basis && latestPrice !== void 0 ? {
      absolute: latestPrice - basis,
      percent: basis !== 0 ? (latestPrice - basis) / basis * 100 : void 0
    } : void 0
  };
}
function normalizeMeta(meta, symbol, bars, provider) {
  if (meta) {
    return {
      currency: meta.currency,
      exchangeName: meta.exchangeName,
      fullExchangeName: meta.fullExchangeName,
      shortName: meta.shortName ?? symbol,
      regularMarketPrice: meta.regularMarketPrice ?? bars.at(-1)?.close,
      previousClose: meta.previousClose ?? bars.at(-2)?.close,
      regularMarketTime: meta.regularMarketTime ?? bars.at(-1)?.time,
      timezone: meta.timezone ?? "UTC"
    };
  }
  return buildFallbackMeta(symbol, bars, provider);
}
function buildFallbackMeta(symbol, bars, provider) {
  return {
    shortName: symbol,
    currency: inferCurrency(symbol),
    exchangeName: providerLabel(provider),
    fullExchangeName: `${providerLabel(provider)} market data`,
    regularMarketPrice: bars.at(-1)?.close,
    previousClose: bars.at(-2)?.close,
    regularMarketTime: bars.at(-1)?.time,
    timezone: "UTC"
  };
}
function inferCurrency(symbol) {
  if (symbol.includes(".HK")) return "HKD";
  if (symbol.includes(".KS")) return "KRW";
  if (symbol.includes(".SS") || symbol.includes(".SZ")) return "CNY";
  return "USD";
}
function buildNotice(status, reason) {
  if (status === "stale") {
    return `\u884C\u60C5\u5DF2\u8FC7\u671F\uFF0C\u5F53\u524D\u663E\u793A\u4E0A\u6B21\u6210\u529F\u7F13\u5B58\uFF1A${reason}`;
  }
  if (status === "demo_fallback") {
    return `\u884C\u60C5\u6E90\u6682\u4E0D\u53EF\u7528\uFF0C\u5F53\u524D\u663E\u793A\u6F14\u793A\u6570\u636E\uFF1A${reason}`;
  }
  return `\u884C\u60C5\u6682\u4E0D\u53EF\u7528\uFF0C\u5F53\u524D\u663E\u793A\u5360\u4F4D\u6570\u636E\uFF1A${reason}`;
}
function buildFallbackReason(status, reason) {
  return status === "stale" ? `\u5DF2\u4F7F\u7528\u4E0A\u6B21\u6210\u529F\u7F13\u5B58\uFF1A${reason}` : reason;
}
function buildStaleReason(reason) {
  return `\u4E0A\u6E38\u8BF7\u6C42\u5931\u8D25\uFF0C\u5DF2\u4F7F\u7528\u4E0A\u6B21\u6210\u529F\u7F13\u5B58\uFF1A${reason}`;
}
function buildRetryState(attempt, lastAttemptAt, reason, canRetry) {
  return {
    attempt,
    canRetry,
    lastAttemptAt,
    nextRetryAt: canRetry && lastAttemptAt !== void 0 ? lastAttemptAt + Math.min(6e4, 15e3 * Math.max(1, attempt)) : void 0,
    reason
  };
}
function buildCacheStateKey(symbol, range, interval, provider) {
  return `${symbol}::${range}::${interval}::${provider}`;
}
function normalizeProvider(provider) {
  const normalized = provider?.trim().toLowerCase();
  return normalized || "yahoo";
}
function providerLabel(provider) {
  return provider === "yahoo" ? "Yahoo Finance" : provider;
}
function buildCacheKey(symbol, range, interval, provider) {
  return buildCacheStateKey(symbol, range, interval, provider);
}
function parseYahooPayload(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}
function cloneEnvelopeWithState(envelope, patch) {
  const bars = cloneBars(envelope.bars);
  const priceSeries = clonePriceSeries(envelope.priceSeries, bars);
  const sourceHealth = buildSourceHealth({
    status: patch.sourceHealthStatus,
    affectedObjects: patch.sourceHealthStatus === "formal" ? FORMAL_AFFECTED_OBJECTS : DEGRADING_AFFECTED_OBJECTS,
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
    sourceName: patch.sourceName,
    degradationReason: patch.degradationReason,
    lastRefreshedAt: patch.lastRefreshedAt,
    retryState: patch.retryState,
    dataSource: patch.dataSource,
    notice: patch.notice ?? envelope.notice
  };
}
function clonePriceSeries(priceSeries, bars) {
  return {
    ...priceSeries,
    bars,
    latestOhlc: priceSeries.latestOhlc ? { ...priceSeries.latestOhlc } : void 0,
    changeSummary: priceSeries.changeSummary ? { ...priceSeries.changeSummary } : void 0
  };
}
function cloneBars(bars) {
  return bars.map((bar) => ({ ...bar }));
}
function seededRandom(seed) {
  let value = seed % 2147483647;
  return () => {
    value = value * 16807 % 2147483647;
    return (value - 1) / 2147483646;
  };
}

// tests/unit/source/market-data-source.spec.ts
function makeYahooPayload() {
  return {
    chart: {
      result: [
        {
          meta: {
            currency: "USD",
            exchangeName: "NMS",
            fullExchangeName: "NasdaqGS",
            shortName: "Apple Inc.",
            regularMarketPrice: 188.37,
            previousClose: 187.64,
            regularMarketTime: 17e8,
            timezone: "America/New_York"
          },
          timestamp: [17e8, 1700086400],
          indicators: {
            quote: [
              {
                open: [187.5, 188.1],
                high: [188.9, 189.2],
                low: [186.7, 187.9],
                close: [188.2, 188.37],
                volume: [12e5, 11e5]
              }
            ]
          }
        }
      ]
    }
  };
}
describe("market data source", () => {
  it("returns formal Yahoo data on success", async () => {
    const calls = [];
    const currentTime = 17e11;
    const source = createMarketDataSource({
      now: () => currentTime,
      fetchImpl: async (url, init) => {
        calls.push({ url: new URL(String(url)), init });
        return {
          ok: true,
          status: 200,
          text: async () => JSON.stringify(makeYahooPayload())
        };
      }
    });
    const envelope = await source.fetchSeries("aapl", "6mo");
    assert.equal(calls.length, 1);
    assert.equal(envelope.sourceHealth.status, "formal");
    assert.equal(envelope.cacheState, "miss");
    assert.equal(envelope.dataSource, "yahoo");
    assert.equal(envelope.sourceName, "Yahoo Finance");
    assert.equal(envelope.servedAt, currentTime);
    assert.equal(envelope.lastRefreshedAt, currentTime);
    assert.equal(envelope.retryState.attempt, 0);
    assert.equal(envelope.sourceHealth.retryState.attempt, 0);
    assert.equal(envelope.priceSeries.bars.length, 2);
    assert.deepEqual(envelope.bars, envelope.priceSeries.bars);
    assert.equal(envelope.priceSeries.latestPrice, 188.37);
    assert.ok(envelope.priceSeries.changeSummary);
  });
  it("falls back to demo data when Yahoo payload cannot be parsed", async () => {
    const currentTime = 17001e8;
    const source = createMarketDataSource({
      now: () => currentTime,
      fetchImpl: async () => ({
        ok: true,
        status: 200,
        text: async () => "{this is not valid json"
      })
    });
    const envelope = await source.fetchSeries("AAPL", "6mo");
    assert.equal(envelope.sourceHealth.status, "demo_fallback");
    assert.equal(envelope.cacheState, "miss");
    assert.equal(envelope.dataSource, "demo");
    assert.match(envelope.notice ?? "", /演示数据/);
    assert.equal(envelope.servedAt, currentTime);
    assert.equal(envelope.lastRefreshedAt, void 0);
    assert.equal(envelope.retryState.attempt, 1);
    assert.equal(envelope.retryState.canRetry, true);
    assert.equal(envelope.sourceHealth.affectedObjects.length, 3);
    assert.ok(envelope.priceSeries.bars.length > 0);
  });
  it("serves stale cached data when the upstream fails after TTL expiry", async () => {
    const calls = [];
    let currentTime = 17002e8;
    const source = createMarketDataSource({
      now: () => currentTime,
      fetchImpl: async (url, init) => {
        calls.push({ url: new URL(String(url)), init });
        if (calls.length === 1) {
          return {
            ok: true,
            status: 200,
            text: async () => JSON.stringify(makeYahooPayload())
          };
        }
        throw new Error("upstream timeout");
      }
    });
    const first = await source.fetchSeries("AAPL", "6mo");
    currentTime += 61e3;
    const stale = await source.fetchSeries("AAPL", "6mo");
    assert.equal(calls.length, 2);
    assert.equal(first.sourceHealth.status, "formal");
    assert.equal(stale.sourceHealth.status, "stale");
    assert.equal(stale.cacheState, "stale_fallback");
    assert.equal(stale.lastRefreshedAt, first.lastRefreshedAt);
    assert.equal(stale.sourceName, "Yahoo Finance");
    assert.match(stale.degradationReason ?? "", /缓存/);
    assert.match(stale.notice ?? "", /上次成功缓存/);
    assert.equal(stale.retryState.attempt, 1);
    assert.equal(stale.sourceHealth.retryState.attempt, 1);
  });
  it("returns unavailable when the network fails without usable cache", async () => {
    const currentTime = 170025e7;
    const source = createMarketDataSource({
      now: () => currentTime,
      fetchImpl: async () => {
        throw new Error("network unreachable");
      }
    });
    const envelope = await source.fetchSeries("AAPL", "6mo");
    assert.equal(envelope.sourceHealth.status, "unavailable");
    assert.equal(envelope.cacheState, "miss");
    assert.equal(envelope.dataSource, "demo");
    assert.equal(envelope.lastRefreshedAt, void 0);
    assert.equal(envelope.retryState.attempt, 1);
    assert.equal(envelope.retryState.canRetry, true);
    assert.equal(envelope.sourceHealth.affectedObjects.includes("chart"), true);
    assert.equal(envelope.sourceHealth.affectedObjects.includes("mts"), true);
    assert.equal(envelope.sourceHealth.affectedObjects.includes("alerts"), true);
    assert.match(envelope.notice ?? "", /行情暂不可用/);
    assert.match(envelope.degradationReason ?? "", /network unreachable/);
  });
  it("hits the in-memory cache within the 60 second TTL", async () => {
    const calls = [];
    let currentTime = 17003e8;
    const source = createMarketDataSource({
      now: () => currentTime,
      fetchImpl: async (url, init) => {
        calls.push({ url: new URL(String(url)), init });
        return {
          ok: true,
          status: 200,
          text: async () => JSON.stringify(makeYahooPayload())
        };
      }
    });
    const first = await source.fetchSeries("AAPL", "6mo");
    currentTime += 3e4;
    const second = await source.fetchSeries("AAPL", "6mo");
    assert.equal(calls.length, 1);
    assert.equal(first.cacheState, "miss");
    assert.equal(second.cacheState, "hit");
    assert.equal(second.sourceHealth.status, "formal");
    assert.equal(second.lastRefreshedAt, first.lastRefreshedAt);
    assert.equal(second.servedAt, currentTime);
  });
  it("bypasses cache when forceRefresh is set", async () => {
    const calls = [];
    let currentTime = 17004e8;
    const source = createMarketDataSource({
      now: () => currentTime,
      fetchImpl: async (url, init) => {
        calls.push({ url: new URL(String(url)), init });
        return {
          ok: true,
          status: 200,
          text: async () => JSON.stringify(makeYahooPayload())
        };
      }
    });
    const first = await source.fetchSeries("AAPL", "6mo");
    currentTime += 1e4;
    const refreshed = await source.fetchSeries("AAPL", "6mo", { forceRefresh: true });
    assert.equal(calls.length, 2);
    assert.equal(first.cacheState, "miss");
    assert.equal(refreshed.cacheState, "bypass");
    assert.equal(refreshed.sourceHealth.status, "formal");
    assert.equal(refreshed.lastRefreshedAt, currentTime);
  });
  it("uses the provider and range in the cache key", async () => {
    const calls = [];
    let currentTime = 17005e8;
    const source = createMarketDataSource({
      now: () => currentTime,
      fetchImpl: async (url, init) => {
        calls.push({ url: new URL(String(url)), init });
        return {
          ok: true,
          status: 200,
          text: async () => JSON.stringify(makeYahooPayload())
        };
      }
    });
    const first = await source.fetchSeries("AAPL", "6mo", { provider: "yahoo" });
    const second = await source.fetchSeries("AAPL", "1y", { provider: "yahoo" });
    const third = await source.fetchSeries("AAPL", "1y", { provider: "alt-provider" });
    assert.equal(calls.length, 3);
    assert.equal(first.cacheState, "miss");
    assert.equal(second.cacheState, "miss");
    assert.equal(third.cacheState, "miss");
    assert.equal(second.range, "1y");
    assert.equal(third.sourceName, "alt-provider");
  });
});
