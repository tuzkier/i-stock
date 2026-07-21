"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.cleanTickerInput = cleanTickerInput;
exports.normalizeTickerForMarket = normalizeTickerForMarket;
exports.buildNormalizationPreview = buildNormalizationPreview;
const suffixMarket = {
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
function explicitMarket(clean) {
    const match = clean.match(/\.([A-Z]{2})$/);
    return match ? suffixMarket[match[1]] ?? null : null;
}
function numericCandidates(clean) {
    const candidates = [];
    if (/^\d{1,5}$/.test(clean)) {
        candidates.push({ market: "HK", symbol: normalizeTickerForMarket(clean, "HK"), label: "港股" });
    }
    if (/^\d{6}$/.test(clean)) {
        candidates.push({ market: "CN", symbol: normalizeTickerForMarket(clean, "CN"), label: "A股" });
        candidates.push({ market: "KR", symbol: normalizeTickerForMarket(clean, "KR"), label: "韩股" });
    }
    return candidates;
}
function buildNormalizationPreview(rawInput, selectedMarket, watchlist) {
    const clean = cleanTickerInput(rawInput);
    if (!clean) {
        return {
            status: "empty",
            rawInput,
            selectedMarket,
            message: "输入代码后显示归一结果"
        };
    }
    const explicit = explicitMarket(clean);
    const targetMarket = explicit ?? selectedMarket;
    const candidates = numericCandidates(clean);
    
    if (!explicit && selectedMarket === "US" && /^\d+$/.test(clean)) {
        return {
            status: "invalid",
            rawInput,
            selectedMarket,
            candidates: [],
            message: "美股代码不能只使用数字"
        };
    }
    const normalizedSymbol = normalizeTickerForMarket(clean, targetMarket);
    const existing = watchlist.find((item) => item.symbol === normalizedSymbol);
    if (existing && existing.status !== "archived") {
        return {
            status: "duplicate_active",
            rawInput,
            selectedMarket,
            candidates: [],
            message: existing ? "该标的已在 active 自选中" : ""
        };
    }
    return {
        status: "ready",
        rawInput,
        selectedMarket,
        market: targetMarket,
        normalizedSymbol,
        restoresArchived: existing?.status === "archived",
        message: existing?.status === "archived" ? "确认后恢复已归档标的" : "确认后加入 active 自选"
    };
}
