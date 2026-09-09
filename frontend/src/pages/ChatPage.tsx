import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { ChatResponse } from '../api/types'
import { CitationCard } from '../components/CitationCard'
import { AppPage } from './HomePage'

type Message = { question: string; response: ChatResponse }

export function ChatPage() {
  const { id = '' } = useParams()
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [busy, setBusy] = useState(false)

  async function submit() {
    if (!question.trim() || busy) return
    const current = question.trim(); setQuestion(''); setBusy(true)
    try {
      const response = await api<ChatResponse>('/api/chat', {
        method: 'POST', body: JSON.stringify({ knowledge_base_id: id, question: current }),
      })
      setMessages((rows) => [...rows, { question: current, response }])
    } finally { setBusy(false) }
  }

  return <AppPage eyebrow="知识检索 / 问答" title="知识问答" description="答案严格绑定检索证据；点击引用即可核对原文。">
    <section className="chat-panel">
      <div className="conversation" aria-live="polite">
        {messages.length === 0 && <div className="chat-welcome"><span className="spark">✦</span><h2>从资料中获得可核验答案</h2><p>试试询问退款期限、账号规则或产品使用方式。</p></div>}
        {messages.map((message, index) => <div className="message-group" key={`${message.question}-${index}`}><div className="user-message">{message.question}</div><div className="assistant-message"><div className="answer-label"><span>DocPilot</span><span className={`decision ${message.response.decision}`}>{message.response.decision === 'answer' ? '依据资料回答' : '资料不足'}</span></div><p>{message.response.answer}</p>{message.response.citations.length > 0 && <div className="citations"><h3>引用来源</h3>{message.response.citations.map((citation, citationIndex) => <CitationCard key={citation.chunk_id} citation={citation} index={citationIndex + 1} />)}</div>}</div></div>)}
      </div>
      <div className="composer"><label htmlFor="question">问题</label><textarea id="question" value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit() } }} placeholder="输入问题，Enter 发送，Shift + Enter 换行" /><button className="send-button" type="button" onClick={submit} disabled={busy || !question.trim()}>{busy ? '检索中' : '发送'}</button></div>
    </section>
  </AppPage>
}
