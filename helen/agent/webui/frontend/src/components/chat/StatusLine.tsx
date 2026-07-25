import { StatuslineData } from '@/types'

/**
 * Statusline — 仿 Claude Code 风格的底部状态栏
 *
 * 显示当前会话 4 项关键信息：
 *   hostname · cwd（缩略） · model · 上下文占用 %
 *
 * 数据由 Helen 通过 Python FFI (ui.status_emitter) 在关键节点推送
 * （ChatSession 入口 / llm_complete / on_tool_end 注入 hint 后）。
 *
 * Props:
 *   data:     StatuslineData（来自 useChat hook）
 *   connected: WebSocket 是否连接（断连时显示红点）
 */
interface StatusLineProps {
  data: StatuslineData
  connected: boolean
}

/** 把绝对 cwd 缩略为 ~/xxx 形式，过长时只显示末段 */
function shortenCwd(cwd: string | undefined): string {
  if (!cwd) return ''
  // /home/<user>/... → ~/...
  const homeShort = cwd.replace(/^\/home\/[^/]+/, '~')
  if (homeShort !== cwd) return homeShort
  // 其他路径：保留末段
  const parts = cwd.split('/').filter(Boolean)
  if (parts.length === 0) return cwd
  if (parts.length <= 2) return cwd
  return parts.slice(-2).join('/')
}

export function StatusLine({ data, connected }: StatusLineProps) {
  const usagePct = Math.round((data.usageRatio ?? 0) * 100)
  const shortCwd = shortenCwd(data.cwd)

  // 占用率颜色阈值：<60% 绿，60-85% 黄，>85% 红
  const usageColor = usagePct > 85
    ? 'text-red-500'
    : usagePct > 60
      ? 'text-amber-500'
      : 'text-emerald-500'

  // 按顺序拼装各项，过滤空值
  const items: Array<{ key: string; text: string; title?: string; className?: string } | null> = [
    !connected ? { key: 'conn', text: '● 断连', className: 'text-red-500' } : null,
    data.hostname ? { key: 'host', text: data.hostname } : null,
    shortCwd ? { key: 'cwd', text: shortCwd, title: data.cwd } : null,
    data.model ? { key: 'model', text: data.model, className: 'text-muted-foreground' } : null,
    {
      key: 'usage',
      text: `${usagePct}%`,
      title: `上下文占用 ${usagePct}%`,
      className: usageColor,
    },
  ]

  const rendered = items.filter((x): x is NonNullable<typeof x> => x !== null)

  return (
    <div
      className="border-t border-border/40 bg-muted/30 px-4 py-1 text-xs text-muted-foreground flex items-center gap-1 overflow-hidden"
      role="status"
      aria-label="会话状态"
    >
      {rendered.length === 0 ? (
        <span className="italic opacity-60">等待连接...</span>
      ) : (
        rendered.map((item, i) => (
          <span key={item.key} className="flex items-center gap-1 min-w-0">
            {i > 0 && (
              <span className="text-muted-foreground/40 select-none" aria-hidden>·</span>
            )}
            <span
              className={`truncate ${item.className ?? ''}`}
              title={item.title}
            >
              {item.text}
            </span>
          </span>
        ))
      )}
    </div>
  )
}
