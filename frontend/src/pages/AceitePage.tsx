/**
 * Revsist — Ciência do aviso do BETA (doc 43 §43.10).
 *
 * Fica entre a autenticação e o resto da aplicação. Sem ela, a trava do
 * `require_aceite` devolveria 451 em toda rota útil e a pessoa veria apenas
 * uma tela quebrada, sem saber o que fazer.
 *
 * Duas decisões de desenho que não são estéticas:
 *
 * 1. **O botão só habilita depois de o texto ser rolado até o fim.** Não é
 *    para atrapalhar: é para que "li" tenha alguma chance de ser verdade. Um
 *    aviso que ninguém leu não informa ninguém, e um aceite que ninguém leu
 *    não vale grande coisa se for questionado.
 * 2. **A caixa começa desmarcada e não há "aceitar tudo".** O art. 8º §4º da
 *    LGPD anula autorização genérica; marcar por padrão seria pior ainda.
 */

import { useEffect, useRef, useState } from 'react'
import { AlertTriangle, Check, LogOut } from 'lucide-react'

import { api } from '@/api/client'
import { useAuthStore } from '@/stores/useAuthStore'
import { Button } from '@/components/ui'
import type { AceiteVigente } from '@/types/api'
import { analisarAviso, fatiarEnfase } from './avisoMarkdown'
import './AceitePage.css'

/**
 * Desenha o aviso a partir dos blocos que `avisoMarkdown` reconhece.
 *
 * A análise vive separada e testada (`avisoMarkdown.test.ts`): é lá que os
 * defeitos moram, e função pura se testa sem montar componente.
 */
function TextoDoAviso({ markdown }: { markdown: string }): JSX.Element {
  const enfatizar = (texto: string) =>
    fatiarEnfase(texto).map((p, i) =>
      p.forte ? <strong key={i}>{p.texto}</strong> : <span key={i}>{p.texto}</span>
    )

  return (
    <>
      {analisarAviso(markdown).map((bloco, i) => {
        if (bloco.tipo === 'titulo') return <h2 key={i}>{bloco.texto}</h2>
        if (bloco.tipo === 'lista') {
          return (
            <ul key={i}>
              {bloco.itens.map((item, j) => <li key={j}>{enfatizar(item)}</li>)}
            </ul>
          )
        }
        return <p key={i}>{enfatizar(bloco.texto)}</p>
      })}
    </>
  )
}

export function AceitePage({ onAceito }: { onAceito: () => void }): JSX.Element {
  const { logout, user } = useAuthStore()
  const [aviso, setAviso] = useState<AceiteVigente | null>(null)
  const [marcado, setMarcado] = useState(false)
  const [leuAteOFim, setLeuAteOFim] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const rolagem = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api
      .getAceite()
      .then(setAviso)
      .catch(() => setErro('Não foi possível carregar o aviso. Recarregue a página.'))
  }, [])

  // Se o texto couber inteiro na tela, não há rolagem a fazer — e exigi-la
  // deixaria o botão travado para sempre.
  useEffect(() => {
    const el = rolagem.current
    if (!el || !aviso) return
    if (el.scrollHeight <= el.clientHeight + 4) setLeuAteOFim(true)
  }, [aviso])

  const aoRolar = () => {
    const el = rolagem.current
    if (!el) return
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 24) setLeuAteOFim(true)
  }

  const confirmar = async () => {
    if (!aviso) return
    setEnviando(true)
    setErro(null)
    try {
      await api.registrarAceite(aviso.versao)
      onAceito()
    } catch (e: any) {
      setErro(e?.message || 'Não foi possível registrar. Tente de novo.')
      setEnviando(false)
    }
  }

  if (!aviso) {
    return (
      <div className="aceite-pagina">
        <div className="aceite-cartao aceite-cartao--vazio">
          {erro ?? 'Carregando o aviso…'}
        </div>
      </div>
    )
  }

  return (
    <div className="aceite-pagina">
      <div className="aceite-cartao">
        <header className="aceite-topo">
          <div className="aceite-selo"><AlertTriangle size={18} /></div>
          <div>
            <h1>{aviso.titulo}</h1>
            <p className="aceite-versao">
              Versão {aviso.versao}
              {user?.username ? ` · entrando como ${user.username}` : ''}
            </p>
          </div>
        </header>

        <div className="aceite-texto" ref={rolagem} onScroll={aoRolar} tabIndex={0}>
          <TextoDoAviso markdown={aviso.texto} />
        </div>

        {!leuAteOFim && (
          <p className="aceite-dica">Role o texto até o fim para poder continuar.</p>
        )}

        <label className={`aceite-caixa ${leuAteOFim ? '' : 'aceite-caixa--travada'}`}>
          <input
            type="checkbox"
            checked={marcado}
            disabled={!leuAteOFim}
            onChange={(e) => setMarcado(e.target.checked)}
          />
          <span>{aviso.rotulo_da_caixa}</span>
        </label>

        {erro && <div className="aceite-erro" role="alert">{erro}</div>}

        <div className="aceite-acoes">
          <button type="button" className="aceite-sair" onClick={() => void logout()}>
            <LogOut size={14} /> Sair sem aceitar
          </button>
          <Button onClick={() => void confirmar()} disabled={!marcado || enviando}>
            <Check size={15} /> {enviando ? 'Registrando…' : 'Confirmar e continuar'}
          </Button>
        </div>
      </div>
    </div>
  )
}
