/**
 * Revsist — Aceite de termos e aviso de cookies.
 *
 * A porta de entrada do site: ninguém vê a página antes de aceitar os Termos
 * e a Política de Privacidade.
 *
 * O texto diz o que é verdade, e isso é o ponto. O Revsist não tem Google
 * Analytics, pixel, nem métrica de TERCEIRO; o único cookie é o `rsac_session`,
 * técnico, criado apenas depois do login. O que existe é o registro de uso do
 * beta, de primeira parte, que o próprio texto do aceite anuncia desde a
 * versão 2026-09.2 — e que a pessoa desliga em Configurações. Um banner com
 * "aceitar todos" e
 * "recusar" prometeria uma escolha que não existe — e escolha falsa é
 * justamente o que a ANPD trata como prática enganosa. Aqui o aviso informa o
 * que há, e o aceite é dos documentos, que é o que de fato precisa de aceite.
 *
 * Duas páginas nunca são bloqueadas: `/termos` e `/privacidade`. Exigir que
 * alguém aceite documentos que a própria tela impede de ler seria pedir
 * assinatura em papel fechado.
 */

/** Chave compartilhada com a aplicação React — mesma origem, mesmo aceite. */
const CHAVE = 'rsac_aceite_termos';

/**
 * Versão vigente dos documentos. Espelha `terms_version` em
 * `backend/app/config.py`: quando os Termos mudam de verdade, este número
 * muda junto e o aceite é pedido de novo, porque o que foi aceito era outro
 * texto.
 */
const VERSAO = '2026-09.2';

/** Caminhos que precisam continuar legíveis sem aceite. */
const LIVRES = ['/termos', '/privacidade'];

export function jaAceitou() {
  try {
    const bruto = localStorage.getItem(CHAVE);
    if (!bruto) return false;
    return JSON.parse(bruto).versao === VERSAO;
  } catch {
    // Navegador com armazenamento bloqueado (janela anônima restrita, política
    // corporativa). Sem onde guardar a resposta, perguntar a cada carregamento
    // seria hostil e inútil — o aceite é registrado na conta, no cadastro.
    return true;
  }
}

function registrarAceite() {
  try {
    localStorage.setItem(
      CHAVE,
      JSON.stringify({ versao: VERSAO, em: new Date().toISOString() })
    );
  } catch {
    /* Sem armazenamento: o aceite vale para esta visita. */
  }
}

function ehPaginaLivre() {
  const caminho = window.location.pathname.replace(/\/+$/, '') || '/';
  return LIVRES.some((livre) => caminho === livre || caminho.startsWith(livre + '/'));
}

function montarJanela() {
  const veu = document.createElement('div');
  veu.className = 'aceite-veu';
  veu.setAttribute('role', 'dialog');
  veu.setAttribute('aria-modal', 'true');
  veu.setAttribute('aria-labelledby', 'aceite-titulo');

  veu.innerHTML = `
    <div class="aceite-janela">
      <svg class="aceite-marca" viewBox="0 0 80 100" width="34" height="42" aria-hidden="true">
        <g fill="none" stroke-width="14" stroke-linecap="round" stroke-linejoin="round">
          <path d="M 7 7 V 93" stroke="var(--dusk-blue, #274c77)" />
          <circle cx="32" cy="32" r="25" stroke="var(--dusk-blue, #274c77)" />
          <path d="M 45.946 52.749 L 73 93" stroke="var(--steel-blue, #6096ba)" />
        </g>
      </svg>

      <h2 class="aceite-titulo" id="aceite-titulo">Antes de começar</h2>

      <p class="aceite-texto">
        O Revsist usa <strong>um único cookie</strong>, técnico, que serve para
        manter você conectado depois do login. Não há anúncio, nem rastreador ou
        pixel de terceiros — nada que siga você por outros sites.
      </p>

      <p class="aceite-texto">
        <strong>Durante o beta, registramos no nosso próprio servidor como a
        plataforma é usada</strong> — telas, ações, erros e consumo de IA —,
        nunca o conteúdo da sua pesquisa. Você pode desligar isso em
        Configurações. O detalhe está no
        <a href="/privacidade#uso-beta">Aviso de Privacidade</a>.
      </p>

      <label class="aceite-marcacao">
        <input type="checkbox" id="aceite-caixa" />
        <span>
          Li e aceito os <a href="/termos">Termos de Uso</a> e a
          <a href="/privacidade">Política de Privacidade</a>.
        </span>
      </label>

      <button type="button" class="aceite-botao" id="aceite-botao" disabled>
        Aceitar e entrar
      </button>

      <p class="aceite-rodape">
        Você pode ler os dois documentos agora: eles abrem sem precisar aceitar.
      </p>
    </div>
  `;

  const caixa = veu.querySelector('#aceite-caixa');
  const botao = veu.querySelector('#aceite-botao');

  caixa.addEventListener('change', () => {
    botao.disabled = !caixa.checked;
  });

  botao.addEventListener('click', () => {
    if (!caixa.checked) return;
    registrarAceite();
    document.documentElement.removeAttribute('data-aceite');
    veu.remove();
  });

  // O foco entra na caixa de marcação: é o primeiro comando da janela, e quem
  // navega por teclado não deveria ter de tabular até achá-la.
  requestAnimationFrame(() => caixa.focus());

  // Enquanto o aceite não vem, o Tab não sai da janela. Sem isso o foco
  // passeia pela página bloqueada por baixo do véu, que é invisível ao mouse
  // mas não ao teclado.
  veu.addEventListener('keydown', (e) => {
    if (e.key !== 'Tab') return;
    const focaveis = veu.querySelectorAll('a[href], button:not([disabled]), input');
    if (!focaveis.length) return;
    const primeiro = focaveis[0];
    const ultimo = focaveis[focaveis.length - 1];
    if (e.shiftKey && document.activeElement === primeiro) {
      e.preventDefault();
      ultimo.focus();
    } else if (!e.shiftKey && document.activeElement === ultimo) {
      e.preventDefault();
      primeiro.focus();
    }
  });

  return veu;
}

export function instalarAceite() {
  if (ehPaginaLivre() || jaAceitou()) {
    document.documentElement.removeAttribute('data-aceite');
    return;
  }
  document.documentElement.setAttribute('data-aceite', 'pendente');
  document.body.appendChild(montarJanela());
}
