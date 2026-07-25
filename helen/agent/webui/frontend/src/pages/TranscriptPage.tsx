import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '@/services/api'
import { FileText, Loader2, AlertCircle, User, Bot, Wrench, Filter, ChevronRight, Image, Music, Film } from 'lucide-react'

interface TranscriptEntry {
  type: string
  role?: string
  // content can be string (plain text) or array (multimodal: [{type, text/image_url/...}])
  content?: string | any[]
  tool_calls?: any[]
  uuid?: string
  message_type?: string | null
  priority?: number
  compressed?: boolean
  pinned?: boolean
  _line?: number
  error?: string
  raw?: string
}

interface TranscriptData {
  session_id: string
  file: string
  total_entries: number
  roles: Record<string, number>
  tool_calls_count: number
  entries: TranscriptEntry[]
}

interface Session {
  id: string
  title: string
  name?: string
  created_at: string
  updated_at: string
}

type FilterMode = 'all' | string  // string = web_ui_session_id

export function TranscriptPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [data, setData] = useState<TranscriptData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedEntries, setExpandedEntries] = useState<Set<number>>(new Set())
  const [filterMode, setFilterMode] = useState<FilterMode>('all')
  const [sessions, setSessions] = useState<Session[]>([])

  // 加载会话列表（用于过滤下拉）
  useEffect(() => {
    const loadSessions = async () => {
      try {
        const list = await api.sessions.list()
        setSessions(list)
      } catch {
        // ignore
      }
    }
    loadSessions()
  }, [])

  // 根据 filterMode 加载 transcript 数据
  useEffect(() => {
    const loadTranscript = async () => {
      try {
        setIsLoading(true)
        setError(null)

        let entries: TranscriptEntry[] = []
        let helenSid = ''

        if (filterMode === 'all') {
          // 使用原始端点（包含所有条目类型：message + boundary 等）
          const result: TranscriptData = await api.chat.getTranscript(sessionId || 'current')
          setData(result)
          setIsLoading(false)
          return
        } else {
          // filterMode is a web_ui_session_id
          const result = await api.chat.getTranscriptBySession(filterMode)
          helenSid = result.helen_session_id
          entries = result.messages
        }

        // 计算统计信息
        const roles: Record<string, number> = {}
        let toolCallsCount = 0
        for (const e of entries) {
          const role = e.role || 'unknown'
          roles[role] = (roles[role] || 0) + 1
          if (e.tool_calls) toolCallsCount += e.tool_calls.length
        }

        setData({
          session_id: helenSid,
          file: '',
          total_entries: entries.length,
          roles,
          tool_calls_count: toolCallsCount,
          entries,
        })
      } catch (err) {
        setError((err as Error).message)
      } finally {
        setIsLoading(false)
      }
    }

    loadTranscript()
  }, [sessionId, filterMode])

  const toggleEntry = (index: number) => {
    setExpandedEntries(prev => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  const expandAll = () => {
    if (data) {
      setExpandedEntries(new Set(data.entries.map((_, i) => i)))
    }
  }

  const collapseAll = () => {
    setExpandedEntries(new Set())
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
          <p className="text-destructive">{error}</p>
        </div>
      </div>
    )
  }

  if (!data) {
    return null
  }

  const filterLabel = filterMode === 'all'
    ? '全部'
    : sessions.find(s => s.id === filterMode)?.title || filterMode

  return (
    <div className="p-6 overflow-y-auto h-full">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Helen Transcript</h1>
        <p className="text-muted-foreground">LLM 上下文的完整记录</p>
      </div>

      {/* 过滤选择器 */}
      <div className="mb-4 flex items-center gap-3">
        <Filter className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm text-muted-foreground">过滤：</span>
        <select
          value={filterMode}
          onChange={e => setFilterMode(e.target.value)}
          className="border rounded px-2 py-1 text-sm bg-background"
        >
          <option value="all">全部消息</option>
          {sessions.length > 0 && <optgroup label="Web UI 会话">
            {sessions.map(s => (
              <option key={s.id} value={s.id}>
                {s.name ? `${s.name} (${s.title})` : s.title}
              </option>
            ))}
          </optgroup>}
        </select>
        <span className="text-sm text-muted-foreground ml-2">
          当前：{filterLabel}
        </span>
      </div>

      {/* 统计信息 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="border rounded-lg p-4 bg-card">
          <div className="text-sm text-muted-foreground mb-1">Helen Session</div>
          <div className="font-mono text-sm truncate" title={data.session_id}>
            {data.session_id}
          </div>
        </div>
        <div className="border rounded-lg p-4 bg-card">
          <div className="text-sm text-muted-foreground mb-1">消息数</div>
          <div className="text-2xl font-bold">{data.total_entries}</div>
        </div>
        <div className="border rounded-lg p-4 bg-card">
          <div className="text-sm text-muted-foreground mb-1">角色分布</div>
          <div className="text-sm">
            {Object.entries(data.roles).map(([role, count]) => (
              <span key={role} className="mr-2">
                {role}: {count}
              </span>
            ))}
          </div>
        </div>
        <div className="border rounded-lg p-4 bg-card">
          <div className="text-sm text-muted-foreground mb-1">Tool Calls</div>
          <div className="text-2xl font-bold">{data.tool_calls_count}</div>
        </div>
      </div>

      {/* 文件路径（仅全量模式显示） */}
      {data.file && (
        <div className="mb-4 text-sm text-muted-foreground">
          <FileText className="inline h-4 w-4 mr-1" />
          {data.file}
        </div>
      )}

      {/* 操作按钮 */}
      <div className="mb-4 flex gap-2">
        <button
          onClick={expandAll}
          className="px-3 py-1 text-sm border rounded hover:bg-accent"
        >
          全部展开
        </button>
        <button
          onClick={collapseAll}
          className="px-3 py-1 text-sm border rounded hover:bg-accent"
        >
          全部折叠
        </button>
      </div>

      {/* Transcript 条目 */}
      <div className="space-y-3">
        {data.entries.length === 0 ? (
          <div className="text-center text-muted-foreground py-8">
            该过滤条件下无消息
          </div>
        ) : (
          data.entries.map((entry, index) => (
            <TranscriptEntryCard
              key={index}
              entry={entry}
              index={index}
              expanded={expandedEntries.has(index)}
              onToggle={() => toggleEntry(index)}
            />
          ))
        )}
      </div>
    </div>
  )
}

