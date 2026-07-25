/**
 * api.ts 单元测试
 *
 * 测试新增和修改的 API 方法：
 * - getTranscriptBySession / getAllTranscript / getUnmappedTranscript
 * - sessions.update (PATCH)
 * - sessions.delete (不再发送 helen_session_id)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock global fetch
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

// Import api after mocking fetch
import { api } from './api'

describe('chat transcript API', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it('getTranscriptBySession calls correct URL', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ total: 0, messages: [] })
    })
    await api.chat.getTranscriptBySession('web-session-123')
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/chat/sessions/web-session-123/transcript/messages'),
      expect.any(Object)
    )
  })

  it('getAllTranscript calls correct URL', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ total: 0, messages: [] })
    })
    await api.chat.getAllTranscript()
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/chat/transcript/all'),
      expect.any(Object)
    )
  })

  it('getUnmappedTranscript calls correct URL', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ total: 0, messages: [] })
    })
    await api.chat.getUnmappedTranscript()
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/chat/transcript/unmapped'),
      expect.any(Object)
    )
  })
})

describe('sessions.update API', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it('sends PATCH with correct body', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ id: 'sid', name: '新名字' })
    })
    await api.sessions.update('session-id', { name: '新名字' })
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/chat/sessions/session-id'),
      expect.objectContaining({
        method: 'PATCH',
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ name: '新名字' })
      })
    )
  })

  it('sends description update', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ id: 'sid', description: '描述' })
    })
    await api.sessions.update('sid', { description: '描述' })
    const callArgs = mockFetch.mock.calls[0]
    const body = JSON.parse(callArgs[1].body)
    expect(body.description).toBe('描述')
  })
})

describe('sessions.delete API', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it('no longer sends helen_session_id when not provided', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'ok' })
    })
    await api.sessions.delete('session-id')
    const url = mockFetch.mock.calls[0][0] as string
    // URL 不应包含 helen_session_id
    expect(url).not.toContain('helen_session_id')
    expect(url).toContain('/chat/sessions/session-id')
  })

  it('sends helen_session_id as query param when provided (v2.1 architecture)', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'ok' })
    })
    await api.sessions.delete('session-id', 'helen-sid-abc')
    const url = mockFetch.mock.calls[0][0] as string
    // v2.1: 后端根据 helen_session_id 触发 /clear-session 级联删除 transcripts
    expect(url).toContain('helen_session_id=helen-sid-abc')
    expect(url).toContain('/chat/sessions/session-id')
  })

  it('uses DELETE method', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'ok' })
    })
    await api.sessions.delete('session-id')
    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ method: 'DELETE' })
    )
  })
})
