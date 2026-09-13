#!/usr/bin/env node
/**
 * Revsist — Renderiza um laço da landing em duas passadas.
 *
 * Uso: node scripts/renderizar-laco.mjs <hero|busca|registro|diagrama|faixa|registro-faixa|diagrama-faixa|roteiros-faixa|para-quem-faixa>
 *
 * 1. Renderiza na resolução nativa da composição (--scale=1) e com qualidade
 *    alta. Renderizar direto com --scale=0.75 põe o Chrome num devicePixelRatio
 *    fracionário: cada pixel de CSS cai em 0,75 pixel de tela, os glifos são
 *    encaixados num pixel e as caixas em outro, e o texto treme a cada quadro
 *    em que algo se move.
 * 2. Reduz para a largura de entrega com lanczos e codifica o MP4 final. A
 *    redução acontece sobre imagem pronta, então não há encaixe de glifo.
 */

import { spawnSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

const RAIZ = join(fileURLToPath(new URL('.', import.meta.url)), '..')

const LACOS = {
  hero: { composicao: 'HeroLoop', largura: 1440 },
  busca: { composicao: 'LacoBusca', largura: 1280 },
  registro: { composicao: 'LacoRegistro', largura: 1200 },
  diagrama: { composicao: 'LacoDiagrama', largura: 1440 },
  faixa: { composicao: 'FaixaVaiVem', largura: 1920 },
  'registro-faixa': { composicao: 'FaixaRegistro', largura: 1920 },
  'diagrama-faixa': { composicao: 'FaixaDiagrama', largura: 1920 },
  'roteiros-faixa': { composicao: 'FaixaRoteiros', largura: 1920 },
  'para-quem-faixa': { composicao: 'FaixaParaQuem', largura: 1920 },
}

const nome = process.argv[2]
const laco = LACOS[nome]
if (!laco) {
  console.error(`Laço desconhecido: ${nome ?? '(nenhum)'}. Use: ${Object.keys(LACOS).join(', ')}`)
  process.exit(1)
}

const mestre = join('out', `revsist-${nome}-mestre.mp4`)
const final = join('..', 'landing', 'public', 'videos', `revsist-${nome}.mp4`)

const rodar = (args) => {
  const r = spawnSync('npx', ['remotion', ...args], { cwd: RAIZ, stdio: 'inherit', shell: true })
  if (r.status !== 0) process.exit(r.status ?? 1)
}

mkdirSync(join(RAIZ, 'out'), { recursive: true })

rodar([
  'render',
  'src/index.ts',
  laco.composicao,
  mestre,
  '--codec=h264',
  '--crf=12',
  '--scale=1',
  '--jpeg-quality=95',
])

rodar([
  'ffmpeg',
  '-y',
  '-i',
  mestre,
  '-vf',
  `scale=${laco.largura}:-2:flags=lanczos`,
  '-c:v',
  'libx264',
  '-preset',
  'slow',
  '-crf',
  '24',
  '-pix_fmt',
  'yuv420p',
  '-movflags',
  '+faststart',
  '-an',
  final,
])
