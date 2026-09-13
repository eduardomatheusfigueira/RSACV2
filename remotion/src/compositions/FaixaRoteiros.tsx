/**
 * Revsist — Faixa "Roteiros", da seção dos roteiros na landing.
 *
 * Papel claro com as curvas de nível, no formato das faixas. Três tempos:
 *
 *   1. Escolher — os roteiros prontos lado a lado; a revisão de escopo leva ao
 *      PRISMA-ScR.
 *   2. Preencher — o roteiro vira checklist, e os itens são marcados conforme a
 *      revisão avança, com a barra de progresso contando.
 *   3. Conferir — o filtro "Faltam" mostra só o que ainda não foi feito, com o
 *      próximo item em destaque.
 *
 * Os itens são os do PRISMA-ScR, na ordem oficial.
 */

import React from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import { C, MONO, SANS } from '../theme';
import { px, suave, useFasePeriodica, usarFontesDaMarca } from '../components/base';
import {
  Coluna,
  EstadoFaixa,
  FundoPapel,
  LacoDeFaixa,
  Tela,
  limitar,
  vaiEVolta,
} from '../components/faixa';

export const DURACAO_FAIXA_ROTEIROS = 480;

/* ── Linha do tempo (quadros) ────────────────────────────────────────────── */

const PEDIDO = 20;
const PROCURA: [number, number] = [52, 84];
const ESCOLHA = 96;
const CHECKLIST = 150;
const MARCA = (k: number) => 186 + k * 15;
const FALTAM = 336;
const PROXIMO = 362;

/* ── Conteúdo ────────────────────────────────────────────────────────────── */

const ROTEIROS = [
  { nome: 'PRISMA 2020', tag: '27 ITENS', desc: 'o padrão internacional' },
  { nome: 'PRISMA-ScR', tag: '22 ITENS', desc: 'revisão de escopo' },
  { nome: 'JBI Scoping', tag: 'ESQUEMA PCC', desc: 'revisão de escopo' },
  { nome: 'Campbell', tag: 'CIÊNCIAS SOCIAIS', desc: 'educação e políticas' },
  { nome: 'ROSES', tag: 'MEIO AMBIENTE', desc: 'território e conservação' },
  { nome: 'MECIR', tag: 'COCHRANE', desc: 'as exigências da Cochrane' },
];
const ESCOLHIDO = 1;
const TOTAL_ITENS = 22;

const FEITOS = [
  'Título',
  'Resumo estruturado',
  'Justificativa',
  'Objetivos',
  'Protocolo e registro',
  'Critérios de elegibilidade',
  'Fontes de informação',
  'Estratégia de busca',
];

const PENDENTES = [
  'Seleção das fontes de evidência',
  'Processo de extração dos dados',
  'Itens extraídos',
  'Avaliação crítica (opcional)',
  'Síntese dos resultados',
  'Seleção das fontes (resultados)',
  'Características das fontes',
  'Avaliação crítica (resultados)',
];

const CARTAO = { x0: 860, y: 104, w: 240, h: 150, vao: 28 };
const xCartao = (i: number) => CARTAO.x0 + i * (CARTAO.w + CARTAO.vao);

const PAINEL = { x: 860, y: 290, w: 1580, h: 262 };

/* ── Escolher ────────────────────────────────────────────────────────────── */

const Roteiros: React.FC<{ t: number }> = ({ t }) => {
  const anel = vaiEVolta(t, PROCURA, [0, ESCOLHIDO]);
  const anelX = xCartao(0) + (xCartao(1) - xCartao(0)) * anel;
  const mostraAnel = t >= PROCURA[0] - 8 && t < ESCOLHA + 6;
  const escolheu = limitar((t - ESCOLHA) / 10);

  return (
    <g>
      {ROTEIROS.map((r, i) => {
        const x = xCartao(i);
        const { y, w, h } = CARTAO;
        const o = suave(t, [8 + i * 6, 26 + i * 6], [0, 1]);
        const dy = px((1 - o) * 16);
        const eleito = i === ESCOLHIDO;
        const apaga = eleito ? 1 : 1 - 0.5 * escolheu;
        const cheio = eleito ? escolheu : 0;
        return (
          <g key={r.nome} opacity={o * apaga} transform={`translate(0 ${dy})`}>
            <rect x={x} y={y} width={w} height={h} rx={3} fill={C.superficie} stroke={eleito && escolheu > 0 ? C.acento : C.borda} strokeWidth={2} />
            <rect x={x} y={y} width={w} height={h} rx={3} fill={C.acento} opacity={cheio} />
            <rect x={x} y={y} width={6} height={h} fill={eleito ? C.apoio : C.borda} />
            <text x={x + 24} y={y + 36} fontFamily={MONO} fontSize={13} letterSpacing="0.14em" fill={cheio > 0.5 ? C.claroAcento : C.tintaSuave}>
              {r.tag}
            </text>
            <text x={x + 24} y={y + 80} fontFamily={SANS} fontSize={26} fontWeight={700} fill={cheio > 0.5 ? C.branco : C.tinta}>
              {r.nome}
            </text>
            <text x={x + 24} y={y + 114} fontFamily={SANS} fontSize={16} fill={cheio > 0.5 ? 'rgba(255,255,255,0.85)' : C.tintaSuave}>
              {r.desc}
            </text>
            {eleito ? (
              <g opacity={escolheu}>
                <circle cx={x + w - 26} cy={y + 30} r={13} fill={C.claroAcento} />
                <path d={`M${x + w - 32} ${y + 30} l4 4 l8 -9`} fill="none" stroke={C.acento} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />
              </g>
            ) : null}
          </g>
        );
      })}

      {mostraAnel ? (
        <rect
          x={px(anelX) - 8}
          y={CARTAO.y - 8}
          width={CARTAO.w + 16}
          height={CARTAO.h + 16}
          rx={6}
          fill="none"
          stroke={C.apoio}
          strokeWidth={4}
          opacity={suave(t, [PROCURA[0] - 8, PROCURA[0]], [0, 1]) * (1 - limitar((t - ESCOLHA) / 6))}
        />
      ) : null}
    </g>
  );
};

