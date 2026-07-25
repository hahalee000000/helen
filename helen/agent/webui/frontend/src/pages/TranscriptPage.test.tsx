/**
 * TranscriptPage 单元测试
 *
 * 覆盖:
 * - 渲染过滤选择器
 * - 过滤行为（全部/按 session/未映射）
 * - 空状态显示
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { TranscriptPage } from './TranscriptPage'
import { api } from '@/services/api'
import { useParams } from 'react-router-dom'

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  useParams: vi.fn()
}))

// Mock api
vi.mock('@/services/api', () => ({
  api: {
    sessions: {
      list: vi.fn()
    },
    chat: {
      getTranscript: vi.fn(),
      getTranscriptBySession: vi.fn(),
      getAllTranscript: vi.fn(),
      getUnmappedTranscript: vi.fn()
    }
  }
}))

const mockSessions = [
  { id: 'web-session-1', title: '测试会话 A', created_at: '', updated_at: '' },
  { id: 'web-session-2', title: '测试会话 B', name: '命名会话', created_at: '', updated_at: '' }
]

const mockTranscriptData = {
  session_id: 'helen-sid-1',
  file: '/path/to/transcript.jsonl',
  total_entries: 2,
  roles: { user: 1, assistant: 1 },
  tool_calls_count: 0,
  entries: [
    { type: 'message', uuid: 'msg-1', role: 'user', content: '你好' },
    { type: 'message', uuid: 'msg-2', role: 'assistant', content: '你好！' }
  ]
}

describe('TranscriptPage', () => {
  beforeEach(() => {
    vi.mocked(useParams).mockReturnValue({ sessionId: 'current' })
    vi.mocked(api.sessions.list).mockResolvedValue(mockSessions)
    vi.mocked(api.chat.getTranscript).mockResolvedValue(mockTranscriptData)
    vi.mocked(api.chat.getTranscriptBySession).mockResolvedValue({
      session_id: 'web-session-1',
      helen_session_id: 'helen-sid-1',
      total: 0,
      messages: []
    })
    vi.mocked(api.chat.getAllTranscript).mockResolvedValue({
      helen_session_id: 'helen-sid-1',
      total: 0,
      messages: []
    })
    vi.mocked(api.chat.getUnmappedTranscript).mockResolvedValue({
      helen_session_id: 'helen-sid-1',
      total: 0,
      messages: []
    })
    vi.clearAllMocks()
    // Re-setup default mocks after clearAllMocks
    vi.mocked(api.sessions.list).mockResolvedValue(mockSessions)
    vi.mocked(api.chat.getTranscript).mockResolvedValue(mockTranscriptData)
  })

  describe('渲染', () => {
    it('renders filter dropdown', async () => {
      render(<TranscriptPage />)
      await waitFor(() => {
        expect(screen.getByText('过滤：')).toBeInTheDocument()
      })
    })

    it('renders "全部消息" as default option', async () => {
      render(<TranscriptPage />)
      await waitFor(() => {
        const select = screen.getByRole('combobox') as HTMLSelectElement
        expect(select.value).toBe('all')
      })
    })

    it('renders session options in dropdown', async () => {
      render(<TranscriptPage />)
      await waitFor(() => {
        // Check that session titles appear in the dropdown
        expect(screen.getByText('测试会话 A')).toBeInTheDocument()
      })
    })

    it('renders transcript entries', async () => {
      render(<TranscriptPage />)
      await waitFor(() => {
        // Role labels are always visible (in collapsed view)
        expect(screen.getAllByText('user').length).toBeGreaterThan(0)
        expect(screen.getAllByText('assistant').length).toBeGreaterThan(0)
      })
    })

    it('renders statistics', async () => {
      render(<TranscriptPage />)
      await waitFor(() => {
        expect(screen.getByText('2')).toBeInTheDocument() // total_entries
      })
    })
  })

  describe('过滤行为', () => {
    it('calls getTranscript when "全部" selected (default)', async () => {
      render(<TranscriptPage />)
      await waitFor(() => {
        expect(api.chat.getTranscript).toHaveBeenCalledWith('current')
      })
    })

    it('calls getTranscriptBySession when session selected', async () => {
      render(<TranscriptPage />)
      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      const select = screen.getByRole('combobox')
      fireEvent.change(select, { target: { value: 'web-session-1' } })

      await waitFor(() => {
        expect(api.chat.getTranscriptBySession).toHaveBeenCalledWith('web-session-1')
      })
    })

    it('calls getUnmappedTranscript when "未映射" selected', async () => {
      render(<TranscriptPage />)
      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      const select = screen.getByRole('combobox')
      fireEvent.change(select, { target: { value: 'unmapped' } })

      await waitFor(() => {
        expect(api.chat.getUnmappedTranscript).toHaveBeenCalled()
      })
    })
  })

  describe('空状态', () => {
    it('renders "该过滤条件下无消息" when empty', async () => {
      vi.mocked(api.chat.getTranscriptBySession).mockResolvedValue({
        session_id: 'web-session-1',
        helen_session_id: 'helen-sid-1',
        total: 0,
        messages: []
      })

      render(<TranscriptPage />)
      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      const select = screen.getByRole('combobox')
      fireEvent.change(select, { target: { value: 'web-session-1' } })

      await waitFor(() => {
        expect(screen.getByText('该过滤条件下无消息')).toBeInTheDocument()
      })
    })
  })
})
