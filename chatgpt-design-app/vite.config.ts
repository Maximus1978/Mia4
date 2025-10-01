import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'node:path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react({ jsxRuntime: 'classic' })],
  server: { port: 3000 },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
  test: {
    root: resolve(__dirname),
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    include: ['tests/ui/**/*.spec.ts', 'tests/ui/**/*.spec.tsx'],
    globals: true,
  },
});
