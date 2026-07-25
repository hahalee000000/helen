// 使用相对路径，由 vite dev proxy 转发到后端。
// 这样无论用户通过 localhost:5173 还是 WSL IP 访问，API 都能通。
const API_BASE_URL = '/api'

/**
 * 带重试的 fetch 请求
 */
async function fetchWithRetry(
  url: string,
  options: RequestInit = {},
  maxRetries = 3
): Promise<Response> {
  let lastError: Error | null = null

  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url, options)

      // 如果是服务器错误（5xx），重试
      if (response.status >= 500 && i < maxRetries - 1) {
        console.warn(`Request failed with status ${response.status}, retrying... (${i + 1}/${maxRetries})`)
        await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, i))) // 指数退避
        continue
      }

      return response
    } catch (error) {
      lastError = error as Error

      // 网络错误，重试
      if (i < maxRetries - 1) {
        console.warn(`Request failed, retrying... (${i + 1}/${maxRetries})`, error)
        await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, i)))
        continue
      }
    }
  }

  throw lastError || new Error('Request failed after retries')
}

/**
 * API 客户端（带重试机制）
 */
export const api = {
  // 聊天相关（transcript 等）
  chat: {
    getTranscript: async (sessionId: string = 'current') => {
      const response = await fetchWithRetry(`${API_BASE_URL}/chat/sessions/${encodeURIComponent(sessionId)}/transcript`)
      if (!response.ok) throw new Error('Failed to fetch transcript')
      return response.json()
    },
    /** 按 side-channel 索引过滤，返回属于指定 Web UI session 的 transcript 消息 */
    getTranscriptBySession: async (webUISessionId: string) => {
      const response = await fetchWithRetry(
        `${API_BASE_URL}/chat/sessions/${encodeURIComponent(webUISessionId)}/transcript/messages`
      )
      if (!response.ok) throw new Error('Failed to fetch transcript by session')
      return response.json()
    },
    /** 返回完整 transcript 的所有消息 */
    getAllTranscript: async () => {
      const response = await fetchWithRetry(`${API_BASE_URL}/chat/transcript/all`)
      if (!response.ok) throw new Error('Failed to fetch all transcript')
      return response.json()
    },
    /** 返回未映射到任何 Web UI session 的 transcript 消息 */
    getUnmappedTranscript: async () => {
      const response = await fetchWithRetry(`${API_BASE_URL}/chat/transcript/unmapped`)
      if (!response.ok) throw new Error('Failed to fetch unmapped transcript')
      return response.json()
    },
    /** 获取当前工作目录信息 */
    getDirectory: async () => {
      const response = await fetchWithRetry(`${API_BASE_URL}/chat/dir`)
      if (!response.ok) throw new Error('Failed to fetch directory info')
      return response.json()
    },
    /** 切换工作目录 */
    changeDirectory: async (path: string) => {
      const response = await fetchWithRetry(`${API_BASE_URL}/chat/dir`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path })
      })
      if (!response.ok) throw new Error('Failed to change directory')
      return response.json()
    },
    /** 获取当前目录的消息历史 */
    getDirectoryMessages: async (limit: number = 100, offset: number = 0) => {
      const response = await fetchWithRetry(
        `${API_BASE_URL}/chat/dir/messages?limit=${limit}&offset=${offset}`
      )
      if (!response.ok) throw new Error('Failed to fetch directory messages')
      return response.json()
    },
  },

  // 会话相关
  sessions: {
    list: async () => {
      const response = await fetchWithRetry(`${API_BASE_URL}/chat/sessions`)
      if (!response.ok) throw new Error('Failed to fetch sessions')
      return response.json()
    },

    get: async (sessionId: string) => {
      const response = await fetchWithRetry(`${API_BASE_URL}/chat/sessions/${encodeURIComponent(sessionId)}`)
      if (!response.ok) throw new Error('Failed to fetch session')
      return response.json()
    },

    create: async (title: string = 'New Chat') => {
      const response = await fetchWithRetry(`${API_BASE_URL}/chat/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title })
      })
      if (!response.ok) throw new Error('Failed to create session')
      return response.json()
    },

    update: async (sessionId: string, data: { name?: string; description?: string; title?: string }) => {
      const response = await fetchWithRetry(`${API_BASE_URL}/chat/sessions/${encodeURIComponent(sessionId)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })
      if (!response.ok) throw new Error('Failed to update session')
      return response.json()
    },

    delete: async (sessionId: string, helenSessionId?: string) => {
      // v2.1 架构（context-and-transcript-architecture.md §反馈 2）：
      // 若传入 helenSessionId，后端会触发 /clear-session 级联删除 Helen transcripts
      let url = `${API_BASE_URL}/chat/sessions/${encodeURIComponent(sessionId)}`
      if (helenSessionId) {
        url += `?helen_session_id=${encodeURIComponent(helenSessionId)}`
      }
      const response = await fetchWithRetry(url, {
        method: 'DELETE'
      })
      if (!response.ok) throw new Error('Failed to delete session')
      return response.json()
    },

    messages: async (sessionId: string) => {
      const response = await fetchWithRetry(`${API_BASE_URL}/chat/sessions/${encodeURIComponent(sessionId)}/messages`)
      if (!response.ok) throw new Error('Failed to fetch messages')
      return response.json()
    }
  },

  // Agent 相关
  agents: {
    status: async () => {
      const response = await fetchWithRetry(`${API_BASE_URL}/agents/status`)
      if (!response.ok) throw new Error('Failed to fetch agents status')
      return response.json()
    },

    get: async (agentName: string) => {
      const response = await fetchWithRetry(`${API_BASE_URL}/agents/${agentName}/status`)
      if (!response.ok) throw new Error('Failed to fetch agent status')
      return response.json()
    },

    list: async () => {
      const response = await fetchWithRetry(`${API_BASE_URL}/agents/list`)
      if (!response.ok) throw new Error('Failed to list agents')
      return response.json()
    }
  },

  // v6.2 多模态：文件上传
  upload: {
    file: async (file: File): Promise<{
      upload_id: string
      filename: string
      mime_type: string
      size: number
      url: string
    }> => {
      const formData = new FormData()
      formData.append('file', file)
      const response = await fetch(`${API_BASE_URL}/chat/upload`, {
        method: 'POST',
        body: formData
      })
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(error.detail || 'Upload failed')
      }
      return response.json()
    }
  },
}
