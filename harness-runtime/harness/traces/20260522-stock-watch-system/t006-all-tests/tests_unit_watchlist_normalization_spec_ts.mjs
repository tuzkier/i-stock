// tests/unit/watchlist/normalization.spec.ts
import assert from "node:assert/strict";
import { describe, it } from "node:test";

// src/domain/market-normalization.ts
var suffixMarket = {
  HK: "HK",
  SS: "CN",
  SZ: "CN",
  KS: "KR"
};
function cleanTickerInput(symbol) {
  return symbol.trim().toUpperCase().replace(/\s+/g, "");
}
function normalizeTickerForMarket(symbol, market) {
  const clean = cleanTickerInput(symbol);
  if (!clean) {
    return clean;
  }
  if (market === "HK" && /^\d{1,5}$/.test(clean)) {
    return `${clean.padStart(4, "0")}.HK`;
  }
  if (market === "CN" && /^\d{6}$/.test(clean)) {
    const suffix = clean.startsWith("6") ? "SS" : "SZ";
    return `${clean}.${suffix}`;
  }
  if (market === "KR" && /^\d{6}$/.test(clean)) {
    return `${clean}.KS`;
  }
  return clean;
}
function isValidTickerForMarket(clean, market) {
  if (market === "HK") return /^\d{1,5}$/.test(clean) || /^\d{4,5}\.HK$/.test(clean);
  if (market === "CN") return /^\d{6}$/.test(clean) || /^\d{6}\.(SS|SZ)$/.test(clean);
  if (market === "KR") return /^\d{6}$/.test(clean) || /^\d{6}\.KS$/.test(clean);
  return /^(?!\d+$)[A-Z][A-Z0-9.-]{0,14}$/.test(clean);
}
function explicitMarket(clean) {
  const match = clean.match(/\.([A-Z]{2})$/);
  return match ? suffixMarket[match[1]] ?? null : null;
}
function numericCandidates(clean) {
  const candidates = [];
  if (/^\d{1,5}$/.test(clean)) {
    candidates.push({ market: "HK", symbol: normalizeTickerForMarket(clean, "HK"), label: "\u6E2F\u80A1" });
  }
  if (/^\d{6}$/.test(clean)) {
    candidates.push({ market: "CN", symbol: normalizeTickerForMarket(clean, "CN"), label: "A\u80A1" });
    candidates.push({ market: "KR", symbol: normalizeTickerForMarket(clean, "KR"), label: "\u97E9\u80A1" });
  }
  return candidates;
}
function buildNormalizationPreview(rawInput, selectedMarket, watchlist2) {
  const clean = cleanTickerInput(rawInput);
  if (!clean) {
    return {
      status: "empty",
      rawInput,
      selectedMarket,
      message: "\u8F93\u5165\u4EE3\u7801\u540E\u663E\u793A\u5F52\u4E00\u7ED3\u679C"
    };
  }
  const explicit = explicitMarket(clean);
  const targetMarket = explicit ?? selectedMarket;
  const candidates = numericCandidates(clean);
  if (!explicit && candidates.length > 0 && !candidates.some((candidate) => candidate.market === selectedMarket)) {
    return {
      status: "ambiguous",
      rawInput,
      selectedMarket,
      candidates,
      message: "\u7EAF\u6570\u5B57\u4EE3\u7801\u53EF\u80FD\u5C5E\u4E8E\u591A\u4E2A\u5E02\u573A\uFF0C\u8BF7\u5148\u9009\u62E9\u5BF9\u5E94\u5E02\u573A"
    };
  }
  if (!isValidTickerForMarket(clean, targetMarket)) {
    return {
      status: "invalid",
      rawInput,
      selectedMarket,
      candidates,
      message: explicit ? "\u4EE3\u7801\u540E\u7F00\u4E0E\u5E02\u573A\u683C\u5F0F\u4E0D\u5339\u914D" : "\u4EE3\u7801\u683C\u5F0F\u4E0D\u7B26\u5408\u5F53\u524D\u5E02\u573A"
    };
  }
  const normalizedSymbol = normalizeTickerForMarket(clean, targetMarket);
  const existing = watchlist2.find((item) => item.symbol === normalizedSymbol);
  if (existing && existing.status !== "archived") {
    return {
      status: "duplicate_active",
      rawInput,
      selectedMarket,
      candidates: [],
      message: existing ? "\u8BE5\u6807\u7684\u5DF2\u5728 active \u81EA\u9009\u4E2D" : ""
    };
  }
  return {
    status: "ready",
    rawInput,
    selectedMarket,
    market: targetMarket,
    normalizedSymbol,
    restoresArchived: existing?.status === "archived",
    message: existing?.status === "archived" ? "\u786E\u8BA4\u540E\u6062\u590D\u5DF2\u5F52\u6863\u6807\u7684" : "\u786E\u8BA4\u540E\u52A0\u5165 active \u81EA\u9009"
  };
}

