import { useState } from 'react'
import type { Citation } from '../api/types'

export function CitationCard({ citation, index }: { citation: Citation; index: number }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="citation-card">
      <button
        className="citation-trigger"
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="citation-index">{index}</span>
        <span>查看引用：{citation.file_name}</span>
        <span aria-hidden="true">{open ? '−' : '+'}</span>
      </button>
      {open && <blockquote>{citation.content}</blockquote>}
    </div>
  )
}
