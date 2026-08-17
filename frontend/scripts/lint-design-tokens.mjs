#!/usr/bin/env node
/**
 * RSAC V2 — Verificador do Design System
 * ======================================
 *
 * Camada 1 da validação (doc 26). Aplica as regras do doc 24 § 24.11 sobre
 * `frontend/src/`. Sem dependência externa: roda em milissegundos e serve para
 * o gancho de pre-push.
 *
 * MODO DE ADOÇÃO — o detalhe que separa uma regra viva de uma regra desligada:
 * cada categoria entra em `--strict` INDIVIDUALMENTE, no commit que zera a sua
 * última violação. Regra que quebra o build sem caminho de saída é regra que
 * alguém com pressa vai desligar.
 *
 *   node scripts/lint-design-tokens.mjs            # relatório, sai 0
 *   node scripts/lint-design-tokens.mjs --strict   # sai 1 se houver regressão
 *   node scripts/lint-design-tokens.mjs --json     # saída para automação
 */

import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative, extname } from 'node:path'
import { fileURLToPath } from 'node:url'

const RAIZ = join(fileURLToPath(new URL('.', import.meta.url)), '..')
const FONTE = join(RAIZ, 'src')
const TOKENS = join(FONTE, 'styles/globals.css')

/**
 * Linha de base de 17/08/2026, depois da migração de tokens.
 *
 * `teto: 0` é uma categoria já fechada — qualquer violação nova falha em
 * `--strict`. Um teto acima de zero é dívida conhecida: não falha, mas também
 * não pode crescer. Quando zerar, vira `teto: 0` no mesmo commit.
 */
