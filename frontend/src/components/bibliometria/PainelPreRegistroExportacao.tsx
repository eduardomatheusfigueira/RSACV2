/**
 * Revsist — Painel de Pré-Registro, Conformidade BIBLIO e Pacote de Replicação (doc 48 §11, §12, doc 49 Fase 9).
 *
 * Garante que:
 * 1. O plano bibliométrico pré-registrado seja consultável e versionado com emendas rastreáveis.
 * 2. O relatório de 20 itens BIBLIO separe estritamente garantias de software vs. responsabilidade do autor.
 * 3. O pacote de replicação completo (.zip) seja exportável com 1 clique para defesa em banca.
 */

import React, { useEffect, useState } from 'react'
import {
  AlertTriangle,
  Archive,
  CheckCircle2,
  Clock,
  Download,
  FileCheck2,
  FileCode2,
  FileText,
  History,
  Info,
  Lock,
  Plus,
  Save,
  ShieldCheck,
  Sparkles,
  Unlock,
  UserCheck,
} from 'lucide-react'
import { api } from '@/api/client'
import { Button, Card, EmptyState, FormGroup, Input, LoadingState, Select } from '@/components/ui'
import type {
  AtualizarPlanoBibliometricoRequest,
  ItemConformidadeBiblio,
  PlanoBibliometrico,
  RelatorioConformidadeBiblioResponse,
} from '@/types/api'
import './PainelPreRegistroExportacao.css'

interface PainelPreRegistroExportacaoProps {
  projectId: string
  snapshotId?: string | null
}

const INDICADORES_DISPONIVEIS = [
  { id: 'producao_anual', label: 'Produção Anual e CAGR' },
  { id: 'top_autores', label: 'Top Autores e Produtividade (Lotka)' },
  { id: 'top_periodicos', label: 'Top Periódicos e Núcleo (Bradford)' },
  { id: 'colaboracao', label: 'Índice de Colaboração (Subramanyam)' },
  { id: 'citacoes_impacto', label: 'Citações e Índice h' },
  { id: 'acesso_aberto', label: 'Acesso Aberto e Geografia' },
  { id: 'coautoria', label: 'Rede de Coautoria' },
  { id: 'coocorrencia_termos', label: 'Rede de Coocorrência de Termos' },
  { id: 'acoplamento_bibliografico', label: 'Acoplamento Bibliográfico' },
  { id: 'cocitacao', label: 'Cocitação de Referências' },
  { id: 'diagrama_estrategico', label: 'Diagrama Estratégico SciMAT' },
  { id: 'rajadas', label: 'Detecção de Rajadas Temporais (Kleinberg)' },
  { id: 'bootstrap_rankings', label: 'Rankings com Bootstrap IC 95%' },
  { id: 'sensibilidade_louvain', label: 'Sensibilidade de Agrupamento (ARI)' },
  { id: 'cobertura_campo', label: 'Diagnóstico de Cobertura do Campo' },
]

