/**
 * RSAC V2 — Splash de inicialização
 *
 * A camada de marca vive no `index.html` para aparecer antes de o React
 * montar. A Content-Security-Policy proíbe script inline, então quem a
 * comanda daqui em diante é este módulo.
 *
 * A regra de ouro é *quando* dispensá-la: antes, o `main.tsx` a removia no
 * primeiro quadro após a montagem, o que trocava a marca por uma tela em
 * branco enquanto a aplicação ainda procurava o backend e resolvia a sessão.
 * A splash agora sai quando há interface de verdade para pôr no lugar.
 */

const ID_DA_SPLASH = 'boot-splash'
const ID_DO_STATUS = 'boot-status-text'

let dispensada = false

/** Troca a linha de estado da splash ("Iniciando o servidor local…"). */
export function atualizarStatusDoSplash(texto: string): void {
  if (dispensada) return
  const alvo = document.getElementById(ID_DO_STATUS)
  if (alvo) alvo.textContent = texto
}

/** Remove a splash com uma esmaecida curta. Idempotente. */
export function dispensarBootSplash(): void {
  if (dispensada) return
  dispensada = true

  const splash = document.getElementById(ID_DA_SPLASH)
  if (!splash) return

  requestAnimationFrame(() => {
    splash.classList.add('is-leaving')
    splash.addEventListener('transitionend', () => splash.remove(), { once: true })
    // Rede de segurança caso a transição não dispare (ex.: prefers-reduced-motion).
    window.setTimeout(() => splash.remove(), 600)
  })
}
