/**
 * Revsist — Boas-vindas do primeiro acesso.
 *
 * Substitui o Modo Trilho, e a diferença é de natureza, não de tamanho. O
 * trilho era um tutor que ficava junto durante o trabalho inteiro, conduzindo
 * de nó em nó por um grafo metodológico; isto é a apresentação que todo
 * aplicativo faz uma vez: o que a ferramenta é, qual o caminho, por onde
 * começar. Depois ela sai do caminho e o pesquisador trabalha.
 *
 * Três telas, e não sete: o que passa de três a pessoa não lê, fecha. O que
 * precisa mesmo ser aprendido se aprende usando, e cada etapa tem a própria
 * ajuda na tela em que acontece.
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  CheckSquare,
  Download,
  FileDown,
  FileText,
  FolderPlus,
  ShieldCheck,
  Sparkles,
  X,
} from 'lucide-react'
import { Button } from '@/components/ui'
import { RsacLockup } from '@/components/brand/RsacLockup'
import { useAuthStore } from '@/stores/useAuthStore'
import { useBoasVindasStore } from '@/stores/useBoasVindasStore'
import './BoasVindas.css'

/** As seis etapas, na ordem em que aparecem na barra superior. */
const ETAPAS = [
  {
    n: 1,
    nome: 'Protocolo',
    icone: <BookOpen size={15} />,
    texto: 'A pergunta, os critérios e onde buscar — escritos antes de começar.',
  },
  {
    n: 2,
    nome: 'Coleta',
    icone: <Download size={15} />,
    texto: 'Busca simultânea em BDTD, SciELO, OpenAlex, Scopus e PubMed.',
  },
  {
    n: 3,
    nome: 'Triagem',
    icone: <CheckSquare size={15} />,
    texto: 'Incluir ou excluir, com o motivo de cada decisão registrado.',
  },
  {
    n: 4,
    nome: 'Extração',
    icone: <FileText size={15} />,
    texto: 'Os dados de cada estudo incluído, na mesma matriz.',
  },
  {
    n: 5,
    nome: 'Indicadores',
    icone: <BarChart3 size={15} />,
    texto: 'O que o conjunto mostra: autores, temas, lacunas.',
  },
  {
    n: 6,
    nome: 'Síntese',
    icone: <FileDown size={15} />,
    texto: 'Diagrama PRISMA e exportação do material pronto.',
  },
]

const TOTAL_PASSOS = 3

