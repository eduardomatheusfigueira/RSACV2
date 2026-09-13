/**
 * Revsist — Faixa "Na mão × No Revsist", da seção "Por que existe" da landing.
 *
 * Clipe ultralargo (4:1) que conta a diferença numa passada só:
 *
 *   1. Na mão — cinco sites, uma planilha e uma pilha de PDFs, com o cursor
 *      indo e voltando entre eles e o rastro desse percurso se embolando.
 *   2. Uma varredura atravessa a faixa e limpa a bagunça.
 *   3. No Revsist — um trilho só, do plano à ficha, dizendo o que fazer agora,
 *      o que vem em seguida e o que já está feito.
 *
 * Fundo, coluna de texto e paleta vêm de `components/faixa.tsx`, comuns às
 * faixas da landing.
 */

import React from 'react';
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from 'remotion';
import { C, MONO, SANS } from '../theme';
import { px, suave, usarFontesDaMarca } from '../components/base';
import {
  CARTAO,
  Coluna,
  FUNDO,
  Fundo,
  GELO,
  LINHA,
  NEGATIVO,
  Tela,
  W,
  limitar,
  vaiEVolta,
} from '../components/faixa';

export const DURACAO_FAIXA = 480;

/** Quadros, no tempo do ato 1, em que a varredura atravessa a faixa. */
const VARREDURA: [number, number] = [196, 236];
const INICIO_ATO_2 = VARREDURA[0];
const DURACAO_ATO_2 = DURACAO_FAIXA - INICIO_ATO_2;
const FADE = 22;

/* ═══ Ato 1 · Na mão ═════════════════════════════════════════════════════ */

type Ponto = { x: number; y: number };

const ABAS = [
  { nome: 'BDTD', x: 860, y: 104 },
  { nome: 'SciELO', x: 1110, y: 292 },
  { nome: 'Scopus', x: 850, y: 408 },
  { nome: 'OpenAlex', x: 1310, y: 86 },
  { nome: 'PubMed', x: 1340, y: 424 },
];

const PLANILHA = { x: 1620, y: 96, w: 500, h: 448, linha: 40, topo: 76 };
const PDF = { x: 2180, y: 110 };

/** O percurso do cursor: sempre de volta à planilha. */
const ROTA = [
  'BDTD',
  'planilha',
  'SciELO',
  'planilha',
  'pdf',
  'planilha',
  'Scopus',
  'planilha',
  'OpenAlex',
  'pdf',
  'planilha',
  'PubMed',
  'planilha',
];

const T0 = 26;
const PASSO = 13;
const VIAGEM = 9;

/** Linha da planilha que cada chegada preenche. */
const LINHA_DA_PARADA = ROTA.map((_, i) => ROTA.slice(0, i).filter((id) => id === 'planilha').length);

const alvo = (id: string, linha: number): Ponto => {
  if (id === 'planilha') {
    return {
      x: PLANILHA.x + 300,
      y: PLANILHA.y + PLANILHA.topo + linha * PLANILHA.linha + 20,
    };
  }
  if (id === 'pdf') return { x: PDF.x + 110, y: PDF.y + 150 };
  const aba = ABAS.find((a) => a.nome === id)!;
  return { x: aba.x + 110, y: aba.y + 72 };
};

const PONTOS = ROTA.map((id, i) => alvo(id, LINHA_DA_PARADA[i]));

/** Curva de cada salto, alternando o lado para o rastro se embolar. */
const naCurva = (salto: number, u: number): Ponto => {
  const a = PONTOS[salto];
  const b = PONTOS[salto + 1];
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const comprimento = Math.hypot(dx, dy) || 1;
  const lado = (salto % 2 === 0 ? 1 : -1) * 0.28 * comprimento;
  const cx = (a.x + b.x) / 2 - (dy / comprimento) * lado;
  const cy = (a.y + b.y) / 2 + (dx / comprimento) * lado;
  const v = 1 - u;
  return {
    x: v * v * a.x + 2 * v * u * cx + u * u * b.x,
    y: v * v * a.y + 2 * v * u * cy + u * u * b.y,
  };
};

