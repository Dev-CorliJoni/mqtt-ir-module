import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react-swc'
import {defineConfig, loadEnv} from 'vite'

export default defineConfig(({mode}) => {
  const env = loadEnv(mode, process.cwd(), '')
  // Use the same-origin /api in the browser and proxy it in dev when provided.
  const proxyTarget = (env.VITE_DEV_API_CLIENT || '').trim()

  return {
    // Relative assets so a runtime <base href="..."> works for deep-links under
    // any PUBLIC_BASE_URL.
    base: './',
    plugins: [react(), tailwindcss()],
    server: {
      // Proxy /api in dev so the browser stays same-origin and avoids preflight.
      proxy: proxyTarget
        ? {
            '/api': {
              target: proxyTarget,
              changeOrigin: true,
              ws: true,
            },
          }
        : undefined,
    },
  }
})
