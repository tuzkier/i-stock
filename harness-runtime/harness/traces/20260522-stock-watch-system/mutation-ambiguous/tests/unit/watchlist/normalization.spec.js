"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const strict_1 = __importDefault(require("node:assert/strict"));
const node_test_1 = require("node:test");
const market_normalization_js_1 = require("../../../src/domain/market-normalization.js");
const watchlist = [{ id: "0700.HK", symbol: "0700.HK", name: "腾讯控股", market: "HK", status: "active" }];
(0, node_test_1.describe)("watchlist normalization preview", () => {
    (0, node_test_1.it)("blocks ambiguous numeric input while US is selected", () => {
        const preview = (0, market_normalization_js_1.buildNormalizationPreview)("0700", "US", []);
        strict_1.default.equal(preview.status, "ambiguous");
        strict_1.default.match(preview.message, /多个市场/);
        strict_1.default.deepEqual("candidates" in preview ? preview.candidates.map((candidate) => candidate.symbol) : [], ["0700.HK"]);
    });
    (0, node_test_1.it)("normalizes HK input before adding it to active watchlist", () => {
        const preview = (0, market_normalization_js_1.buildNormalizationPreview)("9988", "HK", []);
        strict_1.default.equal(preview.status, "ready");
        if (preview.status !== "ready")
            throw new Error("expected ready preview");
        strict_1.default.equal(preview.normalizedSymbol, "9988.HK");
        strict_1.default.equal(preview.restoresArchived, false);
    });
    (0, node_test_1.it)("does not allow duplicate active symbols", () => {
        const preview = (0, market_normalization_js_1.buildNormalizationPreview)("0700", "HK", watchlist);
        strict_1.default.equal(preview.status, "duplicate_active");
    });
    (0, node_test_1.it)("marks archived symbols as restorable", () => {
        const preview = (0, market_normalization_js_1.buildNormalizationPreview)("9988", "HK", [
            { id: "9988.HK", symbol: "9988.HK", name: "阿里巴巴", market: "HK", status: "archived" }
        ]);
        strict_1.default.equal(preview.status, "ready");
        if (preview.status !== "ready")
            throw new Error("expected ready preview");
        strict_1.default.equal(preview.restoresArchived, true);
    });
});
