import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { MessageList } from './MessageList'
import { MessageInput } from './MessageInput'
import { StatusLine } from './StatusLine'
import { useChat } from '@/hooks/useChat'
import { ArrowDown } from 'lucide-react'

interface ChatWindowProps {
  sessionId: string | null
}

// 距离底部多少像素内算"在底部"
const BOTTOM_THRESHOLD = 50

export function ChatWindow({ sessionId }: ChatWindowProps) {
  const { messages, sendMessage, stopGeneration, isLoading, isConnected, statusline } = useChat(sessionId)
  const containerRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const prevCountRef = useRef(0)
  const wasAtBottomRef = useRef(true)
  const isInitialMountRef = useRef(true)
  const [showScrollBtn, setShowScrollBtn] = useState(false)

  // 判断是否接近底部
  const isNearBottom = (): boolean => {
    const el = containerRef.current
    if (!el) return true
    return el.scrollHeight - el.scrollTop - el.clientHeight < BOTTOM_THRESHOLD
  }

  // 滚动到最底部
  const scrollToBottom = (smooth: boolean = true) => {
    messagesEndRef.current?.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' })
  }

  // 同步捕获每次渲染前的滚动位置（useLayoutEffect 在 DOM 变更后、paint 前运行）
  // 这是判断"用户滚动前是否在底部"的最可靠时机
  useLayoutEffect(() => {
    wasAtBottomRef.current = isNearBottom()
  })

  // 监听滚动事件，更新"回到底部"按钮的可见性
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const handleScroll = () => {
      setShowScrollBtn(!isNearBottom())
    }
    el.addEventListener('scroll', handleScroll, { passive: true })
    return () => el.removeEventListener('scroll', handleScroll)
  }, [])

  // 新消息到达时的自动滚动策略
  useEffect(() => {
    // 首次挂载不滚动（历史消息保持原位）
    if (isInitialMountRef.current) {
      isInitialMountRef.current = false
      prevCountRef.current = messages.length
      return
    }

    const prevCount = prevCountRef.current
    prevCountRef.current = messages.length

    if (messages.length > prevCount) {
      // 新消息（用户发的 或 助手新一轮回复）：强制滚动，保证新对话可见
      scrollToBottom()
      setShowScrollBtn(false)
    } else if (messages.length > 0 && wasAtBottomRef.current) {
      // 同一条消息内容更新（流式输出）：仅当用户在底部时跟随滚动
      scrollToBottom()
    }
    // 用户已上滚 → 什么都不做，保留其阅读位置
  }, [messages])

  // 切换会话时重置所有状态
  useEffect(() => {
    isInitialMountRef.current = true
    prevCountRef.current = 0
    wasAtBottomRef.current = true
    setShowScrollBtn(false)
  }, [sessionId])

  if (!sessionId) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <div className="text-center">
          <p className="text-xl mb-2">选择一个会话开始聊天</p>
          <p className="text-sm">或创建新会话</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* 状态栏 */}
      <div className="border-b px-4 py-2 bg-card">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm text-muted-foreground">
              {isConnected ? '已连接' : '未连接'}
            </span>
          </div>
          {isLoading && (
            <span className="text-sm text-muted-foreground">Helen 思考中...</span>
          )}
        </div>
      </div>

      {/* 消息列表（relative 容器用于定位浮动按钮） */}
      <div ref={containerRef} className="relative flex-1 overflow-y-auto p-4">
        <MessageList messages={messages} />
        <div ref={messagesEndRef} />

        {/* "回到底部" 浮动按钮：仅在用户上滚离开底部后出现 */}
        {showScrollBtn && (
          <button
            onClick={() => scrollToBottom()}
            className="absolute bottom-4 right-4 z-10 flex items-center gap-1 rounded-full bg-primary text-primary-foreground shadow-lg px-3 py-2 text-sm hover:opacity-90 transition-opacity"
            title="滚动到底部"
          >
            <ArrowDown className="w-4 h-4" />
            <span>回到底部</span>
          </button>
        )}
      </div>

      {/* 输入框 */}
      <MessageInput
        onSend={sendMessage}
        onStop={stopGeneration}
        disabled={!isConnected}
        isLoading={isLoading}
      />

      {/* 底部状态栏（仿 Claude Code）：hostname · cwd · model · 上下文占用 % */}
      <StatusLine data={statusline} connected={isConnected} />
    </div>
  )
}
