import { create } from 'zustand'
import { Session } from '@/types'
import { api } from '@/services/api'

/**
 * v6.0 单会话架构：移除了 Helen session ID 的 localStorage 追踪
 * clearHelenSessionId 不再需要 — 会话恢复由后端 ChatSession.main 内部处理
 */

interface ChatStore {
  sessions: Session[]
  currentSessionId: string | null
  isLoading: boolean
  error: string | null

  // Actions
  fetchSessions: () => Promise<void>
  setCurrentSession: (sessionId: string | null) => void
  createSession: (title?: string) => Promise<void>
  deleteSession: (sessionId: string) => Promise<void>
  clearError: () => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  sessions: [],
  currentSessionId: null,
  isLoading: false,
  error: null,

  fetchSessions: async () => {
    set({ isLoading: true, error: null })
    try {
      const sessions = await api.sessions.list()
      set({ sessions, isLoading: false })
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false })
    }
  },

  setCurrentSession: (sessionId) => {
    set({ currentSessionId: sessionId })
  },

  createSession: async (title = 'New Chat') => {
    set({ isLoading: true, error: null })
    try {
      const { session_id } = await api.sessions.create(title)
      await get().fetchSessions()
      set({ currentSessionId: session_id, isLoading: false })
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false })
    }
  },

  deleteSession: async (sessionId) => {
    set({ isLoading: true, error: null })
    try {
      await api.sessions.delete(sessionId)
      await get().fetchSessions()

      // 如果删除的是当前会话，清除选中
      if (get().currentSessionId === sessionId) {
        set({ currentSessionId: null })
      }

      set({ isLoading: false })
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false })
    }
  },

  clearError: () => {
    set({ error: null })
  }
}))
