/**
 * Revsist — Dashboard Page
 * Tela inicial com métricas, boas-vindas e visão geral dos projetos.
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FolderOpen,
  FileText,
  CheckCircle2,
  Clock,
  Plus,
  ArrowRight,
  Sparkles,
} from 'lucide-react'
import { api } from '@/api/client'
import { PageHeader, Button, Card, EmptyState, LoadingState } from '@/components/ui'
import { useSettingsStore } from '@/stores/useSettingsStore'
import type { Project, ProjectStats } from '@/types/api'
import './DashboardPage.css'

export function DashboardPage(): JSX.Element {
  const navigate = useNavigate()
  const { backendStatus, activeProject, setActiveProject } = useSettingsStore()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  /* Os três números do acervo mostravam "—" desde sempre, e o backend já os
     servia em `/projects/:id/stats`. Faltava ligar. O escopo é o projeto ativo:
     somar todos exigiria uma requisição por projeto, e a pergunta que o painel
     responde é "onde está a MINHA revisão", não "quantos artigos há no disco". */
  const [stats, setStats] = useState<ProjectStats | null>(null)

  useEffect(() => {
    if (backendStatus === 'online') {
      loadProjects()
    }
  }, [backendStatus])

  const loadProjects = async () => {
    try {
      const response = await api.listProjects(false)
      setProjects(response.items)
    } catch (error) {
      console.error('Erro ao carregar projetos:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (backendStatus !== 'online' || !activeProject) {
      setStats(null)
      return
    }
    let cancelado = false
    api
      .getProjectStats(activeProject.id)
      .then((s) => {
        if (!cancelado) setStats(s)
      })
      .catch((err) => console.error('Erro ao carregar métricas do projeto ativo:', err))
    return () => {
      cancelado = true
    }
  }, [backendStatus, activeProject?.id])

  /* Sem projeto ativo não há acervo a contar — "—" é a resposta honesta, e
     diferente de "0", que afirmaria um acervo vazio. */
  const numero = (v: number | undefined): string => (v === undefined ? '—' : String(v))

  const handleOpenProject = (project: Project) => {
    setActiveProject(project)
    navigate(`/projects/${project.id}/protocol`)
  }

  return (
    <div className="dashboard animate-slide-up">
      <PageHeader
        title="Revisão Sistemática Assistida por Computador"
        meta={<Sparkles size={16} className="icon-accent" aria-hidden="true" />}
        subtitle="Gerencie seus protocolos, coletas e revisões com rigor metodológico e assistência computacional"
        primaryAction={
          <Button variant="primary" size="md" onClick={() => navigate('/projects')} leftIcon={<Plus size={14} />}>
            Novo Projeto
          </Button>
        }
      />

      {/* Painel de números. Antes eram quatro blocos repetidos com o estilo
          embutido no JSX — inclusive o par cor/tinta, que o verificador não
          alcança dentro de `style={{}}`. Agora é uma lista de dados sobre
          <Card>, e a cor de cada tom sai dos tokens medidos. */}
      <p className="dashboard-stats-escopo">
        {activeProject ? (
          <>Acervo do projeto ativo: <strong>{activeProject.title}</strong></>
        ) : (
          'Selecione um projeto para ver o acervo. Os números abaixo dependem dele.'
        )}
      </p>

      <div className="dashboard-stats">
        {[
          { tom: 'acento', icone: <FolderOpen size={22} />, valor: String(projects.length), rotulo: 'Projetos Ativos' },
          { tom: 'info', icone: <FileText size={22} />, valor: numero(stats?.total_papers), rotulo: 'Artigos Coletados' },
          { tom: 'sucesso', icone: <CheckCircle2 size={22} />, valor: numero(stats?.included_papers), rotulo: 'Artigos Incluídos' },
          { tom: 'aviso', icone: <Clock size={22} />, valor: numero(stats?.pending_papers), rotulo: 'Pendentes de Triagem' },
        ].map((n) => (
          <Card key={n.rotulo} className="stat-card">
            <div className={`stat-icon stat-icon--${n.tom}`} aria-hidden="true">
              {n.icone}
            </div>
            <div className="stat-content">
              <span className="stat-value">{n.valor}</span>
              <span className="stat-label">{n.rotulo}</span>
            </div>
          </Card>
        ))}
      </div>

      {/* Projects List */}
      <div className="dashboard-section">
        <div className="section-header">
          <h2 className="section-title">Projetos Recentes</h2>
          <button className="section-link" onClick={() => navigate('/projects')}>
            Ver todos <ArrowRight size={14} />
          </button>
        </div>

        {loading ? (
          <LoadingState label="Carregando projetos…" />
        ) : projects.length === 0 ? (
          <EmptyState
            icon={<FolderOpen size={32} strokeWidth={1.25} aria-hidden="true" />}
            title="Nenhum projeto ainda"
            description="Um projeto guarda o protocolo, o acervo coletado e as decisões de triagem. Crie o primeiro para começar a revisão."
            action={
              <Button variant="primary" size="md" onClick={() => navigate('/projects')} leftIcon={<Plus size={14} />}>
                Criar Primeiro Projeto
              </Button>
            }
          />
        ) : (
          <div className="project-grid">
            {projects.map((project) => {
              const isActive = activeProject?.id === project.id
              return (
                <Card
                  key={project.id}
                  className={`project-card ${isActive ? 'active-card' : ''}`}
                  accented={isActive}
                  onClick={() => handleOpenProject(project)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      handleOpenProject(project)
                    }
                  }}
                  title={`Abrir projeto: ${project.title}`}
                >
                  <div className="project-card-header">
                    <h3 className="project-card-title">{project.title}</h3>
                    <div className="project-card-meta">
                      <span className="project-card-methodology">{project.methodology}</span>
                      {isActive && (
                        <span className="badge-active">
                          <CheckCircle2 size={11} /> Ativo
                        </span>
                      )}
                    </div>
                  </div>
                  {project.description && (
                    <p className="project-card-description">{project.description}</p>
                  )}
                  <div className="project-card-footer">
                    <span className="project-card-date">
                      {new Date(project.created_at).toLocaleDateString('pt-BR')}
                    </span>
                    <span className="project-card-action">
                      Abrir Projeto <ArrowRight size={14} className="project-card-arrow" />
                    </span>
                  </div>
                </Card>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
