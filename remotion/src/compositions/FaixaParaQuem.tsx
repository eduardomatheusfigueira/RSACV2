/**
 * Revsist — Faixa "Para quem é", da seção sobre quem pesquisa no Brasil.
 *
 * Fundo azul-tinta, no formato das faixas. Os três tempos são os três cartões
 * da seção, na mesma ordem:
 *
 *   1. Buscar — a mesma busca nas cinco bases; só as brasileiras respondem.
 *   2. Ler juntos — duas pessoas decidem os mesmos artigos, e o Revsist aponta
 *      onde discordaram até que decidam juntas.
 *   3. Adaptar — temas fora da área médica, cada um levando ao roteiro que
 *      pede, e a ficha que acompanha o tema.
 */

import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';
import { C, MONO, SANS } from '../theme';
import { px, suave, usarFontesDaMarca } from '../components/base';
import {
  CARTAO,
  Coluna,
  EstadoFaixa,
  FUNDO,
  Fundo,
  GELO,
  LINHA,
  LacoDeFaixa,
  NEGATIVO,
  Tela,
  limitar,
  opacidadeDoAto,
  vaiEVolta,
} from '../components/faixa';

export const DURACAO_FAIXA_PARA_QUEM = 480;

/* ── Linha do tempo (quadros) ────────────────────────────────────────────── */

const ATO_BUSCA: [number, number] = [0, 168];
const ATO_EQUIPE: [number, number] = [168, 310];
const ATO_TEMAS: [number, number] = [310, 500];

const X0 = 860;
const LARGURA = 1580;

/* ═══ 1 · Buscar ═════════════════════════════════════════════════════════ */

const BUSCA = '"arranjos produtivos locais" E "desenvolvimento regional"';

const BASES = [
  { nome: 'BDTD', artigos: 142, brasil: true },
  { nome: 'SciELO', artigos: 89, brasil: true },
  { nome: 'Scopus', artigos: 0, brasil: false },
  { nome: 'OpenAlex', artigos: 0, brasil: false },
  { nome: 'PubMed', artigos: 0, brasil: false },
];

const ENTRADA_BASE = (i: number) => 54 + i * 8;
const TOTAL_EM = 124;

const AtoBusca: React.FC<{ t: number }> = ({ t }) => {
  const digitados = Math.floor(interpolate(t, [10, 46], [0, BUSCA.length], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }));
  const trilho = { x: 1150, w: 880 };
  const total = Math.round(suave(t, [TOTAL_EM, TOTAL_EM + 22], [0, 231]));

  return (
    <g>
      <g opacity={suave(t, [4, 18], [0, 1])}>
        <rect x={X0} y={96} width={LARGURA} height={72} rx={4} fill={CARTAO} stroke={LINHA} strokeWidth={2} />
        <text x={X0 + 26} y={124} fontFamily={MONO} fontSize={15} letterSpacing="0.16em" fill={GELO}>
          UMA BUSCA SÓ, NAS CINCO BASES
        </text>
        <text x={X0 + 26} y={154} fontFamily={MONO} fontSize={22} fill={C.branco}>
          {BUSCA.slice(0, digitados)}
        </text>
      </g>

      {BASES.map((b, i) => {
        const y = 196 + i * 62;
        const o = suave(t, [ENTRADA_BASE(i), ENTRADA_BASE(i) + 14], [0, 1]);
        const cresce = suave(t, [ENTRADA_BASE(i) + 10, ENTRADA_BASE(i) + 40], [0, 1]);
        const valor = Math.round(b.artigos * cresce);
        return (
          <g key={b.nome} opacity={o * (b.brasil ? 1 : 0.7)}>
            <text x={X0} y={y + 32} fontFamily={SANS} fontSize={26} fontWeight={700} fill={C.branco}>
              {b.nome}
            </text>
            {b.brasil ? (
              <g transform={`translate(${X0 + 150} ${y + 12})`}>
                <rect width={98} height={28} rx={14} fill={GELO} />
                <text x={49} y={19} textAnchor="middle" fontFamily={MONO} fontSize={13} fontWeight={700} letterSpacing="0.1em" fill={FUNDO}>
                  BRASIL
                </text>
              </g>
            ) : null}
            <rect x={trilho.x} y={y + 18} width={trilho.w} height={14} rx={7} fill="rgba(163,206,241,0.12)" />
            <rect x={trilho.x} y={y + 18} width={trilho.w * (b.artigos / 142) * cresce} height={14} rx={7} fill={b.brasil ? GELO : C.apoio} />
            {b.artigos > 0 ? (
              <text x={trilho.x + trilho.w + 36} y={y + 38} fontFamily={MONO} fontSize={34} fontWeight={700} fill={C.branco} style={{ fontVariantNumeric: 'tabular-nums' }}>
                {valor}
              </text>
            ) : (
              <text x={trilho.x + trilho.w + 36} y={y + 34} fontFamily={MONO} fontSize={18} fill="rgba(255,255,255,0.55)" opacity={cresce}>
                nada sobre o tema
              </text>
            )}
          </g>
        );
      })}

      <g opacity={suave(t, [TOTAL_EM, TOTAL_EM + 14], [0, 1])}>
        <text x={X0} y={556} fontFamily={MONO} fontSize={40} fontWeight={700} fill={GELO} style={{ fontVariantNumeric: 'tabular-nums' }}>
          {total}
        </text>
        <text x={X0 + 96} y={552} fontFamily={SANS} fontSize={26} fontWeight={600} fill={C.branco}>
          artigos — e todos vieram das bases brasileiras
        </text>
      </g>
    </g>
  );
};

