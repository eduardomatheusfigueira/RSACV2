/**
 * Revsist — Aceite de termos e aviso de cookies, na aplicação.
 *
 * O par do `landing/src/scripts/aceite.js`, e de propósito: a chave de
 * armazenamento e a versão são as mesmas, e a landing e o `/app` moram na
 * mesma origem. Quem aceitou em `revsist.com` chega em `revsist.com/app` sem
 * ser perguntado de novo — que é como qualquer site se comporta, e o
 * contrário do que aconteceria se cada metade guardasse a sua própria
 * resposta.
 *
 * Nada da aplicação é montado enquanto o aceite não vem. É por isso que este
 * componente envolve o resto em vez de flutuar sobre ele: um véu por cima
 * ainda deixaria o `AuthGate` conversar com o backend e a sessão ser
 * restaurada por baixo, o que faria do bloqueio uma cortina, não uma porta.
 */

import { useState } from 'react'
import { RsacLockup } from '@/components/brand/RsacLockup'
import './AceiteDeTermos.css'

/** Mesma chave do script da landing. Mudar uma sem a outra separa os dois lados. */
const CHAVE = 'rsac_aceite_termos'

/** Espelha `terms_version` em `backend/app/config.py`. */
const VERSAO = '2026-09'

/** Endereços dos documentos na landing, servidos pela mesma origem. */
const URL_TERMOS = '/termos'
const URL_PRIVACIDADE = '/privacidade'

export function jaAceitou(): boolean {
  try {
    const bruto = localStorage.getItem(CHAVE)
    if (!bruto) return false
    return JSON.parse(bruto).versao === VERSAO
  } catch {
    // Armazenamento indisponível (janela anônima restrita, política de TI).
    // Perguntar a cada carregamento, sem poder guardar a resposta, seria um
    // laço sem saída — e o aceite que vale juridicamente é o do cadastro,
    // que fica registrado na conta.
    return true
  }
}

function registrar(): void {
  try {
    localStorage.setItem(
      CHAVE,
      JSON.stringify({ versao: VERSAO, em: new Date().toISOString() })
    )
  } catch {
    /* Sem armazenamento: vale para esta visita. */
  }
}

export function AceiteDeTermos({ children }: { children: React.ReactNode }): JSX.Element {
  const [aceito, setAceito] = useState(() => jaAceitou())
  const [marcado, setMarcado] = useState(false)

  if (aceito) return <>{children}</>

  const confirmar = () => {
    if (!marcado) return
    registrar()
    setAceito(true)
  }

  return (
    <div className="aceite-page">
      <div
        className="aceite-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="aceite-titulo"
      >
        <div className="aceite-marca">
          <RsacLockup size="md" />
        </div>

        <h1 className="aceite-titulo" id="aceite-titulo">
          Antes de começar
        </h1>

        <p className="aceite-texto">
          O Revsist usa <strong>um único cookie</strong>, técnico, que serve para
          manter você conectado depois do login. Não há rastreador, anúncio, pixel
          de telemetria nem métrica de terceiros — nada que siga você por outros
          sites.
        </p>

        <label className="aceite-marcacao">
          <input
            type="checkbox"
            checked={marcado}
            onChange={(e) => setMarcado(e.target.checked)}
          />
          <span>
            Li e aceito os{' '}
            <a href={URL_TERMOS} target="_blank" rel="noopener noreferrer">
              Termos de Uso
            </a>{' '}
            e a{' '}
            <a href={URL_PRIVACIDADE} target="_blank" rel="noopener noreferrer">
              Política de Privacidade
            </a>
            .
          </span>
        </label>

        <button
          type="button"
          className="aceite-botao"
          onClick={confirmar}
          disabled={!marcado}
        >
          Aceitar e entrar
        </button>

        <p className="aceite-rodape">
          Os dois documentos abrem em outra aba, sem precisar aceitar antes.
        </p>
      </div>
    </div>
  )
}
