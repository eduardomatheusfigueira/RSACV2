/**
 * Revsist — Faixa "No fim", da seção do diagrama na landing.
 *
 * Formato e narrativa das faixas (coluna com "Agora" e etapas à esquerda,
 * palco contando uma história à direita), mas sobre o papel claro dos laços
 * de seção, com as curvas de nível ondulando atrás.
 *
 * O diagrama deita: numa faixa 4:1, o caminho corre da esquerda para a direita
 * e o que saiu em cada etapa desce para baixo dela. A história tem três tempos:
 *
 *   1. Contar — as caixas se montam e os números correm, cada um a conta do
 *      trabalho feito.
 *   2. Refazer — você revê uma decisão; os dois números afetados trocam sozinhos.
 *   3. Exportar — saem o PNG, o SVG e a lista de termos, bases e datas.
 */

import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';
import { C, MONO, SANS } from '../theme';
import { px, suave, useFasePeriodica, usarFontesDaMarca } from '../components/base';
import { Coluna, FundoPapel, Tela, limitar, opacidadeDeTroca, vaiEVolta } from '../components/faixa';

export const DURACAO_FAIXA_DIAGRAMA = 480;
const FADE = 18;

/* ── Linha do tempo (quadros) ────────────────────────────────────────────── */

const ENTRADA_PRINCIPAL = (k: number) => 24 + k * 30;
const ENTRADA_LATERAL = (k: number) => ENTRADA_PRINCIPAL(k) + 26;
const CONTAS = 160;
const REVISAO = 250;
const TROCA = 282;
const EXPORTA = 340;
const ARQUIVO = (k: number) => 350 + k * 16;

/* ── Geometria ───────────────────────────────────────────────────────────── */

const PRINCIPAL = { x0: 860, y: 150, w: 330, h: 112, vao: 86 };
const LATERAL = { y: 330, w: 300, h: 104 };
const EIXO_Y = PRINCIPAL.y + PRINCIPAL.h / 2;

const xPrincipal = (k: number) => PRINCIPAL.x0 + k * (PRINCIPAL.w + PRINCIPAL.vao);
const centroDoVao = (k: number) => xPrincipal(k) + PRINCIPAL.w + PRINCIPAL.vao / 2;

const PRINCIPAIS = [
  { rotulo: 'Encontrados nas bases', unidade: 'com repetidos', antes: 231, depois: 231 },
  { rotulo: 'Lidos por título e resumo', unidade: 'artigos diferentes', antes: 204, depois: 204 },
  { rotulo: 'Lidos por inteiro', unidade: 'artigos', antes: 48, depois: 48 },
  { rotulo: 'Entraram na revisão', unidade: 'artigos', antes: 24, depois: 25 },
];

const LATERAIS = [
  { rotulo: 'Repetidos removidos', unidade: 'já estavam em outra base', antes: 27, depois: 27 },
  { rotulo: 'Fora pelo resumo', unidade: 'com o motivo guardado', antes: 156, depois: 156 },
  { rotulo: 'Fora após leitura completa', unidade: 'com o motivo guardado', antes: 24, depois: 23 },
];

const ARQUIVOS = [
  { nome: 'diagrama.png', formato: 'PNG', nota: 'imagem para colar no texto' },
  { nome: 'diagrama.svg', formato: 'SVG', nota: 'vetor, amplia sem perder' },
  { nome: 'busca.txt', formato: 'TXT', nota: 'termos, bases e datas' },
];

const ETAPAS = ['Contar', 'Refazer', 'Exportar'];

/* ── Número que conta e, se mudar, rola para o valor novo ────────────────── */

const Numero: React.FC<{
  t: number;
  x: number;
  y: number;
  antes: number;
  depois: number;
  inicio: number;
  tamanho: number;
  cor: string;
}> = ({ t, x, y, antes, depois, inicio, tamanho, cor }) => {
  const contado = Math.round(suave(t, [inicio, inicio + 22], [0, antes]));
  if (antes === depois || t < TROCA) {
    return (
      <text x={x} y={y} fontFamily={MONO} fontSize={tamanho} fontWeight={700} fill={cor} style={{ fontVariantNumeric: 'tabular-nums' }}>
        {contado}
      </text>
    );
  }
  const u = vaiEVolta(t, [TROCA, TROCA + 12], [0, 1]);
  return (
    <g>
      <text
        x={x}
        y={px(y - 18 * u)}
        opacity={1 - u}
        fontFamily={MONO}
        fontSize={tamanho}
        fontWeight={700}
        fill={cor}
        style={{ fontVariantNumeric: 'tabular-nums' }}
      >
        {antes}
      </text>
      <text
        x={x}
        y={px(y + 18 * (1 - u))}
        opacity={u}
        fontFamily={MONO}
        fontSize={tamanho}
        fontWeight={700}
        fill={cor}
        style={{ fontVariantNumeric: 'tabular-nums' }}
      >
        {depois}
      </text>
    </g>
  );
};