/** O que a revisão é, antes de haver checklist. */
const Pedido: React.FC<{ t: number }> = ({ t }) => {
  const o = suave(t, [PEDIDO, PEDIDO + 16], [0, 1]) * (1 - limitar((t - CHECKLIST + 12) / 12));
  const { x, y } = PAINEL;
  return (
    <g opacity={o}>
      <rect x={x} y={y + 20} width={760} height={84} rx={4} fill={C.superficie} stroke={C.apoio} strokeWidth={2} />
      <text x={x + 26} y={y + 52} fontFamily={MONO} fontSize={15} letterSpacing="0.14em" fill={C.acento}>
        A SUA REVISÃO
      </text>
      <text x={x + 26} y={y + 86} fontFamily={SANS} fontSize={24} fontWeight={600} fill={C.tinta}>
        Mapear o que já se sabe sobre APLs no semiárido
      </text>
      <path
        d={`M${x + 380} ${y + 18} C${x + 380} ${y - 10}, ${xCartao(ESCOLHIDO) + 120} ${y - 4}, ${xCartao(ESCOLHIDO) + 120} ${CARTAO.y + CARTAO.h + 10}`}
        fill="none"
        stroke={C.apoio}
        strokeWidth={2.5}
        strokeDasharray="4 8"
        strokeLinecap="round"
        opacity={limitar((t - ESCOLHA) / 10)}
      />
    </g>
  );
};

/* ── Preencher e conferir: o checklist ───────────────────────────────────── */

const Caixa: React.FC<{ x: number; y: number; marcada: number }> = ({ x, y, marcada }) => (
  <g>
    <rect x={x} y={y - 18} width={24} height={24} rx={3} fill={marcada > 0.5 ? C.acento : C.superficie} stroke={C.acento} strokeWidth={2} />
    <path d={`M${x + 5} ${y - 6} l5 5 l9 -10`} fill="none" stroke={C.branco} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" opacity={marcada} />
  </g>
);

