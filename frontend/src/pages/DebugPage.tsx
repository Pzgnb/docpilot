import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { RetrievalTrace } from '../api/types'
import { EmptyState } from '../components/EmptyState'
import { ScoreBar } from '../components/ScoreBar'
import { AppPage } from './HomePage'

export function DebugPage() {
  const { id = '' } = useParams()
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(5)
  const [vectorWeight, setVectorWeight] = useState(0.65)
  const [trace, setTrace] = useState<RetrievalTrace | null>(null)
  const keywordWeight = Number((1 - vectorWeight).toFixed(2))

  async function run(event: React.FormEvent) {
    event.preventDefault()
    const result = await api<RetrievalTrace>('/api/retrieval/debug', {
      method: 'POST', body: JSON.stringify({ query, knowledge_base_id: id, top_k: topK, vector_weight: vectorWeight, keyword_weight: keywordWeight }),
    })
    setTrace(result)
  }

  return <AppPage eyebrow="质量工具 / 检索" title="检索调试" description="查看候选片段如何经过向量、关键词融合与重排得到最终顺序。">
    <form className="debug-controls panel" onSubmit={run}><div className="field grow"><label htmlFor="debug-query">调试问题</label><input id="debug-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="输入一条真实用户问题" required /></div><div className="field compact"><label htmlFor="top-k">Top K</label><input id="top-k" type="number" min="1" max="20" value={topK} onChange={(event) => setTopK(Number(event.target.value))} /></div><div className="field weight"><label htmlFor="vector-weight">向量权重 {vectorWeight.toFixed(2)}</label><input id="vector-weight" type="range" min="0" max="1" step="0.05" value={vectorWeight} onChange={(event) => setVectorWeight(Number(event.target.value))} /><small>关键词权重 {keywordWeight.toFixed(2)}</small></div><button className="button primary" type="submit">运行检索</button></form>
    {!trace ? <EmptyState title="等待一次检索" detail="运行后将显示分数构成、初始名次和最终名次。" /> : <section className="panel"><div className="section-head"><div><h2>候选结果</h2><p>{trace.rerank_status === 'applied' ? '已执行 Rerank' : '未配置 Rerank，按融合分排序'}</p></div><span className="count-pill">{trace.hits.length} 条</span></div>{trace.hits.length === 0 ? <EmptyState title="没有召回片段" detail="检查文档状态或尝试更具体的问题。" /> : <div className="table-wrap"><table><thead><tr><th>排名</th><th>来源与片段</th><th>向量分</th><th>关键词分</th><th>融合分</th><th>重排分</th></tr></thead><tbody>{trace.hits.map((hit) => <tr key={hit.chunk_id}><td><strong className="rank-change">{hit.initial_rank} → {hit.final_rank}</strong></td><td className="content-cell"><strong>{hit.file_name}</strong><p>{hit.content}</p></td><td><ScoreBar value={hit.vector_score} label="向量分" /></td><td>{hit.keyword_score.toFixed(3)}</td><td><ScoreBar value={hit.fusion_score} label="融合分" /></td><td>{hit.rerank_score?.toFixed(3) ?? '—'}</td></tr>)}</tbody></table></div>}</section>}
  </AppPage>
}
