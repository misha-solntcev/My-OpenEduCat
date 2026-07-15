import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  resolve: {
    extensions: ['.tsx', '.ts', '.jsx', '.js', '.json'],
  },
  base: '/rost_max_miniapp/static/src/bundle/',
  build: {
    outDir: '../bundle',
    emptyOutDir: true,
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