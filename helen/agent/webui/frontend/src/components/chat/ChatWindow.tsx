import { useEffect, useRef, useState } from 'react'
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
  // isAtBottomRef:用户是否在底部(由 scroll 事件维护,不受 DOM 内容增长影响)
  const isAtBottomRef = useRef(true)
  const [showScrollBtn, setShowScrollBtn] = useState(false)

  // 判断是否接近底部
  const isNearBottom = (): boolean => {
    const el = containerRef.current
    if (!el) return true
    return el.scrollHeight - el.scrollTop - el.clientHeight < BOTTOM_THRESHOLD
  }

  // 滚动到最底部(瞬间,避免 smooth 动画期间 isAtBottom 误判)
  const scrollToBottom = () => {
    const el = containerRef.current
    if (!el) return
    el.scrollTop = el.scrollHeight
    isAtBottomRef.current = true
    setShowScrollBtn(false)
  }

  // scroll 事件:维护 isAtBottom(基于用户实际滚动位置)
  // scroll 事件只在 scrollTop 变化时触发,流式 chunk 增大 scrollHeight 不触发,
  // 所以 isAtBottomRef 不受内容增长影响(保留用户滚动前的状态)
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const handleScroll = () => {
      const near = isNearBottom()
      isAtBottomRef.current = near
      setShowScrollBtn(!near)
    }
    el.addEventListener('scroll', handleScroll, { passive: true })
    return () => el.removeEventListener('scroll', handleScroll)
  }, [])

  // messages 变化:如果在底部,自动滚动跟随(缺省行为)
  // 用户上滚后 isAtBottomRef=false -> 不滚动,保留阅读位置
  // 用户回到底部 isAtBottomRef=true -> 恢复自动滚动
  useEffect(() => {
    if (isAtBottomRef.current) {
      scrollToBottom()
    }
  }, [messages])

  // 切换会话:重置 + 历史加载后滚到底
  useEffect(() => {
    isAtBottomRef.current = true
    setShowScrollBtn(false)
    requestAnimationFrame(() => {
      const el = containerRef.current
      if (el) el.scrollTop = el.scrollHeight
    })
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
            <span className="flex items-center gap-2 text-sm text-muted-foreground">
              <img src="/helen-logo-64.png" alt="" className="w-4 h-4 rounded-full animate-pulse" />
              Helen 思考中...
            </span>
          )}
        </div>
      </div>

      {/* 消息列表（relative 容器用于定位浮动按钮） */}
      <div ref={containerRef} className="relative flex-1 overflow-y-auto p-4">
        <MessageList messages={messages} />

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
