/**
 * Revsist — Faixa "Quando alguém perguntar", da seção do registro na landing.
 *
 * Mesma família da faixa do "Por que existe" (fundo, coluna e paleta de
 * `components/faixa.tsx`). A história corre em dois tempos:
 *
 *   1. Hoje — você inclui um artigo. As quatro coisas que o Revsist guarda
 *      saem do artigo e entram no registro, uma a uma, e o registro é selado.
 *   2. Meses depois — a banca pergunta por que o estudo entrou. A resposta sai
 *      do registro, linha por linha, e o selo confere: nada foi alterado.
 *
 * O laço fecha como o dos laços de seção: a cena é montada duas vezes,
 * deslocada de um período, e chega a opacidade zero no último quadro.
 */

import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';
import { C, MONO, SANS } from '../theme';
import { px, suave, usarFontesDaMarca } from '../components/base';
import {
  CARTAO,
  Coluna,
  FUNDO,
  Fundo,
  GELO,
  LINHA,
  Tela,
  limitar,
  opacidadeDeTroca,
  vaiEVolta,
} from '../components/faixa';

export const DURACAO_FAIXA_REGISTRO = 480;
const FADE = 18;

/* ── Linha do tempo (quadros) ────────────────────────────────────────────── */

const CLIQUE = 52;
const SAIDA_PACOTE = (k: number) => 62 + k * 18;
const CHEGADA_PACOTE = (k: number) => SAIDA_PACOTE(k) + 16;
const SELO_INICIO = 140;
const SELO_FIM = 188;
const SELADO = 192;
const SALTO = 232;
const PERGUNTA = 272;
const LIGACAO = 300;
const DESTAQUE = (k: number) => 318 + k * 14;
const RESPOSTA = 328;
const CONFERE_INICIO = 384;
const CONFERE_FIM = 408;
const CONFERE = 412;

/* ── Conteúdo ────────────────────────────────────────────────────────────── */

const ARTIGO = { x: 860, y: 118, w: 330, h: 400 };
const REGISTRO = { x: 1560, y: 96, w: 880, h: 448, cabeca: 52, linha: 76 };

const LINHAS = [
  {
    campo: 'QUAL ERA O ARTIGO',
    valor: 'Dinâmica territorial no APL de manga e uva',
    nota: 'Tese · UFPE · 2023 · encontrada na BDTD',
  },
  {
    campo: 'O QUE FOI CONFERIDO',
    valor: 'Atendeu os dois critérios de inclusão',
    nota: '✓ governança territorial   ✓ semiárido',
  },
  {
    campo: 'QUEM DECIDIU',
    valor: 'Eduardo, com um segundo revisor',
    nota: 'a decisão foi conferida por duas pessoas',
  },
  {
    campo: 'QUANDO',
    valor: '10/09/2026, às 20h15',
    nota: 'horário de Brasília',
  },
];

const HASH = '9c3b4f51e0892acb7102e35a9812e4f01488c9f5d1a8e2074d2b9911e8c4a17b';

const ETAPAS = ['Decidir', 'Guardar', 'Consultar'];

const topoDaLinha = (k: number) => REGISTRO.y + REGISTRO.cabeca + k * REGISTRO.linha;

/** Data que corre de 10/09/2026 a 14/02/2027 durante o salto no tempo. */
const dataDoSalto = (t: number): string => {
  const dias = Math.round(vaiEVolta(t, [SALTO + 6, SALTO + 36], [0, 157]));
  const d = new Date(Date.UTC(2026, 8, 10 + dias));
  const dd = String(d.getUTCDate()).padStart(2, '0');
  const mm = String(d.getUTCMonth() + 1).padStart(2, '0');
  return `${dd}/${mm}/${d.getUTCFullYear()}`;
};

/* ── Coluna: o que está acontecendo ──────────────────────────────────────── */

