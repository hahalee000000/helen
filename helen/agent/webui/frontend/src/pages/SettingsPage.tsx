import { useState, useEffect } from 'react'
import { getStoredToken, setStoredToken, clearStoredToken } from '@/services/api'

interface StatusInfo {
  version: string
  helen_path: string
}

export function SettingsPage() {
  const [statusInfo, setStatusInfo] = useState<StatusInfo | null>(null)
  const [token, setToken] = useState<string>(() => getStoredToken())
  const [tokenInput, setTokenInput] = useState<string>('')
  const [tokenSaved, setTokenSaved] = useState(false)

  const loadStatus = async () => {
    try {
      const response = await fetch('/api/status')
      const data = await response.json()
      setStatusInfo({
        version: data.version || '',
        ...data.config,
      })
    } catch (error) {
      console.error('Failed to load status:', error)
    }
  }

  useEffect(() => {
    loadStatus()
  }, [])

  const handleSaveToken = () => {
    const trimmed = tokenInput.trim()
    if (!trimmed) return
    setStoredToken(trimmed)
    setToken(trimmed)
    setTokenInput('')
    setTokenSaved(true)
    setTimeout(() => setTokenSaved(false), 2000)
  }

  const handleClearToken = () => {
    clearStoredToken()
    setToken('')
  }

  return (
    <div className="p-6 overflow-y-auto h-full max-w-4xl">
      <h1 className="text-3xl font-bold mb-6">设置</h1>

      {/* 鉴权 Token */}
      <section className="mb-6">
        <h2 className="text-xl font-semibold mb-4">访问 Token</h2>

        <div className="border rounded-lg p-4 bg-card space-y-3">
          {token ? (
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">
                当前 token 已保存（<span className="font-mono">{token.slice(0, 8)}…</span>）
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => navigator.clipboard?.writeText(token)}
                  className="px-3 py-1.5 text-sm border rounded hover:bg-accent"
                >
                  复制
                </button>
                <button
                  onClick={handleClearToken}
                  className="px-3 py-1.5 text-sm border rounded hover:bg-destructive/10"
                >
                  清除
                </button>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              未设置 token。如果后端启用鉴权，发起请求时会被要求输入。
            </p>
          )}

          <div className="flex gap-2 items-center">
            <input
              type="password"
              placeholder="输入新 token"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleSaveToken() }}
              className="flex-1 px-3 py-1.5 border rounded font-mono text-sm"
            />
            <button
              onClick={handleSaveToken}
              disabled={!tokenInput.trim()}
              className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50"
            >
              保存
            </button>
          </div>
          {tokenSaved && (
            <p className="text-xs text-green-600">✓ Token 已保存</p>
          )}
          <p className="text-xs text-muted-foreground">
            来源：后端启动日志打印的 token，或 <code className="font-mono">~/.helen/webui_token</code> 文件。
          </p>
        </div>
      </section>

      {/* 系统信息 */}
      <section>
        <h2 className="text-xl font-semibold mb-4">系统信息</h2>

        <div className="border rounded-lg p-4 bg-card">
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">版本</dt>
              <dd>{statusInfo?.version ? `v${statusInfo.version}` : '加载中...'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Helen 路径</dt>
              <dd className="font-mono text-xs">{statusInfo?.helen_path ?? '加载中...'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">后端 API</dt>
              <dd className="font-mono text-xs">通过 vite proxy 转发 (同源)</dd>
            </div>
          </dl>
        </div>
      </section>
    </div>
  )
}