/* ═══ 2 · Ler juntos ═════════════════════════════════════════════════════ */

const LEITORES = [
  { iniciais: 'AL', nome: 'Ana' },
  { iniciais: 'ED', nome: 'Eduardo' },
];

type Voto = 'inclui' | 'exclui';

const LEITURAS: { titulo: string; fonte: string; votos: [Voto, Voto]; final: Voto }[] = [
  { titulo: 'Governança em APLs do semiárido', fonte: 'BDTD · tese', votos: ['inclui', 'inclui'], final: 'inclui' },
  { titulo: 'Cooperativas e renda no Vale do São Francisco', fonte: 'SciELO · artigo', votos: ['inclui', 'exclui'], final: 'inclui' },
  { titulo: 'Turismo náutico no litoral sul', fonte: 'BDTD · dissertação', votos: ['exclui', 'exclui'], final: 'exclui' },
];

const VOTO_EM = (linha: number, leitor: number) => ATO_EQUIPE[0] + 30 + linha * 18 + leitor * 8;
const DISCORDANCIA = ATO_EQUIPE[0] + 96;
const ACORDO = ATO_EQUIPE[0] + 122;

const Voto: React.FC<{ voto: Voto; x: number; y: number; o: number }> = ({ voto, x, y, o }) => (
  <g opacity={o} transform={`translate(${x} ${y})`}>
    <rect width={140} height={36} rx={18} fill={voto === 'inclui' ? 'rgba(163,206,241,0.18)' : 'rgba(227,154,154,0.16)'} stroke={voto === 'inclui' ? GELO : NEGATIVO} strokeWidth={2} />
    <text x={70} y={24} textAnchor="middle" fontFamily={SANS} fontSize={17} fontWeight={700} fill={voto === 'inclui' ? GELO : NEGATIVO}>
      {voto === 'inclui' ? '✓ Incluir' : '✕ Excluir'}
    </text>
  </g>
);

