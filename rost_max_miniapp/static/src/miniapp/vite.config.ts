import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

const dirname = import.meta.dirname

export default defineConfig({
  plugins: [react()],
  resolve: {
    extensions: ['.tsx', '.ts', '.jsx', '.js', '.json'],
    alias: {
      '@': path.resolve(dirname, '.'),
      '@shared': path.resolve(dirname, './shared'),
      '@pages': path.resolve(dirname, './pages'),
      '@components': path.resolve(dirname, './shared/components'),
      '@lib': path.resolve(dirname, './shared/lib'),
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