const Estado: React.FC<{ t: number }> = ({ t }) => {
  const trocas = [60, SELO_INICIO, SELADO, PERGUNTA, RESPOSTA, CONFERE];
  const agora =
    t < 60
      ? 'Você decide'
      : t < SELO_INICIO
        ? 'O Revsist anota'
        : t < SELADO
          ? 'O registro é selado'
          : t < PERGUNTA
            ? 'Guardado, com data e hora'
            : t < RESPOSTA
              ? 'Meses depois, a pergunta'
              : t < CONFERE
                ? 'A resposta está no registro'
                : 'E nada foi alterado';
  const etapa = t < 60 ? 0 : t < SALTO ? 1 : 2;

  return (
    <g opacity={suave(t, [22, 38], [0, 1])}>
      <text x={120} y={402} fontFamily={MONO} fontSize={21} letterSpacing="0.24em" fill={GELO} opacity={0.8}>
        AGORA
      </text>
      <text
        x={120}
        y={450}
        fontFamily={SANS}
        fontSize={36}
        fontWeight={700}
        fill={C.branco}
        opacity={opacidadeDeTroca(t, trocas)}
      >
        {agora}
      </text>

      {ETAPAS.map((nome, i) => {
        const x = 120 + i * 200;
        const feita = i < etapa;
        const atual = i === etapa;
        return (
          <g key={nome} opacity={atual ? 1 : feita ? 0.7 : 0.35}>
            {i > 0 ? (
              // Do fim do rótulo anterior (~85 px em mono 20) até este ponto.
              <line x1={x - 66} y1={528} x2={x - 16} y2={528} stroke={GELO} strokeWidth={2} opacity={feita || atual ? 0.6 : 0.3} />
            ) : null}
            <circle cx={x} cy={528} r={9} fill={feita || atual ? GELO : FUNDO} stroke={GELO} strokeWidth={2.5} />
            <text x={x + 20} y={535} fontFamily={MONO} fontSize={20} fontWeight={atual ? 700 : 400} fill={C.branco}>
              {nome}
            </text>
          </g>
        );
      })}
    </g>
  );
};

/* ── Hoje: o artigo e a decisão ──────────────────────────────────────────── */

const Artigo: React.FC<{ t: number }> = ({ t }) => {
  const { x, y, w, h } = ARTIGO;
  const clicou = t >= CLIQUE;
  const pulso = limitar((t - CLIQUE) / 14);
  const criterio = (k: number) => limitar((t - 30 - k * 8) / 6);
  const aparece = suave(t, [8, 28], [0, 1]) * (1 - limitar((t - SALTO) / 16));

  return (
    <g opacity={aparece}>
      <rect x={x} y={y} width={w} height={h} rx={4} fill={CARTAO} stroke={LINHA} strokeWidth={2} />
      <rect x={x} y={y} width={w} height={40} rx={4} fill="rgba(163,206,241,0.12)" />
      <text x={x + 20} y={y + 27} fontFamily={MONO} fontSize={17} letterSpacing="0.08em" fill={GELO}>
        BDTD · TESE · 2023
      </text>

      {['Dinâmica territorial e', 'cooperação no APL de', 'manga e uva'].map((l, i) => (
        <text key={l} x={x + 20} y={y + 86 + i * 32} fontFamily={SANS} fontSize={25} fontWeight={700} fill={C.branco}>
          {l}
        </text>
      ))}
      <text x={x + 20} y={y + 192} fontFamily={MONO} fontSize={16} fill="rgba(255,255,255,0.6)">
        Souza, M. · UFPE
      </text>
      {[280, 250, 196].map((largura, i) => (
        <rect key={i} x={x + 20} y={y + 214 + i * 18} width={largura} height={7} rx={2} fill="rgba(255,255,255,0.18)" />
      ))}

      <text x={x + 20} y={y + 290} fontFamily={MONO} fontSize={14} letterSpacing="0.14em" fill={GELO} opacity={0.75}>
        SEUS CRITÉRIOS
      </text>
      {['governança', 'semiárido'].map((nome, k) => (
        <g key={nome} transform={`translate(${x + 20 + k * 150} ${y + 302})`}>
          <rect width={140} height={32} rx={16} fill="rgba(163,206,241,0.08)" stroke={GELO} strokeOpacity={0.35 + 0.5 * criterio(k)} strokeWidth={2} />
          <circle cx={18} cy={16} r={9} fill={GELO} opacity={criterio(k)} />
          <path d="M13 16 l3.5 3.5 l6 -7" fill="none" stroke={FUNDO} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" opacity={criterio(k)} />
          <text x={34} y={21} fontFamily={MONO} fontSize={15} fill={C.branco}>
            {nome}
          </text>
        </g>
      ))}

      {/* Botões de decisão */}
      <g transform={`translate(${x + 20} ${y + 350})`}>
        <rect width={140} height={34} rx={4} fill={clicou ? GELO : 'none'} stroke={GELO} strokeWidth={2} />
        <text x={70} y={23} textAnchor="middle" fontFamily={SANS} fontSize={17} fontWeight={700} fill={clicou ? FUNDO : GELO}>
          {clicou ? '✓ Incluído' : 'Incluir'}
        </text>
        {clicou && pulso < 1 ? (
          <rect
            x={-10 * pulso}
            y={-10 * pulso}
            width={140 + 20 * pulso}
            height={34 + 20 * pulso}
            rx={6}
            fill="none"
            stroke={GELO}
            strokeWidth={2}
            opacity={0.7 * (1 - pulso)}
          />
        ) : null}
      </g>
      <g transform={`translate(${x + 170} ${y + 350})`} opacity={clicou ? 0.35 : 1}>
        <rect width={140} height={34} rx={4} fill="none" stroke="rgba(163,206,241,0.4)" strokeWidth={2} />
        <text x={70} y={23} textAnchor="middle" fontFamily={SANS} fontSize={17} fontWeight={600} fill="rgba(255,255,255,0.7)">
          Excluir
        </text>
      </g>
    </g>
  );
};