export const PainelPreRegistroExportacao: React.FC<PainelPreRegistroExportacaoProps> = ({
  projectId,
  snapshotId,
}) => {
  const [abaAtiva, setAbaAtiva] = useState<'plano' | 'biblio' | 'exportar'>('plano')
  const [plano, setPlano] = useState<PlanoBibliometrico | null>(null)
  const [relatorioBiblio, setRelatorioBiblio] = useState<RelatorioConformidadeBiblioResponse | null>(null)
  const [carregando, setCarregando] = useState(true)
  const [salvando, setSalvando] = useState(false)
  const [baixandoZip, setBaixandoZip] = useState(false)
  const [mensagemSucesso, setMensagemSucesso] = useState<string | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  // Estado do formulário de plano
  const [indicadoresSel, setIndicadoresSel] = useState<string[]>([])
  const [unidadeAnalise, setUnidadeAnalise] = useState<string>('documento')
  const [janelaTemporal, setJanelaTemporal] = useState<string>('')
  const [justificativaJanela, setJustificativaJanela] = useState<string>('')
  const [tesauroObrigatorio, setTesauroObrigatorio] = useState<boolean>(true)

  const carregarDados = async () => {
    try {
      setCarregando(true)
      setErro(null)
      const [resPlano, resBiblio] = await Promise.all([
        api.obterPlanoBibliometrico(projectId),
        api.obterRelatorioConformidadeBiblio(projectId, snapshotId),
      ])
      setPlano(resPlano)
      setRelatorioBiblio(resBiblio)

      setIndicadoresSel(resPlano.indicadores_previstos || [])
      setUnidadeAnalise(resPlano.unidade_analise || 'documento')
      setJanelaTemporal(resPlano.janela_temporal || '')
      setJustificativaJanela(resPlano.justificativa_janela || '')
      setTesauroObrigatorio(resPlano.tesauro_obrigatorio ?? true)
    } catch (e: any) {
      setErro(e.message || 'Falha ao carregar dados de pré-registro.')
    } finally {
      setCarregando(false)
    }
  }

  useEffect(() => {
    carregarDados()
  }, [projectId, snapshotId])

  const toggleIndicador = (id: string) => {
    setIndicadoresSel((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    )
  }

  const salvarPlano = async () => {
    try {
      setSalvando(true)
      setMensagemSucesso(null)
      const payload: AtualizarPlanoBibliometricoRequest = {
        indicadores_previstos: indicadoresSel,
        unidade_analise: unidadeAnalise,
        janela_temporal: janelaTemporal,
        justificativa_janela: justificativaJanela,
        cortes_declarados: plano?.cortes_declarados || { freq_minima_termo: 2, resolucao_louvain: 1.0 },
        tesauro_obrigatorio: tesauroObrigatorio,
      }
      const res = await api.atualizarPlanoBibliometrico(projectId, payload)
      setPlano(res)
      setMensagemSucesso(
        res.status_protocolo === 'vigente'
          ? 'Plano atualizado com sucesso! Uma emenda formal foi registrada no protocolo.'
          : 'Plano bibliométrico pré-registrado atualizado com sucesso.'
      )
      // Atualizar relatório BIBLIO
      const resBiblio = await api.obterRelatorioConformidadeBiblio(projectId, snapshotId)
      setRelatorioBiblio(resBiblio)
    } catch (e: any) {
      setErro(e.message || 'Erro ao salvar plano bibliométrico.')
    } finally {
      setSalvando(false)
    }
  }

  const handleBaixarZip = async () => {
    try {
      setBaixandoZip(true)
      const blob = await api.baixarPacoteReplicacao(projectId, snapshotId)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `pacote_replicacao_bibliometria_${projectId.slice(0, 8)}.zip`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
    } catch (e: any) {
      setErro(e.message || 'Erro ao baixar pacote de replicação.')
    } finally {
      setBaixandoZip(false)
    }
  }

  if (carregando) {
    return <LoadingState label="Carregando auditoria de pré-registro e conformidade..." />
  }

  return (
    <div className="painel-preregistro">
      {/* ── Navegação de Abas da Fase 9 ───────────────────────────────────── */}
      <div className="painel-preregistro__cabecalho">
        <div className="painel-preregistro__nav">
          <button
            type="button"
            onClick={() => setAbaAtiva('plano')}
            className={`painel-preregistro__nav-btn ${abaAtiva === 'plano' ? 'painel-preregistro__nav-btn--active' : ''}`}
          >
            <ShieldCheck size={15} />
            <span>Plano Pré-Registrado</span>
          </button>

          <button
            type="button"
            onClick={() => setAbaAtiva('biblio')}
            className={`painel-preregistro__nav-btn ${abaAtiva === 'biblio' ? 'painel-preregistro__nav-btn--active' : ''}`}
          >
            <FileCheck2 size={15} />
            <span>Relatório BIBLIO (20 Itens)</span>
            {relatorioBiblio && (
              <span className="painel-preregistro__badge-score">
                {relatorioBiblio.itens_conformes}/20
              </span>
            )}
          </button>

          <button
            type="button"
            onClick={() => setAbaAtiva('exportar')}
            className={`painel-preregistro__nav-btn ${abaAtiva === 'exportar' ? 'painel-preregistro__nav-btn--active' : ''}`}
          >
            <Archive size={15} />
            <span>Pacote de Replicação (.zip)</span>
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>Protocolo:</span>
          <span
            style={{
              padding: 'var(--space-0-5) var(--space-2)',
              borderRadius: 'var(--radius-xl)',
              fontSize: 'var(--text-xs)',
              fontWeight: 700,
              background: plano?.status_protocolo === 'vigente' ? 'var(--color-success-bg)' : 'var(--color-warning-bg)',
              color: plano?.status_protocolo === 'vigente' ? 'var(--color-success-text)' : 'var(--color-warning-text)',
              border: `1px solid ${plano?.status_protocolo === 'vigente' ? 'var(--color-success)' : 'var(--color-warning)'}`,
            }}
          >
            {plano?.status_protocolo === 'vigente' ? '🔒 Vigente (Congelado)' : '📝 Rascunho'}
          </span>
          <span style={{ fontSize: 'var(--text-xs)', fontFamily: 'monospace', background: 'var(--color-bg-primary)', padding: 'var(--space-0-5) var(--space-1-5)', borderRadius: 'var(--radius-xl)' }}>
            {plano?.versao_protocolo}
          </span>
        </div>
      </div>

      {mensagemSucesso && (
        <div style={{ padding: 'var(--space-2-5) var(--space-4)', background: 'var(--color-success-bg)', border: 'var(--space-px) solid var(--color-success)', borderRadius: 'var(--radius-xl)', fontSize: 'var(--text-sm)', color: 'var(--color-success-text)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <CheckCircle2 size={16} />
          <span>{mensagemSucesso}</span>
        </div>
      )}

      {erro && (
        <div className="painel-estatistica__alerta-erro">
          <AlertTriangle size={16} />
          <span>{erro}</span>
        </div>
      )}

      {/* ── ABA 1: PLANO PRÉ-REGISTRADO (Doc 48 §11) ────────────────────────── */}
      {abaAtiva === 'plano' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <Card surface="secundaria" relief="plano" className="p-5">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
              <div>
                <h3 style={{ fontSize: 'var(--text-base)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 'var(--space-2)', margin: 0, color: 'var(--color-text-primary)' }}>
                  <ShieldCheck size={18} className="text-accent" />
                  Indicadores Previstos a Priori (Confirmatórios)
                </h3>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', margin: 'var(--space-1) 0 0 0' }}>
                  Qualquer cálculo ou agregação fora desta lista será automaticamente rotulada como{' '}
                  <strong style={{ color: 'var(--color-warning-text)' }}>exploratória</strong> para evitar viés de seleção
                  (HARK-ing, doc 48 §11).
                </p>
              </div>
              <Button
                variant="primary"
                size="sm"
                onClick={salvarPlano}
                disabled={salvando}
                leftIcon={<Save size={14} />}
              >
                {salvando ? 'Salvando...' : 'Salvar Plano'}
              </Button>
            </div>

            <div className="painel-preregistro__grid-indicadores">
              {INDICADORES_DISPONIVEIS.map((ind) => {
                const checked = indicadoresSel.includes(ind.id)
                return (
                  <label
                    key={ind.id}
                    className={`painel-preregistro__item-indicador ${checked ? 'painel-preregistro__item-indicador--sel' : ''}`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleIndicador(ind.id)}
                      style={{ cursor: 'pointer' }}
                    />
                    <span className="painel-preregistro__item-indicador-label">{ind.label}</span>
                  </label>
                )
              })}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 'var(--space-4)', paddingTop: 'var(--space-4)', borderTop: 'var(--space-px) solid var(--color-border)', marginTop: 'var(--space-4)' }}>
              <FormGroup label="Unidade Principal de Análise" htmlFor="plano-unidade">
                <Select
                  id="plano-unidade"
                  value={unidadeAnalise}
                  onChange={(e) => setUnidadeAnalise(e.target.value)}
                  sizeVariant="sm"
                >
                  <option value="documento">Documento (Artigo)</option>
                  <option value="autor">Autor Individual</option>
                  <option value="fonte">Periódico / Fonte</option>
                  <option value="termo">Palavra-chave / Tópico</option>
                </Select>
              </FormGroup>

              <FormGroup label="Janela Temporal Declarada" htmlFor="plano-janela">
                <Input
                  id="plano-janela"
                  value={janelaTemporal}
                  onChange={(e) => setJanelaTemporal(e.target.value)}
                  placeholder="Ex.: 2015-2024 ou Completa"
                  sizeVariant="sm"
                />
              </FormGroup>

              <FormGroup label="Justificativa da Janela" htmlFor="plano-justificativa">
                <Input
                  id="plano-justificativa"
                  value={justificativaJanela}
                  onChange={(e) => setJustificativaJanela(e.target.value)}
                  placeholder="Ex.: Marco regulatório de inovação regional."
                  sizeVariant="sm"
                />
              </FormGroup>
            </div>
          </Card>

          {/* Emendas de Protocolo */}
          {plano && plano.emendas && plano.emendas.length > 0 && (
            <Card surface="secundaria" relief="plano" className="p-5">
              <h3 style={{ fontSize: 'var(--text-md)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-3)', color: 'var(--color-text-primary)' }}>
                <History size={16} className="text-accent" />
                Histórico de Emendas Metodológicas ({plano.emendas.length})
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                {plano.emendas.map((emenda) => (
                  <div
                    key={emenda.id}
                    style={{ padding: 'var(--space-2-5) var(--space-4)', background: 'var(--color-bg-primary)', border: 'var(--space-px) solid var(--color-border)', borderRadius: 'var(--radius-xl)', fontSize: 'var(--text-sm)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', fontFamily: 'monospace', fontWeight: 600 }}>
                        <span style={{ color: 'var(--color-text-secondary)' }}>{emenda.from_version}</span>
                        <span>→</span>
                        <span style={{ color: 'var(--color-accent)' }}>{emenda.to_version}</span>
                        <span style={{ padding: 'var(--space-px) var(--space-1-5)', background: 'var(--color-bg-elevated)', borderRadius: 'var(--radius-xl)', fontSize: 'var(--text-2xs)', textTransform: 'uppercase' }}>
                          {emenda.section}
                        </span>
                      </div>
                      <p style={{ color: 'var(--color-text-secondary)', margin: 'var(--space-1) 0 0 0' }}>{emenda.reason}</p>
                    </div>
                    <span style={{ color: 'var(--color-text-secondary)', fontFamily: 'monospace', fontSize: 'var(--text-xs)' }}>
                      {emenda.created_at ? new Date(emenda.created_at).toLocaleString() : ''}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ── ABA 2: RELATÓRIO DE CONFORMIDADE BIBLIO (20 Itens) ──────────────── */}
      {abaAtiva === 'biblio' && relatorioBiblio && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          {/* Card Resumo */}
          <div className="painel-preregistro__biblio-resumo">
            <div className="painel-preregistro__biblio-stat">
              <span className="painel-preregistro__biblio-stat-valor">{relatorioBiblio.total_itens}</span>
              <span className="painel-preregistro__biblio-stat-label">Total de Itens</span>
            </div>

            <div className="painel-preregistro__biblio-stat">
              <span className="painel-preregistro__biblio-stat-valor" style={{ color: 'var(--color-success)' }}>
                {relatorioBiblio.itens_conformes}
              </span>
              <span className="painel-preregistro__biblio-stat-label">Itens Conformes</span>
            </div>

            <div className="painel-preregistro__biblio-stat">
              <span className="painel-preregistro__biblio-stat-valor" style={{ color: 'var(--color-info-text)' }}>
                {relatorioBiblio.itens_do_sistema}
              </span>
              <span className="painel-preregistro__biblio-stat-label">Auditoria de Software</span>
            </div>

            <div className="painel-preregistro__biblio-stat">
              <span className="painel-preregistro__biblio-stat-valor" style={{ color: 'var(--color-warning-text)' }}>
                {relatorioBiblio.itens_do_autor}
              </span>
              <span className="painel-preregistro__biblio-stat-label">Responsabilidade do Autor</span>
            </div>
          </div>

          {/* Resumo Executivo */}
          <div style={{ padding: 'var(--space-3) var(--space-4)', background: 'var(--color-bg-primary)', border: 'var(--space-px) solid var(--color-border)', borderRadius: 'var(--radius-xl)', fontSize: 'var(--text-sm)', color: 'var(--color-text-primary)', display: 'flex', alignItems: 'flex-start', gap: 'var(--space-2-5)' }}>
            <Info size={18} className="text-accent" style={{ marginTop: 'var(--space-0-5)', flexShrink: 0 }} />
            <div>
              <strong>Diagnóstico de Integridade:</strong> {relatorioBiblio.resumo_executivo}
            </div>
          </div>

          {/* Lista dos 20 Itens */}
          <Card surface="secundaria" relief="plano" className="p-5">
            <h3 style={{ fontSize: 'var(--text-md)', fontWeight: 700, marginBottom: 'var(--space-4)', color: 'var(--color-text-primary)' }}>
              Checklist Normativo BIBLIO (20 Itens)
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {relatorioBiblio.itens.map((item) => (
                <div
                  key={item.numero}
                  className="painel-preregistro__biblio-item"
                >
                  <div className="painel-preregistro__biblio-item-head">
                    <div className="painel-preregistro__biblio-item-titulo">
                      <span style={{ fontFamily: 'monospace', fontWeight: 700, background: 'var(--color-bg-elevated)', padding: 'var(--space-px) var(--space-1-5)', borderRadius: 'var(--radius-xl)', fontSize: 'var(--text-xs)' }}>
                        #{String(item.numero).padStart(2, '0')}
                      </span>
                      <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>
                        {item.secao}
                      </span>
                      <span>{item.item}</span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1-5)' }}>
                      <span
                        className={`painel-preregistro__biblio-badge-resp ${
                          item.responsabilidade === 'sistema'
                            ? 'painel-preregistro__biblio-badge-resp--software'
                            : 'painel-preregistro__biblio-badge-resp--author'
                        }`}
                      >
                        {item.responsabilidade === 'sistema' ? '💻 Software' : '✍️ Autor'}
                      </span>

                      <span
                        style={{
                          fontSize: 'var(--text-2xs)',
                          fontWeight: 700,
                          padding: 'var(--space-0-5) var(--space-1-5)',
                          borderRadius: 'var(--radius-xl)',
                          textTransform: 'uppercase',
                          background: item.status === 'conforme' ? 'var(--color-success-bg)' : 'var(--color-warning-bg)',
                          color: item.status === 'conforme' ? 'var(--color-success-text)' : 'var(--color-warning-text)',
                          border: `1px solid ${item.status === 'conforme' ? 'var(--color-success)' : 'var(--color-warning)'}`,
                        }}
                      >
                        {item.status === 'conforme' ? '✓ Conforme' : '⏳ Pendente'}
                      </span>
                    </div>
                  </div>

                  <p style={{ margin: 0, fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>{item.descricao}</p>
                  <p style={{ margin: 0, fontSize: 'var(--text-2xs)', color: 'var(--color-accent)', fontFamily: 'monospace' }}>
                    <strong>Evidência:</strong> {item.evidencia}
                  </p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* ── ABA 3: PACOTE DE REPLICAÇÃO EM ZIP ──────────────────────────────── */}
      {abaAtiva === 'exportar' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <div className="painel-preregistro__exportar-card">
            <div style={{ padding: 'var(--space-4)', borderRadius: 'var(--radius-full)', background: 'var(--color-bg-primary)', color: 'var(--color-accent)' }}>
              <Archive size={36} />
            </div>
            <div className="painel-preregistro__coluna-texto">
              <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 700, margin: 0, color: 'var(--color-text-primary)' }}>
                Pacote de Replicação Bibliométrica
              </h3>
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', marginTop: 'var(--space-1-5)' }}>
                Gera um arquivo compacto e autossuficiente contendo todos os dados brutos, grafos,
                proveniência de algoritmos, manifesto SHA-256 e relatório BIBLIO para anexar como
                material suplementar ou apresentar em banca avaliadora.
              </p>
            </div>

            <div style={{ paddingTop: 'var(--space-2)' }}>
              <Button
                variant="primary"
                size="md"
                onClick={handleBaixarZip}
                disabled={baixandoZip}
                leftIcon={<Download size={16} />}
              >
                {baixandoZip ? 'Gerando pacote ZIP...' : 'Baixar Pacote de Replicação (.zip)'}
              </Button>
            </div>
          </div>

          <Card surface="secundaria" relief="plano" className="p-5">
            <h4 style={{ fontSize: 'var(--text-md)', fontWeight: 700, marginBottom: 'var(--space-3)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--color-text-primary)' }}>
              <FileCode2 size={16} className="text-accent" />
              Conteúdo Incluso no Pacote de Replicação (.zip):
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--space-2-5)' }}>
              <div style={{ padding: 'var(--space-2-5) var(--space-3)', background: 'var(--color-bg-primary)', border: 'var(--space-px) solid var(--color-border)', borderRadius: 'var(--radius-xl)', fontSize: 'var(--text-xs)' }}>
                <span style={{ fontFamily: 'monospace', fontWeight: 700, color: 'var(--color-accent)' }}>manifesto_instantaneo.json</span>
                <p style={{ color: 'var(--color-text-secondary)', margin: 'var(--space-0-5) 0 0 0' }}>
                  Hash SHA-256 de cada documento e integridade do corpus congelado.
                </p>
              </div>

              <div style={{ padding: 'var(--space-2-5) var(--space-3)', background: 'var(--color-bg-primary)', border: 'var(--space-px) solid var(--color-border)', borderRadius: 'var(--radius-xl)', fontSize: 'var(--text-xs)' }}>
                <span style={{ fontFamily: 'monospace', fontWeight: 700, color: 'var(--color-accent)' }}>proveniencia.json</span>
                <p style={{ color: 'var(--color-text-secondary)', margin: 'var(--space-0-5) 0 0 0' }}>
                  Versão do motor de cálculo, data/hora exata UTC e filtros aplicados.
                </p>
              </div>

              <div style={{ padding: 'var(--space-2-5) var(--space-3)', background: 'var(--color-bg-primary)', border: 'var(--space-px) solid var(--color-border)', borderRadius: 'var(--radius-xl)', fontSize: 'var(--text-xs)' }}>
                <span style={{ fontFamily: 'monospace', fontWeight: 700, color: 'var(--color-accent)' }}>plano_pre_registro.json</span>
                <p style={{ color: 'var(--color-text-secondary)', margin: 'var(--space-0-5) 0 0 0' }}>
                  Indicadores pré-registrados a priori e histórico de emendas do protocolo D11.
                </p>
              </div>

              <div style={{ padding: 'var(--space-2-5) var(--space-3)', background: 'var(--color-bg-primary)', border: 'var(--space-px) solid var(--color-border)', borderRadius: 'var(--radius-xl)', fontSize: 'var(--text-xs)' }}>
                <span style={{ fontFamily: 'monospace', fontWeight: 700, color: 'var(--color-accent)' }}>relatorio_conformidade_biblio.md</span>
                <p style={{ color: 'var(--color-text-secondary)', margin: 'var(--space-0-5) 0 0 0' }}>
                  Relatório dos 20 itens normativos BIBLIO formatado em Markdown e JSON.
                </p>
              </div>

              <div style={{ padding: 'var(--space-2-5) var(--space-3)', background: 'var(--color-bg-primary)', border: 'var(--space-px) solid var(--color-border)', borderRadius: 'var(--radius-xl)', fontSize: 'var(--text-xs)' }}>
                <span style={{ fontFamily: 'monospace', fontWeight: 700, color: 'var(--color-accent)' }}>indicadores/indicadores_resumo.json</span>
                <p style={{ color: 'var(--color-text-secondary)', margin: 'var(--space-0-5) 0 0 0' }}>
                  Tabelas numéricas consolidadas de Nível 0 e 1 (Bradford, Lotka, CAGR, Subramanyam).
                </p>
              </div>

              <div style={{ padding: 'var(--space-2-5) var(--space-3)', background: 'var(--color-bg-primary)', border: 'var(--space-px) solid var(--color-border)', borderRadius: 'var(--radius-xl)', fontSize: 'var(--text-xs)' }}>
                <span style={{ fontFamily: 'monospace', fontWeight: 700, color: 'var(--color-accent)' }}>grafos/*.graphml</span>
                <p style={{ color: 'var(--color-text-secondary)', margin: 'var(--space-0-5) 0 0 0' }}>
                  Redes estruturais com pesos de força de associação e coordenadas FR pré-calculadas.
                </p>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}
