export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="empty-state">
      <div className="empty-mark" aria-hidden="true">⌁</div>
      <strong>{title}</strong>
      <p>{detail}</p>
    </div>
  )
}
