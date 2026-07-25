import { useState, useEffect } from 'react'

interface StatusInfo {
  version: string
  helen_path: string
}

export function SettingsPage() {
  const [statusInfo, setStatusInfo] = useState<StatusInfo | null>(null)

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

  return (
    <div className="p-6 overflow-y-auto h-full max-w-4xl">
      <h1 className="text-3xl font-bold mb-6">设置</h1>

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
