// tests/replay/gate/fixture-corpus.spec.ts
import assert from "node:assert/strict";
import test from "node:test";

// tests/replay/gate/fixture-loader.ts
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";
var nowSeconds = 1783e6;
var nowMs = nowSeconds * 1e3;
var fixturePath = join(process.cwd(), "fixtures/gate/stock-watch-core.json");
var checksumPath = join(process.cwd(), "fixtures/gate/stock-watch-core.sha256.json");
var corpus = JSON.parse(readFileSync(fixturePath, "utf8"));
var checksum = JSON.parse(readFileSync(checksumPath, "utf8"));
function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.entries(value).sort(([left], [right]) => left.localeCompare(right)).map(([key, nested]) => `${JSON.stringify(key)}:${stableJson(nested)}`).join(",")}}`;
  }
  return JSON.stringify(value);
}
function fixtureChecksum() {
  return createHash("sha256").update(stableJson(corpus)).digest("hex");
}
function expectedFixtureChecksum() {
  return checksum.sha256;
}
function loadGateCorpus() {
  return corpus;
}
function buildFixtureEnvelope(sourceCase) {
  const bars = Array.from({ length: sourceCase.count }, (_, index) => {
    const close = sourceCase.startClose + index * sourceCase.step;
    return {
      time: nowSeconds - (sourceCase.count - index - 1) * 86400,
      open: close - 0.4,
      high: close + 1.2,
      low: close - 1.4,
      close,
      volume: 1e6 + index * 1e4
    };
  });
  const latest = bars.at(-1);
  const previous = bars.at(-2);
  const degraded = sourceCase.status !== "formal";
  const reason = sourceCase.reason ?? `${sourceCase.status} fixture`;
  return {
    symbol: sourceCase.symbol,
    range: sourceCase.range,
    interval: "1d",
    meta: {
      shortName: sourceCase.symbol,
      currency: "USD",
      exchangeName: "Fixture",
      fullExchangeName: "Fixture market data",
      regularMarketPrice: latest?.close,
      previousClose: previous?.close,
      regularMarketTime: latest?.time,
      timezone: "UTC"
    },
    priceSeries: {
      symbol: sourceCase.symbol,
      range: sourceCase.range,
      interval: "1d",
      bars,
      latestOhlc: latest,
      latestPrice: latest?.close,
      changeSummary: latest && previous ? { absolute: latest.close - previous.close, percent: (latest.close - previous.close) / previous.close * 100 } : void 0
    },
    bars,
    servedAt: nowMs,
    cacheState: sourceCase.status === "stale" ? "stale_fallback" : "miss",
    sourceHealth: {
      status: sourceCase.status,
      affectedObjects: degraded ? ["chart", "mts", "alerts"] : [],
      retryState: {
        attempt: degraded ? 1 : 0,
        canRetry: degraded,
        lastAttemptAt: degraded ? nowMs : void 0,
        reason: degraded ? reason : void 0
      },
      lastRefreshedAt: sourceCase.status === "formal" || sourceCase.status === "stale" ? nowMs : void 0,
      degradationReason: degraded ? reason : void 0
    },
    sourceName: sourceCase.status === "demo_fallback" ? "Demo" : "Yahoo Finance",
    degradationReason: degraded ? reason : void 0,
    lastRefreshedAt: sourceCase.status === "formal" || sourceCase.status === "stale" ? nowMs : void 0,
    retryState: {
      attempt: degraded ? 1 : 0,
      canRetry: degraded,
      lastAttemptAt: degraded ? nowMs : void 0,
      reason: degraded ? reason : void 0
    },
    dataSource: sourceCase.status === "demo_fallback" ? "demo" : "yahoo",
    notice: degraded ? `\u6765\u6E90\u964D\u7EA7\uFF1A${reason}` : void 0
  };
}

// tests/replay/gate/fixture-corpus.spec.ts
test("gate fixture checksum matches the frozen corpus sidecar", () => {
  assert.equal(fixtureChecksum(), expectedFixtureChecksum());
});
test("fixture corpus maps AC-01 through AC-05 to replayable surfaces", () => {
  const corpus2 = loadGateCorpus();
  const acIds = new Set(corpus2.acMatrix.map((item) => item.ac));
  assert.deepEqual(Array.from(acIds).sort(), ["AC-01", "AC-02", "AC-03", "AC-04", "AC-05"]);
  for (const row of corpus2.acMatrix) {
    assert.ok(row.scenarios.length > 0, `${row.ac} must map scenarios`);
    assert.ok(row.surfaces.length > 0, `${row.ac} must map surfaces`);
  }
});
test("source fixtures cover formal, degraded, stale, unavailable and insufficient paths without live URLs", () => {
  const corpus2 = loadGateCorpus();
  const statuses = new Set(corpus2.source.map((item) => item.status));
  const insufficient = corpus2.source.find((item) => item.id === "source-insufficient");
  assert.deepEqual(Array.from(statuses).sort(), ["demo_fallback", "formal", "stale", "unavailable"]);
  assert.ok(insufficient);
  assert.ok(insufficient.count < 14);
  assert.equal(JSON.stringify(corpus2).includes("query1.finance.yahoo.com"), false);
});
test("fixture envelope generation is deterministic for replay", () => {
  const corpus2 = loadGateCorpus();
  const sourceCase = corpus2.source.find((item) => item.id === "source-formal-aapl");
  assert.deepEqual(buildFixtureEnvelope(sourceCase), buildFixtureEnvelope(sourceCase));
});
test("alert, archive and workspace fixtures retain negative-path state", () => {
  const corpus2 = loadGateCorpus();
  assert.equal(corpus2.alerts.triggeredRule.triggerState, "triggered");
  assert.equal(corpus2.alerts.archivedRule.activationState, "suspended_by_archive");
  assert.equal(corpus2.workspace.corruptLayout.layoutBySymbol.AAPL.mode, "broken");
  assert.equal(corpus2.workspace.restoreLayout.layoutBySymbol["0700.HK"].mode, "dense");
});