/** 从包含完整系统提示的 user 消息中提取用户实际输入
 *
 * Helen actor 模式下，env_context（系统提示）可能作为 user 消息存入 transcript。
 * 格式：[## Identity ... ## Reminders\n\n用户输入]
 * 本函数以 `## ` 段标题 + 空行分隔为界，把 boilerplate 和实际输入分离。
 */
function extractFromPromptBoilerplate(content: string): {
  userText: string
  boilerplate: string
  isBoilerplate: boolean
} {
  const trimmed = content.trim()
  // 检测特征：以 ## 开头且包含 ## Identity（actor prompt 的标志）
  if (!trimmed.startsWith('## ') || !trimmed.includes('## Identity')) {
    return { userText: content, boilerplate: '', isBoilerplate: false }
  }

  // 策略：
  // 1. 找到最后一个 `## ` 段标题（通常是 ## Reminders）
  // 2. 从该标题后向下扫描，找到第一个空行
  // 3. 空行之前：boilerplate（标题行 + 该段内容）
  // 4. 空行之后：用户实际输入
  //
  // prompt 结构示例：
  //   ## Identity\n...\n## Reminders\nIMPORTANT: ...\nIMPORTANT: ...\n\n用户实际输入
  //                                         ↑ 空行是分隔符
  const lines = content.split('\n')

  // 找最后一个 ## 标题行
  let lastHeadingIdx = -1
  for (let i = lines.length - 1; i >= 0; i--) {
    if (/^##\s+/.test(lines[i])) {
      lastHeadingIdx = i
      break
    }
  }

  if (lastHeadingIdx < 0) {
    return { userText: content, boilerplate: '', isBoilerplate: false }
  }

  // 从标题行之后找第一个空行
  let blankLineIdx = -1
  for (let i = lastHeadingIdx + 1; i < lines.length; i++) {
    if (lines[i].trim() === '') {
      blankLineIdx = i
      break
    }
  }

  if (blankLineIdx < 0) {
    // 没有空行分隔：整段都是 boilerplate
    return { userText: '', boilerplate: content, isBoilerplate: true }
  }

  // 空行之后 = 用户输入（可能还有尾部空白）
  const userText = lines.slice(blankLineIdx + 1).join('\n').trim()
  // 空行之前的所有内容（含标题行 + 该段内容）= boilerplate
  const boilerplate = lines.slice(0, blankLineIdx).join('\n')

  return {
    userText,
    boilerplate: boilerplate + '\n',
    isBoilerplate: true,
  }
}

