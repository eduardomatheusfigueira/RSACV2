/**
 * Revsist — Minimalist Landing Script (< 3 KB)
 * Gerencia alternância de tema e revelação suave ao rolar.
 * Funcionalidade opcional: a página funciona 100% sem JavaScript.
 */

(function () {
  'use strict';

  // 1. Gerenciador de Tema (Light / Dark)
  const THEME_KEY = 'revsist-theme-preference';
  const themeToggleBtn = document.getElementById('theme-toggle-btn');
  const root = document.documentElement;

  function applyTheme(theme) {
    if (theme === 'dark' || theme === 'light') {
      root.setAttribute('data-theme', theme);
    } else {
      root.removeAttribute('data-theme');
    }
  }

  const savedTheme = localStorage.getItem(THEME_KEY);
  if (savedTheme) {
    applyTheme(savedTheme);
  }

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', function () {
      const currentTheme = root.getAttribute('data-theme');
      const isSystemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      
      let nextTheme;
      if (!currentTheme) {
        nextTheme = isSystemDark ? 'light' : 'dark';
      } else if (currentTheme === 'dark') {
        nextTheme = 'light';
      } else {
        nextTheme = 'dark';
      }

      applyTheme(nextTheme);
      localStorage.setItem(THEME_KEY, nextTheme);
    });
  }

  // 2. Revelação suave ao rolar (IntersectionObserver)
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  
  if (!prefersReducedMotion && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(
      (entries, obs) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            obs.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
    );

    document.querySelectorAll('.reveal-on-scroll').forEach((el) => {
      observer.observe(el);
    });
  } else {
    // Se o usuário prefere movimento reduzido ou navegador antigo, exibe tudo imediatamente
    document.querySelectorAll('.reveal-on-scroll').forEach((el) => {
      el.classList.add('is-visible');
    });
  }
})();
