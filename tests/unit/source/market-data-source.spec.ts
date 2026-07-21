import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { createMarketDataSource } from "../../../src/domain/market-data-source.ts";

function futudPayload() {
  return {
    symbol: "US.AAPL",
    name: "Apple",
    market: "US",
    currency: "USD",
    bars: [
      {
        time: 1_700_000_000,
        open: 187.5,
        high: 188.9,
        low: 186.7,
        close: 188.2,
        volume: 1_200_000
      },
      {
        time: 1_700_086_400,
        open: 188.1,
        high: 189.2,
        low: 187.9,
        close: 188.37,
        volume: 1_100_000
      }
    ]
  };
}

describe("market data source", () => {
  it("returns formal FutuOpenD data on success", async () => {
    const currentTime = 1_700_000_000_000;
    const requests: Array<{ symbol: string; range: string; host: string; port: number }> = [];
    const source = createMarketDataSource({
      now: () => currentTime,
      futudClient: async (request) => {
        requests.push(request);
        return futudPayload();
      }
    });

    const envelope = await source.fetchSeries("aapl", "6mo");

    assert.deepEqual(requests, [{ symbol: "US.AAPL", range: "6mo", host: "127.0.0.1", port: 11111 }]);
    assert.equal(envelope.symbol, "AAPL");
    assert.equal(envelope.priceSeries.symbol, "AAPL");
    assert.equal(envelope.sourceHealth.status, "formal");
    assert.equal(envelope.cacheState, "miss");
    assert.equal(envelope.dataSource, "futud");
    assert.equal(envelope.sourceName, "FutuOpenD");
    assert.equal(envelope.meta.shortName, "Apple");
    assert.equal(envelope.meta.exchangeName, "FutuOpenD");
    assert.equal(envelope.meta.currency, "USD");
    assert.equal(envelope.servedAt, currentTime);
    assert.equal(envelope.lastRefreshedAt, currentTime);
    assert.equal(envelope.retryState.attempt, 0);
    assert.equal(envelope.sourceHealth.retryState.attempt, 0);
    assert.equal(envelope.priceSeries.bars.length, 2);
    assert.deepEqual(envelope.bars, envelope.priceSeries.bars);
    assert.equal(envelope.priceSeries.latestPrice, 188.37);
    assert.ok(envelope.priceSeries.changeSummary);
  });

  it("returns unavailable without generating demo bars when futud fails", async () => {
    const currentTime = 1_700_100_000_000;
    const source = createMarketDataSource({
      now: () => currentTime,
      futudClient: async () => {
        throw new Error("FutuOpenD is not reachable");
      }
    });

    const envelope = await source.fetchSeries("AAPL", "6mo");

    assert.equal(envelope.sourceHealth.status, "unavailable");
    assert.equal(envelope.cacheState, "miss");
    assert.equal(envelope.dataSource, "futud");
    assert.equal(envelope.sourceName, "FutuOpenD");
    assert.equal(envelope.bars.length, 0);
    assert.equal(envelope.priceSeries.bars.length, 0);
    assert.equal(envelope.lastRefreshedAt, undefined);
    assert.equal(envelope.retryState.attempt, 1);
    assert.equal(envelope.retryState.canRetry, true);
    assert.equal(envelope.sourceHealth.affectedObjects.length, 3);
    assert.match(envelope.notice ?? "", /FutuOpenD/);
    assert.match(envelope.degradationReason ?? "", /not reachable/);
  });

  it("serves stale cached FutuOpenD data after a later failure", async () => {
    let currentTime = 1_700_200_000_000;
    let calls = 0;
    const source = createMarketDataSource({
      now: () => currentTime,
      futudClient: async () => {
        calls += 1;
        if (calls === 1) return futudPayload();
        throw new Error("OpenD timeout");
      }
    });

    const first = await source.fetchSeries("AAPL", "6mo");
    currentTime += 61_000;
    const stale = await source.fetchSeries("AAPL", "6mo");

    assert.equal(calls, 2);
    assert.equal(first.sourceHealth.status, "formal");
    assert.equal(stale.sourceHealth.status, "stale");
    assert.equal(stale.cacheState, "stale_fallback");
    assert.equal(stale.lastRefreshedAt, first.lastRefreshedAt);
    assert.equal(stale.sourceName, "FutuOpenD");
    assert.equal(stale.dataSource, "futud");
    assert.match(stale.degradationReason ?? "", /缓存/);
    assert.equal(stale.retryState.attempt, 1);
  });

  it("hits the in-memory cache within the 60 second TTL", async () => {
    let calls = 0;
    let currentTime = 1_700_300_000_000;
    const source = createMarketDataSource({
      now: () => currentTime,
      futudClient: async () => {
        calls += 1;
        return futudPayload();
      }
    });

    const first = await source.fetchSeries("AAPL", "6mo");
    currentTime += 30_000;
    const second = await source.fetchSeries("AAPL", "6mo");

    assert.equal(calls, 1);
    assert.equal(first.cacheState, "miss");
    assert.equal(second.cacheState, "hit");
    assert.equal(second.sourceHealth.status, "formal");
    assert.equal(second.lastRefreshedAt, first.lastRefreshedAt);
    assert.equal(second.servedAt, currentTime);
  });

  it("deduplicates concurrent FutuOpenD requests for the same symbol and range", async () => {
    let calls = 0;
    let release: (() => void) | undefined;
    const source = createMarketDataSource({
      futudClient: async () => {
        calls += 1;
        await new Promise<void>((resolve) => {
          release = resolve;
        });
        return futudPayload();
      }
    });

    const first = source.fetchSeries("AAPL", "6mo");
    const second = source.fetchSeries("aapl", "6mo");
    release?.();
    const [firstEnvelope, secondEnvelope] = await Promise.all([first, second]);

    assert.equal(calls, 1);
    assert.equal(firstEnvelope.sourceHealth.status, "formal");
    assert.equal(secondEnvelope.sourceHealth.status, "formal");
    assert.deepEqual(secondEnvelope.bars, firstEnvelope.bars);
  });

  it("bypasses cache when forceRefresh is set", async () => {
    let calls = 0;
    let currentTime = 1_700_400_000_000;
    const source = createMarketDataSource({
      now: () => currentTime,
      futudClient: async () => {
        calls += 1;
        return futudPayload();
      }
    });

    const first = await source.fetchSeries("AAPL", "6mo");
    currentTime += 10_000;
    const refreshed = await source.fetchSeries("AAPL", "6mo", { forceRefresh: true });

    assert.equal(calls, 2);
    assert.equal(first.cacheState, "miss");
    assert.equal(refreshed.cacheState, "bypass");
    assert.equal(refreshed.sourceHealth.status, "formal");
    assert.equal(refreshed.lastRefreshedAt, currentTime);
  });
});