/** 解析 user 消息内容，分离主文本 / 系统提示 / 多模态附件
 *
 * 目标：transcript 页面中 user 消息只显示用户实际输入的文字，
 * 其他信息（prompt boilerplate、system hint、image/audio 等多模态 parts、内部协议命令）
 * 归入可折叠区域，默认收起。
 */
function parseUserContent(content: string | any[] | undefined): {
  mainText: string
  systemHints: string[]
  mediaParts: { type: string; label: string; detail: string }[]
  promptBoilerplate: string
  hasInternalCommand: boolean
} {
  const result = {
    mainText: '',
    systemHints: [] as string[],
    mediaParts: [] as { type: string; label: string; detail: string }[],
    promptBoilerplate: '',
    hasInternalCommand: false,
  }

  if (content == null) return result

  // ── 多模态数组：逐个 part 分类 ──
  if (Array.isArray(content)) {
    const textLines: string[] = []
    for (const part of content) {
      if (typeof part === 'string') {
        textLines.push(part)
        continue
      }
      if (part && typeof part === 'object') {
        if (part.type === 'text' && part.text) {
          textLines.push(part.text)
        } else if (part.type === 'image_url') {
          const url = part.image_url?.url || part.url || ''
          result.mediaParts.push({
            type: 'image',
            label: '图片',
            detail: url.length > 80 ? url.slice(0, 80) + '...' : url,
          })
        } else if (part.type === 'input_audio') {
          result.mediaParts.push({ type: 'audio', label: '音频', detail: '' })
        } else if (part.type === 'media_ref') {
          result.mediaParts.push({
            type: 'media',
            label: '媒体',
            detail: part.path || 'ref',
          })
        } else {
          // 未知 part → 归入主文本
          textLines.push(JSON.stringify(part))
        }
      }
    }
    const joined = textLines.join('\n')
    // 对拼接后的文本再做 boilerplate 检测
    const extracted = extractFromPromptBoilerplate(joined)
    result.mainText = extracted.userText
    result.promptBoilerplate = extracted.boilerplate
  } else {
    // ── 纯字符串 ──
    const str = String(content)

    // 内部协议命令（__helen_xxx__）→ 不显示
    if (/^__helen_\w+__/.test(str.trim())) {
      result.hasInternalCommand = true
      result.mainText = ''
      return result
    }

    // 检测 prompt boilerplate（actor 模式下 env_context 作为 user 消息存入 transcript）
    const extracted = extractFromPromptBoilerplate(str)
    if (extracted.isBoilerplate) {
      result.promptBoilerplate = extracted.boilerplate
      // 对提取出的用户文本继续做 [System Hint] 过滤
      const lines = extracted.userText.split('\n')
      const textLines: string[] = []
      for (const line of lines) {
        if (line.startsWith('[System Hint]')) {
          result.systemHints.push(line.replace('[System Hint]', '').trim())
        } else {
          textLines.push(line)
        }
      }
      result.mainText = textLines.join('\n')
    } else {
      // 无 boilerplate：按行分类 [System Hint]
      const lines = str.split('\n')
      const textLines: string[] = []
      for (const line of lines) {
        if (line.startsWith('[System Hint]')) {
          result.systemHints.push(line.replace('[System Hint]', '').trim())
        } else {
          textLines.push(line)
        }
      }
      result.mainText = textLines.join('\n')
    }
  }

  return result
}