/** Anel que acende em volta de uma caixa cujo número acabou de mudar. */
const Realce: React.FC<{ t: number; x: number; y: number; w: number; h: number }> = ({ t, x, y, w, h }) => {
  const o = t < TROCA - 4 ? 0 : interpolate(t, [TROCA - 4, TROCA + 4, TROCA + 40], [0, 1, 0.35], { extrapolateRight: 'clamp' });
  return <rect x={x - 7} y={y - 7} width={w + 14} height={h + 14} rx={6} fill="none" stroke={C.apoio} strokeWidth={4} opacity={o} />;
};

/* ── Coluna: o que está acontecendo ──────────────────────────────────────── */

const Estado: React.FC<{ t: number }> = ({ t }) => {
  const trocas = [44, CONTAS, REVISAO, EXPORTA];
  const agora =
    t < 44
      ? 'Suas decisões viram números'
      : t < CONTAS
        ? 'O Revsist faz as contas'
        : t < REVISAO
          ? 'Cada número bate com o acervo'
          : t < EXPORTA
            ? 'Mudou algo? Ele refaz as contas'
            : 'Pronto para colar no texto';
  const etapa = t < REVISAO ? 0 : t < EXPORTA ? 1 : 2;

  return (
    <g opacity={suave(t, [22, 38], [0, 1])}>
      <text x={120} y={402} fontFamily={MONO} fontSize={21} letterSpacing="0.24em" fill={C.acento} opacity={0.85}>
        AGORA
      </text>
      <text x={120} y={450} fontFamily={SANS} fontSize={34} fontWeight={700} fill={C.tinta} opacity={opacidadeDeTroca(t, trocas)}>
        {agora}
      </text>
      {ETAPAS.map((nome, i) => {
        const x = 120 + i * 200;
        const feita = i < etapa;
        const atual = i === etapa;
        return (
          <g key={nome} opacity={atual ? 1 : feita ? 0.7 : 0.4}>
            {i > 0 ? (
              <line x1={x - 66} y1={528} x2={x - 16} y2={528} stroke={C.acento} strokeWidth={2} opacity={feita || atual ? 0.6 : 0.3} />
            ) : null}
            <circle cx={x} cy={528} r={9} fill={feita || atual ? C.acento : C.papel} stroke={C.acento} strokeWidth={2.5} />
            <text x={x + 20} y={535} fontFamily={MONO} fontSize={20} fontWeight={atual ? 700 : 400} fill={C.tinta}>
              {nome}
            </text>
          </g>
        );
      })}
    </g>
  );
};

/* ── O diagrama deitado ──────────────────────────────────────────────────── */

