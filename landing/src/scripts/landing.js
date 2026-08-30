/**
 * Revsist — Script da landing page.
 *
 * Quatro tarefas, todas opcionais: a página é inteira legível e navegável com
 * o JavaScript desligado (doc 41, item 5.14).
 *
 *   1. Alternador de tema claro / escuro, com a escolha guardada no navegador.
 *   2. Menu de seções em tela estreita.
 *   3. Marcação da seção corrente na navegação.
 *   4. Ajuste dos botões de acesso ao que a instalação realmente oferece.
 *
 * A tarefa 4 é a única que fala com a rede, e só com a própria origem:
 * `GET /api/v1/auth/status` diz se a entrada com Google está configurada e se
 * quem está lendo já tem sessão aberta. Sem essa consulta — página servida
 * fora do backend, rede fora do ar, requisição barrada — os botões ficam como
 * estão no HTML, apontando para `/app`, que funciona em qualquer instalação.
 */

(function () {
  'use strict';

  var root = document.documentElement;
  // A landing page opera exclusivamente no tema institucional claro (Platinum & Dusk Blue)
  root.removeAttribute('data-theme');

  // ── 1. Menu de seções em tela estreita ─────────────────────────────────
  var navToggleBtn = document.getElementById('nav-toggle-btn');
  var navLinks = document.getElementById('nav-links');

  function fecharMenu() {
    if (!navLinks || !navToggleBtn) return;
    navLinks.classList.remove('is-open');
    navToggleBtn.setAttribute('aria-expanded', 'false');
    navToggleBtn.setAttribute('aria-label', 'Abrir menu de seções');
  }

  if (navToggleBtn && navLinks) {
    navToggleBtn.addEventListener('click', function () {
      var aberto = navLinks.classList.toggle('is-open');
      navToggleBtn.setAttribute('aria-expanded', aberto ? 'true' : 'false');
      navToggleBtn.setAttribute('aria-label', aberto ? 'Fechar menu de seções' : 'Abrir menu de seções');
    });

    // Ir para uma seção fecha o menu — senão o painel cobre o destino.
    navLinks.addEventListener('click', function (evento) {
      if (evento.target.closest('a')) fecharMenu();
    });

    document.addEventListener('keydown', function (evento) {
      if (evento.key === 'Escape' && navLinks.classList.contains('is-open')) {
        fecharMenu();
        navToggleBtn.focus();
      }
    });

    document.addEventListener('click', function (evento) {
      if (!navLinks.classList.contains('is-open')) return;
      if (navLinks.contains(evento.target) || navToggleBtn.contains(evento.target)) return;
      fecharMenu();
    });
  }

  // ── 3. Revelação ao rolar e seção corrente ─────────────────────────────
  var movimentoReduzido = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var reveladores = document.querySelectorAll('.reveal-on-scroll');

  function revelarTudo() {
    reveladores.forEach(function (el) {
      el.classList.add('is-visible');
    });
  }

  if (!movimentoReduzido && 'IntersectionObserver' in window) {
    var observador = new IntersectionObserver(
      function (entradas, obs) {
        entradas.forEach(function (entrada) {
          if (entrada.isIntersecting) {
            entrada.target.classList.add('is-visible');
            obs.unobserve(entrada.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
    );
    reveladores.forEach(function (el) {
      observador.observe(el);
    });

    // Rede de segurança. O estado inicial de `.reveal-on-scroll` é
    // `opacity: 0`, e quem o desfaz é o observador — que só roda quando o
    // navegador está desenhando. Numa aba de fundo, num renderizador
    // estrangulado ou num rastreador que não compõe quadros, o texto ficaria
    // invisível. Passados dois segundos, a animação deixa de valer a pena e o
    // conteúdo aparece de qualquer jeito: nada aqui pode depender dela.
    window.setTimeout(revelarTudo, 2000);
  } else {
    // Movimento reduzido, ou navegador sem o observador: mostra tudo de uma vez.
    revelarTudo();
  }

  if ('IntersectionObserver' in window) {
    var linksPorId = {};
    var alvos = [];

    document.querySelectorAll('.nav-link[href^="#"]').forEach(function (link) {
      var id = link.getAttribute('href').slice(1);
      var secao = document.getElementById(id);
      if (!secao) return;
      linksPorId[id] = link;
      alvos.push(secao);
    });

    if (alvos.length) {
      var visiveis = new Set();

      var marcador = new IntersectionObserver(
        function (entradas) {
          entradas.forEach(function (entrada) {
            if (entrada.isIntersecting) visiveis.add(entrada.target.id);
            else visiveis.delete(entrada.target.id);
          });

          // A seção corrente é a primeira visível na ordem do documento, e não
          // a última a disparar o evento: com duas na tela, a de cima manda.
          var corrente = null;
          for (var i = 0; i < alvos.length; i += 1) {
            if (visiveis.has(alvos[i].id)) {
              corrente = alvos[i].id;
              break;
            }
          }

          Object.keys(linksPorId).forEach(function (id) {
            if (id === corrente) linksPorId[id].setAttribute('aria-current', 'true');
            else linksPorId[id].removeAttribute('aria-current');
          });
        },
        { rootMargin: '-72px 0px -55% 0px', threshold: 0 }
      );

      alvos.forEach(function (secao) {
        marcador.observe(secao);
      });
    }
  }

  // ── 4. Ajustar os botões de acesso ao que a instalação oferece ─────────
  //
  // O HTML entregue aponta para `/app`, que serve em qualquer caso: a tela de
  // entrada do app oferece senha e código de convite, e o botão do Google
  // quando ele existe. O que a consulta abaixo acrescenta é o atalho — mandar
  // direto ao Google quando ele está configurado, e trocar "Entrar" por
  // "Abrir meus projetos" para quem já tem sessão. Nada disso é necessário
  // para usar a página; por isso qualquer falha é silenciosa.
  var protocoloServido = window.location.protocol === 'http:' || window.location.protocol === 'https:';
  if (!protocoloServido || typeof fetch !== 'function') return;

  function definirCta(elemento, texto, destino) {
    if (!elemento) return;
    elemento.textContent = texto;
    elemento.setAttribute('href', destino);
  }

  fetch('/api/v1/auth/status', {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  })
    .then(function (resposta) {
      if (!resposta.ok) throw new Error('status indisponível');
      return resposta.json();
    })
    .then(function (estado) {
      var ctaCabecalho = document.getElementById('cta-header');
      var ctaHero = document.getElementById('cta-hero');
      var ctaLgpd = document.getElementById('cta-lgpd');
      var nota = document.getElementById('cta-hero-note');

      if (estado.authenticated) {
        definirCta(ctaCabecalho, 'Meus projetos', '/app');
        definirCta(ctaHero, 'Abrir meus projetos', '/app');
        definirCta(ctaLgpd, 'Abrir meus projetos', '/app');
        if (nota) {
          nota.textContent =
            'Você já está com sessão aberta' +
            (estado.user && estado.user.username ? ' como ' + estado.user.username : '') +
            '.';
        }
        return;
      }

      if (estado.google_login_enabled) {
        var google = '/api/v1/auth/google/start';
        definirCta(ctaCabecalho, 'Entrar com Google', google);
        definirCta(ctaHero, 'Entrar com Google', google);
        definirCta(ctaLgpd, 'Entrar com Google', google);
        if (nota) {
          nota.textContent =
            'Entre com sua conta Google, ou use um código de convite na tela de acesso. ' +
            'Nenhum cartão, nenhum plano pago.';
        }
      } else if (nota) {
        // Sem Google configurado, prometer o botão dele seria mandar o
        // visitante a um 503.
        nota.textContent =
          'Acesso por usuário e senha ou por código de convite. Nenhum cartão, nenhum plano pago.';
      }
    })
    .catch(function () {
      /* Página servida fora do backend, ou backend fora do ar: fica como está. */
    });

  // Versão real do servidor no rodapé, quando houver um respondendo.
  fetch('/health', { headers: { Accept: 'application/json' } })
    .then(function (resposta) {
      if (!resposta.ok) throw new Error('sem health');
      return resposta.json();
    })
    .then(function (saude) {
      var rodape = document.getElementById('footer-version');
      if (rodape && saude && saude.version) {
        rodape.textContent = 'Versão ' + saude.version + ' · BETA';
      }
    })
    .catch(function () {
      /* mantém a versão escrita no HTML */
    });
})();
