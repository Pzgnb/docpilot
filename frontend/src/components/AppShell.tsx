import type { ReactNode } from 'react'
import { NavLink, useParams } from 'react-router-dom'

export function AppShell({ children }: { children: ReactNode }) {
  const { id } = useParams()
  const items = id
    ? [
        ['资料库', `/knowledge-bases/${id}`],
        ['知识问答', `/knowledge-bases/${id}/chat`],
        ['检索调试', `/knowledge-bases/${id}/debug`],
        ['效果评测', `/knowledge-bases/${id}/evaluations`],
      ]
    : []
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <NavLink className="brand" to="/" aria-label="DocPilot 首页">
          <span className="brand-mark">D</span>
          <span><strong>DocPilot</strong><small>知识可信，答案可查</small></span>
        </NavLink>
        <nav aria-label="主导航">
          <NavLink to="/" end>知识库</NavLink>
          {items.map(([label, path]) => <NavLink key={path} to={path} end>{label}</NavLink>)}
        </nav>
        <div className="sidebar-foot">
          <span className="live-dot" /> 本地工作区
        </div>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  )
}
