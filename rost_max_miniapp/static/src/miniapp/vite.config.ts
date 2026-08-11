import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    extensions: ['.tsx', '.ts', '.jsx', '.js', '.json'],
    alias: {
      '@': path.resolve(__dirname, '.'),
      '@shared': path.resolve(__dirname, './shared'),
      '@pages': path.resolve(__dirname, './pages'),
      '@components': path.resolve(__dirname, './shared/components'),
      '@lib': path.resolve(__dirname, './shared/lib'),
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
