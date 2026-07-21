"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.defaultWatchlist = exports.marketHints = exports.marketLabels = void 0;
exports.normalizeTicker = normalizeTicker;
const market_normalization_1 = require("../domain/market-normalization");
exports.marketLabels = {
    US: "美股",
    HK: "港股",
    CN: "A股",
    KR: "韩股"
};
exports.marketHints = {
    US: "AAPL / MSFT / TSLA",
    HK: "0700.HK / 9988.HK",
    CN: "600519.SS / 000001.SZ",
    KR: "005930.KS / 035420.KS"
};
exports.defaultWatchlist = [
    { id: "AAPL", symbol: "AAPL", name: "Apple", market: "US", status: "active" },
    { id: "0700.HK", symbol: "0700.HK", name: "腾讯控股", market: "HK", status: "active" },
    { id: "600519.SS", symbol: "600519.SS", name: "贵州茅台", market: "CN", status: "active" },
    { id: "005930.KS", symbol: "005930.KS", name: "Samsung Electronics", market: "KR", status: "active" }
];
function normalizeTicker(symbol, market) {
    return (0, market_normalization_1.normalizeTickerForMarket)(symbol, market);
}