const Cursor: React.FC<{ t: number }> = ({ t }) => {
  const destino = { x: ARTIGO.x + 100, y: ARTIGO.y + 372 };
  const x = vaiEVolta(t, [30, 48], [1120, destino.x]);
  const y = vaiEVolta(t, [30, 48], [590, destino.y]);
  const aperto = t >= CLIQUE - 2 && t < CLIQUE + 3 ? 0.9 : 1;
  const opacidade = suave(t, [24, 32], [0, 1]) * (1 - limitar((t - 66) / 10));
  return (
    <g transform={`translate(${px(x)} ${px(y)}) scale(${aperto})`} opacity={opacidade}>
      <path d="M0 0 L0 40 L10 31 L17 47 L25 44 L18 28 L31 28 Z" fill={C.branco} stroke={FUNDO} strokeWidth={2.5} strokeLinejoin="round" />
    </g>
  );
};

/** Os quatro "pacotes" que levam o que foi decidido até o registro. */
const Pacotes: React.FC<{ t: number }> = ({ t }) => {
  const origem = { x: ARTIGO.x + ARTIGO.w + 4, y: ARTIGO.y + 200 };
  const somem = 1 - limitar((t - SALTO) / 14);
  return (
    <g opacity={somem}>
      {LINHAS.map((_, k) => {
        const alvo = { x: REGISTRO.x - 6, y: topoDaLinha(k) + REGISTRO.linha / 2 };
        const u = vaiEVolta(t, [SAIDA_PACOTE(k), CHEGADA_PACOTE(k)], [0, 1]);
        const partiu = t >= SAIDA_PACOTE(k) - 4;
        const trilha = limitar((t - SAIDA_PACOTE(k) + 4) / 6);
        const cx = origem.x + (alvo.x - origem.x) * u;
        const cy = origem.y + (alvo.y - origem.y) * u;
        const noCaminho = t >= SAIDA_PACOTE(k) && t < CHEGADA_PACOTE(k) + 4;
        return (
          <g key={k}>
            {partiu ? (
              <line
                x1={origem.x}
                y1={origem.y}
                x2={origem.x + (alvo.x - origem.x) * trilha}
                y2={origem.y + (alvo.y - origem.y) * trilha}
                stroke={GELO}
                strokeWidth={2}
                strokeDasharray="3 9"
                strokeLinecap="round"
                opacity={0.45}
              />
            ) : null}
            {noCaminho ? (
              <g transform={`translate(${px(cx)} ${px(cy)})`}>
                <rect x={-22} y={-17} width={44} height={34} rx={17} fill={GELO} />
                <text y={7} textAnchor="middle" fontFamily={MONO} fontSize={19} fontWeight={700} fill={FUNDO}>
                  {k + 1}
                </text>
              </g>
            ) : null}
          </g>
        );
      })}
    </g>
  );
};

/* ── O registro, comum aos dois tempos ───────────────────────────────────── */

