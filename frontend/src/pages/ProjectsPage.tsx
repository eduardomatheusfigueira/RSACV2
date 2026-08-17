/**
 * RSAC V2 — Projects Page
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
} from 'lucide-react'
import { api } from '@/api/client'
import { useSettingsStore } from '@/stores/useSettingsStore'
import { useRibbonStore } from '@/stores/useRibbonStore'
import { PROTOCOL_CATALOG, PROTOCOL_OPTIONS } from '@/data/protocolCatalog'
import { AIAssistButton } from '@/components/common/AIAssistButton'
import { PageHeader, Button, EmptyState, LoadingState } from '@/components/ui'
import type { Project, Methodology } from '@/types/api'
import './ProjectsPage.css'

export function ProjectsPage(): JSX.Element {
  const navigate = useNavigate()
  const { activeProject, setActiveProject } = useSettingsStore()
  const registerRibbonActions = useRibbonStore((s) => s.registerActions)
  const unregisterRibbonActions = useRibbonStore((s) => s.unregisterActions)
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [searchFilter, setSearchFilter] = useState('')

  // Form State
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [methodology, setMethodology] = useState<Methodology>('PRISMA-ScR')
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
      })
      setProjects([newProj, ...projects])
      setActiveProject(newProj)
      setIsModalOpen(false)
      setTitle('')
      setDescription('')
      navigate(`/projects/${newProj.id}/protocol`)
    } catch (err) {
      console.error('Erro ao criar projeto:', err)
    } finally {
      setSubmitting(false)
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
      alert(`Erro ao excluir projeto: ${err.message || 'Falha na comunicação com o servidor'}`)
    }
  }

  const handleSelectProject = (project: Project) => {
    setActiveProject(project)
    navigate(`/projects/${project.id}/protocol`)
  }

  const filteredProjects = projects.filter(
    (p) =>
      p.title.toLowerCase().includes(searchFilter.toLowerCase()) ||
      p.description.toLowerCase().includes(searchFilter.toLowerCase()) ||
      p.methodology.toLowerCase().includes(searchFilter.toLowerCase())
  )

  return (
    <div className="projects-page animate-fade-in">
      <PageHeader
        title="Projetos de Revisão Sistemática"
        subtitle="Crie, selecione e gerencie seus protocolos e revisões com rigor metodológico"
        primaryAction={
          <Button variant="primary" size="md" onClick={() => setIsModalOpen(true)} leftIcon={<Plus size={14} />}>
            Novo Projeto
          </Button>
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
      </div>

      {/* Grid of Projects */}
      {loading ? (
        <LoadingState label="Carregando projetos…" />
      ) : filteredProjects.length === 0 ? (
        /* O vazio por filtro e o vazio por acervo têm causas diferentes e
           saídas diferentes — dizer "crie um projeto" a quem só digitou mal
           no filtro é mandar a pessoa pelo caminho errado. */
        searchFilter.trim() ? (
          <EmptyState
            icon={<Search size={32} strokeWidth={1.25} aria-hidden="true" />}
            title="Nenhum projeto corresponde ao filtro"
            description={<>Nenhum título, metodologia ou descrição contém <strong>{searchFilter}</strong>.</>}
            action={
              <Button variant="secondary" size="md" onClick={() => setSearchFilter('')}>
                Limpar filtro
              </Button>
            }
          />
        ) : (
          <EmptyState
            icon={<FolderOpen size={32} strokeWidth={1.25} aria-hidden="true" />}
            title="Nenhum projeto ainda"
            description="Um projeto reúne protocolo, acervo e decisões de triagem sob a mesma metodologia. Comece pelo primeiro."
            action={
              <Button variant="primary" size="md" onClick={() => setIsModalOpen(true)} leftIcon={<Plus size={14} />}>
                Criar Novo Projeto
              </Button>
            }
          />
        )
      ) : (
        <div className="projects-grid">
          {filteredProjects.map((project) => {
            const isActive = activeProject?.id === project.id
            return (
              <div
                key={project.id}
                className={`project-card-full ${isActive ? 'active-card' : ''}`}
                onClick={() => handleSelectProject(project)}
              >
                <div className="card-header">
                  <div className="card-meta">
                    <span className="badge-methodology">{project.methodology}</span>
                    {isActive && (
                      <span className="badge-active">
                        <CheckCircle2 size={12} /> Ativo
                      </span>
                    )}
                  </div>
                  <button
                    className="btn-icon danger"
                    title="Excluir Projeto"
                    onClick={(e) => handleDeleteProject(project.id, e)}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>

                <h3 className="card-title">{project.title}</h3>
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
              </div>
            )
          })}
        </div>
      )}

      {/* Create Modal */}
      {isModalOpen && (
        <div
          className="modal-overlay animate-fade-in"
          onClick={(e) => {
            if (e.target === e.currentTarget) setIsModalOpen(false)
          }}
        >
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-titlebar">
              <span>Novo Projeto de Revisão</span>
              <button
                type="button"
                className="modal-titlebar-btn"
                onClick={() => setIsModalOpen(false)}
                title="Fechar"
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
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
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
