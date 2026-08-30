import { resolve } from 'path';
import { defineConfig } from 'vite';

export default defineConfig({
  root: resolve(__dirname, '../landing'),
  publicDir: resolve(__dirname, '../landing/public'),
  build: {
    outDir: resolve(__dirname, '../landing/dist'),
    emptyOutDir: true,
    target: 'es2020',
    cssMinify: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, '../landing/index.html'),
      },
    },
  },
  server: {
    port: 3000,
    host: '127.0.0.1',
  },
});