function TranscriptEntryCard({
  entry,
  expanded,
  onToggle,
}: {
  entry: TranscriptEntry
  index: number
  expanded: boolean
  onToggle: () => void
}) {
  // ── 内部折叠小组件 ──
  const CollapsibleSection = ({
    icon,
    label,
    count,
    color,
    children,
  }: {
    icon: React.ReactNode
    label: string
    count: number
    color: string
    children: React.ReactNode
  }) => {
    const [open, setOpen] = useState(false)
    return (
      <div className="mt-2">
        <button
          onClick={e => { e.stopPropagation(); setOpen(!open) }}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <ChevronRight
            className={`h-3 w-3 transition-transform ${open ? 'rotate-90' : ''}`}
          />
          {icon}
          <span className={color}>{label}</span>
          <span>({count})</span>
        </button>
        {open && (
          <div className="mt-1 ml-4 text-xs bg-muted/50 rounded p-2 space-y-1">
            {children}
          </div>
        )}
      </div>
    )
  }

  if (entry.type === 'parse_error') {
    return (
      <div className="border border-destructive rounded-lg p-4 bg-destructive/10">
        <div className="flex items-center gap-2 text-destructive mb-2">
          <AlertCircle className="h-4 w-4" />
          <span className="font-semibold">解析错误 (行 {entry._line})</span>
        </div>
        <div className="text-sm">{entry.error}</div>
        <div className="text-xs text-muted-foreground mt-2 font-mono">
          {entry.raw}
        </div>
      </div>
    )
  }

  const role = entry.role || 'unknown'
  const Icon = role === 'user' ? User : role === 'assistant' ? Bot : FileText
  const roleColor =
    role === 'user'
      ? 'text-blue-500'
      : role === 'assistant'
      ? 'text-green-500'
      : 'text-muted-foreground'

  // ── user 消息：解析并分段显示 ──
  if (role === 'user') {
    const parsed = parseUserContent(entry.content)

    // 内部协议命令：完全跳过
    if (parsed.hasInternalCommand) {
      return null
    }

    // 没有任何可显示内容（且无 boilerplate）：跳过
    if (!parsed.mainText && parsed.systemHints.length === 0 && parsed.mediaParts.length === 0 && !parsed.promptBoilerplate) {
      return null
    }

    // 摘要行：只显示主文本前 200 字符
    const summary = parsed.mainText.length > 200
      ? parsed.mainText.slice(0, 200) + '...'
      : parsed.mainText

    return (
      <div className="border rounded-lg bg-card">
        <div
          className="flex items-center gap-3 p-4 cursor-pointer hover:bg-accent/50"
          onClick={onToggle}
        >
          <Icon className={`h-5 w-5 ${roleColor}`} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-semibold">user</span>
              {entry._line && (
                <span className="text-xs text-muted-foreground">行 {entry._line}</span>
              )}
            </div>
            {summary && (
              <div className="text-sm text-muted-foreground mt-1 truncate">
                {summary}
              </div>
            )}
          </div>
          <button className="text-sm text-muted-foreground">
            {expanded ? '▲' : '▼'}
          </button>
        </div>

        {expanded && (
          <div className="px-4 pb-4 border-t">
            {/* 系统提示（折叠）— actor 模式下 env_context 作为 user 消息存入 transcript */}
            {parsed.promptBoilerplate && (
              <CollapsibleSection
                icon={<span className="text-xs">📋</span>}
                label="系统提示"
                count={1}
                color="text-slate-500"
              >
                <pre className="text-xs bg-slate-50 dark:bg-slate-900/30 p-2 rounded overflow-x-auto whitespace-pre-wrap break-words max-h-96 overflow-y-auto">
                  {parsed.promptBoilerplate}
                </pre>
              </CollapsibleSection>
            )}

            {/* 主文本 */}
            {parsed.mainText && (
              <div className="mt-3">
                <div className="text-sm text-muted-foreground mb-1">用户输入:</div>
                <pre className="text-sm bg-muted p-3 rounded overflow-x-auto whitespace-pre-wrap break-words">
                  {parsed.mainText}
                </pre>
              </div>
            )}

            {/* 系统注入（折叠） */}
            {parsed.systemHints.length > 0 && (
              <CollapsibleSection
                icon={<span className="text-xs">💡</span>}
                label="系统注入"
                count={parsed.systemHints.length}
                color="text-amber-600"
              >
                {parsed.systemHints.map((hint, i) => (
                  <pre key={i} className="text-xs bg-amber-50 dark:bg-amber-950/20 p-2 rounded whitespace-pre-wrap break-words">
                    {hint}
                  </pre>
                ))}
              </CollapsibleSection>
            )}

            {/* 多模态附件（折叠） */}
            {parsed.mediaParts.length > 0 && (
              <CollapsibleSection
                icon={<Image className="h-3 w-3" />}
                label="多模态附件"
                count={parsed.mediaParts.length}
                color="text-purple-600"
              >
                {parsed.mediaParts.map((part, i) => (
                  <div key={i} className="flex items-center gap-2">
                    {part.type === 'image' && <Image className="h-3 w-3" />}
                    {part.type === 'audio' && <Music className="h-3 w-3" />}
                    {part.type === 'media' && <Film className="h-3 w-3" />}
                    <span>{part.label}</span>
                    {part.detail && (
                      <span className="text-muted-foreground truncate max-w-xs">
                        {part.detail}
                      </span>
                    )}
                  </div>
                ))}
              </CollapsibleSection>
            )}

            {/* 元数据（折叠） */}
            <div className="mt-3 text-xs text-muted-foreground">
              <div>UUID: {entry.uuid || 'N/A'}</div>
              {entry.message_type && <div>Type: {entry.message_type}</div>}
              {entry.priority !== undefined && <div>Priority: {entry.priority}</div>}
              {entry.compressed && <div>Compressed: Yes</div>}
              {entry.pinned && <div>Pinned: Yes</div>}
            </div>
          </div>
        )}
      </div>
    )
  }

  // ── 非 user 消息：保持原有行为 ──
  const rawContent = entry.content || ''
  const contentStr = Array.isArray(rawContent)
    ? rawContent.map(part => {
        if (typeof part === 'string') return part
        if (part && typeof part === 'object') {
          if (part.type === 'text' && part.text) return part.text
          if (part.type === 'image_url') return '[图片]'
          if (part.type === 'input_audio') return '[音频]'
          if (part.type === 'media_ref') return `[媒体: ${part.path || 'ref'}]`
          return JSON.stringify(part)
        }
        return String(part)
      }).join('\n')
    : String(rawContent)
  const isLong = contentStr.length > 200
  const displayContent = expanded || !isLong ? contentStr : contentStr.slice(0, 200) + '...'

  return (
    <div className="border rounded-lg bg-card">
      <div
        className="flex items-center gap-3 p-4 cursor-pointer hover:bg-accent/50"
        onClick={onToggle}
      >
        <Icon className={`h-5 w-5 ${roleColor}`} />
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold">{role}</span>
            {entry.tool_calls && entry.tool_calls.length > 0 && (
              <span className="flex items-center gap-1 text-sm text-muted-foreground">
                <Wrench className="h-3 w-3" />
                {entry.tool_calls.length} tool call{entry.tool_calls.length > 1 ? 's' : ''}
              </span>
            )}
            {entry._line && (
              <span className="text-xs text-muted-foreground">行 {entry._line}</span>
            )}
          </div>
        </div>
        <button className="text-sm text-muted-foreground">
          {expanded ? '▲' : '▼'}
        </button>
      </div>

      {expanded && (
        <div className="px-4 pb-4 border-t">
          {/* 内容 */}
          <div className="mt-3">
            <div className="text-sm text-muted-foreground mb-1">内容:</div>
            <pre className="text-sm bg-muted p-3 rounded overflow-x-auto whitespace-pre-wrap break-words">
              {displayContent}
            </pre>
          </div>

          {/* Tool Calls */}
          {entry.tool_calls && entry.tool_calls.length > 0 && (
            <div className="mt-3">
              <div className="text-sm text-muted-foreground mb-1">Tool Calls:</div>
              <div className="space-y-2">
                {entry.tool_calls.map((tc, i) => (
                  <div key={i} className="bg-muted p-2 rounded text-sm">
                    <div className="font-mono text-xs">
                      {tc.name || tc.function?.name || 'unknown'}
                    </div>
                    {tc.arguments && (
                      <pre className="text-xs mt-1 overflow-x-auto">
                        {typeof tc.arguments === 'string'
                          ? tc.arguments
                          : JSON.stringify(tc.arguments, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 元数据 */}
          <div className="mt-3 text-xs text-muted-foreground">
            <div>UUID: {entry.uuid || 'N/A'}</div>
            {entry.message_type && <div>Type: {entry.message_type}</div>}
            {entry.priority !== undefined && <div>Priority: {entry.priority}</div>}
            {entry.compressed && <div>Compressed: Yes</div>}
            {entry.pinned && <div>Pinned: Yes</div>}
          </div>
        </div>
      )}
    </div>
  )
}
