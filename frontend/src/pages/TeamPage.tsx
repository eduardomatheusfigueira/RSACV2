/**
 * Revsist — Gestão de Equipe e Pesquisa Colaborativa (Doc 43 & Doc 44, Fase 1)
 *
 * A tela segue a mesma gramática das etapas de Protocolo, Coleta, Triagem e
 * Extração: `PageHeader` com uma única ação primária, `Card` para cada bloco,
 * `Badge` para os selos, `Dialog` na variante janela para os formulários e
 * `toast` para o retorno das operações. Antes esta página trazia paleta e
 * componentes próprios — ficava legível apenas no tema `platinum-dusk` e
 * destoava de todos os demais.
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Users,
  UserPlus,
  Shield,
  UserCheck,
  UserX,
  Copy,
  Check,
  Clock,
  Trash2,
  Key,
  LogOut,
  Mail,
  HelpCircle,
  Settings2,
  AlertTriangle,
  RotateCcw,
  Link2,
} from 'lucide-react'
import { api } from '@/api/client'
import { useProjectChannel } from '@/hooks/useProjectChannel'
import {
  PageHeader,
  Button,
  Badge,
  Card,
  CardHeader,
  CardTitle,
  EmptyState,
  LoadingState,
  toast,
  Dialog,
  DialogContent,
  DialogTitlebar,
  DialogBody,
} from '@/components/ui'
import type {
  TeamResponse,
  ProjectMember,
  ProjectRoleType,
  Project,
  CollaborationMode,
} from '@/types/api'
import './TeamPage.css'

/** Selo de papel: o mesmo vocabulário de variantes usado nos cartões de projeto. */
function SeloDePapel({ papel }: { papel: ProjectRoleType | 'inativo' }): JSX.Element {
  const variante =
    papel === 'coordenador' ? 'brand' : papel === 'revisor' ? 'info' : 'neutral'
  const rotulo =
    papel === 'coordenador'
      ? 'Coordenador'
      : papel === 'revisor'
      ? 'Revisor'
      : papel === 'observador'
      ? 'Observador'
      : 'Desligado'
  return (
    <Badge variant={papel === 'inativo' ? 'neutral' : variante} size="xs">
      {rotulo}
    </Badge>
  )
}

const ROTULO_MODALIDADE: Record<CollaborationMode, string> = {
  individual: 'Individual (Pesquisador Único)',
  colaborativa: 'Equipe Colaborativa',
  cega_por_pares: 'Revisão Cega por Pares',
}

