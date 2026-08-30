import React, { useState, useEffect } from 'react'
import {
  Lock,
  GitBranch,
  Calendar,
  User,
  Hash,
  CheckCircle2,
  ShieldCheck,
  History,
} from 'lucide-react'
import type { ProtocolAmendment, ProtocolVersion } from '@/types/api'
import {
  Badge,
  Button,
  FormGroup,
  Input,
  Textarea,
  Select,
  Dialog,
  DialogContent,
  DialogTitlebar,
  DialogBody,
  DialogFooter,
} from '@/components/ui'
import { api } from '@/api/client'
import { ANCORAGEM_NORMATIVA } from '@/data/protocolCatalog'
import './ProtocolStudio.css'

interface ProtocolVersionDialogProps {
  projectId: string
  open: boolean
  onOpenChange: (open: boolean) => void
  currentVersion?: string | null
  protocolStatus?: string
  onVersionChanged?: () => void
  readOnly?: boolean
}

export function ProtocolVersionDialog({
  projectId,
  open,
  onOpenChange,
  currentVersion,
  protocolStatus,
  onVersionChanged,
  readOnly = false,
}: ProtocolVersionDialogProps): JSX.Element {
  const [activeTab, setActiveTab] = useState<'freeze' | 'amend' | 'history'>('history')
  const [versions, setVersions] = useState<ProtocolVersion[]>([])
  const [amendments, setAmendments] = useState<ProtocolAmendment[]>([])
  const [loading, setLoading] = useState(false)

  // Freeze form
  const [freezeLabel, setFreezeLabel] = useState(currentVersion ? `v${parseFloat(currentVersion.replace('v', '') || '1.0') + 0.1}` : 'v1.0')
  const [freezeLoading, setFreezeLoading] = useState(false)
  const [freezeSuccess, setFreezeSuccess] = useState(false)

  // Amendment form
  const [amendReason, setAmendReason] = useState('')
  const [amendPhase, setAmendPhase] = useState<'planejamento' | 'coleta' | 'triagem' | 'extracao' | 'sintese'>('coleta')
  const [amendNewVersion, setAmendNewVersion] = useState('v1.1')
  const [amendLoading, setAmendLoading] = useState(false)

  useEffect(() => {
    if (open) {
      loadHistory()
    }
  }, [open, projectId])

  const loadHistory = async () => {
    setLoading(true)
    try {
      const [vList, aList] = await Promise.all([
        api.listProtocolVersions(projectId),
        api.listProtocolAmendments(projectId),
      ])
      setVersions(vList)
      setAmendments(aList)
      if (vList.length === 0) {
        setActiveTab('freeze')
      }
    } catch (err) {
      console.error('Erro ao carregar histórico de versões:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleFreeze = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!freezeLabel.trim() || readOnly) return
    setFreezeLoading(true)
    try {
      await api.freezeProtocolVersion(projectId, freezeLabel.trim())
      setFreezeSuccess(true)
      setTimeout(() => {
        setFreezeSuccess(false)
        setActiveTab('history')
        loadHistory()
        if (onVersionChanged) onVersionChanged()
      }, 1500)
    } catch (err) {
      console.error('Erro ao congelar versão:', err)
    } finally {
      setFreezeLoading(false)
    }
  }

  const handleCreateAmendment = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!amendReason.trim() || !amendNewVersion.trim() || readOnly) return
    setAmendLoading(true)
    try {
      await api.createProtocolAmendment(projectId, {
        from_version: currentVersion || 'v1.0',
        to_version: amendNewVersion.trim(),
        reason: amendReason.trim(),
        project_phase: amendPhase,
      })
      setAmendReason('')
      setActiveTab('history')
      loadHistory()
      if (onVersionChanged) onVersionChanged()
    } catch (err) {
      console.error('Erro ao registrar emenda:', err)
    } finally {
      setAmendLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogTitlebar>
          <Lock size={15} />
          <span>Versões e emendas do protocolo</span>
        </DialogTitlebar>

        <DialogBody>
          <div className="protocol-versions">
            <div className="protocol-versions__tabs" role="tablist">
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'history'}
                onClick={() => setActiveTab('history')}
                className={`protocol-toggle ${activeTab === 'history' ? 'is-selected' : ''}`}
              >
                <History size={13} />
                <span>Histórico ({versions.length})</span>
              </button>

              {!readOnly && (
                <>
                  <button
                    type="button"
                    role="tab"
                    aria-selected={activeTab === 'freeze'}
                    onClick={() => setActiveTab('freeze')}
                    className={`protocol-toggle ${activeTab === 'freeze' ? 'is-selected' : ''}`}
                  >
                    <Lock size={13} />
                    <span>Congelar versão</span>
                  </button>

                  {currentVersion && (
                    <button
                      type="button"
                      role="tab"
                      aria-selected={activeTab === 'amend'}
                      onClick={() => setActiveTab('amend')}
                      className={`protocol-toggle ${activeTab === 'amend' ? 'is-selected' : ''}`}
                    >
                      <GitBranch size={13} />
                      <span>Registrar emenda</span>
                    </button>
                  )}
                </>
              )}
            </div>

            {/* ── Histórico ──────────────────────────────────── */}
            {activeTab === 'history' && (
              <div className="protocol-versions__pane">
                {loading ? (
                  <p className="strategy-loading">Carregando o histórico…</p>
                ) : versions.length === 0 ? (
                  <div className="protocol-versions__empty">
                    <ShieldCheck size={28} />
                    <strong>Nenhuma versão congelada até agora</strong>
                    <p>
                      Congelar antes da primeira coleta é o que torna o protocolo <em>a priori</em>.
                      Fica a seu critério — o Revsist oferece, não obriga —, mas o aviso permanece
                      enquanto não houver versão congelada.
                    </p>
                  </div>
                ) : (
                  <>
                    <span className="protocol-versions__label">Versões registradas</span>
                    <div className="protocol-versions__list">
                      {versions.map((v) => (
                        <div key={v.id} className="version-entry">
                          <div className="version-entry__head">
                            <span className="version-entry__identity">
                              <span className="version-entry__label">{v.label}</span>
                              {v.label === currentVersion && (
                                <Badge variant="success" size="xs">Vigente</Badge>
                              )}
                            </span>
                            <span className="version-entry__meta">
                              <Calendar size={12} />
                              {new Date(v.frozen_at).toLocaleString('pt-BR')}
                            </span>
                          </div>

                          <span className="version-entry__hash">
                            <Hash size={12} />
                            <span>SHA-256: {v.content_hash}</span>
                          </span>

                          {v.frozen_by_username && (
                            <span className="version-entry__meta">
                              <User size={12} />
                              Congelada por @{v.frozen_by_username}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>

                    {amendments.length > 0 && (
                      <div className="protocol-versions__section">
                        <span className="protocol-versions__label">
                          Emendas justificadas ({amendments.length})
                        </span>
                        <div className="protocol-versions__list protocol-versions__list--curta">
                          {amendments.map((a) => (
                            <div key={a.id} className="amendment-entry">
                              <div className="amendment-entry__head">
                                <span>
                                  {a.from_version} → {a.to_version} · {a.project_phase}
                                </span>
                                <span className="amendment-entry__date">
                                  {new Date(a.created_at).toLocaleDateString('pt-BR')}
                                </span>
                              </div>
                              <p className="amendment-entry__reason">“{a.reason}”</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {/* ── Congelar ───────────────────────────────────── */}
            {activeTab === 'freeze' && (
              <form onSubmit={handleFreeze} className="protocol-versions__form">
                <div className="protocol-versions__note">
                  <strong>O que o congelamento faz</strong>
                  <p>
                    Grava um retrato imutável de todo o protocolo em JSON, com hash SHA-256, autor e
                    data. É o que permite citar depois a versão exata que orientou a busca — e é o que
                    responde, na revisão por pares, se os critérios mudaram após ver os resultados.
                  </p>
                </div>

                <FormGroup label="Rótulo da versão" required>
                  <Input
                    type="text"
                    value={freezeLabel}
                    onChange={(e) => setFreezeLabel(e.target.value)}
                    placeholder="Ex.: v1.0 ou v1.0-pre-coleta"
                    required
                  />
                </FormGroup>

                <Button type="submit" size="sm" disabled={freezeLoading}>
                  {freezeSuccess ? (
                    <>
                      <CheckCircle2 size={14} />
                      <span>Versão congelada</span>
                    </>
                  ) : freezeLoading ? (
                    <span>Calculando o hash e congelando…</span>
                  ) : (
                    <>
                      <Lock size={14} />
                      <span>Congelar protocolo agora</span>
                    </>
                  )}
                </Button>
              </form>
            )}

            {/* ── Emenda ─────────────────────────────────────── */}
            {activeTab === 'amend' && (
              <form onSubmit={handleCreateAmendment} className="protocol-versions__form">
                <div className="protocol-versions__note protocol-versions__note--emenda">
                  <strong>Registro formal de emenda</strong>
                  <p>
                    {ANCORAGEM_NORMATIVA.emendaDeProtocolo}
                  </p>
                </div>

                <div className="protocol-versions__form-grid">
                  <FormGroup label="Versão anterior">
                    <Input type="text" value={currentVersion || 'v1.0'} disabled readOnly />
                  </FormGroup>

                  <FormGroup label="Nova versão" required>
                    <Input
                      type="text"
                      value={amendNewVersion}
                      onChange={(e) => setAmendNewVersion(e.target.value)}
                      placeholder="Ex.: v1.1"
                      required
                    />
                  </FormGroup>
                </div>

                <FormGroup label="Fase em que a emenda ocorreu" required>
                  <Select value={amendPhase} onChange={(e) => setAmendPhase(e.target.value as any)}>
                    <option value="planejamento">Planejamento (a priori)</option>
                    <option value="coleta">Coleta</option>
                    <option value="triagem">Triagem</option>
                    <option value="extracao">Extração</option>
                    <option value="sintese">Síntese e redação</option>
                  </Select>
                </FormGroup>

                <FormGroup
                  label="Justificativa da emenda"
                  required
                  helperText="O que mudou e por quê. É este texto que aparece no histórico exportado."
                >
                  <Textarea
                    value={amendReason}
                    onChange={(e) => setAmendReason(e.target.value)}
                    placeholder="Ex.: recorte temporal ampliado para 2012 após a identificação de marcos regulatórios anteriores ao período inicialmente previsto…"
                    rows={3}
                    required
                  />
                </FormGroup>

                <Button type="submit" size="sm" disabled={amendLoading}>
                  <GitBranch size={14} />
                  <span>{amendLoading ? 'Registrando…' : 'Registrar emenda e congelar nova versão'}</span>
                </Button>
              </form>
            )}
          </div>
        </DialogBody>

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Fechar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
