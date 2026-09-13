/**
 * Revsist — Tela de Acesso e Registro com Convite
 *
 * Suporta entrada direta para usuários cadastrados e fluxo completo de
 * registro acadêmico para portadores de convite de uso único.
 */

import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import {
  AlertCircle,
  Award,
  BookOpen,
  Building2,
  CheckCircle2,
  GraduationCap,
  KeyRound,
  LogIn,
  Mail,
  MailQuestion,
  Phone,
  Send,
  ShieldCheck,
  Ticket,
  User,
  UserPlus,
} from 'lucide-react'
import { Button, FormGroup, Input } from '@/components/ui'
import { RsacLockup } from '@/components/brand/RsacLockup'
import { useAuthStore } from '@/stores/useAuthStore'
import { api } from '@/api/client'
import './LoginPage.css'

export function LoginPage(): JSX.Element {
  const { login, registerWithInvite, error, submitting, status, setError } = useAuthStore()
  const location = useLocation()

  const [activeTab, setActiveTab] = useState<'login' | 'invite' | 'request'>('login')

  // Estado do formulário de Login
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const usuarioRef = useRef<HTMLInputElement>(null)

  // Estado do fluxo de Convite
  const [inviteStep, setInviteStep] = useState<'validate' | 'form'>('validate')
  // Convite chegou por link (`/c/CODIGO`) em vez de digitado?
  const [veioPorLink, setVeioPorLink] = useState(false)
  const [inviteCodeInput, setInviteCodeInput] = useState('')
  const [validatingInvite, setValidatingInvite] = useState(false)
  const [inviteNote, setInviteNote] = useState('')
  const inviteCodeRef = useRef<HTMLInputElement>(null)

  // Campos de Cadastro com Convite
  const [regFullName, setRegFullName] = useState('')
  const [regEmail, setRegEmail] = useState('')
  const [regPhone, setRegPhone] = useState('')
  const [regInstitution, setRegInstitution] = useState('')
  const [regAcademicDegree, setRegAcademicDegree] = useState('Doutorando(a)')
  const [regIsStudying, setRegIsStudying] = useState(true)
  const [regStudyProgram, setRegStudyProgram] = useState('')
  const [regProfession, setRegProfession] = useState('')
  const [regResearchArea, setRegResearchArea] = useState('')
  const [regUsername, setRegUsername] = useState('')
  const [regPassword, setRegPassword] = useState('')
  const [regPasswordConfirm, setRegPasswordConfirm] = useState('')
  const [regTermsAccepted, setRegTermsAccepted] = useState(false)

  // Estado do pedido de convite (para quem ainda não tem código)
  const [reqName, setReqName] = useState('')
  const [reqEmail, setReqEmail] = useState('')
  const [reqPhone, setReqPhone] = useState('')
  const [reqInstitution, setReqInstitution] = useState('')
  const [reqSource, setReqSource] = useState('')
  const [reqSourceDetail, setReqSourceDetail] = useState('')
  const [sendingRequest, setSendingRequest] = useState(false)
  const [requestSent, setRequestSent] = useState(false)
  const reqNameRef = useRef<HTMLInputElement>(null)

  /**
   * Convite que chegou pronto no endereço.
   *
   * O backend redireciona `revsist.com/c/RSAC-XXXX` para `#/convite/RSAC-XXXX`,
   * e é aqui que esse caminho vira tela: o código é validado sozinho e, dando
   * certo, a pessoa cai direto no formulário de cadastro. O ponto do link é
   * não pedir que ninguém copie, cole ou digite o código — parar num campo
   * preenchido esperando um clique em "Validar" desperdiçaria metade disso.
   *
   * Se a validação falhar — convite revogado, expirado, já usado —, a tela
   * fica no passo do código com o erro explicado. Nesse caso o campo
   * preenchido ajuda: a pessoa vê qual código foi recusado.
   */
  useEffect(() => {
    const m = location.pathname.match(/^\/convite\/([A-Za-z0-9-]{4,32})$/)
    if (!m) return

    const codigo = m[1].toUpperCase()
    setActiveTab('invite')
    setInviteCodeInput(codigo)
    setVeioPorLink(true)

    let cancelado = false
    const validar = async () => {
      setValidatingInvite(true)
      setError(null)
      try {
        const res = await api.validateInvite(codigo)
        if (cancelado) return
        if (res.valid) {
          setInviteNote(res.note || 'Convite válido.')
          setInviteStep('form')
        }
      } catch (err: any) {
        if (cancelado) return
        setError(err?.message || 'Este convite não é mais válido.')
        setInviteStep('validate')
      } finally {
        if (!cancelado) setValidatingInvite(false)
      }
    }
    void validar()
    return () => {
      cancelado = true
    }
  }, [location.pathname])

  useEffect(() => {
    if (activeTab === 'login') {
      usuarioRef.current?.focus()
    } else if (activeTab === 'request') {
      reqNameRef.current?.focus()
    } else if (inviteStep === 'validate' && !veioPorLink) {
      inviteCodeRef.current?.focus()
    }
  }, [activeTab, inviteStep, veioPorLink])

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password) {
      setError('Informe usuário e senha.')
      return
    }
    await login(username.trim(), password)
    setPassword('')
  }

  const handleValidateInvite = async (e: React.FormEvent) => {
    e.preventDefault()
    const codigo = inviteCodeInput.trim().toUpperCase()
    if (!codigo) {
      setError('Informe o código de convite recebido.')
      return
    }

    setValidatingInvite(true)
    setError(null)
    try {
      const res = await api.validateInvite(codigo)
      if (res.valid) {
        setInviteNote(res.note || 'Convite válido.')
        setInviteStep('form')
      }
    } catch (err: any) {
      setError(err?.message || 'Código de convite inválido, revogado ou já utilizado.')
    } finally {
      setValidatingInvite(false)
    }
  }

  const handleRequestSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (reqName.trim().length < 3) {
      setError('Informe seu nome completo.')
      return
    }
    if (!reqEmail.trim().includes('@')) {
      setError('Informe um endereço de e-mail válido — é por ele que o convite chega.')
      return
    }
    if (reqPhone.trim().length < 8) {
      setError('Informe um telefone de contato.')
      return
    }
    if (!reqSource) {
      setError('Conte como você chegou até o Revsist.')
      return
    }

    // O campo aberto complementa a escolha em vez de substituí-la: "Outro" sem
    // detalhe não diria nada a quem avalia o pedido.
    const origem = reqSourceDetail.trim()
      ? `${reqSource} — ${reqSourceDetail.trim()}`
      : reqSource

    setSendingRequest(true)
    try {
      await api.requestInvite({
        nome: reqName.trim(),
        email: reqEmail.trim().toLowerCase(),
        telefone: reqPhone.trim(),
        onde_conheceu: origem.slice(0, 255),
        instituicao: reqInstitution.trim(),
      })
      setRequestSent(true)
    } catch (err: any) {
      setError(err?.message || 'Não foi possível enviar o pedido. Tente novamente em instantes.')
    } finally {
      setSendingRequest(false)
    }
  }

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!regFullName.trim()) {
      setError('Informe seu nome completo.')
      return
    }
    if (!regEmail.trim()) {
      setError('Informe seu endereço de e-mail.')
      return
    }
    if (!regUsername.trim()) {
      setError('Escolha um nome de usuário para login.')
      return
    }
    if (!regPassword || regPassword.length < 12) {
      setError('A senha deve conter no mínimo 12 caracteres.')
      return
    }
    if (regPassword !== regPasswordConfirm) {
      setError('As senhas digitadas não conferem.')
      return
    }
    if (!regTermsAccepted) {
      setError('É obrigatório concordar com os Termos de Uso e a Política de Privacidade.')
      return
    }

    const payload = {
      invite_code: inviteCodeInput.trim().toUpperCase(),
      username: regUsername.trim().toLowerCase(),
      password: regPassword,
      full_name: regFullName.trim(),
      email: regEmail.trim().toLowerCase(),
      phone: regPhone.trim(),
      institution: regInstitution.trim(),
      academic_degree: regAcademicDegree,
      is_studying: regIsStudying,
      study_program: regStudyProgram.trim(),
      profession: regProfession.trim(),
      research_area: regResearchArea.trim(),
      terms_accepted: regTermsAccepted,
    }

    await registerWithInvite(payload)
  }

  const semContas = status?.has_accounts === false

  return (
    <div className="login-page">
      <div className={`login-card ${activeTab === 'invite' && inviteStep === 'form' ? 'login-card--wide' : ''}`}>
        <div className="login-brand">
          <RsacLockup size="lg" />
        </div>

        <h1 className="login-title">Acesso ao ambiente de revisão</h1>
        <p className="login-subtitle">
          Plataforma de apoio metodológico para revisões sistemáticas em Ciências Sociais Aplicadas e Desenvolvimento Regional.
        </p>

        {semContas ? (
          <div className="login-alert login-alert--info" role="status">
            <ShieldCheck size={18} />
            <div>
              <strong>Nenhuma conta provisionada</strong>
              <p>
                Crie a primeira conta de administração no servidor:
                <code>python -m app.cli create-user seu_usuario --role owner</code>
                ou gere um convite para registro:
                <code>python -m app.cli create-invite --note "Primeiro usuário"</code>
              </p>
            </div>
          </div>
        ) : (
          <>
            {/* Seletor de Modo: Login vs Convite */}
            <div className="login-tabs" role="tablist">
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'login'}
                className={`login-tab ${activeTab === 'login' ? 'login-tab--active' : ''}`}
                onClick={() => {
                  setActiveTab('login')
                  setError(null)
                }}
              >
                <LogIn size={15} />
                <span>Já sou cadastrado</span>
              </button>

              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'invite'}
                className={`login-tab ${activeTab === 'invite' ? 'login-tab--active' : ''}`}
                onClick={() => {
                  setActiveTab('invite')
                  setError(null)
                }}
              >
                <Ticket size={15} />
                <span>Tenho um convite</span>
              </button>

              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'request'}
                className={`login-tab ${activeTab === 'request' ? 'login-tab--active' : ''}`}
                onClick={() => {
                  setActiveTab('request')
                  setError(null)
                }}
              >
                <MailQuestion size={15} />
                <span>Quero um convite</span>
              </button>
            </div>

            {/* Mensagem de Erro Geral */}
            {error && (
              <div className="login-alert login-alert--error" role="alert">
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}

            {/* ABA 1: LOGIN TRADICIONAL */}
            {activeTab === 'login' && (
              <form className="login-form" onSubmit={handleLoginSubmit}>
                <FormGroup label="Usuário ou E-mail" htmlFor="login-usuario">
                  <Input
                    id="login-usuario"
                    ref={usuarioRef}
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    autoComplete="username"
                    placeholder="seu_usuario"
                    leftIcon={<User size={15} />}
                    disabled={submitting}
                  />
                </FormGroup>

                <FormGroup label="Senha" htmlFor="login-senha">
                  <Input
                    id="login-senha"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                    placeholder="••••••••••••"
                    leftIcon={<KeyRound size={15} />}
                    disabled={submitting}
                  />
                </FormGroup>

                <Button
                  type="submit"
                  variant="primary"
                  size="lg"
                  loading={submitting}
                  leftIcon={<LogIn size={16} />}
                  className="login-submit"
                >
                  {submitting ? 'Entrando…' : 'Entrar'}
                </Button>
              </form>
            )}

            {/* ABA 2: REGISTRO COM CONVITE */}
            {activeTab === 'invite' && (
              <>
                {inviteStep === 'validate' ? (
                  <form className="login-form" onSubmit={handleValidateInvite}>
                    <div className="invite-intro">
                      <p>
                        {veioPorLink
                          ? 'Este é o código que veio no seu link. Confira se é o mesmo da mensagem que você recebeu e tente novamente.'
                          : 'O registro no Revsist é realizado exclusivamente mediante convite de uso único. Insira o código fornecido pelo orientador ou administrador:'}
                      </p>
                    </div>

                    <FormGroup label="Código do Convite" htmlFor="invite-code">
                      <Input
                        id="invite-code"
                        ref={inviteCodeRef}
                        value={inviteCodeInput}
                        onChange={(e) => setInviteCodeInput(e.target.value.toUpperCase())}
                        placeholder="RSAC-XXXX-YYYY"
                        leftIcon={<Ticket size={15} />}
                        disabled={validatingInvite}
                        style={{ textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 'bold' }}
                      />
                    </FormGroup>

                    <Button
                      type="submit"
                      variant="primary"
                      size="lg"
                      loading={validatingInvite}
                      leftIcon={<CheckCircle2 size={16} />}
                      className="login-submit"
                    >
                      {validatingInvite ? 'Validando…' : 'Validar Convite e Continuar'}
                    </Button>
                  </form>
                ) : (
                  <form className="login-form registration-grid-form" onSubmit={handleRegisterSubmit}>
                    <div className="invite-badge-success">
                      <CheckCircle2 size={16} />
                      <span>
                        {veioPorLink ? 'Convite reconhecido pelo seu link: ' : 'Convite Validado: '}
                        <strong>{inviteCodeInput}</strong>
                        {/* A nota é rótulo interno do administrador, e a nota
                            de um convite aprovado carrega o nome e o e-mail de
                            quem pediu. Ela ajuda quem digitou o código a
                            confirmar que é o seu; num link encaminhado, só
                            entregaria o contato do destinatário original a
                            quem recebeu o encaminhamento. */}
                        {!veioPorLink && inviteNote && ` (${inviteNote})`}
                      </span>
                    </div>

                    <div className="reg-section-title">1. Dados Pessoais e Institucionais</div>

                    <div className="reg-grid-2">
                      <FormGroup label="Nome Completo *" htmlFor="reg-name">
                        <Input
                          id="reg-name"
                          value={regFullName}
                          onChange={(e) => setRegFullName(e.target.value)}
                          placeholder="Prof. Dra. Maria Silva"
                          leftIcon={<User size={14} />}
                          disabled={submitting}
                          required
                        />
                      </FormGroup>

                      <FormGroup label="E-mail *" htmlFor="reg-email">
                        <Input
                          id="reg-email"
                          type="email"
                          value={regEmail}
                          onChange={(e) => setRegEmail(e.target.value)}
                          placeholder="pesquisador@universidade.edu.br"
                          leftIcon={<Mail size={14} />}
                          disabled={submitting}
                          required
                        />
                      </FormGroup>
                    </div>

                    <div className="reg-grid-2">
                      <FormGroup label="Telefone / WhatsApp" htmlFor="reg-phone">
                        <Input
                          id="reg-phone"
                          value={regPhone}
                          onChange={(e) => setRegPhone(e.target.value)}
                          placeholder="(51) 99999-8888"
                          leftIcon={<Phone size={14} />}
                          disabled={submitting}
                        />
                      </FormGroup>

                      <FormGroup label="Universidade / Instituição" htmlFor="reg-inst">
                        <Input
                          id="reg-inst"
                          value={regInstitution}
                          onChange={(e) => setRegInstitution(e.target.value)}
                          placeholder="ex: UFRGS, USP, IBICT…"
                          leftIcon={<Building2 size={14} />}
                          disabled={submitting}
                        />
                      </FormGroup>
                    </div>

                    <div className="reg-grid-2">
                      <FormGroup label="Titulação / Grau Acadêmico" htmlFor="reg-degree">
                        <div className="select-wrapper">
                          <GraduationCap size={14} className="select-left-icon" />
                          <select
                            id="reg-degree"
                            className="rsac-custom-select"
                            value={regAcademicDegree}
                            onChange={(e) => setRegAcademicDegree(e.target.value)}
                            disabled={submitting}
                          >
                            <option value="Graduando(a)">Graduando(a)</option>
                            <option value="Especialista">Especialista</option>
                            <option value="Mestrando(a)">Mestrando(a)</option>
                            <option value="Mestre">Mestre</option>
                            <option value="Doutorando(a)">Doutorando(a)</option>
                            <option value="Doutor(a)">Doutor(a)</option>
                            <option value="Pós-Doutor(a)">Pós-Doutor(a)</option>
                            <option value="Professor(a) / Pesquisador(a)">Professor(a) / Pesquisador(a)</option>
                            <option value="Outro">Outro</option>
                          </select>
                        </div>
                      </FormGroup>

                      <FormGroup label="Profissão / Cargo Atual" htmlFor="reg-prof">
                        <Input
                          id="reg-prof"
                          value={regProfession}
                          onChange={(e) => setRegProfession(e.target.value)}
                          placeholder="ex: Docente, Analista, Pesquisador"
                          leftIcon={<Award size={14} />}
                          disabled={submitting}
                        />
                      </FormGroup>
                    </div>

                    <div className="reg-checkbox-group">
                      <label className="reg-checkbox-label">
                        <input
                          type="checkbox"
                          checked={regIsStudying}
                          onChange={(e) => setRegIsStudying(e.target.checked)}
                          disabled={submitting}
                        />
                        <span>Estou matriculado(a) em curso de graduação ou pós-graduação atualmente</span>
                      </label>
                    </div>

                    <div className="reg-grid-2">
                      <FormGroup label="Programa de Pós / Curso" htmlFor="reg-program">
                        <Input
                          id="reg-program"
                          value={regStudyProgram}
                          onChange={(e) => setRegStudyProgram(e.target.value)}
                          placeholder="ex: PPG em Desenvolvimento Regional"
                          leftIcon={<BookOpen size={14} />}
                          disabled={submitting}
                        />
                      </FormGroup>

                      <FormGroup label="Área de Atuação / Linha de Pesquisa" htmlFor="reg-area">
                        <Input
                          id="reg-area"
                          value={regResearchArea}
                          onChange={(e) => setRegResearchArea(e.target.value)}
                          placeholder="ex: Políticas Públicas Territoriais, APLs"
                          disabled={submitting}
                        />
                      </FormGroup>
                    </div>

                    <div className="reg-section-title">2. Credenciais de Acesso</div>

                    <div className="reg-grid-3">
                      <FormGroup label="Nome de Usuário *" htmlFor="reg-user">
                        <Input
                          id="reg-user"
                          value={regUsername}
                          onChange={(e) => setRegUsername(e.target.value)}
                          placeholder="seu.usuario"
                          leftIcon={<User size={14} />}
                          disabled={submitting}
                          required
                        />
                      </FormGroup>

                      <FormGroup label="Senha (mín. 12 caracteres) *" htmlFor="reg-pass">
                        <Input
                          id="reg-pass"
                          type="password"
                          value={regPassword}
                          onChange={(e) => setRegPassword(e.target.value)}
                          placeholder="••••••••••••"
                          leftIcon={<KeyRound size={14} />}
                          disabled={submitting}
                          required
                        />
                      </FormGroup>

                      <FormGroup label="Confirmar Senha *" htmlFor="reg-pass-confirm">
                        <Input
                          id="reg-pass-confirm"
                          type="password"
                          value={regPasswordConfirm}
                          onChange={(e) => setRegPasswordConfirm(e.target.value)}
                          placeholder="••••••••••••"
                          leftIcon={<KeyRound size={14} />}
                          disabled={submitting}
                          required
                        />
                      </FormGroup>
                    </div>

                    <div className="reg-checkbox-group reg-terms-consent">
                      <label className="reg-checkbox-label">
                        <input
                          type="checkbox"
                          checked={regTermsAccepted}
                          onChange={(e) => setRegTermsAccepted(e.target.checked)}
                          disabled={submitting}
                          required
                        />
                        <span>
                          Concordo com os <strong>Termos de Uso</strong> e com a <strong>Política de Privacidade (LGPD)</strong> do Revsist.
                        </span>
                      </label>
                    </div>

                    <div className="reg-actions">
                      <Button
                        type="button"
                        variant="secondary"
                        size="md"
                        onClick={() => setInviteStep('validate')}
                        disabled={submitting}
                      >
                        Trocar Código
                      </Button>

                      <Button
                        type="submit"
                        variant="primary"
                        size="lg"
                        loading={submitting}
                        leftIcon={<UserPlus size={16} />}
                      >
                        {submitting ? 'Cadastrando…' : 'Concluir Cadastro e Iniciar'}
                      </Button>
                    </div>
                  </form>
                )}
              </>
            )}

            {/* ABA 3: PEDIDO DE CONVITE */}
            {activeTab === 'request' && (
              requestSent ? (
                <div className="request-sent-box" role="status">
                  <CheckCircle2 size={34} className="request-sent-icon" />
                  <h2 className="request-sent-title">Pedido enviado</h2>
                  <p className="request-sent-text">
                    Seu pedido chegou à coordenação do Revsist. A avaliação é manual,
                    e a resposta — com o código de convite, se aprovado — vai para{' '}
                    <strong>{reqEmail.trim().toLowerCase()}</strong>.
                  </p>
                  <p className="request-sent-text request-sent-text--muted">
                    Já tem um código em mãos? Use a aba <strong>Tenho um convite</strong> para concluir o cadastro.
                  </p>
                  <Button
                    type="button"
                    variant="secondary"
                    size="md"
                    onClick={() => {
                      setActiveTab('login')
                      setRequestSent(false)
                    }}
                  >
                    Voltar ao acesso
                  </Button>
                </div>
              ) : (
                <form className="login-form" onSubmit={handleRequestSubmit}>
                  <div className="invite-intro">
                    <p>
                      Ainda não tem um convite? Deixe seus dados abaixo. A coordenação
                      avalia cada pedido e envia o código de acesso por e-mail.
                    </p>
                  </div>

                  <FormGroup label="Nome Completo *" htmlFor="req-name">
                    <Input
                      id="req-name"
                      ref={reqNameRef}
                      value={reqName}
                      onChange={(e) => setReqName(e.target.value)}
                      placeholder="Maria Silva"
                      leftIcon={<User size={15} />}
                      disabled={sendingRequest}
                      autoComplete="name"
                      required
                    />
                  </FormGroup>

                  <div className="reg-grid-2">
                    <FormGroup label="E-mail *" htmlFor="req-email">
                      <Input
                        id="req-email"
                        type="email"
                        value={reqEmail}
                        onChange={(e) => setReqEmail(e.target.value)}
                        placeholder="pesquisador@universidade.edu.br"
                        leftIcon={<Mail size={15} />}
                        disabled={sendingRequest}
                        autoComplete="email"
                        required
                      />
                    </FormGroup>

                    <FormGroup label="Telefone / WhatsApp *" htmlFor="req-phone">
                      <Input
                        id="req-phone"
                        value={reqPhone}
                        onChange={(e) => setReqPhone(e.target.value)}
                        placeholder="(51) 99999-8888"
                        leftIcon={<Phone size={15} />}
                        disabled={sendingRequest}
                        autoComplete="tel"
                        required
                      />
                    </FormGroup>
                  </div>

                  <FormGroup label="Universidade / Instituição" htmlFor="req-inst">
                    <Input
                      id="req-inst"
                      value={reqInstitution}
                      onChange={(e) => setReqInstitution(e.target.value)}
                      placeholder="ex: UFRGS, USP, IBICT…"
                      leftIcon={<Building2 size={15} />}
                      disabled={sendingRequest}
                    />
                  </FormGroup>

                  <FormGroup label="Como você ficou sabendo do Revsist? *" htmlFor="req-source">
                    <div className="select-wrapper">
                      <MailQuestion size={14} className="select-left-icon" />
                      <select
                        id="req-source"
                        className="rsac-custom-select"
                        value={reqSource}
                        onChange={(e) => setReqSource(e.target.value)}
                        disabled={sendingRequest}
                        required
                      >
                        <option value="">Selecione…</option>
                        <option value="Indicação de orientador(a) ou colega">Indicação de orientador(a) ou colega</option>
                        <option value="Apresentação em aula, evento ou congresso">Apresentação em aula, evento ou congresso</option>
                        <option value="Programa de pós-graduação">Programa de pós-graduação</option>
                        <option value="Busca na internet">Busca na internet</option>
                        <option value="Redes sociais">Redes sociais</option>
                        <option value="Artigo ou publicação">Artigo ou publicação</option>
                        <option value="Outro">Outro</option>
                      </select>
                    </div>
                  </FormGroup>

                  <FormGroup label="Detalhe (opcional)" htmlFor="req-source-detail">
                    <Input
                      id="req-source-detail"
                      value={reqSourceDetail}
                      onChange={(e) => setReqSourceDetail(e.target.value)}
                      placeholder="ex: nome de quem indicou, evento, perfil…"
                      disabled={sendingRequest}
                    />
                  </FormGroup>

                  <p className="request-privacy-note">
                    Estes dados são usados apenas para avaliar e responder ao seu pedido de
                    acesso. Se o pedido for recusado, você pode solicitar a exclusão do
                    registro a qualquer momento.
                  </p>

                  <Button
                    type="submit"
                    variant="primary"
                    size="lg"
                    loading={sendingRequest}
                    leftIcon={<Send size={16} />}
                    className="login-submit"
                  >
                    {sendingRequest ? 'Enviando…' : 'Enviar Pedido de Convite'}
                  </Button>
                </form>
              )
            )}
          </>
        )}

        {status?.deployment_profile === 'server' && (
          <p className="login-footnote">
            Servidor publicado — convites de uso único garantem o acesso exclusivo a pesquisadores autorizados.
          </p>
        )}
      </div>
    </div>
  )
}
