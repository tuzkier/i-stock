import assert from "node:assert/strict";
import test from "node:test";
import {
  buildFixtureEnvelope,
  expectedFixtureChecksum,
  fixtureChecksum,
  loadGateCorpus,
  type GateSourceCase
} from "./fixture-loader";

test("gate fixture checksum matches the frozen corpus sidecar", () => {
  assert.equal(fixtureChecksum(), expectedFixtureChecksum());
});

test("fixture corpus maps AC-01 through AC-05 to replayable surfaces", () => {
  const corpus = loadGateCorpus();
  const acIds = new Set(corpus.acMatrix.map((item) => item.ac));

  assert.deepEqual(Array.from(acIds).sort(), ["AC-01", "AC-02", "AC-03", "AC-04", "AC-05"]);
  for (const row of corpus.acMatrix) {
    assert.ok(row.scenarios.length > 0, `${row.ac} must map scenarios`);
    assert.ok(row.surfaces.length > 0, `${row.ac} must map surfaces`);
  }
});

test("source fixtures cover formal, degraded, stale, unavailable and insufficient paths without live URLs", () => {
  const corpus = loadGateCorpus();
  const statuses = new Set(corpus.source.map((item) => item.status));
  const insufficient = corpus.source.find((item) => item.id === "source-insufficient");

  assert.deepEqual(Array.from(statuses).sort(), ["demo_fallback", "formal", "stale", "unavailable"]);
  assert.ok(insufficient);
  assert.ok(insufficient.count < 14);
  assert.equal(JSON.stringify(corpus).includes("query1.finance.yahoo.com"), false);
});

test("fixture envelope generation is deterministic for replay", () => {
  const corpus = loadGateCorpus();
  const sourceCase = corpus.source.find((item) => item.id === "source-formal-aapl") as GateSourceCase;

  assert.deepEqual(buildFixtureEnvelope(sourceCase), buildFixtureEnvelope(sourceCase));
});

test("alert, archive and workspace fixtures retain negative-path state", () => {
  const corpus = loadGateCorpus();

  assert.equal(corpus.alerts.triggeredRule.triggerState, "triggered");
  assert.equal(corpus.alerts.archivedRule.activationState, "suspended_by_archive");
  assert.equal(corpus.workspace.corruptLayout.layoutBySymbol.AAPL.mode, "broken");
  assert.equal(corpus.workspace.restoreLayout.layoutBySymbol["0700.HK"].mode, "dense");
});