const Checklist: React.FC<{ t: number }> = ({ t }) => {
  const { x, y, w, h } = PAINEL;
  const o = suave(t, [CHECKLIST, CHECKLIST + 18], [0, 1]);
  const marcados = FEITOS.filter((_, k) => t >= MARCA(k)).length;
  const progresso = vaiEVolta(t, [MARCA(0) - 4, MARCA(FEITOS.length - 1) + 8], [0, FEITOS.length]) / TOTAL_ITENS;
  const faltam = limitar((t - FALTAM) / 12);
  const barra = { x: x + 760, w: 520 };
  const linhaY = (k: number) => y + 100 + (k % 4) * 42;
  const colunaX = (k: number) => x + 28 + (k >= 4 ? 780 : 0);

  return (
    <g opacity={o}>
      <rect x={x} y={y} width={w} height={h} rx={4} fill={C.superficie} stroke={C.borda} strokeWidth={2} />
      <rect x={x} y={y} width={w} height={62} rx={4} fill={C.papelFundo} />

      <text x={x + 28} y={y + 40} fontFamily={SANS} fontSize={26} fontWeight={700} fill={C.tinta}>
        PRISMA-ScR
      </text>
      <text x={x + 214} y={y + 39} fontFamily={MONO} fontSize={17} fill={C.tintaSuave}>
        checklist da sua revisão
      </text>

      {/* Filtro Todos / Faltam */}
      {['Todos', 'Faltam'].map((rotulo, i) => {
        const ativo = i === 0 ? 1 - faltam : faltam;
        const bx = x + 520 + i * 110;
        return (
          <g key={rotulo}>
            <rect x={bx} y={y + 16} width={100} height={30} rx={15} fill={C.acento} opacity={ativo} />
            <rect x={bx} y={y + 16} width={100} height={30} rx={15} fill="none" stroke={C.acento} strokeWidth={1.5} />
            <text x={bx + 50} y={y + 37} textAnchor="middle" fontFamily={MONO} fontSize={15} fontWeight={700} fill={ativo > 0.5 ? C.branco : C.acento}>
              {rotulo}
            </text>
          </g>
        );
      })}

      {/* Progresso */}
      <rect x={barra.x} y={y + 25} width={barra.w} height={12} rx={6} fill={C.papel} stroke={C.borda} strokeWidth={1} />
      <rect x={barra.x} y={y + 25} width={barra.w * progresso} height={12} rx={6} fill={C.acento} />
      <text x={x + w - 28} y={y + 38} textAnchor="end" fontFamily={MONO} fontSize={18} fontWeight={700} fill={C.tinta} style={{ fontVariantNumeric: 'tabular-nums' }}>
        {`${marcados} de ${TOTAL_ITENS} · faltam ${TOTAL_ITENS - marcados}`}
      </text>

      {/* Todos: os feitos sendo marcados */}
      <g opacity={1 - faltam}>
        {FEITOS.map((nome, k) => {
          const cx = colunaX(k);
          const cy = linhaY(k);
          const marcada = limitar((t - MARCA(k)) / 6);
          const brilho = t >= MARCA(k) ? 1 - limitar((t - MARCA(k)) / 18) : 0;
          return (
            <g key={nome}>
              <rect x={cx - 12} y={cy - 28} width={740} height={38} rx={3} fill={C.apoio} opacity={0.16 * brilho} />
              <Caixa x={cx} y={cy} marcada={marcada} />
              <text x={cx + 42} y={cy} fontFamily={MONO} fontSize={16} fill={C.tintaSuave}>
                {String(k + 1).padStart(2, '0')}
              </text>
              <text x={cx + 82} y={cy} fontFamily={SANS} fontSize={21} fontWeight={500} fill={C.tinta} opacity={0.55 + 0.45 * marcada}>
                {nome}
              </text>
            </g>
          );
        })}
      </g>

      {/* Faltam: só o que ainda não foi feito, com o próximo em destaque */}
      <g opacity={faltam}>
        {PENDENTES.map((nome, k) => {
          const cx = colunaX(k);
          const cy = linhaY(k);
          const proximo = k === 0 ? limitar((t - PROXIMO) / 10) : 0;
          return (
            <g key={nome}>
              {k === 0 ? (
                <g opacity={proximo}>
                  <rect x={cx - 12} y={cy - 28} width={740} height={38} rx={3} fill="#e3ebf3" />
                  <rect x={cx - 12} y={cy - 28} width={4} height={38} fill={C.acento} />
                  <rect x={cx + 560} y={cy - 22} width={120} height={26} rx={13} fill={C.acento} />
                  <text x={cx + 620} y={cy - 4} textAnchor="middle" fontFamily={MONO} fontSize={13} fontWeight={700} letterSpacing="0.1em" fill={C.branco}>
                    PRÓXIMO
                  </text>
                </g>
              ) : null}
              <Caixa x={cx} y={cy} marcada={0} />
              <text x={cx + 42} y={cy} fontFamily={MONO} fontSize={16} fill={C.tintaSuave}>
                {String(k + 9).padStart(2, '0')}
              </text>
              <text x={cx + 82} y={cy} fontFamily={SANS} fontSize={21} fontWeight={k === 0 ? 700 : 500} fill={C.tinta}>
                {nome}
              </text>
            </g>
          );
        })}
      </g>
    </g>
  );
};

/* ═══ Montagem ═══════════════════════════════════════════════════════════ */

const Cena: React.FC<{ t: number }> = ({ t }) => (
  <Tela>
    <Coluna t={t} kicker="ROTEIROS" linhas={['O roteiro da sua área,', 'em checklist']} claro />
    <EstadoFaixa
      t={t}
      claro
      valores={[
        'Qual roteiro a sua área pede?',
        'Onze prontos para escolher',
        'Ele vira o seu checklist',
        'Você marca conforme avança',
        'E sabe o que ainda falta',
      ]}
      trocas={[PROCURA[0], CHECKLIST, MARCA(0), FALTAM]}
      etapas={['Escolher', 'Preencher', 'Conferir']}
      inicioDasEtapas={[0, CHECKLIST, FALTAM]}
    />
    <Roteiros t={t} />
    {t < CHECKLIST ? <Pedido t={t} /> : null}
    {t >= CHECKLIST ? <Checklist t={t} /> : null}
  </Tela>
);

export const FaixaRoteiros: React.FC = () => {
  usarFontesDaMarca();
  const frame = useCurrentFrame();
  const fase = useFasePeriodica();

  return (
    <AbsoluteFill style={{ backgroundColor: C.papel, overflow: 'hidden' }}>
      <FundoPapel fase={fase} />
      <LacoDeFaixa frame={frame} duracao={DURACAO_FAIXA_ROTEIROS}>
        {(t) => <Cena t={t} />}
      </LacoDeFaixa>
    </AbsoluteFill>
  );
};