const REGRAS = [
  {
    id: 'R1',
    nome: 'cor literal fora de globals.css',
    teto: 0,
    arquivos: /\.css$/,
    isento: (rel) => rel.endsWith('styles/globals.css'),
    padrao: /#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)/g,
    dica: 'use um token de cor; se não existir, crie-o em globals.css',
  },
  {
    id: 'R2a',
    nome: 'font-size literal',
    teto: 0,
    arquivos: /\.css$/,
    isento: (rel) => rel.endsWith('styles/globals.css'),
    // Captura o valor e testa em código: o lookahead `(?!var\()` tem buraco de
    // backtracking — o `\s*` recua para zero e a asserção passa no espaço.
    propriedade: /font-size:\s*([^;]+);/g,
    // `em`/`%` são relativos ao pai: dentro de prosa aninhada é justamente o
    // comportamento desejado, e nenhum token absoluto substitui isso.
    literal: (v) => !v.startsWith('var(') && !/^[\d.]+(?:em|%)$/.test(v)
      && !['inherit', 'initial', 'unset', 'smaller', 'larger'].includes(v),
    dica: 'use var(--font-size-*)',
  },
  {
    id: 'R2b',
    nome: 'z-index literal',
    teto: 0,
    arquivos: /\.css$/,
    isento: (rel) => rel.endsWith('styles/globals.css'),
    propriedade: /z-index:\s*([^;]+);/g,
    literal: (v) => !v.startsWith('var(') && v !== 'auto',
    dica: 'use a escala nomeada var(--z-*)',
  },
  {
    id: 'R2c',
    nome: 'border-radius literal',
    teto: 0,
    arquivos: /\.css$/,
    isento: (rel) => rel.endsWith('styles/globals.css'),
    propriedade: /border-radius:\s*([^;]+);/g,
    // 50% é ponto de estado circular, não canto de controle; 0 é zerar.
    literal: (v) => !v.startsWith('var(') && !['50%', '0', 'inherit'].includes(v)
      && !v.split(/\s+/).every((parte) => parte.startsWith('var(') || parte === '0'),
    dica: 'use var(--radius-*)',
  },
  {
    id: 'R2d',
    nome: 'espaçamento literal',
    // Dívida conhecida: a migração dos espaçamentos é a única categoria da
    // Fase 1 ainda aberta. O teto trava o crescimento até ela ser fechada.
    teto: 265,
    arquivos: /\.css$/,
    isento: (rel) => rel.endsWith('styles/globals.css'),
    propriedade: /(?:padding|margin|gap):\s*([^;]+);/g,
    literal: (v) => /\d\s*(?:px|rem|em)/.test(v)
      && !v.split(/\s+/).every((parte) => parte.startsWith('var(') || parte === '0' || parte === 'auto'),
    dica: 'use var(--space-*)',
  },
  {
    id: 'R3',
    nome: 'interface acionada pelo DOM',
    teto: 0,
    arquivos: /\.tsx?$/,
    padrao: /document\.querySelector[^\n]*\.click\(\)|clickDomBy\w+|clickDom\(/g,
    dica: 'despache pelo registro de comandos (useRibbonStore)',
  },
  {
    id: 'R7',
    nome: 'diretriz metodológica fixa no JSX',
    // Dívida conhecida (5): modelos de texto que o pesquisador INSERE no
    // manuscrito citam PRISMA-P/ScR na própria prosa. Sob CEE/ROSES o modelo
    // fica errado, mas corrigir exige redigir um modelo por diretriz — é
    // conteúdo da Fase 6 (doc 25 § 25.8), não ajuste de rótulo. O teto impede
    // que o número cresça enquanto isso.
    teto: 5,
    arquivos: /\.tsx$/,
    isento: (rel) => rel.includes('src/data/protocol'),
    // Só o texto VISÍVEL é violação. Uma string cujo conteúdo inteiro é o nome
    // da diretriz é chave ou valor padrão — `PROTOCOL_CATALOG['PRISMA-ScR']`,
    // `methodology = 'PRISMA-ScR'` — e continua legítima.
    padrao: /(?<!['"])(?:PRISMA-ScR|PRISMA 2020|PRISMA-P|Methodi Ordinatio)(?!['"])/g,
    dica: 'leia de PROTOCOL_CATALOG — a diretriz ativa varia por projeto',
  },
]

// ── Coleta de arquivos ────────────────────────────────────────────────────
function varrer(dir, saida = []) {
  for (const nome of readdirSync(dir)) {
    if (nome === 'node_modules' || nome.startsWith('.')) continue
    const caminho = join(dir, nome)
    if (statSync(caminho).isDirectory()) varrer(caminho, saida)
    else if (['.css', '.ts', '.tsx'].includes(extname(nome))) saida.push(caminho)
  }
  return saida
}

/** Remove comentários para não acusar exemplo em documentação. */
function semComentarios(texto, ext) {
  const semBloco = texto.replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, ' '))
  return ext === '.css' ? semBloco : semBloco.replace(/^\s*\/\/.*$/gm, '')
}

// ── Execução ──────────────────────────────────────────────────────────────
const arquivos = varrer(FONTE)
const achados = new Map(REGRAS.map((r) => [r.id, []]))

for (const caminho of arquivos) {
  const rel = relative(RAIZ, caminho).replace(/\\/g, '/')
  const ext = extname(caminho)
  const bruto = readFileSync(caminho, 'utf8')
  const limpo = semComentarios(bruto, ext)
  const linhas = limpo.split('\n')

  for (const regra of REGRAS) {
    if (!regra.arquivos.test(caminho)) continue
    if (regra.isento?.(rel)) continue
    linhas.forEach((linha, i) => {
      if (regra.propriedade) {
        for (const m of linha.matchAll(regra.propriedade)) {
          const valor = m[1].trim()
          if (regra.literal(valor)) {
            achados.get(regra.id).push({ arquivo: rel, linha: i + 1, trecho: m[0].trim().slice(0, 62) })
          }
        }
        return
      }
      for (const trecho of linha.match(regra.padrao) ?? []) {
        achados.get(regra.id).push({ arquivo: rel, linha: i + 1, trecho: trecho.trim().slice(0, 62) })
      }
    })
  }
}

// Sanidade: todo token referenciado precisa existir em globals.css.
const declarados = new Set()
for (const caminho of [TOKENS, ...arquivos.filter((c) => extname(c) === '.css')]) {
  for (const m of readFileSync(caminho, 'utf8').matchAll(/^\s*(--[a-z0-9-]+)\s*:/gm)) {
    declarados.add(m[1])
  }
}
const fantasmas = new Map()
for (const caminho of arquivos.filter((c) => extname(c) === '.css')) {
  const rel = relative(RAIZ, caminho).replace(/\\/g, '/')
  const texto = semComentarios(readFileSync(caminho, 'utf8'), '.css')
  for (const m of texto.matchAll(/var\((--[a-z0-9-]+)(\s*,)?/g)) {
    // Um token indefinido COM fallback é escolha deliberada; sem fallback é erro.
    if (!declarados.has(m[1]) && !m[2] && !fantasmas.has(m[1])) fantasmas.set(m[1], rel)
  }
}

// ── Relatório ─────────────────────────────────────────────────────────────
const estrito = process.argv.includes('--strict')
const json = process.argv.includes('--json')
let regrediu = false
const resumo = []

for (const regra of REGRAS) {
  const lista = achados.get(regra.id)
  const acima = lista.length > regra.teto
  if (acima) regrediu = true
  resumo.push({ id: regra.id, nome: regra.nome, encontrados: lista.length, teto: regra.teto, acima })

  if (json) continue
  const marca = acima ? '✗' : lista.length === 0 ? '✓' : '·'
  const alvo = regra.teto === 0 ? 'fechada' : `teto ${regra.teto}`
  console.log(`${marca} ${regra.id.padEnd(4)} ${regra.nome.padEnd(38)} ${String(lista.length).padStart(4)}  (${alvo})`)
  if (acima) {
    for (const a of lista.slice(0, 12)) console.log(`      ${a.arquivo}:${a.linha}  ${a.trecho}`)
    if (lista.length > 12) console.log(`      … e mais ${lista.length - 12}`)
    console.log(`      → ${regra.dica}`)
  }
}

if (fantasmas.size) {
  regrediu = true
  if (!json) {
    console.log(`\n✗ TOKEN token indefinido e sem fallback (${fantasmas.size})`)
    for (const [tok, arq] of fantasmas) console.log(`      ${arq}  ${tok}`)
  }
  resumo.push({ id: 'TOKEN', nome: 'token indefinido', encontrados: fantasmas.size, teto: 0, acima: true })
}

if (json) {
  console.log(JSON.stringify({ regrediu, regras: resumo }, null, 2))
} else {
  console.log(
    regrediu
      ? '\nRegressão detectada. Corrija ou justifique ajustando o teto no mesmo commit.'
      : `\nSem regressão · ${arquivos.length} arquivos verificados.`
  )
}

process.exit(estrito && regrediu ? 1 : 0)
