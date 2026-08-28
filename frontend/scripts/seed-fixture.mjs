#!/usr/bin/env node
/**
 * Revsist — Semeador da fixture de validação (doc 26 § 26.3)
 * ====================================================================
 *
 * Cria (ou recria do zero) um projeto determinístico para a comparação
 * visual e os roteiros manuais funcionarem sem ruído: mesmo título, mesma
 * metodologia, mesmos 12 estudos com decisões conhecidas, mesmas 3
 * extrações preenchidas — sempre que rodar, o estado é idêntico.
 *
 *   node scripts/seed-fixture.mjs
 *
 * Idempotente: se o projeto fixture (pelo título fixo) já existir, ele é
 * apagado e recriado — nunca acumula em cima do que rodou antes.
 *
 * Requer o backend rodando (RSAC_BACKEND_URL, padrão http://127.0.0.1:8000).
 */

import { BACKEND_URL, TITULO_FIXTURE, chamar, checaBackend } from './shared/rsac-fixture.mjs'

async function apagaFixtureExistente() {
  const lista = await chamar('/projects?page_size=100')
  const items = lista.items || lista
  const existentes = (Array.isArray(items) ? items : []).filter((p) => p.title === TITULO_FIXTURE)
  for (const p of existentes) {
    await chamar(`/projects/${p.id}`, { method: 'DELETE' })
    console.log(`  removido projeto fixture anterior (${p.id})`)
  }
}

async function criaProjeto() {
  const projeto = await chamar('/projects', {
    method: 'POST',
    body: JSON.stringify({
      title: TITULO_FIXTURE,
      description: 'Projeto gerado por scripts/seed-fixture.mjs — não editar manualmente.',
      methodology: 'PRISMA-ScR',
    }),
  })
  console.log(`  projeto criado: ${projeto.id}`)
  return projeto
}

async function preencheProtocolo(projectId) {
  await chamar(`/projects/${projectId}/protocol`, {
    method: 'PUT',
    body: JSON.stringify({
      objective:
        'Mapear, na literatura de Ciências Sociais Aplicadas, os instrumentos de política pública ' +
        'usados em arranjos de governança territorial multinível voltados ao desenvolvimento regional.',
      pico_framework: {
        population: 'Territórios e arranjos produtivos locais em desenvolvimento regional',
        concept: 'Instrumentos de governança territorial multinível',
        context: 'Ciências Sociais Aplicadas — América Latina',
      },
      search_descriptors: {
        pt: ['"governança territorial" AND "desenvolvimento regional"', '"arranjo produtivo local" AND "política pública"'],
        en: ['"territorial governance" AND "regional development"'],
      },
      search_filters: { year_start: 2015, year_end: 2026, languages: ['pt', 'en', 'es'] },
      manuscript_sections: {
        rationale: 'Fixture de validação — não representa pesquisa real.',
      },
      criteria: [
        { text: 'Estudo empírico sobre governança territorial multinível', is_exclusion: false, order: 0 },
        { text: 'Publicado entre 2015 e 2026', is_exclusion: false, order: 1 },
        { text: 'Não é revisão sistemática ou de escopo', is_exclusion: true, order: 2 },
        { text: 'Não está em português, inglês ou espanhol', is_exclusion: true, order: 3 },
      ],
      extraction_questions: [
        { text: 'Qual o desenho metodológico do estudo?', order: 0 },
        { text: 'Quais instrumentos de política pública foram identificados?', order: 1 },
        { text: 'Qual a escala territorial analisada (local, regional, nacional)?', order: 2 },
        { text: 'Quais atores institucionais participam do arranjo de governança?', order: 3 },
        { text: 'Quais limitações os autores reportam?', order: 4 },
      ],
    }),
  })
  console.log('  protocolo preenchido (4 critérios, 5 perguntas de extração)')
}

const AUTORES = ['Silva, J. A.', 'Santos, M. B. C.', 'Oliveira, P. R.', 'Costa, A. L.', 'Ferreira, T. M.']

function autoresPara(indice) {
  return [AUTORES[indice % AUTORES.length], AUTORES[(indice + 2) % AUTORES.length]].join('; ')
}

