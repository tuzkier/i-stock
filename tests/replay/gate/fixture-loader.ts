import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";

type SourceStatus = "formal" | "demo_fallback" | "stale" | "unavailable";

export type GateSourceCase = {
  id: string;
  symbol: string;
  range: string;
  status: SourceStatus;
  count: number;
  startClose: number;
  step: number;
  reason?: string;
};

export type GateCorpus = {
  version: number;
  generatedAt: string;
  description: string;
  watchlist: Array<Record<string, unknown>>;
  ambiguousInputs: Array<Record<string, unknown>>;
  source: GateSourceCase[];
  mts: Array<Record<string, unknown>>;
  alerts: Record<string, any>;
  workspace: Record<string, any>;
  acMatrix: Array<{
    ac: string;
    scenarios: string[];
    surfaces: string[];
    fixtureIds: string[];
  }>;
};

const nowSeconds = 1_783_000_000;
const nowMs = nowSeconds * 1000;
const fixturePath = join(process.cwd(), "fixtures/gate/stock-watch-core.json");
const checksumPath = join(process.cwd(), "fixtures/gate/stock-watch-core.sha256.json");
const corpus = JSON.parse(readFileSync(fixturePath, "utf8")) as GateCorpus;
const checksum = JSON.parse(readFileSync(checksumPath, "utf8")) as { sha256: string };

function stableJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.entries(value)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, nested]) => `${JSON.stringify(key)}:${stableJson(nested)}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
}

export function fixtureChecksum() {
  return createHash("sha256").update(stableJson(corpus)).digest("hex");
}

export function expectedFixtureChecksum() {
  return checksum.sha256;
}

export function loadGateCorpus(): GateCorpus {
  return corpus;
}

export function buildFixtureEnvelope(sourceCase: GateSourceCase) {
  const bars = Array.from({ length: sourceCase.count }, (_, index) => {
    const close = sourceCase.startClose + index * sourceCase.step;
    return {
      time: nowSeconds - (sourceCase.count - index - 1) * 86_400,
      open: close - 0.4,
      high: close + 1.2,
      low: close - 1.4,
      close,
      volume: 1_000_000 + index * 10_000
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
      changeSummary:
        latest && previous
          ? { absolute: latest.close - previous.close, percent: ((latest.close - previous.close) / previous.close) * 100 }
          : undefined
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
        lastAttemptAt: degraded ? nowMs : undefined,
        reason: degraded ? reason : undefined
      },
      lastRefreshedAt: sourceCase.status === "formal" || sourceCase.status === "stale" ? nowMs : undefined,
      degradationReason: degraded ? reason : undefined
    },
    sourceName: sourceCase.status === "demo_fallback" ? "Demo" : "Yahoo Finance",
    degradationReason: degraded ? reason : undefined,
    lastRefreshedAt: sourceCase.status === "formal" || sourceCase.status === "stale" ? nowMs : undefined,
    retryState: {
      attempt: degraded ? 1 : 0,
      canRetry: degraded,
      lastAttemptAt: degraded ? nowMs : undefined,
      reason: degraded ? reason : undefined
    },
    dataSource: sourceCase.status === "demo_fallback" ? "demo" : "yahoo",
    notice: degraded ? `来源降级：${reason}` : undefined
  };
}
