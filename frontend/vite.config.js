import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react-swc'
import {defineConfig} from 'vite'

export default defineConfig({
  // Relative assets so a runtime <base href="..."> works for deep-links under
  // any PUBLIC_BASE_URL.
  base: './',
  plugins: [react(), tailwindcss()],
})