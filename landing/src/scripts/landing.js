/**
 * Revsist — Comportamento do site público.
 *
 * Sete módulos pequenos, sem dependências e sem manipuladores inline:
 *   1. Menu de navegação em telas estreitas.
 *   2. Abas das seis etapas metodológicas.
 *   3. Alternador entre captura real e rastro técnico, por etapa.
 *   4. Ampliação de capturas de tela.
 *   5. Acordeão das perguntas frequentes.
 *   6. Laços de vídeo: tocam ao entrar na tela, param ao sair, e param de
 *      vez quando o visitante pede — ou quando o sistema pede menos movimento.
 *   7. Blocos do "Por que existe": entram ao aparecer na tela.
 *
 * Tudo é progressivo: sem JavaScript a primeira etapa continua visível, as
 * capturas continuam legíveis, as respostas do FAQ ficam no HTML e os vídeos
 * continuam com os seus pôsteres.
 */

import { instalarAceite } from './aceite.js';

// Antes de qualquer comportamento da página: se o aceite não veio, é ele que
// aparece. Os módulos abaixo seguem instalados de todo jeito — quando o véu
// sair, a página já está pronta por baixo.
instalarAceite();

(function () {
  'use strict';

  var pt = function (sel, raiz) {
    return (raiz || document).querySelector(sel);
  };
  var pts = function (sel, raiz) {
    return Array.prototype.slice.call((raiz || document).querySelectorAll(sel));
  };

  /* ── 1. Menu de navegação ───────────────────────────────────────────── */

  var botaoMenu = pt('#nav-toggle');
  var menu = pt('#main-nav');

  if (botaoMenu && menu) {
    botaoMenu.addEventListener('click', function () {
      var aberto = menu.classList.toggle('aberto');
      botaoMenu.setAttribute('aria-expanded', String(aberto));
      botaoMenu.setAttribute('aria-label', aberto ? 'Fechar menu de navegação' : 'Abrir menu de navegação');
    });

    menu.addEventListener('click', function (evento) {
      if (evento.target.closest('a')) {
        menu.classList.remove('aberto');
        botaoMenu.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* ── 2. Abas das etapas metodológicas ───────────────────────────────── */

  var abas = pts('.etapa-aba');

  function selecionarEtapa(indice, moverFoco) {
    abas.forEach(function (aba, i) {
      var ativa = i === indice;
      var painel = pt('#' + aba.getAttribute('aria-controls'));
      aba.setAttribute('aria-selected', String(ativa));
      aba.tabIndex = ativa ? 0 : -1;
      if (painel) painel.hidden = !ativa;
    });
    if (moverFoco && abas[indice]) abas[indice].focus();
  }

  abas.forEach(function (aba, i) {
    aba.tabIndex = aba.getAttribute('aria-selected') === 'true' ? 0 : -1;

    aba.addEventListener('click', function () {
      selecionarEtapa(i, false);
    });

    // Navegação por setas, conforme o padrão de abas do WAI-ARIA.
    aba.addEventListener('keydown', function (evento) {
      var destino = null;
      if (evento.key === 'ArrowRight') destino = (i + 1) % abas.length;
      if (evento.key === 'ArrowLeft') destino = (i - 1 + abas.length) % abas.length;
      if (evento.key === 'Home') destino = 0;
      if (evento.key === 'End') destino = abas.length - 1;
      if (destino === null) return;
      evento.preventDefault();
      selecionarEtapa(destino, true);
    });
  });

  /* ── 3. Captura real x rastro técnico ───────────────────────────────── */

  pts('.alternador').forEach(function (grupo) {
    var painel = grupo.closest('.etapa-painel');
    if (!painel) return;

    grupo.addEventListener('click', function (evento) {
      var botao = evento.target.closest('button[data-modo]');
      if (!botao) return;

      var modo = botao.getAttribute('data-modo');
      pts('button[data-modo]', grupo).forEach(function (b) {
        b.setAttribute('aria-pressed', String(b === botao));
      });
      pts('.vista', painel).forEach(function (vista) {
        vista.hidden = !vista.classList.contains('vista-' + modo);
      });
    });
  });

  /* ── 4. Ampliação de capturas ───────────────────────────────────────── */

  var lightbox = pt('#lightbox');
  var lightboxImg = pt('#lightbox-img');
  var lightboxLegenda = pt('#lightbox-legenda');
  var origemDoFoco = null;

  function abrirLightbox(img) {
    if (!lightbox || !lightboxImg) return;
    lightboxImg.src = img.src;
    lightboxImg.alt = img.alt;
    if (lightboxLegenda) {
      lightboxLegenda.textContent = img.getAttribute('data-legenda') || img.alt;
    }
    origemDoFoco = img;
    lightbox.classList.add('aberto');
    document.body.style.overflow = 'hidden';
    var fechar = pt('#lightbox-fechar');
    if (fechar) fechar.focus();
  }

  function fecharLightbox() {
    if (!lightbox) return;
    lightbox.classList.remove('aberto');
    document.body.style.overflow = '';
    if (origemDoFoco) origemDoFoco.focus();
  }

  pts('.captura img').forEach(function (img) {
    img.addEventListener('click', function () {
      abrirLightbox(img);
    });
  });

  if (lightbox) {
    lightbox.addEventListener('click', function (evento) {
      if (evento.target === lightbox || evento.target.closest('#lightbox-fechar')) {
        fecharLightbox();
      }
    });
  }

  document.addEventListener('keydown', function (evento) {
    if (evento.key === 'Escape' && lightbox && lightbox.classList.contains('aberto')) {
      fecharLightbox();
    }
  });

  /* ── 5. Perguntas frequentes ────────────────────────────────────────── */

  pts('.faq-pergunta').forEach(function (pergunta) {
    pergunta.addEventListener('click', function () {
      var resposta = pt('#' + pergunta.getAttribute('aria-controls'));
      var aberta = pergunta.getAttribute('aria-expanded') === 'true';
      pergunta.setAttribute('aria-expanded', String(!aberta));
      if (resposta) resposta.hidden = aberta;
    });
  });

  /* ── 6. Laços de vídeo ──────────────────────────────────────────────── */

  var menosMovimento = window.matchMedia('(prefers-reduced-motion: reduce)');

  pts('[data-laco]').forEach(function (video) {
    var caixa = video.closest('.laco');
    var botao = caixa ? pt('[data-laco-pausa]', caixa) : null;
    var icone = botao ? pt('use', botao) : null;
    // Pausa pedida no botão: manda o observador não religar o vídeo sozinho.
    var pausadoPeloUsuario = menosMovimento.matches;

    function tocar() {
      var promessa = video.play();
      if (promessa && promessa.catch) promessa.catch(function () {});
    }

    function refletirEstado() {
      if (!botao) return;
      var tocando = !video.paused;
      if (icone) icone.setAttribute('href', tocando ? '#i-pausa' : '#i-play');
      botao.setAttribute('aria-label', tocando ? 'Pausar a animação' : 'Reproduzir a animação');
    }

    // Quem pede menos movimento recebe o pôster parado, e não o laço.
    if (menosMovimento.matches) {
      video.autoplay = false;
      video.removeAttribute('autoplay');
      video.pause();
    }

    if (botao) {
      botao.addEventListener('click', function () {
        pausadoPeloUsuario = !video.paused;
        if (video.paused) tocar();
        else video.pause();
      });
    }

    video.addEventListener('play', refletirEstado);
    video.addEventListener('pause', refletirEstado);
    refletirEstado();

    // Vídeo fora da tela não precisa rodar: economiza bateria e banda, e é o
    // que o próprio Chrome já faz com vídeo mudo — aqui só ficamos explícitos,
    // porque nem todo navegador faz.
    if (!('IntersectionObserver' in window)) return;

    var observador = new IntersectionObserver(
      function (entradas) {
        entradas.forEach(function (entrada) {
          if (pausadoPeloUsuario) return;
          if (entrada.isIntersecting) tocar();
          else video.pause();
        });
      },
      { threshold: 0.25 }
    );
    observador.observe(video);
  });

  /* ── 7. Blocos do "Por que existe" ──────────────────────────────────── */

  // Cada bloco entra quando aparece na tela, e só então as fichas do vai e
  // vem começam a acender. Sem observador, a classe nem é posta e tudo fica
  // visível e parado.
  var dores = pt('[data-dores]');

  if (dores && 'IntersectionObserver' in window) {
    dores.classList.add('dores--animadas');

    var observadorDores = new IntersectionObserver(
      function (entradas) {
        entradas.forEach(function (entrada) {
          if (!entrada.isIntersecting) return;
          entrada.target.classList.add('visivel');
          observadorDores.unobserve(entrada.target);
        });
      },
      { threshold: 0.2, rootMargin: '0px 0px -6% 0px' }
    );

    pts('.dor', dores).forEach(function (dor) {
      observadorDores.observe(dor);
    });
  }
})();