const AtoEquipe: React.FC<{ t: number }> = ({ t }) => {
  const colunaLeitor = (i: number) => 1530 + i * 190;
  const resultadoX = 1960;

  return (
    <g>
      <text x={X0} y={124} fontFamily={MONO} fontSize={15} letterSpacing="0.16em" fill={GELO} opacity={suave(t, [ATO_EQUIPE[0] + 4, ATO_EQUIPE[0] + 18], [0, 1])}>
        MESTRADO, DOUTORADO E GRUPOS DE PESQUISA
      </text>
      <text x={X0} y={160} fontFamily={SANS} fontSize={26} fontWeight={600} fill={C.branco} opacity={suave(t, [ATO_EQUIPE[0] + 8, ATO_EQUIPE[0] + 22], [0, 1])}>
        Cada pessoa lê a sua parte, no mesmo projeto
      </text>

      {LEITORES.map((l, i) => (
        <g key={l.nome} opacity={suave(t, [ATO_EQUIPE[0] + 14 + i * 6, ATO_EQUIPE[0] + 28 + i * 6], [0, 1])}>
          <circle cx={colunaLeitor(i) + 70} cy={214} r={22} fill={i === 0 ? C.apoio : GELO} />
          <text x={colunaLeitor(i) + 70} y={221} textAnchor="middle" fontFamily={MONO} fontSize={16} fontWeight={700} fill={FUNDO}>
            {l.iniciais}
          </text>
          <text x={colunaLeitor(i) + 102} y={221} fontFamily={SANS} fontSize={18} fill="rgba(255,255,255,0.8)">
            {l.nome}
          </text>
        </g>
      ))}
      <text x={resultadoX} y={221} fontFamily={MONO} fontSize={15} letterSpacing="0.14em" fill={GELO} opacity={suave(t, [ATO_EQUIPE[0] + 20, ATO_EQUIPE[0] + 34], [0, 1])}>
        O QUE O REVSIST MOSTRA
      </text>

      {LEITURAS.map((l, k) => {
        const y = 256 + k * 96;
        const o = suave(t, [ATO_EQUIPE[0] + 18 + k * 8, ATO_EQUIPE[0] + 34 + k * 8], [0, 1]);
        const discordam = l.votos[0] !== l.votos[1];
        const decidido = t >= VOTO_EM(k, 1) + 10;
        const alerta = discordam ? limitar((t - DISCORDANCIA) / 8) : 0;
        const resolvido = discordam ? limitar((t - ACORDO) / 10) : 0;
        const pulso = discordam && t >= DISCORDANCIA && t < ACORDO ? ((t - DISCORDANCIA) % 18) / 18 : 1;

        return (
          <g key={l.titulo} opacity={o}>
            {discordam ? (
              <rect x={X0 - 14} y={y - 10} width={LARGURA + 28} height={84} rx={6} fill={NEGATIVO} opacity={0.08 * alerta * (1 - resolvido)} />
            ) : null}
            <rect x={X0} y={y} width={620} height={64} rx={4} fill={CARTAO} stroke={LINHA} strokeWidth={2} />
            <text x={X0 + 22} y={y + 28} fontFamily={SANS} fontSize={21} fontWeight={700} fill={C.branco}>
              {l.titulo}
            </text>
            <text x={X0 + 22} y={y + 52} fontFamily={MONO} fontSize={14} fill="rgba(255,255,255,0.55)">
              {l.fonte}
            </text>

            {l.votos.map((v, i) => (
              <Voto key={i} voto={v} x={colunaLeitor(i)} y={y + 14} o={limitar((t - VOTO_EM(k, i)) / 6)} />
            ))}

            {/* O que aparece para a dupla */}
            {!discordam ? (
              <g opacity={decidido ? limitar((t - VOTO_EM(k, 1) - 10) / 8) : 0}>
                <circle cx={resultadoX + 14} cy={y + 32} r={13} fill={GELO} />
                <path d={`M${resultadoX + 8} ${y + 32} l4 4 l8 -9`} fill="none" stroke={FUNDO} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />
                <text x={resultadoX + 40} y={y + 39} fontFamily={SANS} fontSize={19} fill="rgba(255,255,255,0.85)">
                  De acordo: {l.final === 'inclui' ? 'incluir' : 'excluir'}
                </text>
              </g>
            ) : (
              <g>
                <g opacity={alerta * (1 - resolvido)}>
                  <circle cx={resultadoX + 14} cy={y + 32} r={13 + 10 * (1 - pulso)} fill="none" stroke={NEGATIVO} strokeWidth={2} opacity={pulso} />
                  <circle cx={resultadoX + 14} cy={y + 32} r={13} fill={NEGATIVO} />
                  <text x={resultadoX + 14} y={y + 39} textAnchor="middle" fontFamily={SANS} fontSize={18} fontWeight={800} fill={FUNDO}>
                    !
                  </text>
                  <text x={resultadoX + 40} y={y + 39} fontFamily={SANS} fontSize={19} fontWeight={700} fill={NEGATIVO}>
                    Vocês discordaram aqui
                  </text>
                </g>
                <g opacity={resolvido}>
                  <circle cx={resultadoX + 14} cy={y + 32} r={13} fill={GELO} />
                  <path d={`M${resultadoX + 8} ${y + 32} l4 4 l8 -9`} fill="none" stroke={FUNDO} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />
                  <text x={resultadoX + 40} y={y + 39} fontFamily={SANS} fontSize={19} fontWeight={700} fill={C.branco}>
                    Decidido juntos: incluir
                  </text>
                </g>
              </g>
            )}
          </g>
        );
      })}
    </g>
  );
};

