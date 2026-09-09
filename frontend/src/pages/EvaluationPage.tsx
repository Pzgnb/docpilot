import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { EvaluationCase, EvaluationRun } from '../api/types'
import { EmptyState } from '../components/EmptyState'
import { AppPage } from './HomePage'

const errorLabels: Record<string, string> = { none: '通过', not_retrieved: '未召回', ranked_too_low: '排名过低', answer_omission: '回答遗漏', wrong_citation: '引用错误', wrong_refusal: '错误拒答' }

export function EvaluationPage() {
  const { id = '' } = useParams()
  const [cases, setCases] = useState<EvaluationCase[]>([])
  const [run, setRun] = useState<EvaluationRun | null>(null)
  const [running, setRunning] = useState(false)

  useEffect(() => { api<EvaluationCase[]>(`/api/evaluations/cases?knowledge_base_id=${id}`).then((rows) => setCases(Array.isArray(rows) ? rows : [])).catch(() => setCases([])) }, [id])

  async function runAll() {
    setRunning(true)
    try { setRun(await api<EvaluationRun>('/api/evaluations/run', { method: 'POST', body: JSON.stringify({ knowledge_base_id: id }) })) } finally { setRunning(false) }
  }

  return <AppPage eyebrow="质量工具 / 评测" title="效果评测" description="用固定问题集重复验证召回、回答、引用与拒答行为。" actions={<button className="button primary" type="button" onClick={runAll} disabled={running}>{running ? '评测中…' : '运行全部评测'}</button>}>
    <div className="metric-grid"><article className="metric-card"><span>评测用例</span><strong>{run?.total ?? cases.length}</strong><small>覆盖已知问题与未知问题</small></article><article className="metric-card accent"><span>本次通过率</span><strong>{run ? `${Math.round(run.pass_rate * 100)}%` : '—'}</strong><small>{run ? `${run.passed} / ${run.total} 通过` : '运行后生成结果'}</small></article><article className="metric-card"><span>失败项</span><strong>{run ? run.total - run.passed : '—'}</strong><small>可按错误类型定位原因</small></article></div>
    <section className="panel"><div className="section-head"><div><h2>评测结果</h2><p>失败项保留对应检索轨迹，便于回溯。</p></div></div>{!run ? <EmptyState title="尚未运行评测" detail="准备好测试用例后运行，查看真实通过率。" /> : run.results.length === 0 ? <EmptyState title="没有评测用例" detail="先通过接口添加测试用例。" /> : <div className="table-wrap"><table><thead><tr><th>状态</th><th>错误类型</th><th>诊断</th><th>检索轨迹</th></tr></thead><tbody>{run.results.map((result, index) => <tr key={result.case_id ?? index}><td><span className={`result-dot ${result.passed ? 'pass' : 'fail'}`} />{result.passed ? '通过' : '失败'}</td><td><span className="error-chip">{errorLabels[result.error_type]}</span></td><td>{result.message}</td><td><code>{result.retrieval_trace_id.slice(0, 8)}</code></td></tr>)}</tbody></table></div>}</section>
  </AppPage>
}
