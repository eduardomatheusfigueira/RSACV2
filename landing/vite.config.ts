import { defineConfig, Plugin } from 'vite';
import { resolve, relative, join } from 'node:path';
import { readdirSync, statSync } from 'node:fs';
import { gerarBlog } from './scripts/gerar-blog.mjs';

function findHtmlInputs(baseDir: string, currentDir = baseDir, inputs: Record<string, string> = {}) {
  const entries = readdirSync(currentDir);
  for (const entry of entries) {
    if (entry === 'node_modules' || entry === 'dist' || entry.startsWith('.')) continue;
    const fullPath = join(currentDir, entry);
    const stat = statSync(fullPath);
    if (stat.isDirectory()) {
      findHtmlInputs(baseDir, fullPath, inputs);
    } else if (stat.isFile() && entry === 'index.html') {
      const rel = relative(baseDir, fullPath);
      let key = rel.replace(/[\\/]index\.html$/, '').replace(/[\\/]/g, '_');
      if (key === 'index.html' || key === '') key = 'main';
      inputs[key] = fullPath;
    }
  }
  return inputs;
}

export default defineConfig(() => {
  // Garante compilação prévia do blog para que todas as rotas existam no momento do build
  gerarBlog();
  const inputs = findHtmlInputs(__dirname);

  return {
    root: resolve(__dirname, '.'),
    publicDir: resolve(__dirname, 'public'),
    build: {
      outDir: resolve(__dirname, 'dist'),
      emptyOutDir: true,
      target: 'es2020',
      cssMinify: true,
      rollupOptions: {
        input: inputs,
        output: {
          assetFileNames: 'assets/[name]-[hash][extname]',
          entryFileNames: 'assets/[name]-[hash].js',
        },
      },
    },
    server: {
      port: 3000,
      open: true,
    },
  };
});