/* ═══ 3 · Adaptar ════════════════════════════════════════════════════════ */

const TEMAS = [
  { tema: 'Políticas públicas', roteiro: 0 },
  { tema: 'Desenvolvimento regional', roteiro: 1 },
  { tema: 'Educação', roteiro: 0 },
  { tema: 'Gestão', roteiro: 2 },
  { tema: 'Meio ambiente', roteiro: 1 },
];

const ROTEIROS = [
  { nome: 'Campbell', nota: 'ciências sociais' },
  { nome: 'ROSES', nota: 'território e ambiente' },
  { nome: 'PRISMA 2020', nota: 'o padrão internacional' },
];

const TEMA_EM = (i: number) => ATO_TEMAS[0] + 28 + i * 12;
// A ficha precisa terminar de preencher antes de o laço começar a sumir.
const FICHA_EM = ATO_TEMAS[0] + 86;

const CAMPOS_FICHA = ['Onde foi estudado', 'Como se organiza', 'Política analisada', 'Indicador usado'];

const AtoTemas: React.FC<{ t: number }> = ({ t }) => {
  const temaY = (i: number) => 200 + i * 68;
  const roteiroY = (j: number) => 226 + j * 110;
  const roteiroX = 1560;

  return (
    <g>
      <text x={X0} y={124} fontFamily={MONO} fontSize={15} letterSpacing="0.16em" fill={GELO} opacity={suave(t, [ATO_TEMAS[0] + 4, ATO_TEMAS[0] + 18], [0, 1])}>
        TEMAS FORA DA ÁREA MÉDICA
      </text>
      <text x={X0} y={160} fontFamily={SANS} fontSize={26} fontWeight={600} fill={C.branco} opacity={suave(t, [ATO_TEMAS[0] + 8, ATO_TEMAS[0] + 22], [0, 1])}>
        O roteiro e a ficha acompanham o seu tema
      </text>

      {/* Ligações tema → roteiro */}
      {TEMAS.map((tm, i) => {
        const u = vaiEVolta(t, [TEMA_EM(i) + 4, TEMA_EM(i) + 18], [0, 1]);
        const x1 = X0 + 400;
        const y1 = temaY(i) + 20;
        const x2 = roteiroX - 6;
        const y2 = roteiroY(tm.roteiro) + 36;
        const pontos = Array.from({ length: 13 }, (_, k) => {
          const s = (k / 12) * u;
          const cx = x1 + (x2 - x1) * s;
          const e = s * s * (3 - 2 * s);
          return `${cx.toFixed(1)} ${(y1 + (y2 - y1) * e).toFixed(1)}`;
        });
        return u > 0 ? (
          <path key={tm.tema} d={`M${pontos.join(' L')}`} fill="none" stroke={GELO} strokeWidth={2} strokeDasharray="3 8" strokeLinecap="round" opacity={0.6} />
        ) : null;
      })}

      {TEMAS.map((tm, i) => {
        const o = suave(t, [TEMA_EM(i) - 10, TEMA_EM(i) + 4], [0, 1]);
        const dx = px((1 - o) * -16);
        return (
          <g key={tm.tema} opacity={o} transform={`translate(${dx} 0)`}>
            <rect x={X0} y={temaY(i)} width={400} height={44} rx={22} fill={CARTAO} stroke={GELO} strokeOpacity={0.55} strokeWidth={2} />
            <text x={X0 + 24} y={temaY(i) + 29} fontFamily={SANS} fontSize={20} fontWeight={600} fill={C.branco}>
              {tm.tema}
            </text>
          </g>
        );
      })}

      {ROTEIROS.map((r, j) => {
        const primeiro = TEMAS.findIndex((tm) => tm.roteiro === j);
        const o = suave(t, [TEMA_EM(primeiro) + 14, TEMA_EM(primeiro) + 26], [0, 1]);
        return (
          <g key={r.nome} opacity={o}>
            <rect x={roteiroX} y={roteiroY(j)} width={340} height={72} rx={4} fill={CARTAO} stroke={GELO} strokeWidth={2} />
            <rect x={roteiroX} y={roteiroY(j)} width={6} height={72} fill={GELO} />
            <text x={roteiroX + 26} y={roteiroY(j) + 32} fontFamily={SANS} fontSize={24} fontWeight={700} fill={C.branco}>
              {r.nome}
            </text>
            <text x={roteiroX + 26} y={roteiroY(j) + 56} fontFamily={MONO} fontSize={15} fill="rgba(255,255,255,0.6)">
              {r.nota}
            </text>
          </g>
        );
      })}

      {/* A ficha da revisão */}
      <g opacity={suave(t, [FICHA_EM, FICHA_EM + 16], [0, 1])}>
        <line x1={roteiroX + 346} y1={roteiroY(1) + 36} x2={2024} y2={roteiroY(1) + 36} stroke={GELO} strokeWidth={2} strokeDasharray="3 8" strokeLinecap="round" opacity={0.6} />
        <rect x={2030} y={196} width={410} height={326} rx={4} fill={C.superficie} opacity={0.97} />
        <rect x={2030} y={196} width={410} height={48} rx={4} fill={GELO} />
        <text x={2054} y={227} fontFamily={MONO} fontSize={16} fontWeight={700} letterSpacing="0.12em" fill={FUNDO}>
          FICHA DA SUA REVISÃO
        </text>
        {CAMPOS_FICHA.map((campo, k) => {
          const y = 272 + k * 62;
          const preenche = limitar((t - FICHA_EM - 14 - k * 8) / 10);
          return (
            <g key={campo}>
              <text x={2054} y={y} fontFamily={MONO} fontSize={14} letterSpacing="0.08em" fill={C.tintaSuave}>
                {campo.toUpperCase()}
              </text>
              <rect x={2054} y={y + 12} width={362} height={30} rx={3} fill={C.papel} stroke={C.borda} strokeWidth={1.5} />
              <rect x={2066} y={y + 23} width={px(220 * preenche) - (k % 2) * 60 * preenche} height={8} rx={2} fill={C.acento} opacity={0.75} />
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
    <Coluna t={t} kicker="PARA QUEM É" linhas={['Feito para quem', 'pesquisa no Brasil']} />
    <EstadoFaixa
      t={t}
      valores={[
        'Uma busca, cinco bases',
        'As brasileiras respondem',
        'Tudo veio das bases brasileiras',
        'Cada pessoa lê a sua parte',
        'Ele mostra onde discordaram',
        'O roteiro acompanha o tema',
        'E a ficha também',
      ]}
      trocas={[ENTRADA_BASE(0) + 10, TOTAL_EM, ATO_EQUIPE[0], DISCORDANCIA, ATO_TEMAS[0], FICHA_EM]}
      etapas={['Buscar', 'Ler juntos', 'Adaptar']}
      inicioDasEtapas={[0, ATO_EQUIPE[0], ATO_TEMAS[0]]}
    />
    <g opacity={opacidadeDoAto(t, -20, ATO_BUSCA[1])}>{t < ATO_BUSCA[1] ? <AtoBusca t={t} /> : null}</g>
    <g opacity={opacidadeDoAto(t, ATO_EQUIPE[0], ATO_EQUIPE[1])}>
      {t >= ATO_EQUIPE[0] && t < ATO_EQUIPE[1] ? <AtoEquipe t={t} /> : null}
    </g>
    <g opacity={opacidadeDoAto(t, ATO_TEMAS[0], ATO_TEMAS[1])}>{t >= ATO_TEMAS[0] ? <AtoTemas t={t} /> : null}</g>
  </Tela>
);

export const FaixaParaQuem: React.FC = () => {
  usarFontesDaMarca();
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ backgroundColor: FUNDO, overflow: 'hidden' }}>
      <Fundo />
      <LacoDeFaixa frame={frame} duracao={DURACAO_FAIXA_PARA_QUEM}>
        {(t) => <Cena t={t} />}
      </LacoDeFaixa>
    </AbsoluteFill>
  );
};
