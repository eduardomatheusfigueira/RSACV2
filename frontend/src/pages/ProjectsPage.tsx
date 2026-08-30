/**
 * Revsist — Projects Page
 * Listagem, criação e seleção de projetos de revisão sistemática.
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Plus,
  FolderOpen,
  Calendar,
  CheckCircle2,
  Trash2,
  BookOpen,
  Search,
  Sparkles,
  ArrowRight,
  Filter,
  Users,
  Key,
  Shield,
} from 'lucide-react'
import { api } from '@/api/client'
import { useSettingsStore } from '@/stores/useSettingsStore'
import { useRibbonStore } from '@/stores/useRibbonStore'
import { PROTOCOL_CATALOG, PROTOCOL_OPTIONS } from '@/data/protocolCatalog'
import { AIAssistButton } from '@/components/common/AIAssistButton'
import {
  PageHeader,
  Button,
  Card,
  EmptyState,
  LoadingState,
  toast,
  Dialog,
  DialogContent,
  DialogTitlebar,
  DialogBody,
} from '@/components/ui'
import type { Project, Methodology, CollaborationMode } from '@/types/api'
import './ProjectsPage.css'

export function ProjectsPage(): JSX.Element {
  const navigate = useNavigate()
  const { activeProject, setActiveProject } = useSettingsStore()
  const registerRibbonActions = useRibbonStore((s) => s.registerActions)
  const unregisterRibbonActions = useRibbonStore((s) => s.unregisterActions)
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isJoinModalOpen, setIsJoinModalOpen] = useState(false)
  const [joinCode, setJoinCode] = useState('')
  const [joining, setJoining] = useState(false)
  const [searchFilter, setSearchFilter] = useState('')
  const [roleFilter, setRoleFilter] = useState<'all' | 'mine' | 'team'>('all')

  // Form State
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [methodology, setMethodology] = useState<Methodology>('PRISMA-ScR')
  const [collaborationMode, setCollaborationMode] = useState<CollaborationMode>('individual')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    registerRibbonActions({
      createProject: () => setIsModalOpen(true),
    })
    return () => {
      unregisterRibbonActions(['createProject'])
    }
  }, [registerRibbonActions, unregisterRibbonActions])

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    try {
      setLoading(true)
      const data = await api.listProjects()
      setProjects(data.items)
    } catch (err) {
      console.error('Erro ao listar projetos:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return

    try {
      setSubmitting(true)
      const newProj = await api.createProject({
        title: title.trim(),
        description: description.trim(),
        methodology,
        collaboration_mode: collaborationMode,
        reviewers_per_paper: collaborationMode === 'cega_por_pares' ? 2 : 1,
        conflict_resolution: 'coordenador',
      })
      setProjects([newProj, ...projects])
      setActiveProject(newProj)
      setIsModalOpen(false)
      setTitle('')
      setDescription('')
      setCollaborationMode('individual')
      navigate(`/projects/${newProj.id}/protocol`)
    } catch (err) {
      console.error('Erro ao criar projeto:', err)
    } finally {
      setSubmitting(false)
    }
  }

  const handleJoinProject = async (e: React.FormEvent) => {
    e.preventDefault()
    const code = joinCode.trim().toUpperCase()
    if (!code) return

    try {
      setJoining(true)
      const res = await api.acceptTeamInvitation(code)
      toast.success('Ingresso na Equipe', {
        description: res.message || 'Convite aceito com sucesso!',
      })
      setIsJoinModalOpen(false)
      setJoinCode('')
      await loadProjects()
      if (res.project_id) {
        navigate(`/projects/${res.project_id}/protocol`)
      }
    } catch (err: any) {
      toast.error('Erro ao aceitar convite', {
        description: err?.detail || err?.message || 'Código de convite inválido ou expirado.',
      })
    } finally {
      setJoining(false)
    }
  }

  const handleDeleteProject = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!window.confirm('Tem certeza que deseja excluir este projeto? Todos os dados vinculados (protocolo, artigos e triagens) serão permanentemente apagados.')) {
      return
    }
    try {
      await api.deleteProject(id)
      setProjects((prev) => prev.filter((p) => p.id !== id))
      if (activeProject?.id === id) {
        setActiveProject(null)
      }
    } catch (err: any) {
      console.error('Erro ao excluir projeto:', err)
      toast.error('Não foi possível excluir o projeto', {
        description: err.message || 'Falha na comunicação com o servidor.',
      })
    }
  }

  const handleSelectProject = (project: Project) => {
    setActiveProject(project)
    navigate(`/projects/${project.id}/protocol`)
  }

  const filteredProjects = projects.filter((p) => {
    const matchesSearch =
      p.title.toLowerCase().includes(searchFilter.toLowerCase()) ||
      p.description.toLowerCase().includes(searchFilter.toLowerCase()) ||
      p.methodology.toLowerCase().includes(searchFilter.toLowerCase())
    if (!matchesSearch) return false

    if (roleFilter === 'mine') {
      return !p.my_role || p.my_role === 'coordenador'
    }
    if (roleFilter === 'team') {
      return p.my_role === 'revisor' || p.my_role === 'observador' || (p.member_count && p.member_count > 1)
    }
    return true
  })

  return (
    <div className="projects-page animate-fade-in">
      <PageHeader
        title="Projetos de Revisão Sistemática"
        subtitle="Crie, selecione e gerencie seus protocolos e revisões com rigor metodológico"
        primaryAction={
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <Button
              variant="secondary"
              size="md"
              onClick={() => setIsJoinModalOpen(true)}
              leftIcon={<Key size={14} />}
            >
              Entrar com Convite
            </Button>
            <Button
              variant="primary"
              size="md"
              onClick={() => setIsModalOpen(true)}
              leftIcon={<Plus size={14} />}
            >
              Novo Projeto
            </Button>
          </div>
        }
      />

      {/* Filter Bar */}
      <div className="projects-filter-bar">
        <div className="search-input-wrapper">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Filtrar por título, metodologia ou descrição..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
          />
        </div>

        <div className="role-filter-tabs">
          <button
            type="button"
            className={`filter-tab-btn ${roleFilter === 'all' ? 'active' : ''}`}
            onClick={() => setRoleFilter('all')}
          >
            Todos ({projects.length})
          </button>
          <button
            type="button"
            className={`filter-tab-btn ${roleFilter === 'mine' ? 'active' : ''}`}
            onClick={() => setRoleFilter('mine')}
          >
            Minhas Coordenações
          </button>
          <button
            type="button"
            className={`filter-tab-btn ${roleFilter === 'team' ? 'active' : ''}`}
            onClick={() => setRoleFilter('team')}
          >
            <Users size={12} /> Revisões em Equipe
          </button>
        </div>
      </div>

      {/* Grid of Projects */}
      {loading ? (
        <LoadingState label="Carregando projetos…" />
      ) : filteredProjects.length === 0 ? (
        searchFilter.trim() || roleFilter !== 'all' ? (
          <EmptyState
            icon={<Search size={32} strokeWidth={1.25} aria-hidden="true" />}
            title="Nenhum projeto corresponde ao filtro"
            description={<>Nenhum projeto encontrado para o filtro selecionado.</>}
            action={
              <Button
                variant="secondary"
                size="md"
                onClick={() => {
                  setSearchFilter('')
                  setRoleFilter('all')
                }}
              >
                Limpar filtros
              </Button>
            }
          />
        ) : (
          <EmptyState
            icon={<FolderOpen size={32} strokeWidth={1.25} aria-hidden="true" />}
            title="Nenhum projeto ainda"
            description="Um projeto reúne protocolo, acervo e decisões de triagem sob a mesma metodologia. Comece pelo primeiro ou entre na equipe de um colega com convite."
            action={
              <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
                <Button variant="secondary" size="md" onClick={() => setIsJoinModalOpen(true)} leftIcon={<Key size={14} />}>
                  Entrar com Convite
                </Button>
                <Button variant="primary" size="md" onClick={() => setIsModalOpen(true)} leftIcon={<Plus size={14} />}>
                  Criar Novo Projeto
                </Button>
              </div>
            }
          />
        )
      ) : (
        <div className="projects-grid">
          {filteredProjects.map((project) => {
            const isActive = activeProject?.id === project.id
            const role = project.my_role || 'coordenador'
            const memberCount = project.member_count || 1

            return (
              <Card
                key={project.id}
                className={`project-card-full ${isActive ? 'active-card' : ''}`}
                relief="plano"
                accented={isActive}
              >
                <div className="card-header">
                  <div className="card-meta">
                    <span className="badge-methodology">{project.methodology}</span>
                    <span className={`badge-role role-${role}`}>
                      <Shield size={10} /> {role}
                    </span>
                    <span className={`badge-collab-mode mode-${project.collaboration_mode || 'individual'}`}>
                      {project.collaboration_mode === 'cega_por_pares'
                        ? 'Cega por Pares (2)'
                        : project.collaboration_mode === 'colaborativa'
                        ? 'Colaborativa'
                        : 'Individual'}
                    </span>
                    {isActive && (
                      <span className="badge-active">
                        <CheckCircle2 size={12} /> Ativo
                      </span>
                    )}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    <button
                      type="button"
                      className="badge-team-btn"
                      title="Gerenciar Equipe e Convites"
                      onClick={(e) => {
                        e.stopPropagation()
                        setActiveProject(project)
                        navigate(`/projects/${project.id}/team`)
                      }}
                    >
                      <Users size={12} />
                      <span>{memberCount > 1 ? `${memberCount} membros` : 'Equipe'}</span>
                    </button>

                    {role === 'coordenador' && (
                      <button
                        type="button"
                        className="btn-icon danger"
                        title="Excluir Projeto"
                        aria-label={`Excluir projeto: ${project.title}`}
                        onClick={(e) => handleDeleteProject(project.id, e)}
                      >
                        <Trash2 size={16} aria-hidden="true" />
                      </button>
                    )}
                  </div>
                </div>

                <h3 className="card-title">
                  <button
                    type="button"
                    className="card-title-action"
                    onClick={() => handleSelectProject(project)}
                  >
                    {project.title}
                  </button>
                </h3>
                <p className="card-desc">
                  {project.description || 'Sem descrição cadastrada.'}
                </p>

                <div className="card-footer">
                  <span className="card-date">
                    <Calendar size={13} />
                    {new Date(project.created_at).toLocaleDateString('pt-BR')}
                  </span>
                  <span className="card-action">
                    Acessar Etapas <ArrowRight size={14} />
                  </span>
                </div>
              </Card>
            )
          })}
        </div>
      )}

      {/* Criação de projeto — janela clássica sobre o Dialog do Radix, que
          prende o foco, fecha no Escape e devolve o foco ao botão de origem. */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent variant="window" size="md" aria-describedby={undefined}>
          <DialogTitlebar>Novo Projeto de Revisão</DialogTitlebar>
          <DialogBody>
              <div className="modal-intro">
                <p>Defina o título, a diretriz metodológica e a justificativa inicial da sua pesquisa secundária.</p>
              </div>

              <form onSubmit={handleCreateProject} className="modal-form">
                <div className="form-group">
                  <div className="form-label-row">
                    <label htmlFor="new-proj-title">Título do Projeto *</label>
                    <AIAssistButton
                      fieldId="new_proj_title"
                      fieldLabel="Título da Revisão"
                      currentValue={title}
                      fieldGuidelines={`Formule um título acadêmico preciso para uma revisão em ${methodology}, delimitando População/Atores, Conceito Central e Contexto Territorial em Ciências Sociais Aplicadas / Desenvolvimento Regional.`}
                      methodology={methodology}
                      projectContext={{
                        project_description: description,
                      }}
                      compact
                      onApply={(t) => setTitle(t)}
                    />
                  </div>
                  <input
                    id="new-proj-title"
                    type="text"
                    required
                    placeholder="Ex: Arranjos Produtivos Locais e Governança Territorial no Desenvolvimento Regional: Uma Revisão de Escopo..."
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    disabled={submitting}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="new-proj-methodology">Diretriz / Protocolo Metodológico</label>
                  <select
                    id="new-proj-methodology"
                    value={methodology}
                    onChange={(e) => setMethodology(e.target.value as Methodology)}
                    disabled={submitting}
                  >
                    {PROTOCOL_OPTIONS.map((m) => {
                      const proto = PROTOCOL_CATALOG[m]
                      return (
                        <option key={m} value={m}>
                          {proto?.name || m}
                        </option>
                      )
                    })}
                  </select>

                  {/* Protocol Info Preview Card */}
                  {PROTOCOL_CATALOG[methodology] && (
                    <div className="protocol-preview-box">
                      <div className="protocol-preview-header">
                        <span className="protocol-preview-badge">
                          {PROTOCOL_CATALOG[methodology].badge}
                        </span>
                        <span className="protocol-preview-framework">
                          Framework: <strong>{PROTOCOL_CATALOG[methodology].defaultFramework}</strong>
                        </span>
                      </div>
                      <p className="protocol-preview-desc">
                        {PROTOCOL_CATALOG[methodology].description}
                      </p>
                      <div className="protocol-preview-focus">
                        <strong>Foco:</strong> {PROTOCOL_CATALOG[methodology].domainFocus}
                      </div>
                    </div>
                  )}
                </div>

                <div className="form-group">
                  <label htmlFor="new-proj-collab-mode">Modalidade de Colaboração (Doc 43)</label>
                  <select
                    id="new-proj-collab-mode"
                    value={collaborationMode}
                    onChange={(e) => setCollaborationMode(e.target.value as CollaborationMode)}
                    disabled={submitting}
                  >
                    <option value="individual">Individual (Pesquisador Único)</option>
                    <option value="colaborativa">Equipe Colaborativa (Acervo e Protocolo Compartilhados)</option>
                    <option value="cega_por_pares">Revisão Cega por Pares (2 Revisores Independentes)</option>
                  </select>
                  <div className="collab-preview-desc">
                    {collaborationMode === 'cega_por_pares' && (
                      <p>
                        <strong>Duplo-Cego:</strong> Cada estudo recebe 2 pareceres independentes. Divergências são enviadas para resolução pela coordenação.
                      </p>
                    )}
                    {collaborationMode === 'colaborativa' && (
                      <p>
                        <strong>Colaborativo:</strong> Todos os membros podem coeditar protocolo e acervo. 1 parecer define a decisão do estudo.
                      </p>
                    )}
                    {collaborationMode === 'individual' && (
                      <p>
                        <strong>Individual:</strong> Protocolo e decisões centralizadas no autor do projeto.
                      </p>
                    )}
                  </div>
                </div>

                <div className="form-group">
                  <div className="form-label-row">
                    <label htmlFor="new-proj-desc">Descrição / Justificativa</label>
                    <AIAssistButton
                      fieldId="new_proj_desc"
                      fieldLabel="Descrição e Justificativa do Projeto"
                      currentValue={description}
                      fieldGuidelines="Apresente a justificativa socioeconômica, lacunas teóricas e relevância para o desenvolvimento regional da revisão proposta."
                      projectTitle={title}
                      methodology={methodology}
                      projectContext={{
                        project_title: title,
                      }}
                      compact
                      onApply={(d) => setDescription(d)}
                    />
                  </div>
                  <textarea
                    id="new-proj-desc"
                    rows={4}
                    placeholder="Descreva o escopo geral, objetivos e contexto da revisão..."
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    disabled={submitting}
                  />
                </div>

                <div className="modal-actions">
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setIsModalOpen(false)}
                    disabled={submitting}
                  >
                    Cancelar
                  </button>
                  <button type="submit" className="btn-primary" disabled={submitting}>
                    {submitting ? 'Criando...' : 'Criar e Configurar Protocolo'}
                  </button>
                </div>
              </form>
          </DialogBody>
        </DialogContent>
      </Dialog>

      {/* Modal: Entrar com Código de Convite RSAC-EQ */}
      <Dialog open={isJoinModalOpen} onOpenChange={setIsJoinModalOpen}>
        <DialogContent variant="window" size="sm" aria-describedby={undefined}>
          <DialogTitlebar>Ingressar em Revisão por Convite</DialogTitlebar>
          <DialogBody>
            <div className="modal-intro">
              <p>
                Insira o código <code>RSAC-EQ-...</code> fornecido pelo coordenador da pesquisa para ter acesso imediato ao protocolo e estudos.
              </p>
            </div>

            <form onSubmit={handleJoinProject} className="modal-form">
              <div className="form-group">
                <label htmlFor="join-invite-code">Código do Convite *</label>
                <input
                  id="join-invite-code"
                  type="text"
                  required
                  placeholder="Ex: RSAC-EQ-XXXX-YYYY"
                  value={joinCode}
                  onChange={(e) => setJoinCode(e.target.value)}
                  disabled={joining}
                  style={{ textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}
                />
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setIsJoinModalOpen(false)}
                  disabled={joining}
                >
                  Cancelar
                </button>
                <button type="submit" className="btn-primary" disabled={joining}>
                  {joining ? 'Validando...' : 'Ingressar na Revisão'}
                </button>
              </div>
            </form>
          </DialogBody>
        </DialogContent>
      </Dialog>
    </div>
  )
}