const Registro: React.FC<{ t: number }> = ({ t }) => {
  const { x, y, w, h, cabeca, linha } = REGISTRO;
  const digitados = Math.floor(interpolate(t, [SELO_INICIO, SELO_FIM], [0, HASH.length], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }));
  const selado = limitar((t - SELADO) / 8);
  const conferindo = t >= CONFERE_INICIO && t < CONFERE;
  const varre = interpolate(t, [CONFERE_INICIO, CONFERE_FIM], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const confere = limitar((t - CONFERE) / 8);
  const larguraHash = 19 * 0.6 * HASH.length;

  return (
    <g opacity={suave(t, [14, 36], [0, 1])}>
      <rect x={x} y={y} width={w} height={h} rx={4} fill={CARTAO} stroke={LINHA} strokeWidth={2} />
      <rect x={x} y={y} width={w} height={cabeca} rx={4} fill="rgba(163,206,241,0.12)" />
      <text x={x + 24} y={y + 33} fontFamily={MONO} fontSize={19} letterSpacing="0.16em" fill={GELO}>
        REGISTRO DA DECISÃO
      </text>
      <text x={x + w - 24} y={y + 33} textAnchor="end" fontFamily={MONO} fontSize={19} fill="rgba(255,255,255,0.55)">
        #0412
      </text>

      {LINHAS.map((l, k) => {
        const topo = topoDaLinha(k);
        const chegou = limitar((t - CHEGADA_PACOTE(k)) / 8);
        const brilho = t >= CHEGADA_PACOTE(k) ? 1 - limitar((t - CHEGADA_PACOTE(k)) / 20) : 0;
        const destaque = limitar((t - DESTAQUE(k)) / 8);
        return (
          <g key={l.campo}>
            <rect
              x={x + 2}
              y={topo}
              width={w - 4}
              height={linha}
              fill={GELO}
              opacity={Math.max(0.14 * brilho, 0.09 * destaque)}
            />
            {destaque > 0 ? <rect x={x + 2} y={topo} width={4} height={linha} fill={GELO} opacity={destaque} /> : null}
            <line x1={x + 16} y1={topo + linha} x2={x + w - 16} y2={topo + linha} stroke="rgba(163,206,241,0.14)" strokeWidth={1.5} />
            <text x={x + 24} y={topo + 44} fontFamily={MONO} fontSize={17} letterSpacing="0.08em" fill={GELO} opacity={0.35 + 0.55 * chegou}>
              {l.campo}
            </text>
            <g opacity={chegou}>
              <text x={x + 300} y={topo + 36} fontFamily={SANS} fontSize={24} fontWeight={600} fill={C.branco}>
                {l.valor}
              </text>
              <text x={x + 300} y={topo + 62} fontFamily={MONO} fontSize={16} fill="rgba(255,255,255,0.6)">
                {l.nota}
              </text>
            </g>
          </g>
        );
      })}

      {/* O selo */}
      <g>
        <rect x={x + 16} y={y + 364} width={w - 32} height={70} rx={4} fill="rgba(0,0,0,0.2)" />
        <text x={x + 36} y={y + 390} fontFamily={MONO} fontSize={16} letterSpacing="0.16em" fill={GELO} opacity={0.85}>
          SELO DE QUE NADA MUDOU
        </text>
        <text x={x + 36} y={y + 420} fontFamily={MONO} fontSize={19} fill={C.branco}>
          {HASH.slice(0, digitados)}
        </text>
        {conferindo ? (
          <rect x={x + 36} y={y + 400} width={larguraHash * varre} height={28} fill={GELO} opacity={0.22} />
        ) : null}

        <g opacity={selado * (1 - confere)} transform={`translate(${x + w - 182} ${y + 372})`}>
          <rect width={158} height={28} rx={14} fill="none" stroke={GELO} strokeWidth={2} />
          <text x={79} y={19} textAnchor="middle" fontFamily={MONO} fontSize={15} fontWeight={700} fill={GELO}>
            {conferindo ? 'CONFERINDO…' : 'SELADO'}
          </text>
        </g>
        <g opacity={confere} transform={`translate(${x + w - 322} ${y + 372})`}>
          <rect width={298} height={28} rx={14} fill={GELO} />
          <text x={149} y={19} textAnchor="middle" fontFamily={MONO} fontSize={15} fontWeight={700} fill={FUNDO}>
            ✓ CONFERE COM O ORIGINAL
          </text>
        </g>
      </g>
    </g>
  );
};

/* ── Meses depois: a pergunta e a resposta ───────────────────────────────── */