export function BoasVindas(): JSX.Element | null {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const { aberta, fechar, abrirSePrimeiraVez, marcarComoVista } = useBoasVindasStore()
  const [passo, setPasso] = useState(0)

  const username = user?.username || ''

  // Definidas antes dos efeitos que as usam. Deixá-las embaixo do
  // `if (!aberta) return null` faria o efeito do Esc fechar sobre uma
  // constante que, nas renderizações em que a janela está fechada, nunca
  // chega a ser inicializada — funciona hoje porque o efeito desiste antes,
  // e quebraria no dia em que essa guarda saísse.
  const encerrar = () => {
    marcarComoVista(username)
    fechar()
  }

  const concluir = () => {
    encerrar()
    navigate('/projects')
  }

  // Primeira vez desta conta neste navegador.
  useEffect(() => {
    if (username) abrirSePrimeiraVez(username)
  }, [username])

  // Reabrir sempre recomeça do primeiro passo: retomar no passo 3 de uma
  // apresentação que a pessoa pediu para rever seria responder outra pergunta.
  useEffect(() => {
    if (aberta) setPasso(0)
  }, [aberta])

  // Fechar com Esc é o que se espera de qualquer janela sobreposta, e aqui
  // não há nada a confirmar: a apresentação não é um passo obrigatório.
  useEffect(() => {
    if (!aberta) return
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key === 'Escape') encerrar()
    }
    window.addEventListener('keydown', aoTeclar)
    return () => window.removeEventListener('keydown', aoTeclar)
  }, [aberta])

  if (!aberta) return null

  const primeiroNome = (user?.full_name || username || '').trim().split(/\s+/)[0] || ''

  return (
    <div
      className="bv-veu"
      role="dialog"
      aria-modal="true"
      aria-labelledby="bv-titulo"
      onClick={(e) => {
        if (e.target === e.currentTarget) encerrar()
      }}
    >
      <div className="bv-janela">
        <button
          type="button"
          className="bv-fechar"
          onClick={encerrar}
          aria-label="Fechar as boas-vindas"
        >
          <X size={16} />
        </button>

        {/* ── 1. Quem somos ─────────────────────────────────────────── */}
        {passo === 0 && (
          <div className="bv-passo">
            <div className="bv-marca">
              <RsacLockup size="md" />
            </div>
            <h2 id="bv-titulo" className="bv-titulo">
              {primeiroNome ? `Bem-vindo, ${primeiroNome}.` : 'Bem-vindo ao Revsist.'}
            </h2>
            <p className="bv-texto">
              Este é o ambiente onde você conduz uma revisão sistemática do começo
              ao fim — da pergunta ao diagrama PRISMA — sem planilha paralela e
              sem perder o registro de como cada decisão foi tomada.
            </p>
            <div className="bv-destaques">
              <div className="bv-destaque">
                <ShieldCheck size={16} aria-hidden="true" />
                <span>
                  <strong>Tudo fica registrado.</strong> Cada inclusão e exclusão
                  guarda o motivo e a data, prontos para a auditoria do método.
                </span>
              </div>
              <div className="bv-destaque">
                <Sparkles size={16} aria-hidden="true" />
                <span>
                  <strong>A assistência é opcional.</strong> Você pode trabalhar
                  em modo 100% manual; quando ativa, ela sugere e você decide.
                </span>
              </div>
            </div>
          </div>
        )}

        {/* ── 2. O caminho ──────────────────────────────────────────── */}
        {passo === 1 && (
          <div className="bv-passo">
            <h2 id="bv-titulo" className="bv-titulo">
              O caminho tem seis etapas
            </h2>
            <p className="bv-texto">
              Elas estão na barra do topo, numeradas e na ordem. Dá para voltar a
              qualquer uma quando quiser — a numeração é o caminho recomendado,
              não uma trava.
            </p>
            <ol className="bv-etapas">
              {ETAPAS.map((e) => (
                <li key={e.n} className="bv-etapa">
                  <span className="bv-etapa-n">{e.n}</span>
                  <span className="bv-etapa-icone" aria-hidden="true">
                    {e.icone}
                  </span>
                  <span className="bv-etapa-corpo">
                    <strong>{e.nome}</strong>
                    <span>{e.texto}</span>
                  </span>
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* ── 3. Por onde começar ───────────────────────────────────── */}
        {passo === 2 && (
          <div className="bv-passo">
            <div className="bv-icone-grande" aria-hidden="true">
              <FolderPlus size={38} />
            </div>
            <h2 id="bv-titulo" className="bv-titulo">
              Comece criando um projeto
            </h2>
            <p className="bv-texto">
              Um projeto guarda o protocolo, o acervo coletado e as decisões de
              triagem de uma revisão. Tudo o que você fizer daqui em diante fica
              dentro dele.
            </p>
            <p className="bv-texto bv-texto--secundario">
              Se em algum momento quiser rever esta apresentação, ela está no
              botão <strong>Guia rápido</strong>, na barra do topo.
            </p>
          </div>
        )}

        {/* ── Rodapé ────────────────────────────────────────────────── */}
        <div className="bv-rodape">
          <div className="bv-marcadores" aria-hidden="true">
            {Array.from({ length: TOTAL_PASSOS }, (_, i) => (
              <span
                key={i}
                className={`bv-marcador ${i === passo ? 'bv-marcador--ativo' : ''}`}
              />
            ))}
          </div>

          <div className="bv-acoes">
            {passo > 0 && (
              <Button variant="ghost" size="sm" onClick={() => setPasso(passo - 1)}>
                Voltar
              </Button>
            )}

            {passo < TOTAL_PASSOS - 1 ? (
              <>
                <button type="button" className="bv-pular" onClick={encerrar}>
                  Pular
                </button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => setPasso(passo + 1)}
                  rightIcon={<ArrowRight size={14} />}
                >
                  Continuar
                </Button>
              </>
            ) : (
              <Button
                variant="primary"
                size="sm"
                onClick={concluir}
                rightIcon={<ArrowRight size={14} />}
              >
                Criar meu primeiro projeto
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
