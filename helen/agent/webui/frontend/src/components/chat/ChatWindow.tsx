import { useEffect, useRef, useState, useCallback } from 'react'
import { MessageList } from './MessageList'
import { MessageInput } from './MessageInput'
import { StatusLine } from './StatusLine'
import { useChat } from '@/hooks/useChat'
import { useT } from '@/i18n'
import { ArrowDown, Pause, Play } from 'lucide-react'

interface ChatWindowProps {
  sessionId: string | null
}

// 距离底部多少像素内算"在底部"(用于隐藏/显示 "回到底部" 按钮)
const BOTTOM_THRESHOLD = 50

export function ChatWindow({ sessionId }: ChatWindowProps) {
  const { messages, sendMessage, stopGeneration, isLoading, isConnected, statusline } = useChat(sessionId)
  const containerRef = useRef<HTMLDivElement>(null)
  const t = useT()
  // showScrollBtn: 控制 "回到底部" 浮动按钮显示(基于用户当前滚动位置)
  const [showScrollBtn, setShowScrollBtn] = useState(false)
  // autoScrollEnabled: 用户是否启用了自动滚动
  //   - 初始为 true (新会话开始自动跟随)
  //   - 用户任何形式的滚动/滚轮/触摸都视为"手动干预",暂停自动滚动
  //   - 显式恢复途径:
  //       1. 用户发送新消息 (通过 sendMessage 包装)
  //       2. 用户点击 "回到底部" 按钮
  //       3. 切换会话
  //       4. 用户点击 "启用自动滚动" 按钮
  //   用 state 而不是 ref,因为按钮状态需要反映到 UI
  const [autoScrollEnabled, setAutoScrollEnabled] = useState(true)
  // isProgrammaticScrollRef: 区分程序化滚动和用户滚动
  //   scrollToBottom 设置 scrollTop 时会同步触发 scroll 事件,
  //   用此标志屏蔽,避免程序化滚动被误判为用户滚动
  const isProgrammaticScrollRef = useRef(false)

  // 判断是否接近底部
  const isNearBottom = (): boolean => {
    const el = containerRef.current
    if (!el) return true
    return el.scrollHeight - el.scrollTop - el.clientHeight < BOTTOM_THRESHOLD
  }

  // 滚动到最底部(瞬间).
  const scrollToBottom = useCallback(() => {
    const el = containerRef.current
    if (!el) return
    isProgrammaticScrollRef.current = true
    el.scrollTop = el.scrollHeight
    // 程序化滚动触发的 scroll 事件在同一帧内处理,
    // 下一帧再解除标志
    requestAnimationFrame(() => {
      isProgrammaticScrollRef.current = false
    })
    setShowScrollBtn(false)
  }, [])

  // 重新启用自动滚动 + 立即滚到底部
  const enableAutoScroll = useCallback(() => {
    setAutoScrollEnabled(true)
    scrollToBottom()
  }, [scrollToBottom])

  // 暂停自动滚动 (用户任何形式的滚动/滚轮/触摸干预)
  const pauseAutoScroll = useCallback(() => {
    setAutoScrollEnabled(false)
  }, [])

  // scroll 事件:区分用户滚动 vs 程序化滚动.
  // 只有用户滚动才会暂停自动跟随.
  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const handleScroll = () => {
      if (isProgrammaticScrollRef.current) {
        // 程序化滚动 (scrollToBottom 触发),忽略
        return
      }
      // 用户主动滚动 — 无论滚动多少,都视为手动干预
      // (不再使用 BOTTOM_THRESHOLD 判断,任何用户滚动都暂停)
      setAutoScrollEnabled(false)
      // 更新"回到底部"按钮显示状态
      setShowScrollBtn(!isNearBottom())
    }

    el.addEventListener('scroll', handleScroll, { passive: true })
    return () => el.removeEventListener('scroll', handleScroll)
  }, [])

  // wheel / touchmove 事件:某些浏览器/系统下,滚动条拖拽可能不触发 scroll 事件,
  // 但 wheel (鼠标滚轮) 和 touchmove (触摸滑动) 一定会触发.
  // 用这些事件作为兜底检测,确保用户意图被捕获.
  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const handleWheel = () => {
      // 鼠标滚轮 — 用户意图明确,暂停自动滚动
      setAutoScrollEnabled(false)
      // 延迟更新按钮状态 (等 scroll 事件触发后再判断位置)
      requestAnimationFrame(() => setShowScrollBtn(!isNearBottom()))
    }

    const handleTouchMove = () => {
      // 触摸滑动 — 用户意图明确,暂停自动滚动
      setAutoScrollEnabled(false)
      requestAnimationFrame(() => setShowScrollBtn(!isNearBottom()))
    }

    el.addEventListener('wheel', handleWheel, { passive: true })
    el.addEventListener('touchmove', handleTouchMove, { passive: true })
    return () => {
      el.removeEventListener('wheel', handleWheel)
      el.removeEventListener('touchmove', handleTouchMove)
    }
  }, [])

  // messages 变化:只有自动滚动启用时才跟随
  useEffect(() => {
    if (autoScrollEnabled) {
      scrollToBottom()
    }
  }, [messages, autoScrollEnabled, scrollToBottom])

  // 切换会话:重置自动滚动 + 历史加载后滚到底
  useEffect(() => {
    setAutoScrollEnabled(true)
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

        {/* 浮动按钮区：右下角叠加 "回到底部" 和 "启用/暂停自动滚动" */}
        <div className="absolute bottom-4 right-4 z-10 flex flex-col gap-2">
          {/* 暂停/启用 自动滚动切换按钮: 始终可见(用户可显式控制) */}
          <button
            onClick={() => autoScrollEnabled ? pauseAutoScroll() : enableAutoScroll()}
            className={`flex items-center gap-1 rounded-full shadow-lg px-3 py-2 text-sm transition-opacity ${
              autoScrollEnabled
                ? 'bg-emerald-500 hover:bg-emerald-600 text-white'
                : 'bg-amber-500 hover:bg-amber-600 text-white'
            }`}
            title={autoScrollEnabled ? '暂停自动滚动 (滚动/滚轮/触摸也会自动暂停)' : '启用自动滚动 (跟随最新消息)'}
          >
            {autoScrollEnabled ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            <span>{autoScrollEnabled ? '暂停' : '跟随'}</span>
          </button>

          {/* "回到底部" 浮动按钮：仅在用户上滚离开底部后出现 */}
          {showScrollBtn && (
            <button
              onClick={() => enableAutoScroll()}
              className="flex items-center gap-1 rounded-full bg-primary text-primary-foreground shadow-lg px-3 py-2 text-sm hover:opacity-90 transition-opacity"
              title={t('chat.scrollBottom')}
            >
              <ArrowDown className="w-4 h-4" />
              <span>{t('chat.atBottom')}</span>
            </button>
          )}
        </div>
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