const Diagrama: React.FC<{ t: number }> = ({ t }) => {
  const risca = (inicio: number, duracao = 14) => limitar((t - inicio) / duracao);

  return (
    <g>
      <defs>
        <filter id="relevo-faixa" x="-8%" y="-14%" width="116%" height="132%">
          <feDropShadow dx="0" dy="3" stdDeviation="4" floodColor="#152940" floodOpacity="0.14" />
        </filter>
      </defs>

      {/* Conectores do eixo, da caixa k para a k+1 */}
      {PRINCIPAIS.slice(0, -1).map((_, k) => {
        const de = xPrincipal(k) + PRINCIPAL.w;
        const ate = xPrincipal(k + 1);
        const u = risca(ENTRADA_PRINCIPAL(k) + 14);
        return (
          <g key={`eixo-${k}`}>
            <line x1={de} y1={EIXO_Y} x2={de + (ate - 4 - de) * u} y2={EIXO_Y} stroke={C.acento} strokeWidth={2.5} />
            <path
              d={`M${ate - 16} ${EIXO_Y - 9} L${ate - 2} ${EIXO_Y} L${ate - 16} ${EIXO_Y + 9}`}
              fill="none"
              stroke={C.acento}
              strokeWidth={2.5}
              opacity={u >= 1 ? 1 : 0}
            />
          </g>
        );
      })}

      {/* Cotovelos: o que saiu desce do vão para a caixa lateral */}
      {LATERAIS.map((_, k) => {
        const cx = centroDoVao(k);
        const u = risca(ENTRADA_PRINCIPAL(k) + 20);
        const fim = LATERAL.y - 4;
        return (
          <g key={`cotovelo-${k}`}>
            <line x1={cx} y1={EIXO_Y} x2={cx} y2={EIXO_Y + (fim - EIXO_Y) * u} stroke={C.apoio} strokeWidth={2.5} />
            <path
              d={`M${cx - 8} ${fim - 14} L${cx} ${fim} L${cx + 8} ${fim - 14}`}
              fill="none"
              stroke={C.apoio}
              strokeWidth={2.5}
              opacity={u >= 1 ? 1 : 0}
            />
          </g>
        );
      })}

      {/* Caixas do caminho principal */}
      {PRINCIPAIS.map((caixa, k) => {
        const x = xPrincipal(k);
        const { y, w, h } = PRINCIPAL;
        const o = suave(t, [ENTRADA_PRINCIPAL(k), ENTRADA_PRINCIPAL(k) + 18], [0, 1]);
        const dy = px((1 - o) * 16);
        const final = k === PRINCIPAIS.length - 1;
        const digitos = String(caixa.depois).length;
        return (
          <g key={caixa.rotulo} opacity={o} transform={`translate(0 ${dy})`}>
            {caixa.antes !== caixa.depois ? <Realce t={t} x={x} y={y} w={w} h={h} /> : null}
            <g filter="url(#relevo-faixa)">
              <rect x={x} y={y} width={w} height={h} rx={3} fill={final ? C.acento : C.superficie} stroke={C.acento} strokeWidth={2} />
              <rect x={x} y={y} width={6} height={h} fill={final ? C.claroAcento : C.apoio} />
            </g>
            <text x={x + 26} y={y + 38} fontFamily={SANS} fontSize={20} fontWeight={600} fill={final ? C.branco : C.tinta}>
              {caixa.rotulo}
            </text>
            <Numero
              t={t}
              x={x + 26}
              y={y + 92}
              antes={caixa.antes}
              depois={caixa.depois}
              inicio={ENTRADA_PRINCIPAL(k) + 4}
              tamanho={44}
              cor={final ? C.branco : C.acento}
            />
            <text
              x={x + 26 + digitos * 26.4 + 14}
              y={y + 90}
              fontFamily={MONO}
              fontSize={16}
              fill={final ? 'rgba(255,255,255,0.8)' : C.tintaSuave}
            >
              {caixa.unidade}
            </text>
          </g>
        );
      })}

      {/* Caixas do que saiu */}
      {LATERAIS.map((caixa, k) => {
        const x = centroDoVao(k) - LATERAL.w / 2;
        const { y, w, h } = LATERAL;
        const o = suave(t, [ENTRADA_LATERAL(k), ENTRADA_LATERAL(k) + 18], [0, 1]);
        const digitos = String(caixa.depois).length;
        return (
          <g key={caixa.rotulo} opacity={o}>
            {caixa.antes !== caixa.depois ? <Realce t={t} x={x} y={y} w={w} h={h} /> : null}
            <rect x={x} y={y} width={w} height={h} rx={3} fill={C.papelFundo} stroke={C.borda} strokeWidth={2} strokeDasharray="7 5" />
            <text x={x + 20} y={y + 34} fontFamily={SANS} fontSize={18} fontWeight={600} fill={C.tinta}>
              {caixa.rotulo}
            </text>
            <Numero
              t={t}
              x={x + 20}
              y={y + 80}
              antes={caixa.antes}
              depois={caixa.depois}
              inicio={ENTRADA_LATERAL(k) + 4}
              tamanho={34}
              cor={C.tintaSuave}
            />
            <text x={x + 20 + digitos * 20.4 + 12} y={y + 78} fontFamily={MONO} fontSize={13} fill={C.tintaSuave}>
              {caixa.unidade}
            </text>
          </g>
        );
      })}
    </g>
  );
};

/* ── Refazer: a decisão revista ──────────────────────────────────────────── */

