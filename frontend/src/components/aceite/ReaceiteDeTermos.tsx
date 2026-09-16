/**
 * Revsist — Reaceite dos documentos quando a versão muda (doc 52 §8.0).
 *
 * O `AceiteDeTermos` guarda a resposta no navegador, o que basta para quem
 * ainda não tem conta. Para quem tem, o aceite que vale juridicamente é o que
 * fica gravado **na conta** (art. 8º, §2º) — e é ele que o servidor compara
 * antes de registrar qualquer dado de uso: quem não aceitou a versão vigente
 * não tem nada coletado, mesmo que o navegador diga que aceitou.
 *
 * Daí esta segunda porta, depois do login: ela compara a versão aceita pela
 * conta com a vigente e, quando diverge, pede o aceite outra vez dizendo o que
 * mudou. Recusar é possível — o botão "Agora não" deixa a pessoa usar a
 * plataforma —, e a consequência é apenas que nada de uso é registrado sobre
 * ela até que aceite.
 */

import { useState } from 'react'
import { api } from '@/api/client'
import { RsacLockup } from '@/components/brand/RsacLockup'
import { useAuthStore } from '@/stores/useAuthStore'
import { VERSAO_DOS_DOCUMENTOS } from './AceiteDeTermos'
import './AceiteDeTermos.css'

const URL_TERMOS = '/termos'
const URL_PRIVACIDADE = '/privacidade'

export function ReaceiteDeTermos({ children }: { children: React.ReactNode }): JSX.Element {
  const { user, status, refreshUser } = useAuthStore()
  const [adiado, setAdiado] = useState(false)
  const [marcado, setMarcado] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  const precisaAceitar =
    !!user && (user.terms_version || '') !== VERSAO_DOS_DOCUMENTOS && !adiado

  if (!precisaAceitar) return <>{children}</>

  const confirmar = async () => {
    if (!marcado) {
      setErro('Marque a caixa para continuar.')
      return
    }
    try {
      setEnviando(true)
      setErro(null)
      await api.aceitarTermos()
      await refreshUser()
    } catch (err: any) {
      setErro(err?.message || 'Não foi possível registrar o aceite. Tente de novo.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="aceite-page">
      <div className="aceite-card" role="dialog" aria-modal="true" aria-labelledby="reaceite-titulo">
        <div className="aceite-marca">
          <RsacLockup size="md" />
        </div>

        <h1 className="aceite-titulo" id="reaceite-titulo">
          Atualizamos os documentos
        </h1>

        <p className="aceite-texto">
          O Aviso de Privacidade e os Termos de Uso mudaram em 15 de setembro de 2026. O que mudou:
          durante o beta, <strong>registramos no nosso próprio servidor como a plataforma é usada</strong>
          {' '}— telas, ações, erros e consumo de IA —, nunca o conteúdo da sua pesquisa. O beta tem
          prazo: termina em 12 de setembro de 2027.
        </p>

        <p className="aceite-texto">
          Você pode desligar o registro de uso em <strong>Configurações → Privacidade e dados de
          uso</strong>, e apagar o que já foi registrado, sem perder nenhum recurso.
        </p>

        {status?.deployment_profile !== 'server' && (
          <p className="aceite-texto">
            <strong>Nesta instalação, nada disso é registrado:</strong> o Revsist de mesa roda na sua
            máquina e não envia dados de uso para lugar nenhum. O texto acima descreve o serviço
            publicado, e você está aceitando os mesmos documentos.
          </p>
        )}

        <label className="aceite-marcacao">
          <input
            type="checkbox"
            checked={marcado}
            onChange={(e) => {
              setMarcado(e.target.checked)
              setErro(null)
            }}
          />
          <span>
            Li e aceito os{' '}
            <a href={URL_TERMOS} target="_blank" rel="noopener noreferrer">
              Termos de Uso
            </a>{' '}
            e a{' '}
            <a href={URL_PRIVACIDADE} target="_blank" rel="noopener noreferrer">
              Política de Privacidade
            </a>{' '}
            na versão vigente.
          </span>
        </label>

        {erro && (
          <p className="aceite-erro" role="alert">
            {erro}
          </p>
        )}

        <button type="button" className="aceite-botao" onClick={confirmar} disabled={enviando}>
          {enviando ? 'Registrando…' : 'Aceitar e continuar'}
        </button>

        <button type="button" className="aceite-adiar" onClick={() => setAdiado(true)}>
          Agora não
        </button>

        <p className="aceite-rodape">
          Enquanto você não aceitar, nada de uso é registrado sobre a sua conta. Os dois documentos
          abrem em outra aba.
        </p>
      </div>
    </div>
  )
}
