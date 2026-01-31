import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory.
  // process.cwd() is already 'frontend/' when vite runs
  const env = loadEnv(mode, process.cwd(), 'VITE_')

  return {
    plugins: [react()],
    server: {
      port: 5174,
      host: '0.0.0.0', // Allow access from network
      // Read allowed hosts from env (comma-separated)
      allowedHosts: env.VITE_ALLOWED_HOSTS
        ? env.VITE_ALLOWED_HOSTS.split(',').map(h => h.trim())
        : undefined,
      // HMR configuration for domain deployment (optional)
      hmr: env.VITE_HMR_HOST ? {
        host: env.VITE_HMR_HOST,
        clientPort: env.VITE_HMR_CLIENT_PORT ? Number(env.VITE_HMR_CLIENT_PORT) : undefined,
        protocol: env.VITE_HMR_PROTOCOL as 'ws' | 'wss' | undefined,
      } : undefined,
      proxy: {
        '/api': {
          target: 'http://192.168.10.32:8004',
          changeOrigin: true,
          rewrite: (path) => path, // Keep /api prefix
        }
      }
    }
  }
})