/** Início do salto que sai da parada `i`, e chegada à parada `i`. */
const saidaDe = (i: number): number => T0 + i * PASSO;
const chegadaEm = (i: number): number => T0 + (i - 1) * PASSO + VIAGEM;

const Aba: React.FC<{ nome: string; x: number; y: number; ativa: boolean; opacidade: number }> = ({
  nome,
  x,
  y,
  ativa,
  opacidade,
}) => (
  <g opacity={opacidade}>
    <rect
      x={x}
      y={y}
      width={220}
      height={120}
      rx={4}
      fill={CARTAO}
      stroke={ativa ? GELO : LINHA}
      strokeWidth={ativa ? 3 : 2}
    />
    <rect x={x} y={y} width={220} height={30} rx={4} fill="rgba(163,206,241,0.10)" />
    <circle cx={x + 16} cy={y + 15} r={4} fill="rgba(163,206,241,0.45)" />
    <text x={x + 30} y={y + 21} fontFamily={MONO} fontSize={17} fill={GELO} letterSpacing="0.04em">
      {nome}
    </text>
    <rect
      x={x + 16}
      y={y + 46}
      width={188}
      height={20}
      rx={2}
      fill="rgba(255,255,255,0.06)"
      stroke="rgba(163,206,241,0.2)"
    />
    <rect x={x + 16} y={y + 80} width={150} height={7} rx={2} fill="rgba(255,255,255,0.18)" />
    <rect x={x + 16} y={y + 96} width={120} height={7} rx={2} fill="rgba(255,255,255,0.12)" />
  </g>
);

const Planilha: React.FC<{ t: number; ativa: boolean }> = ({ t, ativa }) => {
  const { x, y, w, h, linha, topo } = PLANILHA;
  const larguraCol = (w - 44) / 4;
  const chegadas = ROTA.map((id, i) => (id === 'planilha' ? chegadaEm(i) : null)).filter(
    (v): v is number => v !== null,
  );

  return (
    <g opacity={suave(t, [10, 26], [0, 1])}>
      <rect
        x={x}
        y={y}
        width={w}
        height={h}
        rx={4}
        fill={CARTAO}
        stroke={ativa ? GELO : LINHA}
        strokeWidth={ativa ? 3 : 2}
      />
      <rect x={x} y={y} width={w} height={44} rx={4} fill="rgba(163,206,241,0.12)" />
      <text x={x + 18} y={y + 29} fontFamily={MONO} fontSize={19} fill="rgba(255,255,255,0.85)">
        revisao_FINAL_v3.xlsx
      </text>

      {['A', 'B', 'C', 'D'].map((letra, c) => (
        <text
          key={letra}
          x={x + 44 + larguraCol * c + larguraCol / 2}
          y={y + 67}
          textAnchor="middle"
          fontFamily={MONO}
          fontSize={16}
          fill="rgba(163,206,241,0.6)"
        >
          {letra}
        </text>
      ))}

      {Array.from({ length: 10 }, (_, r) => (
        <line
          key={`h-${r}`}
          x1={x}
          y1={y + topo + r * linha}
          x2={x + w}
          y2={y + topo + r * linha}
          stroke="rgba(163,206,241,0.14)"
          strokeWidth={1.5}
        />
      ))}
      {Array.from({ length: 4 }, (_, c) => (
        <line
          key={`v-${c}`}
          x1={x + 44 + larguraCol * c}
          y1={y + 44}
          x2={x + 44 + larguraCol * c}
          y2={y + topo + 9 * linha}
          stroke="rgba(163,206,241,0.14)"
          strokeWidth={1.5}
        />
      ))}

      {chegadas.map((chegada, r) => {
        const s = limitar((t - chegada) / 6);
        if (s <= 0) return null;
        return [0, 1, 2, 3].map((c) => (
          <rect
            key={`${r}-${c}`}
            x={x + 44 + larguraCol * c + 12}
            y={y + topo + r * linha + 15}
            width={px([70, 92, 58, 80][(r + c) % 4] * s)}
            height={10}
            rx={2}
            fill="rgba(255,255,255,0.55)"
          />
        ));
      })}
    </g>
  );
};