const MesesDepois: React.FC<{ t: number }> = ({ t }) => {
  const x = ARTIGO.x;
  const data = suave(t, [SALTO + 4, SALTO + 18], [0, 1]);
  const pergunta = suave(t, [PERGUNTA, PERGUNTA + 18], [0, 1]);
  const ligacao = limitar((t - LIGACAO) / 16);
  const respostaLinhas = [
    'Atendeu os dois critérios de inclusão.',
    'Decidido por Eduardo, conferido por um',
    'segundo revisor, em 10/09/2026, às 20h15.',
  ];

  return (
    <g>
      <g opacity={data}>
        <text x={x} y={128} fontFamily={MONO} fontSize={18} letterSpacing="0.2em" fill={GELO}>
          MESES DEPOIS
        </text>
        <text x={x} y={176} fontFamily={MONO} fontSize={40} fontWeight={700} fill={C.branco} style={{ fontVariantNumeric: 'tabular-nums' }}>
          {dataDoSalto(t)}
        </text>
      </g>

      <g opacity={pergunta} transform={`translate(0 ${px((1 - pergunta) * 14)})`}>
        <rect x={x} y={212} width={620} height={116} rx={6} fill={CARTAO} stroke={GELO} strokeOpacity={0.5} strokeWidth={2} />
        <path d={`M${x + 40} 327 l0 26 l26 -26`} fill={CARTAO} stroke={GELO} strokeOpacity={0.5} strokeWidth={2} strokeLinejoin="round" />
        <rect x={x + 41} y={322} width={24} height={8} fill={CARTAO} />
        <text x={x + 24} y={248} fontFamily={MONO} fontSize={16} letterSpacing="0.16em" fill={GELO}>
          A BANCA PERGUNTA
        </text>
        <text x={x + 24} y={298} fontFamily={SANS} fontSize={29} fontWeight={700} fill={C.branco}>
          Por que este estudo entrou na revisão?
        </text>
      </g>

      {/* Da pergunta ao registro */}
      <line
        x1={x + 620}
        y1={270}
        x2={x + 620 + (REGISTRO.x - 10 - x - 620) * ligacao}
        y2={270}
        stroke={GELO}
        strokeWidth={2.5}
        strokeDasharray="3 9"
        strokeLinecap="round"
        opacity={ligacao > 0 ? 0.7 : 0}
      />
      <path
        d={`M${REGISTRO.x - 22} 262 l10 8 l-10 8`}
        fill="none"
        stroke={GELO}
        strokeWidth={2.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={limitar((t - LIGACAO - 14) / 4)}
      />

      <g opacity={suave(t, [RESPOSTA, RESPOSTA + 16], [0, 1])}>
        <rect x={x} y={386} width={620} height={150} rx={6} fill="rgba(163,206,241,0.08)" />
        <rect x={x} y={386} width={4} height={150} fill={GELO} />
        <text x={x + 26} y={420} fontFamily={MONO} fontSize={16} letterSpacing="0.16em" fill={GELO}>
          A RESPOSTA, NO REGISTRO
        </text>
        {respostaLinhas.map((l, i) => (
          <text
            key={l}
            x={x + 26}
            y={458 + i * 30}
            fontFamily={SANS}
            fontSize={23}
            fill={C.branco}
            opacity={suave(t, [RESPOSTA + 6 + i * 10, RESPOSTA + 20 + i * 10], [0, 1])}
          >
            {l}
          </text>
        ))}
      </g>
    </g>
  );
};

/* ═══ Montagem ═══════════════════════════════════════════════════════════ */

const Cena: React.FC<{ t: number }> = ({ t }) => (
  <Tela>
    <Coluna t={t} kicker="QUANDO ALGUÉM PERGUNTAR" linhas={['Cada decisão', 'vira um registro']} />
    <Estado t={t} />
    <Artigo t={t} />
    <Registro t={t} />
    <Pacotes t={t} />
    {t >= SALTO ? <MesesDepois t={t} /> : null}
    {t < 80 ? <Cursor t={t} /> : null}
  </Tela>
);

export const FaixaRegistro: React.FC = () => {
  usarFontesDaMarca();
  const frame = useCurrentFrame();
  const duracao = DURACAO_FAIXA_REGISTRO - FADE;

  return (
    <AbsoluteFill style={{ backgroundColor: FUNDO, overflow: 'hidden' }}>
      <Fundo />
      {[0, DURACAO_FAIXA_REGISTRO].map((inicio) => {
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