const DecisaoRevista: React.FC<{ t: number }> = ({ t }) => {
  const x = 860;
  const y = 466;
  const o = suave(t, [REVISAO, REVISAO + 16], [0, 1]);
  const dy = px((1 - o) * 14);
  // O aviso volta a ficar discreto quando os arquivos começam a sair.
  const discreto = 1 - 0.45 * limitar((t - EXPORTA) / 14);

  return (
    <g opacity={o * discreto} transform={`translate(0 ${dy})`}>
      <rect x={x} y={y} width={560} height={76} rx={4} fill={C.superficie} stroke={C.apoio} strokeWidth={2} />
      <circle cx={x + 38} cy={y + 38} r={20} fill={C.acento} />
      <path
        d={`M${x + 30} ${y + 32} h12 a7 7 0 0 1 0 14 h-8 M${x + 30} ${y + 32} l5 -5 M${x + 30} ${y + 32} l5 5`}
        fill="none"
        stroke={C.branco}
        strokeWidth={2.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <text x={x + 76} y={y + 30} fontFamily={MONO} fontSize={15} letterSpacing="0.14em" fill={C.acento}>
        VOCÊ REVIU UMA DECISÃO
      </text>
      <text x={x + 76} y={y + 58} fontFamily={SANS} fontSize={21} fontWeight={600} fill={C.tinta}>
        1 artigo volta para a revisão
      </text>
    </g>
  );
};

/* ── Exportar: os arquivos que saem ──────────────────────────────────────── */

const Arquivos: React.FC<{ t: number }> = ({ t }) => (
  <g>
    {ARQUIVOS.map((a, k) => {
      const x = 1500 + k * 320;
      const y = 466;
      const o = suave(t, [ARQUIVO(k), ARQUIVO(k) + 16], [0, 1]);
      const dy = px((1 - o) * 18);
      const pronto = limitar((t - ARQUIVO(k) - 22) / 8);
      return (
        <g key={a.nome} opacity={o} transform={`translate(0 ${dy})`}>
          <rect x={x} y={y} width={300} height={76} rx={4} fill={C.superficie} stroke={C.borda} strokeWidth={2} />
          <path
            d={`M${x + 18} ${y + 14} h26 l12 12 v38 h-38 Z`}
            fill={C.papel}
            stroke={C.acento}
            strokeWidth={2}
            strokeLinejoin="round"
          />
          <text x={x + 37} y={y + 54} textAnchor="middle" fontFamily={MONO} fontSize={11} fontWeight={700} fill={C.acento}>
            {a.formato}
          </text>
          <text x={x + 72} y={y + 33} fontFamily={MONO} fontSize={18} fontWeight={700} fill={C.tinta}>
            {a.nome}
          </text>
          <text x={x + 72} y={y + 58} fontFamily={SANS} fontSize={15} fill={C.tintaSuave}>
            {a.nota}
          </text>
          <g opacity={pronto}>
            <circle cx={x + 272} cy={y + 24} r={11} fill={C.acento} />
            <path d={`M${x + 266} ${y + 24} l4 4 l7 -8`} fill="none" stroke={C.branco} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />
          </g>
        </g>
      );
    })}
  </g>
);

/* ═══ Montagem ═══════════════════════════════════════════════════════════ */

const Cena: React.FC<{ t: number }> = ({ t }) => (
  <Tela>
    <Coluna t={t} kicker="NO FIM" linhas={['O diagrama', 'monta-se sozinho']} claro />
    <Estado t={t} />
    <Diagrama t={t} />
    {t >= REVISAO - 2 ? <DecisaoRevista t={t} /> : null}
    {t >= EXPORTA ? <Arquivos t={t} /> : null}
  </Tela>
);

export const FaixaDiagrama: React.FC = () => {
  usarFontesDaMarca();
  const frame = useCurrentFrame();
  const fase = useFasePeriodica();
  const duracao = DURACAO_FAIXA_DIAGRAMA - FADE;

  return (
    <AbsoluteFill style={{ backgroundColor: C.papel, overflow: 'hidden' }}>
      <FundoPapel fase={fase} />
      {[0, DURACAO_FAIXA_DIAGRAMA].map((inicio) => {
        const t = frame - inicio;
        const o =
          interpolate(t, [-FADE * 0.4, FADE], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }) *
          interpolate(t, [duracao - FADE, duracao + FADE * 0.4], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
        if (o <= 0.001) return null;
        return (
          <AbsoluteFill key={inicio} style={{ opacity: o }}>
            <Cena t={t} />
          </AbsoluteFill>
        );
      })}
    </AbsoluteFill>
  );
};
