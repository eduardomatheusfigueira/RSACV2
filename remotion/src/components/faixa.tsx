/**
 * Revsist — Peças comuns das faixas ultralargas (4:1) da landing.
 *
 * As faixas são uma família: mesmo fundo chapado em azul-tinta, a mesma
 * coluna de texto à esquerda e o mesmo filete separando-a do palco. O fundo é
 * o da faixa na página, e o brilho some antes das bordas — em tela mais larga
 * que o vídeo, a faixa continua sem emenda visível.
 *
 * Tudo que tem texto só se desloca em pixel inteiro (ver `px` em base.tsx), e
 * o fundo não se move: em vídeo tão largo, fundo animado só gasta bitrate.
 */

import React from 'react';
import { Easing, interpolate } from 'remotion';
import { C, MONO, SANS } from '../theme';
import { px, suave } from './base';

export const W = 2560;
export const H = 640;

export const GELO = C.claroAcento;
export const FUNDO = C.tinta;
export const CARTAO = '#1d3a5c';
export const LINHA = 'rgba(163,206,241,0.28)';
export const NEGATIVO = '#e39a9a';

export const limitar = (v: number): number => Math.max(0, Math.min(1, v));

export const vaiEVolta = (frame: number, entrada: number[], saida: number[]): number =>
  interpolate(frame, entrada, saida, {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.cubic),
  });

export const Tela: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <svg
    viewBox={`0 0 ${W} ${H}`}
    style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
    aria-hidden
  >
    {children}
  </svg>
);

export const Fundo: React.FC = () => (
  <Tela>
    <defs>
      <pattern id="faixa-grade" width={40} height={40} patternUnits="userSpaceOnUse">
        <path d="M40 0H0V40" fill="none" stroke="rgba(163,206,241,0.05)" strokeWidth={1.5} />
      </pattern>
      <radialGradient id="faixa-brilho" cx="60%" cy="50%" r="42%">
        <stop offset="0%" stopColor={C.apoio} stopOpacity={0.17} />
        <stop offset="100%" stopColor={C.apoio} stopOpacity={0} />
      </radialGradient>
    </defs>
    <rect width={W} height={H} fill={FUNDO} />
    <rect width={W} height={H} fill="url(#faixa-grade)" />
    <rect width={W} height={H} fill="url(#faixa-brilho)" />
    <line x1={800} y1={96} x2={800} y2={544} stroke="rgba(163,206,241,0.16)" strokeWidth={2} />
  </Tela>
);

/**
 * Fundo claro das faixas: o papel dos laços de seção, com grade técnica, grão
 * e as curvas de nível ondulando devagar. As curvas usam só funções periódicas
 * no período do vídeo, então o último quadro emenda no primeiro.
 *
 * O centro clareia, mas as bordas voltam ao `C.papel` exato — a mesma cor da
 * página, para a faixa se dissolver nela.
 */
export const FundoPapel: React.FC<{ fase: number }> = ({ fase }) => {
  const contorno = (indice: number): string => {
    const base = 34 + indice * 54;
    const pontos: string[] = [];
    for (let x = -80; x <= W + 80; x += 40) {
      const y =
        base +
        Math.sin(x / 360 + fase + indice * 0.42) * 18 +
        Math.sin(x / 150 + fase * 2 + indice) * 6;
      pontos.push(`${x},${y.toFixed(1)}`);
    }
    return `M${pontos.join(' L')}`;
  };

  return (
    <Tela>
      <defs>
        <pattern id="papel-grade" width={56} height={56} patternUnits="userSpaceOnUse">
          <path d="M56 0H0V56" fill="none" stroke="rgba(39,76,119,0.07)" strokeWidth={1.5} />
        </pattern>
        <radialGradient id="papel-luz" cx="58%" cy="46%" r="46%">
          <stop offset="0%" stopColor="#f3f6f8" stopOpacity={1} />
          <stop offset="100%" stopColor={C.papel} stopOpacity={0} />
        </radialGradient>
        <filter id="papel-grao">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" stitchTiles="stitch" />
          <feColorMatrix type="saturate" values="0" />
        </filter>
      </defs>
      <rect width={W} height={H} fill={C.papel} />
      <rect width={W} height={H} fill="url(#papel-luz)" />
      <rect width={W} height={H} fill="url(#papel-grade)" />
      <g fill="none" stroke={C.apoio} strokeWidth={1.4} opacity={0.26}>
        {Array.from({ length: 12 }, (_, i) => (
          <path key={i} d={contorno(i)} />
        ))}
      </g>
      <rect width={W} height={H} filter="url(#papel-grao)" opacity={0.05} style={{ mixBlendMode: 'multiply' }} />
      <line x1={800} y1={96} x2={800} y2={544} stroke={C.borda} strokeWidth={2} />
    </Tela>
  );
};

