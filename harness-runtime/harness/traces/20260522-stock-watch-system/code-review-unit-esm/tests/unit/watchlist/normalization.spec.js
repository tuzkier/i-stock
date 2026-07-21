import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { buildNormalizationPreview } from "../../../src/domain/market-normalization.js";
const watchlist = [{ id: "0700.HK", symbol: "0700.HK", name: "腾讯控股", market: "HK", status: "active" }];
describe("watchlist normalization preview", () => {
    it("blocks ambiguous numeric input while US is selected", () => {
        const preview = buildNormalizationPreview("0700", "US", []);
        assert.equal(preview.status, "ambiguous");
        assert.match(preview.message, /多个市场/);
        assert.deepEqual("candidates" in preview ? preview.candidates.map((candidate) => candidate.symbol) : [], ["0700.HK"]);
    });
    it("normalizes HK input before adding it to active watchlist", () => {
        const preview = buildNormalizationPreview("9988", "HK", []);
        assert.equal(preview.status, "ready");
        if (preview.status !== "ready")
            throw new Error("expected ready preview");
        assert.equal(preview.normalizedSymbol, "9988.HK");
        assert.equal(preview.restoresArchived, false);
    });
    it("normalizes mainland China symbols with exchange suffixes", () => {
        const shanghaiPreview = buildNormalizationPreview("600519", "CN", []);
        const shenzhenPreview = buildNormalizationPreview("000001", "CN", []);
        assert.equal(shanghaiPreview.status, "ready");
        assert.equal(shenzhenPreview.status, "ready");
        if (shanghaiPreview.status !== "ready" || shenzhenPreview.status !== "ready")
            throw new Error("expected ready previews");
        assert.equal(shanghaiPreview.normalizedSymbol, "600519.SS");
        assert.equal(shenzhenPreview.normalizedSymbol, "000001.SZ");
    });
    it("normalizes Korean numeric symbols with KS suffix", () => {
        const preview = buildNormalizationPreview("005930", "KR", []);
        assert.equal(preview.status, "ready");
        if (preview.status !== "ready")
            throw new Error("expected ready preview");
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
            { id: "9988.HK", symbol: "9988.HK", name: "阿里巴巴", market: "HK", status: "archived" }
        ]);
        assert.equal(preview.status, "ready");
        if (preview.status !== "ready")
            throw new Error("expected ready preview");
        assert.equal(preview.restoresArchived, true);
    });
});
