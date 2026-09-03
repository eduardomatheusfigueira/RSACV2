/**
 * Revsist — Visualizador de Grafos e Redes Estruturais em HTML5 Canvas (60fps)
 *
 * Características (doc 48 §8.4, §12, doc 49 Fase 6):
 * - Canvas 2D interativo com Pan & Zoom fluído e seleção de nós por clique
 * - Layout Fruchterman-Reingold calculado no servidor com semente determinística
 * - Comunidades Louvain coloridas por cluster
 * - Visualização alternativa em Tabela Acessível completa
 * - Exportação para PNG em alta resolução e GraphML
 */

import React, { useEffect, useRef, useState } from 'react'
import {
  Download,
  Layers,
  RotateCcw,
  Share2,
  Table,
  ZoomIn,
  ZoomOut,
} from 'lucide-react'
import { Button } from '@/components/ui'
import type { GrafoInfo, NoGrafo } from '@/types/api'
import './VisualizadorGrafoCanvas.css'

interface VisualizadorGrafoCanvasProps {
  grafo: GrafoInfo
  onExportGraphML?: () => void
}

export const VisualizadorGrafoCanvas: React.FC<VisualizadorGrafoCanvasProps> = ({
  grafo,
  onExportGraphML,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const [noSelecionado, setNoSelecionado] = useState<NoGrafo | null>(null)
  const [abaAtiva, setAbaAtiva] = useState<'grafo' | 'tabela'>('grafo')
  const [filtroTabela, setFiltroTabela] = useState('')
  const [zoom, setZoom] = useState(1.0)
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })

  // Ajustar tamanho do Canvas ao contêiner
  useEffect(() => {
    const updateSize = () => {
      const container = containerRef.current
      const canvas = canvasRef.current
      if (container && canvas) {
        const rect = container.getBoundingClientRect()
        canvas.width = rect.width || 800
        canvas.height = 520
      }
    }
    updateSize()
    window.addEventListener('resize', updateSize)
    return () => window.removeEventListener('resize', updateSize)
  }, [abaAtiva])

  // Renderização em Canvas com escala e centralização
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || abaAtiva !== 'grafo') return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const width = canvas.width
    const height = canvas.height
    ctx.clearRect(0, 0, width, height)

    ctx.save()
    // Centralizar no canvas com offset e zoom
    ctx.translate(width / 2 + offset.x, height / 2 + offset.y)
    ctx.scale(zoom, zoom)

    const scaleFactor = Math.min(width, height) * 0.38

    // 1. Desenhar arestas
    const nodeMap = new Map<string, NoGrafo>()
    grafo.nodes.forEach((n) => nodeMap.set(n.id, n))

    grafo.edges.forEach((edge) => {
      const u = nodeMap.get(edge.source)
      const v = nodeMap.get(edge.target)
      if (!u || !v) return

      const ux = u.x * scaleFactor
      const uy = u.y * scaleFactor
      const vx = v.x * scaleFactor
      const vy = v.y * scaleFactor

      ctx.beginPath()
      ctx.moveTo(ux, uy)
      ctx.lineTo(vx, vy)
      ctx.strokeStyle = '#94a3b8'
      ctx.globalAlpha = Math.min(0.65, Math.max(0.15, edge.weight * 0.35))
      ctx.lineWidth = Math.max(1, Math.min(4, edge.weight * 0.8))
      ctx.stroke()
    })

    ctx.globalAlpha = 1.0

    // Detectar modo escuro para cor dos rótulos
    const isDark = document.documentElement.classList.contains('dark')
    const textColor = isDark ? '#e2e8f0' : '#1e293b'
    const borderDefault = isDark ? '#334155' : '#ffffff'

    // 2. Desenhar nós
    grafo.nodes.forEach((node) => {
      const nx = node.x * scaleFactor
      const ny = node.y * scaleFactor
      const isSelected = noSelecionado?.id === node.id

      const r = Math.max(6, Math.min(24, 6 + Math.sqrt(node.size) * 3.5))

      ctx.beginPath()
      ctx.arc(nx, ny, isSelected ? r + 3 : r, 0, 2 * Math.PI)
      ctx.fillStyle = node.color || '#3b82f6'
      ctx.fill()
      ctx.lineWidth = isSelected ? 3 : 1.5
      ctx.strokeStyle = isSelected ? '#3b82f6' : borderDefault
      ctx.stroke()

      // Rótulo de texto
      ctx.font = isSelected ? 'bold 12px Inter, sans-serif' : '10px Inter, sans-serif'
      ctx.fillStyle = textColor
      ctx.textAlign = 'center'
      ctx.fillText(node.label, nx, ny + r + 12)
    })

    ctx.restore()
  }, [grafo, zoom, offset, noSelecionado, abaAtiva])

  // Tratar cliques para seleção de nós
  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const clickX = e.clientX - rect.left
    const clickY = e.clientY - rect.top

    const width = canvas.width
    const height = canvas.height
    const scaleFactor = Math.min(width, height) * 0.38

    // Converter coordenada do canvas para espaço do grafo
    const gx = (clickX - width / 2 - offset.x) / (zoom * scaleFactor)
    const gy = (clickY - height / 2 - offset.y) / (zoom * scaleFactor)

    // Encontrar nó mais próximo
    let menorDist = Infinity
    let noClicado: NoGrafo | null = null

    for (const node of grafo.nodes) {
      const dist = Math.hypot(node.x - gx, node.y - gy)
      const rRelativo = (6 + Math.sqrt(node.size) * 3.5) / scaleFactor
      if (dist <= rRelativo * 2.0 && dist < menorDist) {
        menorDist = dist
        noClicado = node
      }
    }

    setNoSelecionado(noClicado)
  }

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(true)
    setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y })
  }

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDragging) return
    setOffset({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y })
  }

  const handleMouseUp = () => {
    setIsDragging(false)
  }

  const downloadCanvasPNG = () => {
    const canvas = canvasRef.current
    if (!canvas) return
    const link = document.createElement('a')
    link.download = `rede_${grafo.network_type}_${grafo.id.slice(0, 8)}.png`
    link.href = canvas.toDataURL('image/png')
    link.click()
  }

  const nosFiltrados = grafo.nodes.filter(
    (n) =>
      n.label.toLowerCase().includes(filtroTabela.toLowerCase()) ||
      String(n.cluster).includes(filtroTabela)
  )

  const nClusters = Object.keys(grafo.clusters || {}).length

  return (
    <div className="grafo-container">
      {/* Cabeçalho com controles e abas */}
      <div className="grafo-header">
        <div className="grafo-titulo">
          <h3>Rede de {grafo.network_type.replace('_', ' ')}</h3>
          <p>
            {grafo.nodes.length} nós • {grafo.edges.length} arestas • {nClusters} clusters Louvain
          </p>
        </div>

        <div className="grafo-acoes">
          <div className="grafo-toggle-group">
            <button
              type="button"
              onClick={() => setAbaAtiva('grafo')}
              className={`grafo-toggle-btn ${abaAtiva === 'grafo' ? 'grafo-toggle-btn--active' : ''}`}
            >
              <Layers size={14} />
              <span>Grafo (Canvas)</span>
            </button>
            <button
              type="button"
              onClick={() => setAbaAtiva('tabela')}
              className={`grafo-toggle-btn ${abaAtiva === 'tabela' ? 'grafo-toggle-btn--active' : ''}`}
            >
              <Table size={14} />
              <span>Tabela de Nós</span>
            </button>
          </div>

          {onExportGraphML && (
            <Button
              variant="outline"
              size="sm"
              onClick={onExportGraphML}
              leftIcon={<Share2 size={13} />}
              title="Exportar em formato GraphML com coordenadas embutidas (Gephi / VOSviewer)"
            >
              GraphML
            </Button>
          )}

          {abaAtiva === 'grafo' && (
            <Button
              variant="primary"
              size="sm"
              onClick={downloadCanvasPNG}
              leftIcon={<Download size={13} />}
              title="Baixar imagem em PNG de alta resolução"
            >
              PNG
            </Button>
          )}
        </div>
      </div>

      {/* Conteúdo: Canvas ou Tabela */}
      {abaAtiva === 'grafo' ? (
        <div ref={containerRef} className="grafo-canvas-wrapper">
          <canvas
            ref={canvasRef}
            onClick={handleCanvasClick}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            className="grafo-canvas"
          />

          {/* Controles de Zoom sobre o Canvas */}
          <div className="grafo-zoom-controls">
            <button
              type="button"
              onClick={() => setZoom((z) => Math.min(3.0, z + 0.2))}
              className="grafo-zoom-btn"
              title="Aumentar zoom"
            >
              <ZoomIn size={14} />
            </button>
            <button
              type="button"
              onClick={() => setZoom((z) => Math.max(0.3, z - 0.2))}
              className="grafo-zoom-btn"
              title="Diminuir zoom"
            >
              <ZoomOut size={14} />
            </button>
            <button
              type="button"
              onClick={() => {
                setZoom(1.0)
                setOffset({ x: 0, y: 0 })
              }}
              className="grafo-zoom-btn"
              title="Redefinir visualização"
            >
              <RotateCcw size={14} />
            </button>
          </div>

          {/* Painel do Nó Selecionado */}
          {noSelecionado && (
            <div className="grafo-no-card">
              <div className="grafo-no-card__head">
                <span className="grafo-no-card__label" title={noSelecionado.label}>
                  {noSelecionado.label}
                </span>
                <span
                  className="grafo-no-card__bullet"
                  style={{ backgroundColor: noSelecionado.color }}
                />
              </div>
              <div className="grafo-no-card__grid">
                <span>Tamanho/Ocorrências:</span>
                <span className="grafo-no-card__val">{noSelecionado.size}</span>
                <span>Grau (Conexões):</span>
                <span className="grafo-no-card__val">{noSelecionado.degree}</span>
                <span>Cluster Louvain:</span>
                <span className="grafo-no-card__val">#{noSelecionado.cluster}</span>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Tabela Acessível e Equivalente (Doc 48 §8.4, §12) */
        <div className="grafo-tabela-view">
          <input
            type="text"
            placeholder="Filtrar nós por termo ou número de cluster..."
            value={filtroTabela}
            onChange={(e) => setFiltroTabela(e.target.value)}
            className="grafo-tabela-filtro"
          />

          <div className="grafo-tabela-wrapper">
            <table className="grafo-tabela">
              <thead>
                <tr>
                  <th>Rótulo / Elemento</th>
                  <th style={{ textAlign: 'right' }}>Ocorrências</th>
                  <th style={{ textAlign: 'right' }}>Grau</th>
                  <th style={{ textAlign: 'center' }}>Cluster</th>
                  <th style={{ textAlign: 'right' }}>Coord. X</th>
                  <th style={{ textAlign: 'right' }}>Coord. Y</th>
                </tr>
              </thead>
              <tbody>
                {nosFiltrados.map((no) => (
                  <tr
                    key={no.id}
                    onClick={() => setNoSelecionado(no)}
                    className={noSelecionado?.id === no.id ? 'is-selected' : ''}
                  >
                    <td style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                      <span
                        style={{
                          width: 'var(--space-2)',
                          height: 'var(--space-2)',
                          borderRadius: '50%',
                          backgroundColor: no.color,
                          flexShrink: 0,
                        }}
                      />
                      <span>{no.label}</span>
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace', fontWeight: 600 }}>
                      {no.size}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace', fontWeight: 600 }}>
                      {no.degree}
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <span
                        className="grafo-badge-cluster"
                        style={{ backgroundColor: no.color }}
                      >
                        #{no.cluster}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-text-secondary)' }}>
                      {no.x.toFixed(3)}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-text-secondary)' }}>
                      {no.y.toFixed(3)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Legenda Metodológica e Carimbo de Proveniência (Doc 48 §8.4) */}
      <div className="grafo-nota-proveniencia">
        <div style={{ fontWeight: 700, marginBottom: 'var(--space-0-5)', color: 'var(--color-text-primary)' }}>
          Nota Metodológica de Proveniência Estrutural
        </div>
        <p style={{ margin: 0 }}>
          Layout Fruchterman–Reingold com semente determinística (seed={grafo.seed}),{' '}
          {grafo.parameters.iteracoes_fr || 200} iterações; normalização de força:{' '}
          <strong>
            {grafo.parameters.normalizacao === 'association_strength'
              ? 'Força de Associação (VOSviewer / Van Eck & Waltman 2009)'
              : grafo.parameters.normalizacao}
          </strong>
          ; detecção de comunidades por Louvain (resolução {grafo.parameters.resolucao_louvain || 1.0}
          ); corte mínimo de coocorrência: {grafo.parameters.corte_minimo || 1}.
        </p>
      </div>
    </div>
  )
}
