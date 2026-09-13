/**
 * Revsist — Tokens de marca compartilhados entre o app, a landing e os vídeos.
 *
 * Paleta Platinum & Dusk Blue: é o tema padrão do aplicativo, fixado em
 * `frontend/index.html` (`data-theme="platinum-dusk"`) e em `useSettingsStore`.
 * É o que o usuário vê ao abrir o Revsist, e é o das capturas de tela — por
 * isso é também o dos vídeos.
 *
 * Os nomes abaixo são por papel, não por matiz: `acento` é a cor que carrega
 * texto e número sobre o papel claro; `apoio` só preenche forma (barra, anel,
 * filete), porque não alcança contraste de leitura; `claroAcento` é a versão
 * que funciona sobre o azul profundo.
 */

export const C = {
  papel: '#e7ecef',
  papelFundo: '#dce3e7',
  superficie: '#ffffff',

  tinta: '#152940',
  tintaProfunda: '#10243c',
  tintaSuave: '#3d5a78',

  acento: '#274c77',
  apoio: '#6096ba',
  claroAcento: '#a3cef1',

  borda: '#c4d3de',
  branco: '#ffffff',
  excluido: '#a83434',
} as const;

export const SANS = "'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif";
export const MONO = "'JetBrains Mono', 'Cascadia Code', monospace";

export const FPS = 30;

/** Duração de cada laço, em frames. Todo fundo animado usa o período do seu. */
export const DURACOES = {
  hero: 750, // 25 s
  busca: 270, // 9 s
  registro: 300, // 10 s
  diagrama: 300, // 10 s
} as const;

/** Cenas do laço do hero, em frames. As bordas se sobrepõem via crossfade. */
export const SCENES = {
  abertura: { start: 0, dur: 125 },
  coleta: { start: 125, dur: 140 },
  triagem: { start: 265, dur: 150 },
  extracao: { start: 415, dur: 130 },
  prisma: { start: 545, dur: 145 },
  fecho: { start: 690, dur: 60 },
} as const;