const PilhaDePdf: React.FC<{ t: number; ativa: boolean }> = ({ t, ativa }) => {
  const documento = (dx: number, dy: number) =>
    `M${PDF.x + dx} ${PDF.y + dy} H${PDF.x + dx + 160} L${PDF.x + dx + 200} ${PDF.y + dy + 40} V${
      PDF.y + dy + 280
    } H${PDF.x + dx} Z`;
  const progresso = t > 20 ? ((t - 20) % 58) / 58 : 0;

  return (
    <g opacity={suave(t, [18, 34], [0, 1])}>
      {[36, 18].map((d) => (
        <path key={d} d={documento(d, d)} fill={CARTAO} stroke={LINHA} strokeWidth={2} opacity={0.7} />
      ))}
      <path d={documento(0, 0)} fill={CARTAO} stroke={ativa ? GELO : LINHA} strokeWidth={ativa ? 3 : 2} />
      <text x={PDF.x + 24} y={PDF.y + 72} fontFamily={MONO} fontSize={28} fontWeight={700} fill={GELO}>
        PDF
      </text>
      {[140, 120, 150, 96].map((largura, i) => (
        <rect
          key={i}
          x={PDF.x + 24}
          y={PDF.y + 104 + i * 24}
          width={largura}
          height={7}
          rx={2}
          fill="rgba(255,255,255,0.2)"
        />
      ))}
      <rect x={PDF.x + 24} y={PDF.y + 222} width={152} height={10} rx={2} fill="rgba(163,206,241,0.15)" />
      <rect
        x={PDF.x + 24}
        y={PDF.y + 222}
        width={px(152 * progresso)}
        height={10}
        rx={2}
        fill={GELO}
      />
      <text x={PDF.x + 24} y={PDF.y + 258} fontFamily={MONO} fontSize={16} fill="rgba(255,255,255,0.7)">
        {`baixando… ${Math.round(progresso * 100)}%`}
      </text>
    </g>
  );
};

const Atalho: React.FC<{ ponto: Ponto; texto: string; opacidade: number }> = ({
  ponto,
  texto,
  opacidade,
}) => (
  <g opacity={opacidade} transform={`translate(${px(ponto.x + 26)} ${px(ponto.y - 62)})`}>
    <rect width={116} height={40} rx={4} fill={C.branco} />
    <text
      x={58}
      y={27}
      textAnchor="middle"
      fontFamily={MONO}
      fontSize={20}
      fontWeight={700}
      fill={FUNDO}
    >
      {texto}
    </text>
  </g>
);

