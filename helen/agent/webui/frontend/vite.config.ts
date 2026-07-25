import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
    // 把 /api 请求代理到 WSL 内的 uvicorn 后端（8000 端口）。
    // 好处：前端代码不再需要硬编码 localhost:8000，
    // 通过 WSL IP (172.x.x.x:5173) 或 Windows localhost:5173 访问都能通，
    // 彻底绕开 WSL2 localhost 转发失效的问题。
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,   // WebSocket 也走同一个代理
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
    },
  },
})
