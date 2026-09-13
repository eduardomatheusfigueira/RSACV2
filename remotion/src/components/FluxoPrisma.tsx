/**
 * Revsist — O diagrama final, desenhado quadro a quadro.
 *
 * É o mesmo diagrama que o app exporta e que as revistas exigem: quantos
 * artigos entraram em cada etapa e quantos saíram. Os rótulos são os da
 * landing, em linguagem comum — quem chega aqui pela primeira vez não precisa
 * saber o que é "identificação" ou "elegibilidade" para entender o caminho.
 *
 * Cada caixa é dividida em duas células, rótulo à esquerda e contagem à
 * direita, separadas por um filete. Sem isso os números longos encavalam o
 * texto.
 */

import React from 'react';
import { interpolate } from 'remotion';
import { C, MONO, SANS } from '../theme';
import { px, suave } from './base';

type Caixa = {
  y: number;
  rotulo: string;
  valor: string;
  unidade: string;
};

const PRINCIPAIS: Caixa[] = [
  { y: 292, rotulo: 'Encontrados nas bases', valor: '231', unidade: 'artigos, com repetidos' },
  { y: 462, rotulo: 'Lidos por título e resumo', valor: '204', unidade: 'artigos diferentes' },
  { y: 632, rotulo: 'Lidos por inteiro', valor: '48', unidade: 'artigos' },
  { y: 802, rotulo: 'Entraram na revisão', valor: '24', unidade: 'artigos' },
];

const LATERAIS: Caixa[] = [
  { y: 404, rotulo: 'Repetidos removidos', valor: '27', unidade: 'o mesmo artigo em outra base' },
  { y: 574, rotulo: 'Fora pelo resumo', valor: '156', unidade: 'com o motivo registrado' },
  { y: 744, rotulo: 'Fora após leitura completa', valor: '24', unidade: 'com o motivo registrado' },
];

const X_PRINCIPAL = 286;
const L_PRINCIPAL = 588;
const CEL_PRINCIPAL = 158;
const A_PRINCIPAL = 116;

const X_LATERAL = 1014;
const L_LATERAL = 500;
const CEL_LATERAL = 126;
const A_LATERAL = 94;

const X_EIXO = X_PRINCIPAL + L_PRINCIPAL / 2;

