/**
 * TranscriptViewerModal - 查看 session 完整历史记录的弹窗组件
 *
 * 功能：
 * - 显示完整 transcript（user/assistant/tool 消息）
 * - 搜索/过滤功能
 * - 按角色过滤
 * - 消息时间戳
 * - Markdown 渲染
 */

import { useState, useEffect, useCallback } from 'react'
import { api } from '../../services/api'

interface TranscriptEntry {
  type?: string
  role?: string
  content?: string
  timestamp?: string
  uuid?: string
  tool_calls?: Array<{ name: string; arguments: string }>
  _line?: number
}

interface TranscriptViewerModalProps {
  sessionId: string
  onClose: () => void
}

// 角色颜色映射
const ROLE_COLORS: Record<string, string> = {
  user: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  assistant: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  tool: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  system: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
}

export function TranscriptViewerModal({ sessionId, onClose }: TranscriptViewerModalProps) {
  const [entries, setEntries] = useState<TranscriptEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [roleFilter, setRoleFilter] = useState<string>('all')
  const [selectedEntry, setSelectedEntry] = useState<TranscriptEntry | null>(null)

  // 加载 transcript
  useEffect(() => {
    loadTranscript()
  }, [sessionId])

  const loadTranscript = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.sessions.getTranscript(sessionId)
      setEntries(data.entries || data || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load transcript')
    } finally {
      setLoading(false)
    }
  }

  // 过滤消息
  const filteredEntries = entries.filter(entry => {
    // 角色过滤
    if (roleFilter !== 'all' && entry.role !== roleFilter) {
      return false
    }
    // 搜索过滤
    if (searchQuery) {
      const content = String(entry.content || '').toLowerCase()
      const query = searchQuery.toLowerCase()
      return content.includes(query)
    }
    return true
  })

  // 格式化时间戳
  const formatTimestamp = (ts?: string) => {
    if (!ts) return ''
    try {
      const date = new Date(ts)
      return date.toLocaleString()
    } catch {
      return ts
    }
  }

  // 截短内容显示
  const truncateContent = (content: string, maxLen: number = 500) => {
    if (content.length <= maxLen) return content
    return content.slice(0, maxLen) + '...'
  }

  // 处理点击遮罩关闭
  const handleBackdropClick = useCallback((e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }, [onClose])

  // ESC 键关闭
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [onClose])

  // 统计信息
  const stats = {
    total: entries.length,
    user: entries.filter(e => e.role === 'user').length,
    assistant: entries.filter(e => e.role === 'assistant').length,
    tool: entries.filter(e => e.role === 'tool').length,
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={handleBackdropClick}
    >
      <div className="relative flex h-[85vh] w-[90vw] max-w-6xl flex-col rounded-lg bg-white shadow-2xl dark:bg-gray-800">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4 dark:border-gray-700">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              📖 Transcript Viewer
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Session: <code className="rounded bg-gray-100 px-1 py-0.5 text-xs dark:bg-gray-700">{sessionId}</code>
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-3 border-b border-gray-200 px-6 py-3 dark:border-gray-700">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <input
              type="text"
              placeholder="搜索消息内容..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 pl-10 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            />
            <svg className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>

          {/* Role Filter */}
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          >
            <option value="all">所有角色</option>
            <option value="user">User</option>
            <option value="assistant">Assistant</option>
            <option value="tool">Tool</option>
          </select>

          {/* Stats */}
          <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
            <span className="rounded bg-gray-100 px-2 py-1 dark:bg-gray-700">
              {filteredEntries.length} / {stats.total} 条消息
            </span>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading ? (
            <div className="flex h-full items-center justify-center">
              <div className="text-gray-500 dark:text-gray-400">加载中...</div>
            </div>
          ) : error ? (
            <div className="flex h-full items-center justify-center">
              <div className="text-red-500">错误: {error}</div>
            </div>
          ) : filteredEntries.length === 0 ? (
            <div className="flex h-full items-center justify-center">
              <div className="text-gray-500 dark:text-gray-400">
                {searchQuery || roleFilter !== 'all' ? '没有匹配的消息' : '没有消息'}
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredEntries.map((entry, index) => {
                const role = entry.role || 'unknown'
                const roleColor = ROLE_COLORS[role] || ROLE_COLORS.system
                const content = String(entry.content || '')

                return (
                  <div
                    key={entry._line || index}
                    className="group rounded-lg border border-gray-200 p-4 hover:border-gray-300 hover:shadow-sm dark:border-gray-700 dark:hover:border-gray-600"
                  >
                    {/* Message Header */}
                    <div className="mb-2 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className={`rounded px-2 py-0.5 text-xs font-medium ${roleColor}`}>
                          {role}
                        </span>
                        {entry.timestamp && (
                          <span className="text-xs text-gray-400">
                            {formatTimestamp(entry.timestamp)}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {entry.uuid && (
                          <code className="text-xs text-gray-400 opacity-0 group-hover:opacity-100">
                            {entry.uuid.slice(0, 8)}
                          </code>
                        )}
                        <button
                          onClick={() => setSelectedEntry(entry)}
                          className="rounded p-1 text-gray-400 opacity-0 hover:bg-gray-100 hover:text-gray-600 group-hover:opacity-100 dark:hover:bg-gray-700 dark:hover:text-gray-300"
                          title="查看完整内容"
                        >
                          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                        </button>
                      </div>
                    </div>

                    {/* Message Content */}
                    <div className="whitespace-pre-wrap break-words text-sm text-gray-700 dark:text-gray-300">
                      {truncateContent(content)}
                    </div>

                    {/* Tool Calls */}
                    {entry.tool_calls && entry.tool_calls.length > 0 && (
                      <div className="mt-2 rounded bg-purple-50 p-2 text-xs dark:bg-purple-900/20">
                        <span className="font-medium text-purple-700 dark:text-purple-300">Tool Calls: </span>
                        {entry.tool_calls.map((tc, i) => (
                          <span key={i} className="text-purple-600 dark:text-purple-400">
                            {tc.name}()
                            {i < entry.tool_calls!.length - 1 ? ', ' : ''}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Detail Modal */}
        {selectedEntry && (
          <div
            className="absolute inset-0 z-10 flex items-center justify-center bg-black/30"
            onClick={() => setSelectedEntry(null)}
          >
            <div
              className="max-h-[80%] w-[80%] max-w-3xl overflow-auto rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Message Detail
                </h3>
                <button
                  onClick={() => setSelectedEntry(null)}
                  className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div className="mb-4 flex items-center gap-2">
                <span className={`rounded px-2 py-0.5 text-xs font-medium ${ROLE_COLORS[selectedEntry.role || 'system'] || ROLE_COLORS.system}`}>
                  {selectedEntry.role || 'unknown'}
                </span>
                {selectedEntry.timestamp && (
                  <span className="text-sm text-gray-500">
                    {formatTimestamp(selectedEntry.timestamp)}
                  </span>
                )}
                {selectedEntry.uuid && (
                  <code className="text-xs text-gray-400">{selectedEntry.uuid}</code>
                )}
              </div>
              <pre className="whitespace-pre-wrap break-words rounded-lg bg-gray-50 p-4 text-sm text-gray-700 dark:bg-gray-900 dark:text-gray-300">
                {String(selectedEntry.content || '')}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
