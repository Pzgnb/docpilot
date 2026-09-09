import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import { ChatPage } from './ChatPage'
import { DebugPage } from './DebugPage'
import { EvaluationPage } from './EvaluationPage'
import { HomePage } from './HomePage'
import { KnowledgeBasePage } from './KnowledgeBasePage'


function jsonResponse(payload: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

function renderRoute(path: string, element: React.ReactNode) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/" element={element} />
        <Route path="/knowledge-bases/:id" element={element} />
        <Route path="/knowledge-bases/:id/chat" element={element} />
        <Route path="/knowledge-bases/:id/debug" element={element} />
        <Route path="/knowledge-bases/:id/evaluations" element={element} />
      </Routes>
    </MemoryRouter>,
  )
}

it('shows knowledge bases on the home page', async () => {
  vi.stubGlobal('fetch', vi.fn(() => jsonResponse([
    {
      id: 'kb-1',
      name: '产品知识库',
      description: '公开演示资料',
      document_count: 3,
      created_at: '2026-09-08T08:00:00Z',
      updated_at: '2026-09-08T08:00:00Z',
    },
  ])))

  renderRoute('/', <HomePage />)

  expect(await screen.findByText('产品知识库')).toBeVisible()
  expect(screen.getByText('3 份文档')).toBeVisible()
})

it('shows document processing status on the knowledge base page', async () => {
  vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/documents')) {
      return jsonResponse([{
        id: 'doc-1', knowledge_base_id: 'kb-1', filename: '退款政策.md',
        media_type: 'text/markdown', status: 'ready', chunk_count: 6,
        error_code: null, error_message: null,
        created_at: '2026-09-08T08:00:00Z', updated_at: '2026-09-08T08:00:00Z',
      }])
    }
    return jsonResponse({ id: 'kb-1', name: '产品知识库', description: '公开演示资料', document_count: 1, created_at: '', updated_at: '' })
  }))

  renderRoute('/knowledge-bases/kb-1', <KnowledgeBasePage />)

  expect(await screen.findByText('退款政策.md')).toBeVisible()
  expect(screen.getByText('处理完成')).toBeVisible()
})

it('shows citation source beside an answered message', async () => {
  vi.stubGlobal('fetch', vi.fn(() => jsonResponse({
    answer: '退款期限为30天。',
    decision: 'answer',
    citations: [{
      chunk_id: 'chunk-1', document_id: 'doc-1', file_name: '退款政策.md',
      content: '用户可在付款后30天内申请退款。',
    }],
    retrieval_trace_id: 'trace-1',
    created_at: '2026-09-08T08:00:00Z',
  })))
  const user = userEvent.setup()
  renderRoute('/knowledge-bases/kb-1/chat', <ChatPage />)

  await user.type(screen.getByLabelText('问题'), '退款多久{enter}')

  expect(await screen.findByText('退款期限为30天。')).toBeVisible()
  expect(screen.getByRole('button', { name: /查看引用：退款政策.md/ })).toBeVisible()
})

it('shows retrieval scores and rank changes', async () => {
  vi.stubGlobal('fetch', vi.fn(() => jsonResponse({
    query: '退款多久', knowledge_base_id: 'kb-1', rerank_status: 'applied',
    hits: [{
      chunk_id: 'chunk-1', knowledge_base_id: 'kb-1', document_id: 'doc-1',
      file_name: '退款政策.md', content: '退款期限为30天。', vector_score: 0.82,
      keyword_score: 1.2, fusion_score: 0.91, rerank_score: 0.97,
      initial_rank: 2, final_rank: 1,
    }],
  })))
  const user = userEvent.setup()
  renderRoute('/knowledge-bases/kb-1/debug', <DebugPage />)

  await user.type(screen.getByLabelText('调试问题'), '退款多久')
  await user.click(screen.getByRole('button', { name: '运行检索' }))

  expect(await screen.findByText('退款政策.md')).toBeVisible()
  expect(screen.getByText('2 → 1')).toBeVisible()
})

it('shows evaluation summary and failure type', async () => {
  vi.stubGlobal('fetch', vi.fn(() => jsonResponse({
    id: 'run-1', knowledge_base_id: 'kb-1', total: 10, passed: 8, pass_rate: 0.8,
    created_at: '2026-09-08T08:00:00Z',
    results: [{
      case_id: 'case-1', passed: false, error_type: 'not_retrieved',
      message: '未召回预期文档', retrieval_trace_id: 'trace-1',
    }],
  })))
  const user = userEvent.setup()
  renderRoute('/knowledge-bases/kb-1/evaluations', <EvaluationPage />)

  await user.click(screen.getByRole('button', { name: '运行全部评测' }))

  expect(await screen.findByText('80%')).toBeVisible()
  expect(screen.getByText('未召回')).toBeVisible()
})
