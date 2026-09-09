import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { KnowledgeBase, KnowledgeDocument } from '../api/types'
import { EmptyState } from '../components/EmptyState'
import { StatusBadge } from '../components/StatusBadge'
import { AppPage } from './HomePage'

export function KnowledgeBasePage() {
  const { id = '' } = useParams()
  const [knowledgeBase, setKnowledgeBase] = useState<KnowledgeBase | null>(null)
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [busy, setBusy] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    Promise.all([
      api<KnowledgeBase>(`/api/knowledge-bases/${id}`),
      api<KnowledgeDocument[]>(`/api/knowledge-bases/${id}/documents`),
    ]).then(([kb, docs]) => { setKnowledgeBase(kb); setDocuments(docs) })
  }, [id])

  async function upload(file: File) {
    setBusy(true)
    const form = new FormData(); form.append('file', file)
    const created = await api<KnowledgeDocument>(`/api/knowledge-bases/${id}/documents`, { method: 'POST', body: form })
    setDocuments((rows) => [...rows, created])
    setBusy(false)
  }

  async function process(documentId: string, action: 'process' | 'retry') {
    const updated = await api<KnowledgeDocument>(`/api/documents/${documentId}/${action}`, { method: 'POST' })
    setDocuments((rows) => rows.map((row) => row.id === updated.id ? updated : row))
  }

  return <AppPage eyebrow="知识资产 / 资料库" title={knowledgeBase?.name ?? '知识库详情'} description={knowledgeBase?.description || '上传并处理用于问答的企业文档。'} actions={<><Link className="button" to={`/knowledge-bases/${id}/chat`}>开始问答</Link><button className="button primary" type="button" onClick={() => inputRef.current?.click()} disabled={busy}>上传文档</button><input ref={inputRef} hidden type="file" accept=".pdf,.docx,.md,.txt" onChange={(event) => event.target.files?.[0] && upload(event.target.files[0])} /></>}>
    <section className="panel"><div className="section-head"><div><h2>文档</h2><p>支持 PDF、DOCX、Markdown 和 TXT</p></div><span className="count-pill">{documents.length} 份</span></div>
      {documents.length === 0 ? <EmptyState title="尚未上传文档" detail="上传公开资料，处理完成后即可检索。" /> : <div className="document-list">{documents.map((document) => <article className="document-row" key={document.id}><div className="file-mark">{document.filename.split('.').pop()?.toUpperCase()}</div><div className="document-main"><strong>{document.filename}</strong><span>{document.chunk_count ? `${document.chunk_count} 个文本片段` : '等待建立索引'}</span>{document.error_message && <small className="error-text">{document.error_message}</small>}</div><StatusBadge status={document.status} />{document.status === 'pending' && <button className="text-button" onClick={() => process(document.id, 'process')}>开始处理</button>}{document.status === 'failed' && <button className="text-button" onClick={() => process(document.id, 'retry')}>重新处理</button>}</article>)}</div>}
    </section>
  </AppPage>
}
