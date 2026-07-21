import { normalizeTickerForMarket } from "../domain/market-normalization";
export const marketLabels = {
    US: "美股",
    HK: "港股",
    CN: "A股",
    KR: "韩股"
};
export const marketHints = {
    US: "AAPL / MSFT / TSLA",
    HK: "0700.HK / 9988.HK",
    CN: "600519.SS / 000001.SZ",
    KR: "005930.KS / 035420.KS"
};
export const defaultWatchlist = [
    { id: "AAPL", symbol: "AAPL", name: "Apple", market: "US", status: "active" },
    { id: "0700.HK", symbol: "0700.HK", name: "腾讯控股", market: "HK", status: "active" },
    { id: "600519.SS", symbol: "600519.SS", name: "贵州茅台", market: "CN", status: "active" },
    { id: "005930.KS", symbol: "005930.KS", name: "Samsung Electronics", market: "KR", status: "active" }
];
export function normalizeTicker(symbol, market) {
    return normalizeTickerForMarket(symbol, market);
}
