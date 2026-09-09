import type { DocumentStatus } from '../api/types'

const labels: Record<DocumentStatus, string> = {
  pending: '等待处理',
  processing: '处理中',
  ready: '处理完成',
  failed: '处理失败',
}

export function StatusBadge({ status }: { status: DocumentStatus }) {
  return <span className={`status-badge status-${status}`}>{labels[status]}</span>
}
