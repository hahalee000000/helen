import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { I18nProvider } from './i18n'
import { setStoredToken } from './services/api'
import App from './App'
import './index.css'

// ── URL token 自动注入 ──────────────────────────────────────
// 启动时检测 URL 中的 ?token=xxx，自动存入 localStorage 并从 URL 移除
// 这样 vite 的 o 快捷键可以直接打开带 token 的 URL，前端自动完成认证
;(function bootstrapTokenFromURL() {
  try {
    const params = new URLSearchParams(window.location.search)
    const token = params.get('token')
    if (token) {
      setStoredToken(token)
      // 从 URL 移除 token 参数，保持 history 干净
      params.delete('token')
      const newUrl = params.toString()
        ? `${window.location.pathname}?${params.toString()}`
        : window.location.pathname
      window.history.replaceState({}, '', newUrl)
    }
  } catch {
    // 忽略（隐私模式等）
  }
})()

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <I18nProvider>
          <App />
        </I18nProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
