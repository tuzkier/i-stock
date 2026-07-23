import { useCallback, useEffect, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";
import type { CoveredHolding, HoldingBase } from "../../domain/holdings-panel";

type HoldingsResponse = {
  env: string;
  range: string;
  generatedAt: number;
  holdings: CoveredHolding[];
  uncovered: HoldingBase[];
};

const POLL_MS = 60_000;

function fmt(value?: number | null, digits = 2) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) return "--";
  return Number(value).toFixed(digits);
}
function pct(value?: number | null) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) return "--";
  return `${Number(value).toFixed(1)}%`;
}
function plClass(value?: number) {
  if (value === undefined || value === null) return "";
  return value > 0 ? "pl-up" : value < 0 ? "pl-down" : "";
}
function clock(ts?: number) {
  if (!ts) return "--";
  const d = new Date(ts);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

function HoldingCard({ holding }: { holding: CoveredHolding }) {
  const { signal, fanT } = holding;
  const L = signal.levels;
  return (
    <section className="holding-card" data-testid={`holding-${holding.code}`}>
      <div className="holding-head">
        <div>
          <strong>{holding.name}</strong> <span className="holding-code">{holding.code}</span>
          <span className="holding-style">{holding.styleTag}</span>
        </div>
        <div className={`holding-pl ${plClass(holding.plRatio)}`}>{pct(holding.plRatio)}</div>
      </div>
      <div className="holding-pos">
        {holding.qty} 股 @ 成本 {fmt(holding.cost)}｜现价 {fmt(holding.price)}
      </div>
      <div className="holding-stance">{signal.stanceLabel}</div>

      <div className="holding-levels">
        {signal.holding ? (
          <>
            {L.takeProfit !== undefined && (
              <div><span>止盈线</span><strong>{fmt(L.takeProfit)}</strong></div>
            )}
            {L.stopLoss !== undefined && (
              <div><span>止损线</span><strong>{fmt(L.stopLoss)}</strong></div>
            )}
            {L.sellTargetSma !== undefined && (
              <div><span>卖出目标</span><strong>{fmt(L.sellTargetSma)}</strong></div>
            )}
            {L.addPositionTrigger !== undefined && (
              <div><span>加仓触发</span><strong>{fmt(L.addPositionTrigger)}</strong></div>
            )}
          </>
        ) : (
          <>
            {L.nextBuyTrigger !== undefined && (
              <div><span>下一买点</span><strong>{fmt(L.nextBuyTrigger)}</strong></div>
            )}
            {L.sellTargetSma !== undefined && (
              <div><span>回归卖出目标</span><strong>{fmt(L.sellTargetSma)}</strong></div>
            )}
          </>
        )}
        {holding.chandelierStop !== undefined && (
          <div className={holding.chandelierBreached ? "level-breached" : ""}>
            <span>吊灯止损{holding.chandelierBreached ? "（已破）" : ""}</span>
            <strong>{fmt(holding.chandelierStop)}</strong>
          </div>
        )}
      </div>

      <div className={`holding-fant ${fanT.enabled ? "on" : "off"}`}>
        {fanT.enabled ? (
          fanT.phase === "full" ? (
            <>反T·满仓等高卖：高卖触发 <strong>{fmt(fanT.sellTrigger)}</strong>（近1年累计价差 {pct(fanT.totalSpreadPct)}）</>
          ) : (
            <>反T·已高卖等买回：买回触发 <strong>{fmt(fanT.buyBackTrigger)}</strong>，认错追高 {fmt(fanT.chaseStop)}（累计价差 {pct(fanT.totalSpreadPct)}）</>
          )
        ) : (
          <>反T 不适用：本票实证为负期望（趋势票易卖飞），只做趋势持有与离场。</>
        )}
      </div>
    </section>
  );
}

export function HoldingsPanel() {
  const [data, setData] = useState<HoldingsResponse | undefined>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | undefined>();
  const timer = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/holdings?env=REAL&range=1y");
      const payload = await res.json();
      if (!res.ok || payload.error) throw new Error(payload.detail ?? payload.error ?? `HTTP ${res.status}`);
      setData(payload);
      setError(undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    timer.current = setInterval(load, POLL_MS);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [load]);

  return (
    <div className="holdings-panel" data-testid="holdings-panel">
      <div className="holdings-bar">
        <span>真实持仓（FutuOpenD）· 每 60 秒自动刷新</span>
        <span className="holdings-updated">
          更新于 {clock(data?.generatedAt)}
          <button className="icon-button" onClick={load} type="button" aria-label="立即刷新持仓">
            <RefreshCw size={14} className={loading ? "spin" : ""} />
          </button>
        </span>
      </div>
      <p className="holdings-disclaimer">点位由固定策略规则机械计算，仅作技术分析参考，非投资建议；是否操作由你自行判断。</p>

      {error && <p className="holdings-error" data-testid="holdings-error">持仓获取失败：{error}（确认 FutuOpenD 已登录且开放交易查询）</p>}
      {!data && !error && <p className="holdings-loading">加载持仓中…</p>}

      {data && (
        <>
          <div className="holdings-grid">
            {data.holdings.map((h) => (
              <HoldingCard key={h.code} holding={h} />
            ))}
          </div>
          {data.uncovered.length > 0 && (
            <div className="holdings-uncovered">
              <p className="plan-group-title">无定制策略的持仓</p>
              {data.uncovered.map((u) => (
                <div key={u.code} className="uncovered-row">
                  <span>{u.name} <em>{u.code}</em></span>
                  <span className={plClass(u.plRatio)}>{u.qty} 股 @ {fmt(u.cost)}｜现 {fmt(u.price)}｜{pct(u.plRatio)}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
