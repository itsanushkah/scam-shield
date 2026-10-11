import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The backend runs on localhost:8000. Proxying keeps the browser on one origin, so no CORS.
const BACKEND = 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/samples': BACKEND,
      '/health': BACKEND,
      '/ws': { target: BACKEND, ws: true },
    },
  },
})
