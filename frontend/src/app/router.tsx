import { createBrowserRouter } from 'react-router-dom'
import { AppShell } from '../components/AppShell'
import { ChatPage } from '../pages/ChatPage'
import { DebugPage } from '../pages/DebugPage'
import { EvaluationPage } from '../pages/EvaluationPage'
import { HomePage } from '../pages/HomePage'
import { KnowledgeBasePage } from '../pages/KnowledgeBasePage'

const withShell = (page: React.ReactNode) => <AppShell>{page}</AppShell>

export const router = createBrowserRouter([
  { path: '/', element: withShell(<HomePage />) },
  { path: '/knowledge-bases/:id', element: withShell(<KnowledgeBasePage />) },
  { path: '/knowledge-bases/:id/chat', element: withShell(<ChatPage />) },
  { path: '/knowledge-bases/:id/debug', element: withShell(<DebugPage />) },
  { path: '/knowledge-bases/:id/evaluations', element: withShell(<EvaluationPage />) },
])
