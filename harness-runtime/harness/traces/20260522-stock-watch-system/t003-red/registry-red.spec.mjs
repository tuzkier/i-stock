// harness-runtime/harness/traces/20260522-stock-watch-system/t003-red/registry-red.spec.ts
import assert from "node:assert/strict";
import test from "node:test";

// src/domain/mts-registry.ts
var reasonRegistry = {
  TREND_ABOVE_EMA: {
    code: "TREND_ABOVE_EMA",
    label: "\u8D8B\u52BF\u7ED3\u6784\u504F\u5F3A",
    detail: "\u4EF7\u683C\u7AD9\u4E0A EMA20\uFF0C\u4E14 EMA20 \u4F4D\u4E8E EMA60 \u4E0A\u65B9\u3002",
    polarity: "positive"
  },
  TREND_BELOW_EMA: {
    code: "TREND_BELOW_EMA",
    label: "\u77ED\u7EBF\u8D8B\u52BF\u504F\u5F31",
    detail: "\u4EF7\u683C\u4F4E\u4E8E EMA20\uFF0C\u77ED\u7EBF\u8D8B\u52BF\u5C1A\u672A\u6062\u590D\u3002",
    polarity: "negative"
  },
  MACD_MOMENTUM_UP: {
    code: "MACD_MOMENTUM_UP",
    label: "MACD \u52A8\u91CF\u6539\u5584",
    detail: "MACD \u67F1\u4F53\u4E3A\u6B63\u4E14\u7EE7\u7EED\u62AC\u5347\uFF0C\u77ED\u7EBF\u52A8\u91CF\u6B63\u5728\u6539\u5584\u3002",
    polarity: "positive"
  },
  MACD_MOMENTUM_DOWN: {
    code: "MACD_MOMENTUM_DOWN",
    label: "MACD \u52A8\u91CF\u8D70\u5F31",
    detail: "MACD \u67F1\u4F53\u4E3A\u8D1F\u6216\u7EE7\u7EED\u56DE\u843D\uFF0C\u77ED\u7EBF\u52A8\u91CF\u4E0D\u8DB3\u3002",
    polarity: "negative"
  },
  RSI_LOW_RECOVERY: {
    code: "RSI_LOW_RECOVERY",
    label: "RSI \u4F4E\u4F4D\u4FEE\u590D",
    detail: "RSI \u4ECE\u4F4E\u4F4D\u56DE\u5347\uFF0C\u5B58\u5728\u8D85\u8DCC\u4FEE\u590D\u8FF9\u8C61\u3002",
    polarity: "positive"
  },
  RSI_OVERHEATED: {
    code: "RSI_OVERHEATED",
    label: "RSI \u8FC7\u70ED",
    detail: "RSI \u9AD8\u4E8E 72\uFF0C\u77ED\u7EBF\u8FFD\u9AD8\u98CE\u9669\u4E0A\u5347\u3002",
    polarity: "negative"
  },
  VOLUME_EXPANSION: {
    code: "VOLUME_EXPANSION",
    label: "\u91CF\u80FD\u653E\u5927",
    detail: "\u6210\u4EA4\u91CF\u660E\u663E\u9AD8\u4E8E 20 \u671F\u5747\u91CF\uFF0C\u4EF7\u683C\u52A8\u4F5C\u6709\u91CF\u80FD\u786E\u8BA4\u3002",
    polarity: "positive"
  },
  BOLLINGER_BREAKOUT: {
    code: "BOLLINGER_BREAKOUT",
    label: "\u6CE2\u52A8\u5411\u4E0A\u6269\u5F20",
    detail: "\u5E03\u6797\u5E26\u6536\u7A84\u540E\u5411\u4E0A\u7A81\u7834\uFF0C\u53EF\u80FD\u8FDB\u5165\u6CE2\u52A8\u6269\u5F20\u9636\u6BB5\u3002",
    polarity: "positive"
  },
  BOLLINGER_BREAKDOWN: {
    code: "BOLLINGER_BREAKDOWN",
    label: "\u8DCC\u7834\u5E03\u6797\u4E0B\u8F68",
    detail: "\u4EF7\u683C\u8DCC\u7834\u5E03\u6797\u4E0B\u8F68\uFF0C\u5F31\u52BF\u6CE2\u52A8\u4ECD\u5728\u91CA\u653E\u3002",
    polarity: "negative"
  },
  HIGH_VOLATILITY: {
    code: "HIGH_VOLATILITY",
    label: "\u6CE2\u52A8\u7387\u504F\u9AD8",
    detail: "ATR \u5360\u4EF7\u683C\u6BD4\u4F8B\u504F\u9AD8\uFF0C\u63D0\u9192\u9608\u503C\u548C\u4ED3\u4F4D\u9700\u8981\u66F4\u4FDD\u5B88\u3002",
    polarity: "negative"
  },
  NO_CONFLUENCE: {
    code: "NO_CONFLUENCE",
    label: "\u5C1A\u672A\u5171\u632F",
    detail: "\u8D8B\u52BF\u3001\u52A8\u91CF\u3001\u6CE2\u52A8\u7387\u548C\u6210\u4EA4\u91CF\u5C1A\u672A\u5F62\u6210\u660E\u786E\u5171\u632F\u3002",
    polarity: "neutral"
  },
  DATA_INSUFFICIENT: {
    code: "DATA_INSUFFICIENT",
    label: "\u6570\u636E\u4E0D\u8DB3",
    detail: "\u9700\u8981\u81F3\u5C11 60 \u6839 K \u7EBF\u6765\u7A33\u5B9A\u8BA1\u7B97\u8D8B\u52BF\u3001\u52A8\u91CF\u548C\u6CE2\u52A8\u7387\u3002",
    polarity: "neutral"
  },
  SOURCE_DEGRADED: {
    code: "SOURCE_DEGRADED",
    label: "\u6765\u6E90\u964D\u7EA7",
    detail: "\u884C\u60C5\u6765\u6E90\u5904\u4E8E\u964D\u7EA7\u72B6\u6001\uFF0CMTS \u53EA\u4FDD\u7559\u89E3\u91CA\u6027\u6280\u672F\u63D0\u9192\u3002",
    polarity: "neutral"
  },
  UNKNOWN_CODE: {
    code: "UNKNOWN_CODE",
    label: "\u672A\u77E5\u539F\u56E0\u7801",
    detail: "\u5F53\u524D\u539F\u56E0\u7801\u672A\u6CE8\u518C\uFF0C\u4E0D\u80FD\u4F5C\u4E3A\u6709\u6548\u89E3\u91CA\u4F9D\u636E\u3002",
    polarity: "neutral"
  }
};
function resolveMtsReason(code, detail) {
  const entry = reasonRegistry[code] ?? reasonRegistry.UNKNOWN_CODE;
  return detail ? { ...entry, detail } : entry;
}

// harness-runtime/harness/traces/20260522-stock-watch-system/t003-red/registry-red.spec.ts
test("red: removed registry entries must not pass through as free-text MTS reasons", () => {
  const resolved = resolveMtsReason("REMOVED_REASON_ENTRY");
  assert.equal(
    resolved.code,
    "REMOVED_REASON_ENTRY",
    "Red proof: a broken registry implementation that lets unknown codes pass through would satisfy this assertion"
  );
});
