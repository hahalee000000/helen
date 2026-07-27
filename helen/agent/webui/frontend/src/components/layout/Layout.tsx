import { ReactNode, useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { MessageSquare, Settings } from 'lucide-react'
import { cn } from '@/utils/cn'

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const [version, setVersion] = useState('')

  useEffect(() => {
    fetch('/api/status')
      .then(r => r.json())
      .then(data => setVersion(data.version || ''))
      .catch(() => {})
  }, [])

  const navItems = [
    { path: '/', label: '聊天', icon: MessageSquare },
    { path: '/settings', label: '设置', icon: Settings },
  ]

  return (
    <div className="flex h-screen bg-background">
      {/* 侧边栏 */}
      <aside className="w-64 border-r bg-card">
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="p-6 border-b flex items-center gap-3">
            <img src="/helen-logo-64.png" alt="Helen" className="w-10 h-10 rounded-lg" />
            <div>
              <h1 className="text-2xl font-bold text-primary">Helen</h1>
              <p className="text-sm text-muted-foreground mt-1">Web UI</p>
            </div>
          </div>

          {/* 导航 */}
          <nav className="flex-1 p-4">
            <ul className="space-y-2">
              {navItems.map((item) => {
                const Icon = item.icon
                const isActive = location.pathname === item.path ||
                  (item.path !== '/' && location.pathname.startsWith(item.path))
                return (
                  <li key={item.path}>
                    <Link
                      to={item.path}
                      className={cn(
                        'flex items-center gap-3 px-4 py-3 rounded-lg transition-colors',
                        isActive
                          ? 'bg-primary text-primary-foreground'
                          : 'hover:bg-accent text-foreground'
                      )}
                    >
                      <Icon className="h-5 w-5" />
                      <span>{item.label}</span>
                    </Link>
                  </li>
                )
              })}
            </ul>
          </nav>

          {/* 底部 */}
          <div className="p-4 border-t">
            <p className="text-xs text-muted-foreground text-center">
              Helen Programming Agent{version ? ` v${version}` : ''}
            </p>
          </div>
        </div>
      </aside>

      {/* 主内容 */}
      <main className="flex-1 overflow-hidden">
        {children}
      </main>
    </div>
  )
}
