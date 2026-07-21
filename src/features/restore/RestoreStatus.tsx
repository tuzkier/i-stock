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

export function RestoreStatus({ metadata }: RestoreStatusProps) {
  return (
    <div className="data-notice" data-testid="restore-status">
      {statusLabel(metadata)}
      {metadata.reason ? ` · ${metadata.reason}` : ""}
      {metadata.discardedLayoutKeys?.length ? ` · 已丢弃坏布局 ${metadata.discardedLayoutKeys.join(", ")}` : ""}
    </div>
  );
}
