import { useEffect, useState, useCallback, type ReactNode } from 'react'
import { getStoredToken, setStoredToken, onAuthRequired } from '@/services/api'

interface Props {
  children: ReactNode
}

/**
 * Auth gate: 在首次 401 或 token 缺失时弹出输入框。
 * 一旦用户输入正确 token 并存入 localStorage，子组件即可正常渲染。
 */
export function AuthGate({ children }: Props) {
  const [token, setToken] = useState<string>(() => getStoredToken())
  const [prompting, setPrompting] = useState(false)

  const askForToken = useCallback(() => {
    setPrompting(true)
  }, [])

  useEffect(() => {
    const unsub = onAuthRequired(askForToken)
    return unsub
  }, [askForToken])

  // 初次启动：主动探测一次 /api/status，若 401 则立即弹框
  useEffect(() => {
    if (token) return // 已有 token，跳过探测
    const probe = async () => {
      try {
        const resp = await fetch('/api/status')
        if (resp.status === 401 || resp.status === 403) {
          setPrompting(true)
        }
      } catch {
        // 网络错误（后端未启动）：不弹，让用户看到正常的连接错误
      }
    }
    probe()
  }, [token])

  const handleSubmit = (value: string) => {
    const trimmed = value.trim()
    if (!trimmed) return
    setStoredToken(trimmed)
    setToken(trimmed)
    setPrompting(false)
    // 触发页面重载以便所有已缓存的请求带上 token
    window.location.reload()
  }

  const handleClear = () => {
    setStoredToken('')
    setToken('')
    setPrompting(false)
  }

  // 没 token 且不在弹框状态：等 probe 决定
  if (!token && !prompting) {
    return null
  }

  if (prompting) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
        <form
          className="bg-card border rounded-lg shadow-lg p-6 w-96 space-y-4"
          onSubmit={(e) => {
            e.preventDefault()
            const input = (e.currentTarget.elements.namedItem('token') as HTMLInputElement).value
            handleSubmit(input)
          }}
        >
          <h2 className="text-lg font-semibold">需要访问 Token</h2>
          <p className="text-sm text-muted-foreground">
            后端要求 X-Helen-Token。请输入启动日志中打印的 token，或 <code className="font-mono">~/.helen/webui_token</code> 文件中的值。
          </p>
          <input
            name="token"
            type="password"
            autoFocus
            placeholder="粘贴 token"
            className="w-full px-3 py-2 border rounded font-mono text-sm"
          />
          <div className="flex gap-2 justify-end">
            {token && (
              <button
                type="button"
                onClick={handleClear}
                className="px-3 py-1.5 text-sm border rounded hover:bg-destructive/10"
              >
                清除
              </button>
            )}
            <button
              type="submit"
              className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded hover:bg-primary/90"
            >
              确认
            </button>
          </div>
        </form>
      </div>
    )
  }

  return <>{children}</>
}