const AtoNaMao: React.FC<{ t: number }> = ({ t }) => {
  const saltos = PONTOS.length - 1;
  const bruto = (t - T0) / PASSO;
  const salto = Math.max(0, Math.min(saltos - 1, Math.floor(bruto)));
  const u = t < T0 ? 0 : bruto >= saltos ? 1 : Easing.inOut(Easing.cubic)(limitar((t - saidaDe(salto)) / VIAGEM));
  const cursor = naCurva(salto, u);

  // Parada em que o cursor está agora, para acender o que ele está usando.
  const parado = t >= T0 && (u >= 1 || u <= 0);
  const paradaAtual = !parado ? null : u >= 1 ? ROTA[salto + 1] : ROTA[salto];

  const rastro = (() => {
    if (t < T0) return '';
    const pontos: Ponto[] = [PONTOS[0]];
    for (let s = 0; s <= salto; s++) {
      const fim = s < salto ? 1 : u;
      for (let k = 1; k <= 18; k++) pontos.push(naCurva(s, (k / 18) * fim));
    }
    return `M${pontos.map((p) => `${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' L')}`;
  })();

  const pulso = (evento: number) =>
    interpolate(t, [evento - 2, evento + 2, evento + 10, evento + 15], [0, 1, 1, 0], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    });

  return (
    <Tela>
      <Coluna t={t} kicker="NA MÃO" linhas={['Cinco sites,', 'uma planilha', 'e muito copiar e colar']} />

      <g opacity={suave(t, [30, 46], [0, 1])}>
        <text
          x={120}
          y={472}
          fontFamily={MONO}
          fontSize={46}
          fontWeight={700}
          fill={GELO}
          style={{ fontVariantNumeric: 'tabular-nums' }}
        >
          {Math.min(14, 3 + Math.floor(Math.max(0, t) / 15))}
        </text>
        <text x={250} y={466} fontFamily={MONO} fontSize={22} letterSpacing="0.12em" fill="rgba(255,255,255,0.72)">
          ABAS ABERTAS
        </text>
        <text
          x={120}
          y={534}
          fontFamily={MONO}
          fontSize={46}
          fontWeight={700}
          fill={GELO}
          style={{ fontVariantNumeric: 'tabular-nums' }}
        >
          {Math.round(interpolate(t, [T0, VARREDURA[0]], [0, 238], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }))}
        </text>
        <text x={250} y={528} fontFamily={MONO} fontSize={22} letterSpacing="0.12em" fill="rgba(255,255,255,0.72)">
          VEZES QUE VOCÊ COPIOU E COLOU
        </text>
      </g>

      {ABAS.map((aba, i) => (
        <Aba
          key={aba.nome}
          {...aba}
          ativa={paradaAtual === aba.nome}
          opacidade={suave(t, [4 + i * 6, 18 + i * 6], [0, 1])}
        />
      ))}
      <Planilha t={t} ativa={paradaAtual === 'planilha'} />
      <PilhaDePdf t={t} ativa={paradaAtual === 'pdf'} />

      <path
        d={rastro}
        fill="none"
        stroke={GELO}
        strokeWidth={3}
        strokeLinecap="round"
        strokeDasharray="1 11"
        opacity={0.55}
      />

      {ROTA.map((id, i) => {
        if (id === 'planilha') {
          return i === 0 ? null : (
            <Atalho key={`v-${i}`} ponto={PONTOS[i]} texto="Ctrl+V" opacidade={pulso(chegadaEm(i))} />
          );
        }
        return i === ROTA.length - 1 ? null : (
          <Atalho key={`c-${i}`} ponto={PONTOS[i]} texto="Ctrl+C" opacidade={pulso(saidaDe(i) - 3)} />
        );
      })}

      <g
        transform={`translate(${px(cursor.x)} ${px(cursor.y)})`}
        opacity={suave(t, [16, 26], [0, 1])}
      >
        <path
          d="M0 0 L0 40 L10 31 L17 47 L25 44 L18 28 L31 28 Z"
          fill={C.branco}
          stroke={FUNDO}
          strokeWidth={2.5}
          strokeLinejoin="round"
        />
      </g>
    </Tela>
  );
};

/* ═══ Ato 2 · No Revsist ═════════════════════════════════════════════════ */

const ESTACOES = [
  { nome: 'Plano da pesquisa', detalhe: 'definido uma vez' },
  { nome: 'Busca', detalhe: 'nas 5 bases juntas' },
  { nome: 'Títulos e resumos', detalhe: 'numa tela só' },
  { nome: 'Texto completo', detalhe: 'o PDF vem até você' },
  { nome: 'Ficha', detalhe: 'perguntas já prontas' },
];

const XS = [940, 1290, 1640, 1990, 2330];
const TRILHO = { de: 880, ate: 2420, y: 400 };
const S = [40, 78, 116, 154, 192];
const FIM = 230;
const DURACAO_ESTACAO = 32;

type Estado = 'pendente' | 'ativa' | 'feita';

const estadoDa = (k: number, t: number): Estado => {
  const termino = k < S.length - 1 ? S[k + 1] : FIM;
  if (t < S[k]) return 'pendente';
  if (t < termino) return 'ativa';
  return 'feita';
};

const IlustraPlano: React.FC<{ u: number }> = ({ u }) => (
  <g>
    <rect x={-80} y={140} width={160} height={200} rx={4} fill={CARTAO} stroke={LINHA} strokeWidth={2} />
    <rect x={-80} y={140} width={160} height={30} rx={4} fill="rgba(163,206,241,0.16)" />
    {[120, 96, 130, 84, 110].map((largura, i) => (
      <rect
        key={i}
        x={-60}
        y={192 + i * 26}
        width={px(largura * limitar(u * 6 - i))}
        height={8}
        rx={2}
        fill="rgba(255,255,255,0.6)"
      />
    ))}
    <g opacity={limitar((u - 0.72) / 0.15)}>
      <circle cx={70} cy={322} r={28} fill={GELO} />
      <path d="M62 318v-7a8 8 0 0 1 16 0v7" fill="none" stroke={FUNDO} strokeWidth={4} />
      <rect x={57} y={317} width={26} height={20} rx={3} fill={FUNDO} />
    </g>
  </g>
);

const PILULAS = [
  { nome: 'BDTD', x: -128, y: 150 },
  { nome: 'SciELO', x: 0, y: 150 },
  { nome: 'Scopus', x: 128, y: 150 },
  { nome: 'OpenAlex', x: -64, y: 204 },
  { nome: 'PubMed', x: 64, y: 204 },
];

const IlustraBusca: React.FC<{ u: number }> = ({ u }) => {
  const junta = vaiEVolta(u, [0.3, 0.65], [0, 1]);
  const traco = limitar((u - 0.05) / 0.25);
  const somePilula = 1 - limitar((u - 0.5) / 0.15);
  // Depois de juntar, as cinco bases ficam marcadas de leve na origem: o
  // quadro parado ainda lê "cinco bases, um resultado".
  const vestigio = 0.24 * limitar((u - 0.7) / 0.15);
  const destino = { x: 0, y: 293 };

  return (
    <g>
      {PILULAS.map((p) => (
        <line
          key={`l-${p.nome}`}
          x1={p.x}
          y1={p.y}
          x2={p.x + (destino.x - p.x) * traco}
          y2={p.y + (destino.y - p.y) * traco}
          stroke={GELO}
          strokeWidth={2}
          strokeDasharray="4 6"
          opacity={Math.max(0.5 * somePilula, vestigio)}
        />
      ))}
      {PILULAS.map((p) => (
        <g key={`v-${p.nome}`} transform={`translate(${p.x} ${p.y})`} opacity={vestigio}>
          <rect x={-59} y={-18} width={118} height={36} rx={18} fill={CARTAO} stroke={GELO} strokeWidth={2} />
          <text y={6} textAnchor="middle" fontFamily={MONO} fontSize={17} fill={GELO}>
            {p.nome}
          </text>
        </g>
      ))}
      {PILULAS.map((p) => {
        const x = px(p.x + (destino.x - p.x) * junta);
        const y = px(p.y + (destino.y - p.y) * junta);
        return (
          <g key={p.nome} transform={`translate(${x} ${y})`} opacity={somePilula}>
            <rect x={-59} y={-18} width={118} height={36} rx={18} fill={CARTAO} stroke={GELO} strokeOpacity={0.55} strokeWidth={2} />
            <text y={6} textAnchor="middle" fontFamily={MONO} fontSize={17} fill={GELO}>
              {p.nome}
            </text>
          </g>
        );
      })}
      <g opacity={limitar((u - 0.6) / 0.15)}>
        <rect x={-104} y={270} width={208} height={46} rx={23} fill={GELO} />
        <text y={301} textAnchor="middle" fontFamily={SANS} fontSize={24} fontWeight={700} fill={FUNDO}>
          231 artigos
        </text>
      </g>
    </g>
  );
};

const DECISOES = [
  { sim: true, marca: 0.12, sai: [0.22, 0.4] },
  { sim: false, marca: 0.5, sai: [0.6, 0.78] },
  { sim: true, marca: 0.88, sai: null },
];

const IlustraTitulos: React.FC<{ u: number }> = ({ u }) => {
  const saidas = DECISOES.map((d) => (d.sai ? vaiEVolta(u, d.sai, [0, 1]) : 0));

  return (
    <g>
      {[2, 1, 0].map((i) => {
        const d = DECISOES[i];
        const posicao = i - saidas.slice(0, i).reduce((a, b) => a + b, 0);
        const x = px(-110 + posicao * 14 + saidas[i] * 80);
        const y = px(160 + posicao * 14);
        return (
          <g key={i} transform={`translate(${x} ${y})`} opacity={1 - saidas[i]}>
            <rect width={220} height={124} rx={4} fill={CARTAO} stroke={LINHA} strokeWidth={2} />
            <rect x={18} y={22} width={150} height={10} rx={2} fill="rgba(255,255,255,0.7)" />
            {[180, 160, 120].map((largura, k) => (
              <rect key={k} x={18} y={50 + k * 18} width={largura} height={7} rx={2} fill="rgba(255,255,255,0.28)" />
            ))}
            <g opacity={limitar((u - d.marca) / 0.06)}>
              <circle cx={212} cy={8} r={19} fill={d.sim ? GELO : NEGATIVO} />
              <path
                d={d.sim ? 'M203 8 L210 15 L222 1' : 'M205 1 L219 15 M219 1 L205 15'}
                fill="none"
                stroke={FUNDO}
                strokeWidth={3.5}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </g>
          </g>
        );
      })}
    </g>
  );
};

const IlustraTexto: React.FC<{ u: number }> = ({ u }) => {
  const r = 34;
  const circunferencia = 2 * Math.PI * r;
  const carga = limitar(u / 0.7);
  const pronto = limitar((u - 0.72) / 0.1);

  return (
    <g>
      <path d="M-100 150 H20 L50 180 V340 H-100 Z" fill={CARTAO} stroke={LINHA} strokeWidth={2} />
      <text x={-78} y={206} fontFamily={MONO} fontSize={28} fontWeight={700} fill={GELO}>
        PDF
      </text>
      {[110, 90, 120, 70].map((largura, i) => (
        <rect key={i} x={-78} y={234 + i * 22} width={largura} height={7} rx={2} fill="rgba(255,255,255,0.22)" />
      ))}
      <circle cx={62} cy={300} r={r + 10} fill={FUNDO} />
      <circle cx={62} cy={300} r={r} fill="none" stroke="rgba(163,206,241,0.2)" strokeWidth={6} />
      <circle
        cx={62}
        cy={300}
        r={r}
        fill="none"
        stroke={GELO}
        strokeWidth={6}
        strokeDasharray={`${circunferencia * carga} ${circunferencia}`}
        transform="rotate(-90 62 300)"
      />
      <path
        d="M62 284 V314 M50 303 L62 315 L74 303"
        fill="none"
        stroke={C.branco}
        strokeWidth={4}
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={1 - pronto}
      />
      <path
        d="M48 300 L58 310 L77 290"
        fill="none"
        stroke={GELO}
        strokeWidth={5}
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={pronto}
      />
    </g>
  );
};

const IlustraFicha: React.FC<{ u: number }> = ({ u }) => (
  <g>
    <rect x={-110} y={150} width={220} height={190} rx={4} fill={CARTAO} stroke={LINHA} strokeWidth={2} />
    <rect x={-110} y={150} width={220} height={30} rx={4} fill="rgba(163,206,241,0.16)" />
    {[0, 1, 2, 3].map((i) => (
      <g key={i}>
        <rect x={-92} y={202 + i * 36} width={48} height={8} rx={2} fill="rgba(163,206,241,0.55)" />
        <rect
          x={-30}
          y={202 + i * 36}
          width={px(112 * limitar(u * 4.5 - i))}
          height={8}
          rx={2}
          fill="rgba(255,255,255,0.75)"
        />
        {i < 3 ? (
          <line x1={-92} y1={224 + i * 36} x2={92} y2={224 + i * 36} stroke="rgba(163,206,241,0.12)" strokeWidth={1.5} />
        ) : null}
      </g>
    ))}
  </g>
);

const ILUSTRACOES = [IlustraPlano, IlustraBusca, IlustraTitulos, IlustraTexto, IlustraFicha];

const AtoNoRevsist: React.FC<{ t: number }> = ({ t }) => {
  const feitas = S.filter((s) => t >= s).length - 1 + (t >= FIM ? 1 : 0);
  const agora = feitas < 0 ? ESTACOES[0].nome : feitas < 5 ? ESTACOES[feitas].nome : 'Tudo pronto';
  const seguinte =
    feitas < 0 ? ESTACOES[1].nome : feitas < 4 ? ESTACOES[feitas + 1].nome : 'Exportar tabela e diagrama';
  const trocas = [...S.slice(1), FIM];
  const oTroca = Math.min(1, ...trocas.map((troca) => Math.abs(t - troca) / 5));

  const marcos: number[] = [26, S[0]];
  const posicoes: number[] = [TRILHO.de, XS[0]];
  for (let k = 1; k < S.length; k++) {
    marcos.push(S[k] - 14, S[k]);
    posicoes.push(XS[k - 1], XS[k]);
  }
  marcos.push(FIM - 14, FIM);
  posicoes.push(XS[XS.length - 1], TRILHO.ate);
  const token = vaiEVolta(t, marcos, posicoes);

  return (
    <Tela>
      <Coluna t={t} kicker="NO REVSIST" linhas={['Um caminho só,', 'do plano ao fim']} />

      <g opacity={suave(t, [22, 38], [0, 1])}>
        <text x={120} y={402} fontFamily={MONO} fontSize={21} letterSpacing="0.24em" fill={GELO} opacity={0.8}>
          AGORA
        </text>
        <text x={120} y={448} fontFamily={SANS} fontSize={36} fontWeight={700} fill={C.branco} opacity={oTroca}>
          {agora}
        </text>
        <text x={120} y={506} fontFamily={MONO} fontSize={21} letterSpacing="0.24em" fill={GELO} opacity={0.8}>
          EM SEGUIDA
        </text>
        <text
          x={120}
          y={546}
          fontFamily={SANS}
          fontSize={28}
          fontWeight={600}
          fill="rgba(255,255,255,0.7)"
          opacity={oTroca}
        >
          {seguinte}
        </text>
      </g>

      {/* Trilho: base, trecho percorrido e o marcador de onde você está */}
      <line
        x1={TRILHO.de}
        y1={TRILHO.y}
        x2={TRILHO.de + (TRILHO.ate - TRILHO.de) * suave(t, [4, 34], [0, 1])}
        y2={TRILHO.y}
        stroke="rgba(163,206,241,0.22)"
        strokeWidth={4}
        strokeLinecap="round"
      />
      <line
        x1={TRILHO.de}
        y1={TRILHO.y}
        x2={token}
        y2={TRILHO.y}
        stroke={GELO}
        strokeWidth={4}
        strokeLinecap="round"
        opacity={t >= 26 ? 1 : 0}
      />

      {ESTACOES.map((estacao, k) => {
        const estado = estadoDa(k, t);
        const u = estado === 'pendente' ? 0 : limitar((t - S[k]) / DURACAO_ESTACAO);
        const Ilustracao = ILUSTRACOES[k];
        const aparece = suave(t, [10 + k * 5, 26 + k * 5], [0, 1]);
        const pulso = ((t - S[k]) % 24) / 24;

        return (
          <g key={estacao.nome} opacity={aparece}>
            <g
              transform={`translate(${XS[k]} 0)`}
              opacity={estado === 'pendente' ? 0.32 : estado === 'ativa' ? 1 : 0.85}
            >
              <Ilustracao u={u} />
            </g>

            {estado === 'ativa' ? (
              <circle
                cx={XS[k]}
                cy={TRILHO.y}
                r={20 + 24 * pulso}
                fill="none"
                stroke={GELO}
                strokeWidth={3}
                opacity={0.55 * (1 - pulso)}
              />
            ) : null}
            <circle
              cx={XS[k]}
              cy={TRILHO.y}
              r={20}
              fill={estado === 'feita' ? GELO : FUNDO}
              stroke={estado === 'pendente' ? 'rgba(163,206,241,0.35)' : GELO}
              strokeWidth={estado === 'ativa' ? 4 : 3}
            />
            {estado === 'feita' ? (
              <path
                d={`M${XS[k] - 9} ${TRILHO.y} l6 6 l12 -12`}
                fill="none"
                stroke={FUNDO}
                strokeWidth={4}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            ) : null}

            <text
              x={XS[k]}
              y={472}
              textAnchor="middle"
              fontFamily={SANS}
              fontSize={30}
              fontWeight={700}
              fill={C.branco}
              opacity={estado === 'pendente' ? 0.45 : 1}
            >
              {estacao.nome}
            </text>
            <text
              x={XS[k]}
              y={510}
              textAnchor="middle"
              fontFamily={MONO}
              fontSize={21}
              fill={GELO}
              opacity={estado === 'pendente' ? 0.4 : 0.9}
            >
              {estacao.detalhe}
            </text>
          </g>
        );
      })}

      <g opacity={t >= 26 ? 1 : 0}>
        <circle cx={token} cy={TRILHO.y} r={22} fill={GELO} opacity={0.22} />
        <circle cx={token} cy={TRILHO.y} r={9} fill={C.branco} />
      </g>
    </Tela>
  );
};

/* ═══ Montagem ═══════════════════════════════════════════════════════════ */

export const FaixaVaiVem: React.FC = () => {
  usarFontesDaMarca();
  const frame = useCurrentFrame();
  const varredura = vaiEVolta(frame, VARREDURA, [0, W]);
  const varrendo = frame > VARREDURA[0] && frame < VARREDURA[1];

  return (
    <AbsoluteFill style={{ backgroundColor: FUNDO, overflow: 'hidden' }}>
      <Fundo />

      {/* Ato 1, montado também um período depois para fechar o laço. Ele não
          some por opacidade: é a varredura que o corta. */}
      {[0, DURACAO_FAIXA].map((inicio) => {
        const t = frame - inicio;
        if (t > VARREDURA[1]) return null;
        const o = suave(t, [-10, 14], [0, 1]);
        if (o <= 0.001) return null;
        const corte = vaiEVolta(t, VARREDURA, [0, W]);
        return (
          <AbsoluteFill key={`mao-${inicio}`} style={{ opacity: o, clipPath: `inset(0 0 0 ${corte}px)` }}>
            <AtoNaMao t={t} />
          </AbsoluteFill>
        );
      })}

      {/* Ato 2, montado também um período antes: seu fim cobre o começo. */}
      {[INICIO_ATO_2 - DURACAO_FAIXA, INICIO_ATO_2].map((inicio) => {
        const t = frame - inicio;
        if (t < 0) return null;
        const o = interpolate(t, [DURACAO_ATO_2 - FADE, DURACAO_ATO_2 + FADE * 0.4], [1, 0], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
          easing: Easing.in(Easing.cubic),
        });
        if (o <= 0.001) return null;
        const corte = vaiEVolta(t, [0, VARREDURA[1] - VARREDURA[0]], [0, W]);
        return (
          <AbsoluteFill
            key={`revsist-${inicio}`}
            style={{ opacity: o, clipPath: `inset(0 ${W - corte}px 0 0)` }}
          >
            <AtoNoRevsist t={t} />
          </AbsoluteFill>
        );
      })}

      {varrendo ? (
        <div
          style={{
            position: 'absolute',
            top: 0,
            bottom: 0,
            left: varredura - 110,
            width: 220,
            background:
              'linear-gradient(90deg, rgba(163,206,241,0) 0%, rgba(163,206,241,0.2) 50%, rgba(163,206,241,0) 100%)',
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: 0,
              bottom: 0,
              left: 108,
              width: 4,
              background: GELO,
              boxShadow: `0 0 28px ${GELO}`,
            }}
          />
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
