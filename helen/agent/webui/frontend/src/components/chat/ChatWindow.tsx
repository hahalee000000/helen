import { useEffect, useRef, useState } from 'react'
import { MessageList } from './MessageList'
import { MessageInput } from './MessageInput'
import { StatusLine } from './StatusLine'
import { useChat } from '@/hooks/useChat'
import { useT } from '@/i18n'
import { ArrowDown } from 'lucide-react'

interface ChatWindowProps {
  sessionId: string | null
}

// 距离底部多少像素内算"在底部"(仅用于显示 "回到底部" 按钮)
const BOTTOM_THRESHOLD = 50

export function ChatWindow({ sessionId }: ChatWindowProps) {
  const { messages, sendMessage, stopGeneration, isLoading, isConnected, statusline } = useChat(sessionId)
  const containerRef = useRef<HTMLDivElement>(null)
  const t = useT()
  // showScrollBtn: 控制 "回到底部" 浮动按钮显示(基于用户当前滚动位置)
  const [showScrollBtn, setShowScrollBtn] = useState(false)
  // userScrolledAwayRef: 用户是否主动滚离底部
  //   - 任何"非底部"的 scroll 事件都会置为 true,冻结自动滚动
  //   - 只有通过以下途径才会重置为 false,恢复自动滚动:
  //       1. 用户发送新消息 (通过 sendMessage 包装)
  //       2. 用户点击 "回到底部" 按钮
  //       3. 切换会话
  //   这样可以避免流式 chunk 过快导致的 race condition:
  //   用户滚上去 → 下一个 chunk 的 scrollToBottom 在 scroll 事件触发前抢占 isAtBottomRef
  const userScrolledAwayRef = useRef(false)

  // 判断是否接近底部
  const isNearBottom = (): boolean => {
    const el = containerRef.current
    if (!el) return true
    return el.scrollHeight - el.scrollTop - el.clientHeight < BOTTOM_THRESHOLD
  }

  // 滚动到最底部(瞬间).
  // 注意:不会重置 userScrolledAwayRef;调用方需要自己决定是否恢复自动滚动
  const scrollToBottom = () => {
    const el = containerRef.current
    if (!el) return
    el.scrollTop = el.scrollHeight
    setShowScrollBtn(false)
  }

  // 重新启用自动滚动 + 立即滚到底部
  const enableAutoScroll = () => {
    userScrolledAwayRef.current = false
    scrollToBottom()
  }

  // scroll 事件:检测用户是否滚离底部.
  // 注意:只在"非底部"时置位 userScrolledAwayRef;
  //       用户滚回底部不会自动恢复自动滚动(需要显式点击按钮/发消息).
  // 程序化 scrollToBottom 触发的 scroll 事件 scrollHeight - scrollTop - clientHeight ≈ 0,
  // 不会误触发"用户滚离".
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const handleScroll = () => {
      if (!isNearBottom()) {
        userScrolledAwayRef.current = true
      }
      setShowScrollBtn(!isNearBottom())
    }
    el.addEventListener('scroll', handleScroll, { passive: true })
    return () => el.removeEventListener('scroll', handleScroll)
  }, [])

  // messages 变化:只有用户没有主动滚离时才自动跟随
  // 用户滚离后,userScrolledAwayRef=true → 不再自动滚动,保留阅读位置
  useEffect(() => {
    if (!userScrolledAwayRef.current) {
      scrollToBottom()
    }
  }, [messages])

  // 切换会话:重置自动滚动 + 历史加载后滚到底
  useEffect(() => {
    userScrolledAwayRef.current = false
    setShowScrollBtn(false)
    requestAnimationFrame(() => {
      const el = containerRef.current
      if (el) el.scrollTop = el.scrollHeight
    })
  }, [sessionId])

  // 包装 sendMessage:发送消息 = 重新启用自动滚动
  const sendMessageWithAutoScroll = (content: string, attachments?: any[]) => {
    enableAutoScroll()
    sendMessage(content, attachments)
  }

  if (!sessionId) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <div className="text-center">
          <p className="text-xl mb-2">{t('chat.selectSession')}</p>
          <p className="text-sm">{t('chat.orCreate')}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* 状态栏 */}
      <div className="border-b px-4 py-2 bg-card flex items-center gap-3" style={{ backgroundColor: '#EAE9E5' }}>
        <img src="/helen-logo-64.png" alt="Helen" className="w-6 h-6 rounded-full" />
        <div className="flex items-center gap-2 flex-1">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm text-muted-foreground">
            {isConnected ? t('status.connected') : t('status.disconnected')}
          </span>
        </div>
        {isLoading && (
          <span className="flex items-center gap-2 text-sm text-muted-foreground">
            <img src="/helen-logo-64.png" alt="" className="w-4 h-4 rounded-full animate-pulse" />
            {t('chat.thinking')}
          </span>
        )}
      </div>

      {/* 消息列表（relative 容器用于定位浮动按钮） */}
      <div
        ref={containerRef}
        className="relative flex-1 overflow-y-auto p-4"
        style={{
          backgroundImage: "url('/wallpaper.png')",
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
        }}
      >
        <MessageList messages={messages} />

        {/* "回到底部" 浮动按钮：仅在用户上滚离开底部后出现 */}
        {showScrollBtn && (
          <button
            onClick={() => enableAutoScroll()}
            className="absolute bottom-4 right-4 z-10 flex items-center gap-1 rounded-full bg-primary text-primary-foreground shadow-lg px-3 py-2 text-sm hover:opacity-90 transition-opacity"
            title={t('chat.scrollBottom')}
          >
            <ArrowDown className="w-4 h-4" />
            <span>{t('chat.atBottom')}</span>
          </button>
        )}
      </div>

      {/* 输入框 */}
      <MessageInput
        onSend={sendMessageWithAutoScroll}
        onStop={stopGeneration}
        disabled={!isConnected}
        isLoading={isLoading}
      />

      {/* 底部状态栏（仿 Claude Code）：hostname · cwd · model · 上下文占用 % */}
      <StatusLine data={statusline} connected={isConnected} />
    </div>
  )
}
