import assert from "node:assert/strict";
import test from "node:test";
import {
  humanizeReason,
  humanizeTradeStatus,
  humanizeTrendState
} from "../../../src/features/presentation/humanize.ts";
import { resolveMtsReason } from "../../../src/domain/mts-registry.ts";

// ---- humanizeTrendState：非常态两值 + 常态不裸露英文枚举 ----

test("humanizeTrendState: data_insufficient -> 数据不足", () => {
  assert.equal(humanizeTrendState("data_insufficient"), "数据不足");
});

test("humanizeTrendState: source_degraded -> 数据来源降级", () => {
  assert.equal(humanizeTrendState("source_degraded"), "数据来源降级");
});

test("humanizeTrendState: bullish/neutral/bearish 不得返回裸英文枚举串", () => {
  for (const trendState of ["bullish", "neutral", "bearish"] as const) {
    const result = humanizeTrendState(trendState);
    assert.notEqual(result, trendState);
    assert.match(result, /[一-龥]/);
  }
});

// ---- humanizeTradeStatus：优先复用 stanceLabel，不新建 status->文案映射表 ----

test("humanizeTradeStatus: not_target_symbol -> 复用 stanceLabel「该标的暂无定制算法」", () => {
  assert.equal(humanizeTradeStatus("not_target_symbol", "该标的暂无定制算法"), "该标的暂无定制算法");
});

test("humanizeTradeStatus: data_insufficient -> 复用 stanceLabel「数据不足」", () => {
  assert.equal(humanizeTradeStatus("data_insufficient", "数据不足"), "数据不足");
});

test("humanizeTradeStatus: source_degraded -> 复用 stanceLabel「来源不可用」", () => {
  assert.equal(humanizeTradeStatus("source_degraded", "来源不可用"), "来源不可用");
});

test("humanizeTradeStatus: ready 态同样透传 stanceLabel（不臆造新文案，忠实复用 domain 产出）", () => {
  assert.equal(
    humanizeTradeStatus("ready", "持有中（3 根 K 线前买入），收盘跌破止盈/止损线即离场"),
    "持有中（3 根 K 线前买入），收盘跌破止盈/止损线即离场"
  );
});

test("humanizeTradeStatus: 未提供 stanceLabel 时不抛错、不臆造文案（返回空串，绝不发明新映射表）", () => {
  assert.equal(humanizeTradeStatus("data_insufficient"), "");
  assert.equal(humanizeTradeStatus("not_target_symbol"), "");
  assert.equal(humanizeTradeStatus("source_degraded"), "");
});

// ---- humanizeReason：等价于 resolveMtsReason(code, detail).label ----

test("humanizeReason: 已注册 code（TREND_ABOVE_EMA）返回 registry label「趋势结构偏强」", () => {
  assert.equal(humanizeReason("TREND_ABOVE_EMA"), "趋势结构偏强");
  assert.equal(humanizeReason("TREND_ABOVE_EMA"), resolveMtsReason("TREND_ABOVE_EMA").label);
});

test("humanizeReason: 已注册 code 传入 detail 时与 resolveMtsReason(code, detail).label 等价", () => {
  const detail = "自定义详情文案";
  assert.equal(humanizeReason("TREND_ABOVE_EMA", detail), resolveMtsReason("TREND_ABOVE_EMA", detail).label);
});

test("NEG-04 故障注入：未注册理由码必须走 UNKNOWN_CODE 回落，绝不能把原始 code 字符串直呈", () => {
  const rawCode = "NOT_A_REAL_CODE";
  const result = humanizeReason(rawCode);
  assert.notEqual(result, rawCode);
  assert.ok(
    !result.includes(rawCode),
    `humanizeReason 对未注册 code 的回落文案不得包含原始 code 字符串，实际返回：${result}`
  );
  assert.equal(result, resolveMtsReason("UNKNOWN_CODE").label);
});