const ESTUDOS = [
  // 5 incluídos (3 com extração preenchida, 2 sem)
  { titulo: 'Governança Territorial Multinível e Arranjos Produtivos Locais no Desenvolvimento Regional', decisao: 'Incluído', extrair: true },
  { titulo: 'Instrumentos de Política Pública em Redes de Cooperação Territorial na América Latina', decisao: 'Incluído', extrair: true },
  { titulo: 'Escalas de Governança e Coordenação Federativa em Políticas de Desenvolvimento Regional', decisao: 'Incluído', extrair: true },
  { titulo: 'Atores Institucionais em Arranjos Produtivos Locais: Uma Análise Comparativa', decisao: 'Incluído', extrair: false },
  { titulo: 'Descentralização e Capacidade Estatal em Territórios de Baixa Densidade Institucional', decisao: 'Incluído', extrair: false },
  // 4 excluídos
  { titulo: 'Revisão Sistemática sobre Desenvolvimento Regional: Uma Síntese da Literatura', decisao: 'Excluído' },
  { titulo: 'Scoping Review dos Instrumentos de Avaliação de Políticas Territoriais', decisao: 'Excluído' },
  { titulo: 'Territorial Governance Instruments: A Meta-Analysis of European Case Studies', decisao: 'Excluído' },
  { titulo: 'Politique Régionale et Gouvernance Territoriale en Amérique Latine', decisao: 'Excluído' },
  // 3 pendentes
  { titulo: 'Cooperação Intermunicipal e Consórcios Públicos no Planejamento Territorial', decisao: 'Pendente' },
  { titulo: 'Financiamento de Arranjos Produtivos Locais: Fontes, Critérios e Efetividade', decisao: 'Pendente' },
  { titulo: 'Participação Social em Conselhos Territoriais de Desenvolvimento Regional', decisao: 'Pendente' },
]

async function criaPapers(projectId, protocolo) {
  const criterios = protocolo.criteria || []
  const perguntas = protocolo.extraction_questions || []
  const criados = []

  for (const [i, estudo] of ESTUDOS.entries()) {
    const paper = await chamar(`/projects/${projectId}/papers`, {
      method: 'POST',
      body: JSON.stringify({
        title: estudo.titulo,
        authors: autoresPara(i),
        year: String(2015 + (i % 11)),
        abstract:
          `Resumo de teste ${i + 1}/12 gerado pela fixture de validação visual. ` +
          'Não representa achado científico real — existe apenas para dar corpo às telas ' +
          'de Triagem, Extração e Exportação durante a comparação visual.',
      }),
    })
    criados.push(paper)

    if (estudo.decisao !== 'Pendente') {
      const avaliacoes = {}
      for (const c of criterios) avaliacoes[c.id] = !c.is_exclusion
      await chamar(`/projects/${projectId}/papers/${paper.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ decision: estudo.decisao, criteria_evaluations: avaliacoes }),
      })
    }

    if (estudo.extrair && perguntas.length) {
      const respostas = {}
      perguntas.forEach((q, qi) => {
        respostas[q.id] = `Resposta fixture ${qi + 1} para "${q.text.slice(0, 40)}…" (estudo ${i + 1}).`
      })
      await chamar(`/projects/${projectId}/papers/${paper.id}/extraction`, {
        method: 'PUT',
        body: JSON.stringify(respostas),
      })
    }
  }

  console.log(`  ${criados.length} estudos criados (5 incluídos · 4 excluídos · 3 pendentes; 3 com extração preenchida)`)
  return criados
}

async function main() {
  console.log(`Semeando fixture em ${BACKEND_URL}…`)
  await checaBackend()
  await apagaFixtureExistente()
  const projeto = await criaProjeto()
  await preencheProtocolo(projeto.id)
  const protocolo = await chamar(`/projects/${projeto.id}/protocol`)
  await criaPapers(projeto.id, protocolo)
  console.log(`\nFixture pronta: projeto ${projeto.id}`)
  console.log(`Título: ${TITULO_FIXTURE}`)
}

main().catch((err) => {
  console.error('\nFalha ao semear a fixture:', err.message)
  process.exit(1)
})
