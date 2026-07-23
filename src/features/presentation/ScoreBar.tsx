import type { CSSProperties } from "react";

type ScoreBarProps = {
  score: number | null;
  /** 当 scoreBand 为 not_applicable 时强制中性不填充（VO-03） */
  notApplicable?: boolean;
};

/**
 * MTS 评分进度条：有限分数映射为 0~100% 填充；null / not_applicable 中性空条。
 * 分数约定与领域一致：约 -100~100，映射到宽度百分比。
 */
export function ScoreBar({ score, notApplicable = false }: ScoreBarProps) {
  const fillable = !notApplicable && typeof score === "number" && Number.isFinite(score);
  const clamped = fillable ? Math.max(-100, Math.min(100, score)) : 0;
  const widthPct = fillable ? ((clamped + 100) / 200) * 100 : 0;

  const fillStyle: CSSProperties = {
    width: `${widthPct}%`,
    opacity: fillable ? 1 : 0
  };

  return (
    <div className="score-bar" data-testid="mts-score-bar" aria-hidden={!fillable}>
      <span className="score-bar__fill" style={fillStyle} />
    </div>
  );
}
