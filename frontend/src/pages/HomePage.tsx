import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { KnowledgeBase } from '../api/types'
import { EmptyState } from '../components/EmptyState'

export function HomePage() {
  const [rows, setRows] = useState<KnowledgeBase[]>([])
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = () => api<KnowledgeBase[]>('/api/knowledge-bases')
    .then(setRows).catch((value: Error) => setError(value.message)).finally(() => setLoading(false))

  useEffect(() => {
    void load()
  }, [])

  async function createKnowledgeBase(event: React.FormEvent) {
    event.preventDefault()
    if (!name.trim()) return
    const created = await api<KnowledgeBase>('/api/knowledge-bases', {
      method: 'POST', body: JSON.stringify({ name, description: '' }),
    })
    setRows((current) => [...current, created])
    setName('')
  }

  return <AppPage eyebrow="知识资产" title="知识库" description="管理文档集合，为问答、检索调试和效果评测提供统一数据源。">
    <form className="quick-create" onSubmit={createKnowledgeBase}>
      <label htmlFor="kb-name">新建知识库</label>
      <input id="kb-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="例如：产品与售后手册" />
      <button className="button primary" type="submit">创建</button>
    </form>
    {error && <p className="notice error">{error}</p>}
    {loading ? <p className="muted">正在加载…</p> : rows.length === 0 ? (
      <EmptyState title="还没有知识库" detail="创建第一个知识库，然后上传公开演示文档。" />
    ) : <div className="card-grid">{rows.map((row) => (
      <Link className="kb-card" to={`/knowledge-bases/${row.id}`} key={row.id}>
        <div className="card-icon">KB</div>
        <div><h2>{row.name}</h2><p>{row.description || '暂无说明'}</p></div>
        <div className="card-meta"><span>{row.document_count} 份文档</span><span>进入 →</span></div>
      </Link>
    ))}</div>}
  </AppPage>
}

export function AppPage({ eyebrow, title, description, actions, children }: { eyebrow: string; title: string; description: string; actions?: React.ReactNode; children: React.ReactNode }) {
  return <div className="page"><header className="page-header"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{actions && <div className="page-actions">{actions}</div>}</header>{children}</div>
}
