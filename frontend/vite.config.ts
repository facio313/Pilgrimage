import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import process from 'node:process'
import { loadEnv } from 'vite'
import { resolveFrontendAuthMode } from './portfolioAuthMode.js'

export default defineConfig(({ mode }) => {
  const environment = { ...loadEnv(mode, process.cwd(), ''), ...process.env }
  const auth = resolveFrontendAuthMode(environment)

  return {
    base: '/pilgrimage/',
    define: {
      'import.meta.env.VITE_SSO_ENABLED': JSON.stringify(String(auth.ssoEnabled)),
    },
    plugins: [react()],
    server: {
      proxy: {
        '/api': 'http://localhost:8000',
      },
    },
    test: {
      environment: 'jsdom',
      globals: true,
    },
  }
})