export const FluxoPrisma: React.FC<{ local: number }> = ({ local }) => {
  const risca = (inicio: number, comprimento: number, duracao = 22) => {
    const t = suave(local, [inicio, inicio + duracao], [0, 1]);
    return { strokeDasharray: comprimento, strokeDashoffset: comprimento * (1 - t) };
  };

  return (
    <svg
      viewBox="0 0 1920 1080"
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
      aria-hidden
    >
      <defs>
        <filter id="relevo-caixa" x="-8%" y="-14%" width="116%" height="132%">
          <feDropShadow dx="0" dy="3" stdDeviation="4" floodColor="#152940" floodOpacity="0.14" />
        </filter>
      </defs>

      {/* Conectores verticais do eixo principal */}
      {PRINCIPAIS.slice(0, -1).map((caixa, i) => {
        const de = caixa.y + A_PRINCIPAL;
        const ate = PRINCIPAIS[i + 1].y;
        return (
          <g key={`v-${i}`}>
            <line
              x1={X_EIXO}
              y1={de}
              x2={X_EIXO}
              y2={ate}
              stroke={C.acento}
              strokeWidth={2.5}
              {...risca(24 + i * 22, ate - de)}
            />
            <path
              d={`M${X_EIXO - 9} ${ate - 16} L${X_EIXO} ${ate - 2} L${X_EIXO + 9} ${ate - 16}`}
              fill="none"
              stroke={C.acento}
              strokeWidth={2.5}
              opacity={suave(local, [34 + i * 22, 46 + i * 22], [0, 1])}
            />
          </g>
        );
      })}

      {/* Cotovelos até as caixas do que saiu */}
      {LATERAIS.map((lateral, i) => {
        const yCotovelo = lateral.y + A_LATERAL / 2;
        const comprimento = X_LATERAL - X_EIXO;
        return (
          <g key={`c-${i}`}>
            <path
              d={`M${X_EIXO} ${yCotovelo} H${X_LATERAL - 14}`}
              fill="none"
              stroke={C.apoio}
              strokeWidth={2.5}
              strokeDasharray={comprimento}
              strokeDashoffset={comprimento * (1 - suave(local, [30 + i * 22, 52 + i * 22], [0, 1]))}
            />
            <path
              d={`M${X_LATERAL - 16} ${yCotovelo - 8} L${X_LATERAL - 2} ${yCotovelo} L${
                X_LATERAL - 16
              } ${yCotovelo + 8}`}
              fill="none"
              stroke={C.apoio}
              strokeWidth={2.5}
              opacity={suave(local, [46 + i * 22, 58 + i * 22], [0, 1])}
            />
          </g>
        );
      })}

      {/* Caixas do eixo principal */}
      {PRINCIPAIS.map((caixa, i) => {
        const entrada = 12 + i * 22;
        const o = suave(local, [entrada, entrada + 20], [0, 1]);
        const dy = px(interpolate(o, [0, 1], [18, 0]));
        const final = i === PRINCIPAIS.length - 1;
        const xCel = X_PRINCIPAL + L_PRINCIPAL - CEL_PRINCIPAL;
        return (
          <g
            key={caixa.rotulo}
            opacity={o}
            transform={`translate(0 ${dy})`}
            filter="url(#relevo-caixa)"
          >
            <rect
              x={X_PRINCIPAL}
              y={caixa.y}
              width={L_PRINCIPAL}
              height={A_PRINCIPAL}
              rx={2}
              fill={final ? C.acento : C.superficie}
              stroke={C.acento}
              strokeWidth={2}
            />
            <rect
              x={X_PRINCIPAL}
              y={caixa.y}
              width={6}
              height={A_PRINCIPAL}
              fill={final ? C.claroAcento : C.apoio}
            />
            <line
              x1={xCel}
              y1={caixa.y + 16}
              x2={xCel}
              y2={caixa.y + A_PRINCIPAL - 16}
              stroke={final ? 'rgba(255,255,255,0.42)' : C.borda}
              strokeWidth={1.5}
            />
            <text
              x={X_PRINCIPAL + 30}
              y={caixa.y + 48}
              fontFamily={SANS}
              fontSize={27}
              fontWeight={600}
              fill={final ? C.branco : C.tinta}
            >
              {caixa.rotulo}
            </text>
            <text
              x={X_PRINCIPAL + 30}
              y={caixa.y + 82}
              fontFamily={MONO}
              fontSize={21}
              fill={final ? 'rgba(255,255,255,0.8)' : C.tintaSuave}
              letterSpacing="0.06em"
            >
              {caixa.unidade}
            </text>
            <text
              x={xCel + CEL_PRINCIPAL / 2}
              y={caixa.y + 76}
              textAnchor="middle"
              fontFamily={MONO}
              fontSize={52}
              fontWeight={700}
              fill={final ? C.branco : C.acento}
            >
              {caixa.valor}
            </text>
          </g>
        );
      })}

      {/* Caixas do que saiu */}
      {LATERAIS.map((caixa, i) => {
        const entrada = 40 + i * 22;
        const o = suave(local, [entrada, entrada + 20], [0, 1]);
        const xCel = X_LATERAL + L_LATERAL - CEL_LATERAL;
        return (
          <g key={caixa.rotulo} opacity={o * 0.96}>
            <rect
              x={X_LATERAL}
              y={caixa.y}
              width={L_LATERAL}
              height={A_LATERAL}
              rx={2}
              fill={C.papelFundo}
              stroke={C.borda}
              strokeWidth={2}
              strokeDasharray="7 5"
            />
            <line
              x1={xCel}
              y1={caixa.y + 14}
              x2={xCel}
              y2={caixa.y + A_LATERAL - 14}
              stroke={C.borda}
              strokeWidth={1.5}
            />
            <text
              x={X_LATERAL + 24}
              y={caixa.y + 40}
              fontFamily={SANS}
              fontSize={24}
              fontWeight={600}
              fill={C.tinta}
            >
              {caixa.rotulo}
            </text>
            <text
              x={X_LATERAL + 24}
              y={caixa.y + 69}
              fontFamily={MONO}
              fontSize={19}
              fill={C.tintaSuave}
              letterSpacing="0.05em"
            >
              {caixa.unidade}
            </text>
            <text
              x={xCel + CEL_LATERAL / 2}
              y={caixa.y + 62}
              textAnchor="middle"
              fontFamily={MONO}
              fontSize={36}
              fontWeight={700}
              fill={C.tintaSuave}
            >
              {caixa.valor}
            </text>
          </g>
        );
      })}
    </svg>
  );
};