/** Kicker e título da coluna da esquerda. `claro` é a versão para o papel. */
export const Coluna: React.FC<{ t: number; kicker: string; linhas: string[]; claro?: boolean }> = ({
  t,
  kicker,
  linhas,
  claro = false,
}) => (
  <g>
    <g opacity={suave(t, [0, 16], [0, 1])}>
      <rect x={120} y={132} width={px(suave(t, [2, 26], [0, 44]))} height={3} fill={claro ? C.acento : GELO} />
      <text
        x={184}
        y={143}
        fontFamily={MONO}
        fontSize={24}
        fontWeight={500}
        letterSpacing="0.3em"
        fill={claro ? C.acento : GELO}
      >
        {kicker}
      </text>
    </g>
    {linhas.map((linha, i) => {
      const l = t - 6 - i * 6;
      return (
        <text
          key={linha}
          x={120}
          y={226 + i * 62}
          transform={`translate(0 ${px(suave(l, [0, 22], [18, 0]))})`}
          opacity={suave(l, [0, 16], [0, 1])}
          fontFamily={SANS}
          fontSize={50}
          fontWeight={700}
          letterSpacing="-0.02em"
          fill={claro ? C.tinta : C.branco}
        >
          {linha}
        </text>
      );
    })}
  </g>
);

/**
 * Opacidade de um valor que troca de texto: some e volta em torno de cada
 * troca, para a palavra nova não aparecer por cima da velha.
 */
export const opacidadeDeTroca = (t: number, trocas: number[], meia = 5): number =>
  Math.min(1, ...trocas.map((troca) => Math.abs(t - troca) / meia));

/**
 * Bloco "Agora" + marcador de etapas da coluna da esquerda.
 *
 * `valores` e `trocas` andam juntos: `valores[i]` vale de `trocas[i - 1]` até
 * `trocas[i]`, e o último vale até o fim.
 */
export const EstadoFaixa: React.FC<{
  t: number;
  valores: string[];
  trocas: number[];
  etapas: string[];
  inicioDasEtapas: number[];
  claro?: boolean;
}> = ({ t, valores, trocas, etapas, inicioDasEtapas, claro = false }) => {
  const i = trocas.filter((troca) => t >= troca).length;
  const etapa = Math.max(0, inicioDasEtapas.filter((inicio) => t >= inicio).length - 1);
  const acento = claro ? C.acento : GELO;
  const texto = claro ? C.tinta : C.branco;

  return (
    <g opacity={suave(t, [22, 38], [0, 1])}>
      <text x={120} y={402} fontFamily={MONO} fontSize={21} letterSpacing="0.24em" fill={acento} opacity={0.85}>
        AGORA
      </text>
      <text x={120} y={450} fontFamily={SANS} fontSize={34} fontWeight={700} fill={texto} opacity={opacidadeDeTroca(t, trocas)}>
        {valores[Math.min(i, valores.length - 1)]}
      </text>
      {etapas.map((nome, k) => {
        // 220 px por etapa: cabe um rótulo de até 10 caracteres em mono 20
        // sem a linha de ligação encostar nele.
        const x = 120 + k * 220;
        const feita = k < etapa;
        const atual = k === etapa;
        return (
          <g key={nome} opacity={atual ? 1 : feita ? 0.7 : 0.4}>
            {k > 0 ? (
              <line x1={x - 68} y1={528} x2={x - 16} y2={528} stroke={acento} strokeWidth={2} opacity={feita || atual ? 0.6 : 0.3} />
            ) : null}
            <circle cx={x} cy={528} r={9} fill={feita || atual ? acento : claro ? C.papel : FUNDO} stroke={acento} strokeWidth={2.5} />
            <text x={x + 20} y={535} fontFamily={MONO} fontSize={20} fontWeight={atual ? 700 : 400} fill={texto}>
              {nome}
            </text>
          </g>
        );
      })}
    </g>
  );
};

/** Opacidade de um ato que ocupa o palco de `inicio` a `fim`. */
export const opacidadeDoAto = (t: number, inicio: number, fim: number, fade = 14): number =>
  interpolate(t, [inicio, inicio + fade, fim - fade, fim], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

/**
 * Monta a cena duas vezes, deslocada de um período, para o laço fechar: a
 * opacidade chega a zero no último quadro, que fica igual ao primeiro.
 */
export const LacoDeFaixa: React.FC<{
  frame: number;
  duracao: number;
  children: (t: number) => React.ReactNode;
  fade?: number;
}> = ({ frame, duracao, children, fade = 18 }) => {
  const util = duracao - fade;
  return (
    <>
      {[0, duracao].map((inicio) => {
        const t = frame - inicio;
        const o =
          interpolate(t, [-fade * 0.4, fade], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }) *
          interpolate(t, [util - fade, util + fade * 0.4], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
        if (o <= 0.001) return null;
        return (
          <div key={inicio} style={{ position: 'absolute', inset: 0, opacity: o }}>
            {children(t)}
          </div>
        );
      })}
    </>
  );
};