export default function TeamPage(): JSX.Element {
  const { id: projectId } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [team, setTeam] = useState<TeamResponse | null>(null)
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Diálogo de novo convite
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState<ProjectRoleType>('revisor')
  const [inviteNote, setInviteNote] = useState('')
  const [creatingInvite, setCreatingInvite] = useState(false)

  // Diálogo de modalidade / reabertura de triagem
  const [showModeModal, setShowModeModal] = useState(false)
  const [selectedMode, setSelectedMode] = useState<CollaborationMode>('individual')
  const [reopenReason, setReopenReason] = useState('')
  const [needsReopen, setNeedsReopen] = useState(false)
  const [updatingMode, setUpdatingMode] = useState(false)

  // Ingresso por código
  const [enterCode, setEnterCode] = useState('')
  const [joining, setJoining] = useState(false)

  const [copiedCode, setCopiedCode] = useState<string | null>(null)

  const isCoordenador = team?.my_role === 'coordenador'

  const carregarEquipe = async () => {
    if (!projectId) return
    setLoading(true)
    setError(null)
    try {
      const [teamData, projectData] = await Promise.all([
        api.getTeam(projectId),
        api.getProject(projectId),
      ])
      setTeam(teamData)
      setProject(projectData)
      setSelectedMode(projectData.collaboration_mode || 'individual')
    } catch (err: any) {
      setError(err?.detail || err?.message || 'Falha ao carregar os dados da equipe.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    carregarEquipe()
  }, [projectId])

  /* Doc 43 §43.12.1: quando um colega aceita o convite ou é desligado, a
     composição muda para todo mundo — quem estiver com esta tela aberta
     precisa ver isso sem recarregar. */
  useProjectChannel({
    projectId,
    screen: 'equipe',
    onTeamChanged: () => {
      carregarEquipe()
    },
  })

  const handleCopiarCodigo = (code: string) => {
    navigator.clipboard.writeText(code)
    setCopiedCode(code)
    setTimeout(() => setCopiedCode(null), 3000)
  }

  const handleCopiarLink = (code: string) => {
    const url = `${window.location.origin}/app?invite_code=${code}`
    navigator.clipboard.writeText(url)
    setCopiedCode(`link-${code}`)
    setTimeout(() => setCopiedCode(null), 3000)
  }

  const handleCriarConvite = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!projectId) return
    setCreatingInvite(true)
    try {
      const convite = await api.createTeamInvitation(projectId, {
        email: inviteEmail.trim() || undefined,
        project_role: inviteRole,
        note: inviteNote.trim() || undefined,
      })
      setShowInviteModal(false)
      setInviteEmail('')
      setInviteNote('')
      setInviteRole('revisor')
      toast.success('Convite emitido', { description: `Código ${convite.code}` })
      await carregarEquipe()
    } catch (err: any) {
      toast.error('Erro ao emitir convite de equipe', {
        description: err?.detail || err?.message,
      })
    } finally {
      setCreatingInvite(false)
    }
  }

  const handleRevogarConvite = async (inviteId: string) => {
    if (!projectId) return
    if (!window.confirm('Tem certeza de que deseja revogar este convite? Ele não poderá mais ser usado.')) {
      return
    }
    try {
      await api.revokeTeamInvitation(projectId, inviteId)
      toast.success('Convite revogado')
      await carregarEquipe()
    } catch (err: any) {
      toast.error('Erro ao revogar convite', { description: err?.detail || err?.message })
    }
  }

  const handleRemoverMembro = async (member: ProjectMember) => {
    if (!projectId || !team) return
    /* `my_user_id` vem do backend justamente para isto: sem ele a tela não
       distingue a própria linha da dos colegas e o aviso sai trocado. */
    const isSelf = member.user_id === team.my_user_id
    const msg = isSelf
      ? 'Deseja realmente sair da equipe deste projeto de revisão?'
      : `Deseja remover ${member.display_name || member.username} da equipe de revisão?`

    if (!window.confirm(msg)) return

    try {
      await api.removeTeamMember(projectId, member.user_id)
      if (isSelf) {
        toast.success('Você saiu da equipe do projeto.')
        navigate('/projects')
      } else {
        toast.success('Pesquisador removido da equipe.')
        await carregarEquipe()
      }
    } catch (err: any) {
      toast.error('Erro ao remover pesquisador da equipe', {
        description: err?.detail || err?.message,
      })
    }
  }

  const handleAceitarCodigo = async (e: React.FormEvent) => {
    e.preventDefault()
    const code = enterCode.trim().toUpperCase()
    if (!code) return
    setJoining(true)
    try {
      const res = await api.acceptTeamInvitation(code)
      setEnterCode('')
      toast.success('Ingresso na equipe', {
        description: res.message || 'Convite aceito com sucesso.',
      })
      if (res.project_id && res.project_id !== projectId) {
        navigate(`/projects/${res.project_id}/team`)
      } else {
        await carregarEquipe()
      }
    } catch (err: any) {
      toast.error('Código de convite inválido ou expirado', {
        description: err?.detail || err?.message,
      })
    } finally {
      setJoining(false)
    }
  }

  const handleSalvarModalidade = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!projectId) return
    setUpdatingMode(true)
    try {
      if (needsReopen) {
        const res = await api.reopenScreening(projectId, {
          collaboration_mode: selectedMode,
          motivo: reopenReason.trim() || 'Alteração de modalidade de colaboração pela coordenação',
        })
        toast.success(`Modalidade alterada para "${ROTULO_MODALIDADE[selectedMode]}"`, {
          description: `Triagem reaberta: ${res.papers_reset} estudos voltaram para Pendente.`,
        })
        setShowModeModal(false)
        setNeedsReopen(false)
        setReopenReason('')
        await carregarEquipe()
      } else {
        const updated = await api.updateProject(projectId, {
          collaboration_mode: selectedMode,
          reviewers_per_paper: selectedMode === 'cega_por_pares' ? 2 : 1,
        })
        setProject(updated)
        toast.success('Modalidade de colaboração atualizada.')
        setShowModeModal(false)
      }
    } catch (err: any) {
      if (
        err?.status === 409 ||
        err?.message?.includes('409') ||
        err?.detail?.includes('reabertura') ||
        err?.detail?.includes('possui')
      ) {
        setNeedsReopen(true)
        toast.warning('Reabertura de triagem necessária', {
          description:
            err?.detail ||
            'O projeto já possui estudos com decisão. Confirme a reabertura para alterar a modalidade.',
        })
      } else {
        toast.error('Falha ao atualizar a modalidade', {
          description: err?.detail || err?.message,
        })
      }
    } finally {
      setUpdatingMode(false)
    }
  }

  if (loading) {
    return (
      <div className="team-page animate-fade-in">
        <LoadingState label="Carregando membros da equipe…" />
      </div>
    )
  }

  if (error || !team) {
    return (
      <div className="team-page animate-fade-in">
        <EmptyState
          icon={<Users size={32} strokeWidth={1.25} aria-hidden="true" />}
          title="Equipe indisponível"
          description={error || 'Projeto não encontrado ou sem participação ativa.'}
          action={
            <Button variant="secondary" size="md" onClick={() => navigate('/projects')}>
              Voltar aos Projetos
            </Button>
          }
        />
      </div>
    )
  }

  const membrosAtivos = team.members.filter((m) => m.is_active)
  const membrosInativos = team.members.filter((m) => !m.is_active)
  const modalidade: CollaborationMode = project?.collaboration_mode || 'individual'

  return (
    <div className="team-page animate-fade-in">
      <PageHeader
        title="Equipe de Pesquisa"
        onBack={() => navigate('/projects')}
        subtitle={
          <span>
            Projeto: <strong>{project?.title || '—'}</strong> — pesquisadores, papéis de revisão e
            convites de colaboração
          </span>
        }
        meta={
          <Badge variant="brand" size="sm" icon={<Shield size={11} aria-hidden="true" />}>
            Seu papel: {team.my_role}
          </Badge>
        }
        primaryAction={
          isCoordenador ? (
            <Button
              variant="primary"
              size="md"
              onClick={() => setShowInviteModal(true)}
              leftIcon={<UserPlus size={14} />}
            >
              Convidar Pesquisador
            </Button>
          ) : undefined
        }
      />

      <div className="team-grid">
        <div className="team-main-col">
          {/* Modalidade de colaboração (Doc 43 §43.4) */}
          <Card relief="plano" className="team-card">
            <CardHeader
              actions={
                isCoordenador ? (
                  <Button
                    variant="secondary"
                    size="xs"
                    leftIcon={<Settings2 size={13} />}
                    onClick={() => {
                      setSelectedMode(modalidade)
                      setNeedsReopen(false)
                      setReopenReason('')
                      setShowModeModal(true)
                    }}
                  >
                    Alterar Modalidade
                  </Button>
                ) : undefined
              }
            >
              <div className="team-card-heading">
                <CardTitle icon={<Shield size={15} aria-hidden="true" />}>
                  Modalidade de Colaboração
                </CardTitle>
                <span className={`badge-collab-mode mode-${modalidade}`}>
                  {ROTULO_MODALIDADE[modalidade]}
                </span>
              </div>
            </CardHeader>

            <p className="team-card-text">
              {modalidade === 'cega_por_pares' ? (
                <>
                  Triagem com <strong>2 pareceres independentes</strong> por estudo (duplo-cego).
                  Protocolo coeditável. Divergências finais são decididas pela coordenação.
                </>
              ) : modalidade === 'colaborativa' ? (
                <>
                  Acervo e protocolo <strong>compartilhados</strong> entre todos os pesquisadores.
                  Cada estudo recebe 1 parecer de qualquer revisor.
                </>
              ) : (
                <>
                  Pesquisa centralizada no <strong>autor do projeto</strong>. Pareceres e edição de
                  protocolo são restritos à coordenação.
                </>
              )}
            </p>
          </Card>

          {/* Pesquisadores ativos */}
          <Card relief="plano" className="team-card">
            <CardHeader>
              <div className="team-card-heading">
                <CardTitle icon={<UserCheck size={15} aria-hidden="true" />}>
                  Pesquisadores Ativos
                </CardTitle>
                <Badge variant="neutral" size="xs">
                  {membrosAtivos.length}
                </Badge>
              </div>
            </CardHeader>

            <ul className="member-list">
              {membrosAtivos.map((member) => {
                const isSelf = member.user_id === team.my_user_id
                return (
                  <li key={member.id} className="member-item">
                    <span className="member-avatar" aria-hidden="true">
                      {(member.display_name || member.username).slice(0, 2).toUpperCase()}
                    </span>

                    <div className="member-info">
                      <div className="member-name-row">
                        <span className="member-name">
                          {member.display_name || member.username}
                        </span>
                        <span className="member-username">@{member.username}</span>
                        <SeloDePapel papel={member.project_role} />
                        {isSelf && (
                          <Badge variant="neutral" size="xs">
                            você
                          </Badge>
                        )}
                      </div>

                      <div className="member-meta-row">
                        {member.email && (
                          <span className="member-meta-item">
                            <Mail size={11} aria-hidden="true" />
                            {member.email}
                          </span>
                        )}
                        <span className="member-meta-item">
                          <Clock size={11} aria-hidden="true" />
                          Desde {new Date(member.joined_at).toLocaleDateString('pt-BR')}
                        </span>
                      </div>
                    </div>

                    <div className="member-actions">
                      {isSelf ? (
                        <Button
                          variant="ghost"
                          size="xs"
                          leftIcon={<LogOut size={13} />}
                          onClick={() => handleRemoverMembro(member)}
                          title="Sair da equipe"
                        >
                          Sair
                        </Button>
                      ) : (
                        isCoordenador && (
                          <Button
                            variant="ghost"
                            size="xs"
                            leftIcon={<UserX size={13} />}
                            onClick={() => handleRemoverMembro(member)}
                            title="Remover da equipe"
                          >
                            Desligar
                          </Button>
                        )
                      )}
                    </div>
                  </li>
                )
              })}
            </ul>
          </Card>

          {/* Participações encerradas — autoria preservada */}
          {membrosInativos.length > 0 && (
            <Card relief="plano" className="team-card">
              <CardHeader>
                <div className="team-card-heading">
                  <CardTitle icon={<Clock size={15} aria-hidden="true" />}>
                    Participações Anteriores
                  </CardTitle>
                  <Badge variant="neutral" size="xs">
                    {membrosInativos.length}
                  </Badge>
                </div>
              </CardHeader>

              <p className="team-card-text">
                Julgamentos e decisões de membros desligados permanecem registrados para
                conformidade e auditoria de rastro.
              </p>

              <ul className="member-list">
                {membrosInativos.map((member) => (
                  <li key={member.id} className="member-item inactive">
                    <span className="member-avatar inactive" aria-hidden="true">
                      {(member.display_name || member.username).slice(0, 2).toUpperCase()}
                    </span>
                    <div className="member-info">
                      <div className="member-name-row">
                        <span className="member-name">
                          {member.display_name || member.username}
                        </span>
                        <span className="member-username">@{member.username}</span>
                        <SeloDePapel papel="inativo" />
                      </div>
                      <div className="member-meta-row">
                        <span className="member-meta-item">
                          <Clock size={11} aria-hidden="true" />
                          Encerramento:{' '}
                          {member.left_at
                            ? new Date(member.left_at).toLocaleDateString('pt-BR')
                            : '—'}
                        </span>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {/* Convites emitidos — só a coordenação enxerga */}
          {isCoordenador && (
            <Card relief="plano" className="team-card">
              <CardHeader>
                <div className="team-card-heading">
                  <CardTitle icon={<Key size={15} aria-hidden="true" />}>
                    Convites de Equipe Emitidos
                  </CardTitle>
                  <Badge variant="neutral" size="xs">
                    {team.invitations.length}
                  </Badge>
                </div>
              </CardHeader>

              {team.invitations.length === 0 ? (
                <EmptyState
                  size="inline"
                  icon={<Key size={22} strokeWidth={1.25} aria-hidden="true" />}
                  title="Nenhum convite emitido"
                  description="Um convite gera um código RSAC-EQ-… válido por 14 dias, que o colega usa para entrar na revisão."
                  action={
                    <Button
                      variant="secondary"
                      size="sm"
                      leftIcon={<UserPlus size={13} />}
                      onClick={() => setShowInviteModal(true)}
                    >
                      Emitir Primeiro Convite
                    </Button>
                  }
                />
              ) : (
                <ul className="invite-list">
                  {team.invitations.map((inv) => (
                    <li key={inv.id} className={`invite-item ${!inv.is_valid ? 'invalid' : ''}`}>
                      <div className="invite-code-col">
                        <code className="invite-code">{inv.code}</code>
                        <div className="invite-copy-row">
                          <Button
                            variant="ghost"
                            size="xs"
                            leftIcon={
                              copiedCode === inv.code ? <Check size={12} /> : <Copy size={12} />
                            }
                            onClick={() => handleCopiarCodigo(inv.code)}
                            title="Copiar código"
                          >
                            {copiedCode === inv.code ? 'Copiado!' : 'Código'}
                          </Button>
                          <Button
                            variant="ghost"
                            size="xs"
                            leftIcon={
                              copiedCode === `link-${inv.code}` ? (
                                <Check size={12} />
                              ) : (
                                <Link2 size={12} />
                              )
                            }
                            onClick={() => handleCopiarLink(inv.code)}
                            title="Copiar link de acesso rápido"
                          >
                            {copiedCode === `link-${inv.code}` ? 'Copiado!' : 'Link'}
                          </Button>
                        </div>
                      </div>

                      <div className="invite-details-col">
                        <div className="invite-role-row">
                          <SeloDePapel papel={inv.project_role} />
                          {inv.email && <span className="invite-email">{inv.email}</span>}
                          {inv.note && <span className="invite-note">“{inv.note}”</span>}
                        </div>

                        <div className="invite-meta-row">
                          <span className="member-meta-item">
                            <Clock size={11} aria-hidden="true" />
                            Expira em {new Date(inv.expires_at).toLocaleDateString('pt-BR')}
                          </span>
                          {inv.accepted_at && (
                            <Badge variant="success" size="xs">
                              Aceito por @{inv.accepted_by_username || 'pesquisador'}
                            </Badge>
                          )}
                          {inv.revoked_at && (
                            <Badge variant="error" size="xs">
                              Revogado
                            </Badge>
                          )}
                        </div>
                      </div>

                      <div className="invite-actions-col">
                        {inv.is_valid && (
                          <Button
                            variant="ghost"
                            size="xs"
                            leftIcon={<Trash2 size={13} />}
                            onClick={() => handleRevogarConvite(inv.id)}
                            title="Revogar convite"
                          >
                            Revogar
                          </Button>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          )}
        </div>

        {/* Coluna lateral: ingresso por código e guia de papéis */}
        <aside className="team-side-col">
          <Card relief="plano" className="team-card">
            <CardHeader>
              <CardTitle icon={<Key size={15} aria-hidden="true" />}>
                Entrar em outra Revisão
              </CardTitle>
            </CardHeader>
            <p className="team-card-text">
              Recebeu um código <code>RSAC-EQ-…</code> de outro coordenador? Informe abaixo para
              ingressar na equipe.
            </p>
            <form onSubmit={handleAceitarCodigo} className="team-join-form">
              <div className="form-group">
                <label htmlFor="team-join-code">Código do convite</label>
                <input
                  id="team-join-code"
                  type="text"
                  placeholder="RSAC-EQ-A1B2-C3D4"
                  value={enterCode}
                  onChange={(e) => setEnterCode(e.target.value)}
                  className="team-code-input"
                  required
                />
              </div>
              <Button
                type="submit"
                variant="secondary"
                size="md"
                fullWidth
                loading={joining}
                leftIcon={<UserCheck size={14} />}
              >
                Ingressar no Projeto
              </Button>
            </form>
          </Card>

          <Card relief="plano" className="team-card">
            <CardHeader>
              <CardTitle icon={<HelpCircle size={15} aria-hidden="true" />}>
                Papéis na Revisão
              </CardTitle>
            </CardHeader>

            <div className="role-guide-item">
              <SeloDePapel papel="coordenador" />
              <p>
                Gerencia a equipe, emite convites, edita o protocolo metodológico, configura a
                modalidade de colaboração e resolve divergências.
              </p>
            </div>

            <div className="role-guide-item">
              <SeloDePapel papel="revisor" />
              <p>
                Executa a triagem (incluir/excluir), preenche critérios de elegibilidade, realiza a
                extração de dados e dispara a assistência com a própria chave.
              </p>
            </div>

            <div className="role-guide-item">
              <SeloDePapel papel="observador" />
              <p>
                Acesso de leitura ao protocolo, ao acervo de estudos e aos relatórios PRISMA — para
                auditoria, bancas e acompanhamento acadêmico.
              </p>
            </div>
          </Card>
        </aside>
      </div>

      {/* Diálogo: emitir convite */}
      <Dialog open={showInviteModal} onOpenChange={setShowInviteModal}>
        <DialogContent variant="window" size="md" aria-describedby={undefined}>
          <DialogTitlebar>Convidar Pesquisador para a Equipe</DialogTitlebar>
          <DialogBody>
            <div className="modal-intro">
              <p>
                O convite gera um código <code>RSAC-EQ-…</code> com validade de 14 dias. Se o colega
                ainda não tiver conta no Revsist, o código permite o autocadastro direto na sua
                revisão.
              </p>
            </div>

            <form onSubmit={handleCriarConvite} className="modal-form">
              <div className="form-group">
                <label htmlFor="inviteRole">Papel de atuação na revisão</label>
                <select
                  id="inviteRole"
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as ProjectRoleType)}
                >
                  <option value="revisor">Revisor (triagem, elegibilidade e extração)</option>
                  <option value="coordenador">Coordenador (gestão plena e protocolo)</option>
                  <option value="observador">Observador (somente leitura e auditoria)</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="inviteEmail">E-mail do destinatário (opcional)</label>
                <input
                  id="inviteEmail"
                  type="email"
                  placeholder="colega@universidade.edu.br"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                />
                <span className="form-hint">
                  Serve para registro e identificação. O código pode ser enviado pelo canal de sua
                  preferência.
                </span>
              </div>

              <div className="form-group">
                <label htmlFor="inviteNote">Nota interna (opcional)</label>
                <input
                  id="inviteNote"
                  type="text"
                  placeholder="Ex.: Revisor 2 para a etapa de elegibilidade"
                  value={inviteNote}
                  onChange={(e) => setInviteNote(e.target.value)}
                />
              </div>

              <div className="modal-actions">
                <Button
                  type="button"
                  variant="secondary"
                  size="md"
                  onClick={() => setShowInviteModal(false)}
                  disabled={creatingInvite}
                >
                  Cancelar
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="md"
                  loading={creatingInvite}
                  leftIcon={<UserPlus size={14} />}
                >
                  Gerar Convite de Equipe
                </Button>
              </div>
            </form>
          </DialogBody>
        </DialogContent>
      </Dialog>

      {/* Diálogo: modalidade de colaboração (Doc 43 §43.4) */}
      <Dialog open={showModeModal} onOpenChange={setShowModeModal}>
        <DialogContent variant="window" size="md" aria-describedby={undefined}>
          <DialogTitlebar>Configurar Modalidade de Colaboração</DialogTitlebar>
          <DialogBody>
            <div className="modal-intro">
              <p>
                A modalidade define as regras de coautoria, o fluxo duplo-cego e a independência dos
                pareceres na triagem metodológica.
              </p>
            </div>

            <form onSubmit={handleSalvarModalidade} className="modal-form">
              <div className="form-group">
                <label htmlFor="selectCollabMode">Modalidade de trabalho</label>
                <select
                  id="selectCollabMode"
                  value={selectedMode}
                  onChange={(e) => {
                    setSelectedMode(e.target.value as CollaborationMode)
                    setNeedsReopen(false)
                  }}
                >
                  <option value="individual">Individual (pesquisador único)</option>
                  <option value="colaborativa">Equipe colaborativa (acervo compartilhado)</option>
                  <option value="cega_por_pares">
                    Revisão cega por pares (2 revisores independentes)
                  </option>
                </select>
              </div>

              <div className="collab-preview-desc">
                {selectedMode === 'cega_por_pares' && (
                  <p>
                    <strong>Duplo-cego:</strong> cada estudo exige 2 pareceres independentes.
                    Protocolo coeditável. Divergências são resolvidas pela coordenação.
                  </p>
                )}
                {selectedMode === 'colaborativa' && (
                  <p>
                    <strong>Colaborativo:</strong> todos os revisores coeditam o protocolo e triam
                    estudos. Um parecer define a decisão.
                  </p>
                )}
                {selectedMode === 'individual' && (
                  <p>
                    <strong>Individual:</strong> centralizado na coordenação. Protocolo e pareceres
                    restritos.
                  </p>
                )}
              </div>

              {needsReopen && (
                <div className="reopen-warning-box">
                  <div className="reopen-warning-head">
                    <AlertTriangle size={15} aria-hidden="true" />
                    <strong>Reabertura de triagem obrigatória</strong>
                  </div>
                  <p>
                    O projeto já possui estudos com decisão finalizada. Para alterar a modalidade,
                    todas as decisões anteriores voltam a <em>Pendente</em>, com registro em log de
                    auditoria.
                  </p>
                  <div className="form-group">
                    <label htmlFor="reopenReason">Motivo da reabertura</label>
                    <input
                      id="reopenReason"
                      type="text"
                      placeholder="Ex.: transição para revisão duplo-cega com ingresso de novos revisores"
                      value={reopenReason}
                      onChange={(e) => setReopenReason(e.target.value)}
                      required
                    />
                  </div>
                </div>
              )}

              <div className="modal-actions">
                <Button
                  type="button"
                  variant="secondary"
                  size="md"
                  onClick={() => setShowModeModal(false)}
                  disabled={updatingMode}
                >
                  Cancelar
                </Button>
                <Button
                  type="submit"
                  variant={needsReopen ? 'destructive' : 'primary'}
                  size="md"
                  loading={updatingMode}
                  leftIcon={needsReopen ? <RotateCcw size={14} /> : <Check size={14} />}
                >
                  {needsReopen ? 'Confirmar e Reabrir Triagem' : 'Salvar Modalidade'}
                </Button>
              </div>
            </form>
          </DialogBody>
        </DialogContent>
      </Dialog>
    </div>
  )
}