// tests/unit/watchlist/normalization.spec.ts
var watchlist = [{ id: "0700.HK", symbol: "0700.HK", name: "\u817E\u8BAF\u63A7\u80A1", market: "HK", status: "active" }];
describe("watchlist normalization preview", () => {
  it("blocks ambiguous numeric input while US is selected", () => {
    const preview = buildNormalizationPreview("0700", "US", []);
    assert.equal(preview.status, "ambiguous");
    assert.match(preview.message, /多个市场/);
    assert.deepEqual(
      "candidates" in preview ? preview.candidates.map((candidate) => candidate.symbol) : [],
      ["0700.HK"]
    );
  });
  it("normalizes HK input before adding it to active watchlist", () => {
    const preview = buildNormalizationPreview("9988", "HK", []);
    assert.equal(preview.status, "ready");
    if (preview.status !== "ready") throw new Error("expected ready preview");
    assert.equal(preview.normalizedSymbol, "9988.HK");
    assert.equal(preview.restoresArchived, false);
  });
  it("normalizes mainland China symbols with exchange suffixes", () => {
    const shanghaiPreview = buildNormalizationPreview("600519", "CN", []);
    const shenzhenPreview = buildNormalizationPreview("000001", "CN", []);
    assert.equal(shanghaiPreview.status, "ready");
    assert.equal(shenzhenPreview.status, "ready");
    if (shanghaiPreview.status !== "ready" || shenzhenPreview.status !== "ready") throw new Error("expected ready previews");
    assert.equal(shanghaiPreview.normalizedSymbol, "600519.SS");
    assert.equal(shenzhenPreview.normalizedSymbol, "000001.SZ");
  });
  it("normalizes Korean numeric symbols with KS suffix", () => {
    const preview = buildNormalizationPreview("005930", "KR", []);
    assert.equal(preview.status, "ready");
    if (preview.status !== "ready") throw new Error("expected ready preview");
    assert.equal(preview.normalizedSymbol, "005930.KS");
  });
  it("blocks numeric symbols that do not match the selected market", () => {
    const hkLikeInChina = buildNormalizationPreview("0700", "CN", []);
    const cnLikeInHongKong = buildNormalizationPreview("600519", "HK", []);
    const hkLikeInKorea = buildNormalizationPreview("9988", "KR", []);
    assert.equal(hkLikeInChina.status, "ambiguous");
    assert.equal(cnLikeInHongKong.status, "ambiguous");
    assert.equal(hkLikeInKorea.status, "ambiguous");
  });
  it("does not allow duplicate active symbols", () => {
    const preview = buildNormalizationPreview("0700", "HK", watchlist);
    assert.equal(preview.status, "duplicate_active");
  });
  it("marks archived symbols as restorable", () => {
    const preview = buildNormalizationPreview("9988", "HK", [
      { id: "9988.HK", symbol: "9988.HK", name: "\u963F\u91CC\u5DF4\u5DF4", market: "HK", status: "archived" }
    ]);
    assert.equal(preview.status, "ready");
    if (preview.status !== "ready") throw new Error("expected ready preview");
    assert.equal(preview.restoresArchived, true);
  });
});
