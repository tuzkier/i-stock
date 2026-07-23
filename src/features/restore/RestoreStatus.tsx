import { resolveRestoreTone } from "../presentation/tone";
import type { WorkspaceRestoreMetadata } from "../../types";

type RestoreStatusProps = {
  metadata: WorkspaceRestoreMetadata;
};

function statusLabel(metadata: WorkspaceRestoreMetadata) {
  if (metadata.status === "restored") return "已恢复";
  if (metadata.status === "partial") return "已从旧存储迁移";
  if (metadata.status === "default_fallback") return "已回退默认布局";
  return "恢复失败";
}

function toneClassName(tone: ReturnType<typeof resolveRestoreTone>) {
  if (tone === "warning") return "notice--warning";
  if (tone === "info") return "notice--info";
  return "restore-status--normal";
}

export function RestoreStatus({ metadata }: RestoreStatusProps) {
  const tone = resolveRestoreTone(metadata);
  const detailParts = [
    metadata.reason ? `原因：${metadata.reason}` : "",
    metadata.discardedLayoutKeys?.length
      ? `已丢弃坏布局：${metadata.discardedLayoutKeys.join(", ")}`
      : "",
    metadata.migratedFromLegacy ? "已从旧存储迁移" : "",
    typeof metadata.snapshotBytes === "number" ? `快照 ${metadata.snapshotBytes} 字节` : ""
  ].filter(Boolean);

  return (
    <div className={`restore-status ${toneClassName(tone)}`} data-testid="restore-status">
      <span data-testid="restore-status-label">{statusLabel(metadata)}</span>
      {detailParts.length > 0 && (
        <details className="restore-status-details" data-testid="restore-status-details">
          <summary>技术详情</summary>
          <ul>
            {detailParts.map((part) => (
              <li key={part}>{part}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
