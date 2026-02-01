import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import os from 'os'

/**
 * Get the host machine's LAN IP address automatically.
 * Looks for non-internal IPv4 addresses (e.g., 192.168.x.x).
 *
 * Note: In Docker containers, this will return container's internal IP.
 * For Docker deployment, override with VITE_BACKEND_URL env variable.
 * TODO: Add automatic Docker environment detection.
 */
function getHostIP(): string {
  const interfaces = os.networkInterfaces()

  for (const name of Object.keys(interfaces)) {
    const iface = interfaces[name]
    if (!iface) continue

    for (const alias of iface) {
      // Skip internal (loopback) and IPv6 addresses
      if (alias.family === 'IPv4' && !alias.internal) {
        return alias.address
      }
    }
  }

  // Fallback to localhost if no external IP found
  return 'localhost'
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory.
  // process.cwd() is already 'frontend/' when vite runs
  const env = loadEnv(mode, process.cwd(), 'VITE_')

  // Auto-detect host IP for LAN access, or use env override
  const hostIP = env.VITE_BACKEND_URL || `http://${getHostIP()}:8004`

  // Log detected backend URL for debugging
  console.log(`[Vite] Backend proxy: ${hostIP}`)

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
          target: hostIP,
          changeOrigin: true,
          rewrite: (path) => path, // Keep /api prefix
        }
      }
    }
  }
})
