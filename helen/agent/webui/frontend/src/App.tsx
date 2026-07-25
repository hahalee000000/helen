import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from '@/components/layout/Layout'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { ChatPage } from '@/pages/ChatPage'
import { TranscriptPage } from '@/pages/TranscriptPage'
import { SettingsPage } from '@/pages/SettingsPage'

function App() {
  return (
    <ErrorBoundary>
      <Layout>
        <Routes>
          <Route path="/" element={
            <ErrorBoundary fallback={<div className="p-8">聊天页面加载失败</div>}>
              <ChatPage />
            </ErrorBoundary>
          } />
          <Route path="/transcript" element={
            <ErrorBoundary fallback={<div className="p-8">Transcript 页面加载失败</div>}>
              <TranscriptPage />
            </ErrorBoundary>
          } />
          <Route path="/transcript/:sessionId" element={
            <ErrorBoundary fallback={<div className="p-8">Transcript 页面加载失败</div>}>
              <TranscriptPage />
            </ErrorBoundary>
          } />
          <Route path="/settings" element={
            <ErrorBoundary fallback={<div className="p-8">设置页面加载失败</div>}>
              <SettingsPage />
            </ErrorBoundary>
          } />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </ErrorBoundary>
  )
}

export default App
