import assert from "node:assert/strict";
import test from "node:test";
import { buildHoldingsPanel } from "../../../src/domain/holdings-panel.ts";
import type { PriceBar } from "../../../src/types.ts";

function bar(index: number, close: number): PriceBar {
  const open = close * 0.995;
  return {
    time: 1_700_000_000 + index * 86_400,
    open,
    high: Math.max(open, close) * 1.01,
    low: Math.min(open, close) * 0.99,
    close,
    volume: 1_000_000
  };
}

// 净上行序列，供突破型策略（阿里 9988）产生趋势数据。
function uptrendBars(): PriceBar[] {
  const closes: number[] = [];
  let price = 80;
  for (let i = 0; i < 200; i += 1) {
    price += i % 4 === 3 ? -0.6 : 1.2;
    closes.push(price);
  }
  return closes.map((close, index) => bar(index, close));
}

test("持仓面板：已注册标的进 holdings、含吊灯止损与反T；未注册标的进 uncovered", () => {
  const bars = uptrendBars();
  const positions = [
    { code: "HK.09988", stock_name: "阿里巴巴-W", qty: 300, cost_price: 90, nominal_price: bars.at(-1)!.close, pl_ratio: 12.3 },
    { code: "US.XYZ", stock_name: "某美股", qty: 10, cost_price: 50, nominal_price: 48, pl_ratio: -4 }
  ];
  const panel = buildHoldingsPanel(positions, { "HK.09988": bars });

  assert.equal(panel.holdings.length, 1, "只有阿里进 holdings");
  assert.equal(panel.uncovered.length, 1, "未注册美股进 uncovered");
  assert.equal(panel.uncovered[0].code, "US.XYZ");

  const ali = panel.holdings[0];
  assert.equal(ali.code, "HK.09988");
  assert.equal(ali.styleTag, "动量突破+跟踪");
  assert.equal(ali.qty, 300);
  assert.equal(typeof ali.chandelierStop, "number", "突破型必须给出吊灯止损");
  assert.equal(typeof ali.chandelierBreached, "boolean");
  assert.ok(ali.signal.status === "ready", "有足够 K 线应产出信号状态");
  assert.ok(ali.fanT, "必须携带反T 状态对象");
});

test("持仓面板：缺 K 线的已注册标的降级为 uncovered，不抛错", () => {
  const positions = [{ code: "HK.00981", stock_name: "中芯国际", qty: 500, cost_price: 82, nominal_price: 71, pl_ratio: -13 }];
  const panel = buildHoldingsPanel(positions, {}); // 不提供 K 线
  assert.equal(panel.holdings.length, 0);
  assert.equal(panel.uncovered.length, 1);
  assert.equal(panel.uncovered[0].code, "HK.00981");
});

// 震荡序列，供反T 启用的腾讯（0700）判定阶段。
function oscillatingBars(): PriceBar[] {
  const closes: number[] = [];
  for (let i = 0; i < 220; i += 1) closes.push(400 + Math.sin(i / 9) * 30 + Math.sin(i / 3.1) * 6);
  return closes.map((close, index) => bar(index, close));
}

test("持仓面板：反T 阶段由真实成交判定——最近卖出=已减档等买回", () => {
  const bars = oscillatingBars();
  const positions = [{ code: "HK.00700", stock_name: "腾讯控股", qty: 100, cost_price: 500, nominal_price: bars.at(-1)!.close, pl_ratio: -5 }];
  const deals = {
    "HK.00700": [
      { code: "HK.00700", trd_side: "BUY", qty: 100, price: 480, create_time: "2026-01-02 10:00:00" },
      { code: "HK.00700", trd_side: "SELL", qty: 50, price: 520, create_time: "2026-07-23 13:00:00" } // 最近一笔=卖
    ]
  };
  const panel = buildHoldingsPanel(positions, { "HK.00700": bars }, deals);
  const tx = panel.holdings.find((h) => h.code === "HK.00700");
  assert.ok(tx, "腾讯应进 holdings");
  assert.equal(tx!.fanT.enabled, true, "腾讯反T 启用");
  assert.equal(tx!.lastDeal?.side, "SELL", "最近一笔应识别为卖出（时间倒序取最新）");
  assert.equal(tx!.fanTRealPhase, "reduced", "最近卖出 → 已减档等买回");
  assert.equal(typeof tx!.fanTBuyBackTrigger, "number", "应给出买回触发位");
  assert.equal(typeof tx!.fanTSellTrigger, "number", "应始终给出高卖触发位");
});

test("持仓面板：无卖出记录时反T 判定为满仓可高卖", () => {
  const bars = oscillatingBars();
  const positions = [{ code: "HK.00700", stock_name: "腾讯控股", qty: 100, cost_price: 500, nominal_price: bars.at(-1)!.close, pl_ratio: -5 }];
  const deals = { "HK.00700": [{ code: "HK.00700", trd_side: "BUY", qty: 100, price: 480, create_time: "2026-01-02 10:00:00" }] };
  const panel = buildHoldingsPanel(positions, { "HK.00700": bars }, deals);
  const tx = panel.holdings.find((h) => h.code === "HK.00700")!;
  assert.equal(tx.fanTRealPhase, "full", "最近为买入 → 满仓可高卖");
});
