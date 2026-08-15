# WebUI Message Persistence Investigation — 2026-08-15

## Problem Statement

User reported two issues in ~/helen-rust WebUI:
1. Messages disappear after page refresh
2. Many empty session ID directories

## Investigation Results

### Issue 1: Empty Session Directories ✓ RESOLVED

**Root Cause**: User previously copied `~/work/.helen` to `~/helen-rust`, bringing old empty session directories.

**Fix**: Cleaned up 11 empty session directories that had no transcript files.

### Issue 2: Messages Disappear After Refresh 🔍 UNDER INVESTIGATION

**Backend Verification**:
- ✅ Backend API works correctly
- ✅ `/api/chat/dir` returns correct session IDs:
  - `session_id`: ef5b78d42b0f5695 (frontend hash)
  - `helen_session_id`: session_1786551257_11a1201e_d5bb2789 (Helen session)
- ✅ `/api/chat/dir/messages` returns 100 messages (limited by default)
- ✅ Transcript file exists with 146 entries at:
  ```
  ~/helen-rust/.helen/sessions/session_1786551257_11a1201e_d5bb2789/transcript.jsonl
  ```

**Frontend Flow Analysis**:

The initialization flow should work correctly:

```
Page Refresh
    ↓
currentSessionId = null (Zustand store resets)
    ↓
ChatPage mounts
    ↓
useEffect calls api.chat.getDirectory()
    ↓
Backend returns {session_id: "ef5b78d42b0f5695", ...}
    ↓
setCurrentSession("ef5b78d42b0f5695")
    ↓
ChatWindow receives sessionId
    ↓
useChat useEffect triggers
    ↓
api.chat.getDirectoryMessages() called
    ↓
Backend returns 100 messages
    ↓
setMessages(history)
    ↓
Messages should display
```

**Code Review**:
- ✅ `ChatPage.tsx` correctly calls `getDirectory()` on mount
- ✅ `useChat.ts` correctly loads messages when `sessionId` changes
- ✅ `api.ts` correctly calls `/api/chat/dir/messages`
- ✅ `MessageList.tsx` correctly renders messages
- ✅ Token authentication works correctly (injected via Vite plugin)
- ✅ WebSocket doesn't interfere with message loading

**Possible Causes**:
1. **Timing issue**: Race condition during initialization (unlikely, code handles this)
2. **Silent API failure**: `getDirectory()` or `getDirectoryMessages()` failing without error
3. **State management**: Zustand store not updating correctly (unlikely, it's a singleton)
4. **Browser caching**: Stale frontend code cached by browser
5. **Multiple tabs**: Another tab sending `clear_messages` event (unlikely)

## Actions Taken

Added comprehensive console logging to help diagnose the issue:

1. **`ChatPage.tsx`**: Log session initialization
   ```typescript
   console.log('[ChatPage] Initializing session from directory...')
   console.log('[ChatPage] Got directory info:', info)
   console.log('[ChatPage] Setting session ID:', info.session_id)
   ```

2. **`useChat.ts`**: Log message loading
   ```typescript
   console.log('[useChat] sessionId is null, clearing messages')
   console.log('[useChat] Loading messages for sessionId:', sessionId)
   console.log('[useChat] Loaded', history.length, 'messages')
   console.error('[useChat] Failed to load messages:', error)
   ```

3. **`api.ts`**: Log API calls
   ```typescript
   console.log('[API] getDirectoryMessages called with limit:', limit, 'offset:', offset)
   console.error('[API] getDirectoryMessages failed with status:', response.status)
   console.log('[API] getDirectoryMessages returned', data.length, 'messages')
   ```

## Next Steps

To reproduce and diagnose:

1. Update Helen to latest version:
   ```bash
   cd ~/helen
   git pull origin master
   uv pip install -e .
   ```

2. Restart WebUI:
   ```bash
   cd ~/helen-rust
   helen agent
   ```

3. Open browser DevTools (F12) → Console tab

4. Refresh the page (Ctrl+R or Cmd+R)

5. Check console for log messages:
   - `[ChatPage] Initializing session from directory...`
   - `[ChatPage] Got directory info: {...}`
   - `[ChatPage] Setting session ID: ...`
   - `[useChat] Loading messages for sessionId: ...`
   - `[API] getDirectoryMessages called with limit: 100 offset: 0`
   - `[API] getDirectoryMessages returned N messages`

6. If messages don't appear, share the console log output

## Potential Fixes (if issue persists)

### Option A: Persist sessionId to localStorage
Store `currentSessionId` in localStorage to avoid the two-render initialization cycle. This would make the sessionId available immediately on page load.

### Option B: Retry mechanism
Add retry logic for API calls in case of transient failures.

### Option C: Error UI
Show error message to user if message loading fails, instead of silently showing empty chat.

### Option D: Backend optimization
Have `/api/chat/dir` return messages directly, eliminating the two-step initialization.

## Files Modified

- `helen/agent/webui/frontend/src/hooks/useChat.ts` - Added logging
- `helen/agent/webui/frontend/src/pages/ChatPage.tsx` - Added logging
- `helen/agent/webui/frontend/src/services/api.ts` - Added logging

## Commit

```
commit b0549652
debug(webui): add console logging for message loading flow

- Log session initialization in ChatPage
- Log message loading in useChat hook
- Log API calls in getDirectoryMessages
- Helps diagnose messages-disappear-after-refresh issue
```

Pushed to GitHub: https://github.com/hahalee000000/helen/commit/b0549652
