import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

const buildTimestamp = Date.now();
const buildCommit = process.env.VERCEL_GIT_COMMIT_SHA || process.env.GIT_COMMIT_SHA || 'local';

export default defineConfig({
  define: {
    __ATLAS_BUILD_VERSION__: JSON.stringify({ commit: buildCommit, builtAt: new Date().toISOString() })
  },
  plugins: [
    tailwindcss(),
    react()
  ],
  build: {
    rollupOptions: {
      output: {
        entryFileNames: `assets/[name]-v${buildTimestamp}-[hash].js`,
        chunkFileNames: `assets/[name]-v${buildTimestamp}-[hash].js`,
        assetFileNames: `assets/[name]-v${buildTimestamp}-[hash].[ext]`
      }
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    },
    watch: {
      ignored: [
        '**/backend/**',
        '**/database/**',
        '**/agents/**',
        '**/sandbox/**',
        '**/datasets/**',
        '**/uploaded_datasets/**',
        '**/__pycache__/**',
        '**/*.py',
        '**/*.pyc',
        '**/*.parquet',
        '**/*.csv'
      ]
    }
  }
});
