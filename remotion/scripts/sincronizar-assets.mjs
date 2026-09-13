#!/usr/bin/env node
/**
 * Revsist — Sincroniza os assets que o vídeo consome a partir da landing.
 *
 * O Remotion só enxerga arquivos dentro de `public/`, mas as capturas de tela e
 * as fontes já vivem em `landing/`. Copiar na hora do render (em vez de manter
 * uma segunda cópia versionada) evita o problema que motivou este script: o
 * vídeo continuar mostrando o app numa paleta que a landing não usa mais.
 *
 * Roda automaticamente antes de `npm start` e dos scripts de render.
 */

import { copyFileSync, existsSync, mkdirSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

const RAIZ = join(fileURLToPath(new URL('.', import.meta.url)), '..')
const LANDING = join(RAIZ, '..', 'landing')

const CONJUNTOS = [
  {
    nome: 'capturas de tela',
    origem: join(LANDING, 'src', 'imagens', 'telas'),
    destino: join(RAIZ, 'public', 'telas'),
    filtro: (arquivo) => arquivo.endsWith('-1280.webp'),
  },
  {
    nome: 'fontes da marca',
    origem: join(LANDING, 'public', 'fonts'),
    destino: join(RAIZ, 'public', 'fonts'),
    filtro: (arquivo) => arquivo.endsWith('.woff2'),
  },
]

let total = 0

for (const { nome, origem, destino, filtro } of CONJUNTOS) {
  if (!existsSync(origem)) {
    console.error(`Origem ausente para ${nome}: ${origem}`)
    process.exitCode = 1
    continue
  }

  mkdirSync(destino, { recursive: true })

  const arquivos = readdirSync(origem).filter(filtro)
  for (const arquivo of arquivos) {
    copyFileSync(join(origem, arquivo), join(destino, arquivo))
  }

  total += arquivos.length
  console.log(`  ${arquivos.length} ${nome} sincronizadas`)
}

console.log(`Assets do vídeo sincronizados com a landing (${total} arquivos).`)
