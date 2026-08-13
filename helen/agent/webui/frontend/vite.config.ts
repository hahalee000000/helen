import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

// 读取 token（由 start-frontend.sh 从 .helen/webui_token 注入）
const token = process.env.HELEN_WEBUI_TOKEN

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
    // 仅绑定 loopback,防止局域网可达。
    // WSL2 跨命名空间访问请用 `wsl --exec curl` 或 `netsh interface portproxy`,
    // 不要把 dev server 暴露给 0.0.0.0(否则同网段任意主机可直接执行 Helen 程序)。
    host: '127.0.0.1',
    // 若有 token，按 o 快捷键直接打开带 token 的 URL（前端自动存入 localStorage）
    open: token ? `/?token=${token}` : true,
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
