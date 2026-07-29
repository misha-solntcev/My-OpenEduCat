import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    extensions: ['.tsx', '.ts', '.jsx', '.js', '.json'],
    alias: {
      '@': path.resolve(__dirname, '.'),
      '@/components': path.resolve(__dirname, './components'),
      '@/lib': path.resolve(__dirname, './lib'),
      '@/pages': path.resolve(__dirname, './pages'),
      '@/shared/lib': path.resolve(__dirname, './shared/lib'),
      '@/shared/components': path.resolve(__dirname, './shared/components'),
      '@/pages/lesson-journal': path.resolve(__dirname, './pages/lesson-journal'),
      '@/pages/timetable': path.resolve(__dirname, './pages/timetable'),
      '@/pages/timetable/components': path.resolve(__dirname, './pages/timetable/components'),
      '@/pages/dashboard': path.resolve(__dirname, './pages/dashboard'),
      '@/pages/dashboard/components': path.resolve(__dirname, './pages/dashboard/components'),
      '@/pages/modules': path.resolve(__dirname, './pages/modules'),
      '@/pages/auth': path.resolve(__dirname, './pages/auth'),
    },
  },
  base: '/rost_max_miniapp/static/src/bundle/',
  build: {
    outDir: '../bundle',
    emptyOutDir: true,
    cssCodeSplit: false,
    rollupOptions: {
      input: './main.tsx',
      output: {
        format: 'umd',
        entryFileNames: 'index.js',
        assetFileNames: 'styles.css',
      },
    },
  },
  server: {
    port: 5173,
    hmr: false,
  },
})