/**
 * Ponte para a configuração canônica da landing page.
 *
 * A landing tem projeto próprio em `landing/`, com o seu `vite.config.ts`.
 * Este arquivo existe só porque os scripts `dev:landing` e `build:landing`
 * moram no `package.json` do frontend — e reexportar, em vez de repetir a
 * configuração, é o que garante que os dois caminhos de build produzam
 * exatamente o mesmo `dist`. Duas cópias divergiriam na primeira alteração
 * feita em apenas uma delas.
 */
export { default } from '../landing/vite.config';
