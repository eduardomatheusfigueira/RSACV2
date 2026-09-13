/**
 * Revsist — Laço de abertura da landing.
 *
 * Vídeo mudo de 25 s que roda em laço ao lado do título da home: capturas reais
 * do programa sangradas até a borda (sem molduras, sem cromo de navegador, sem
 * controles de player), gráficos desenhados quadro a quadro e movimentos lentos
 * de câmera sobre uma base de papel texturizada.
 *
 * O texto segue o mesmo registro da landing — segunda pessoa, sem jargão de
 * método. Quem assiste entende o que vai fazer no programa, e não o que é uma
 * "coleta federada".
 *
 * A emenda do laço é invisível: o fundo usa apenas funções periódicas no
 * período total e as cenas das pontas são renderizadas duas vezes, deslocadas
 * de um período, para que o quadro 750 seja idêntico ao quadro 0.
 */

import React from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import { C, DURACOES, MONO, SANS, SCENES } from '../theme';
import {
  Assinatura,
  AssinaturaRodape,
  Atmosfera,
  Camera,
  Captura,
  Contador,
  Digitado,
  Etiqueta,
  Kicker,
  Marca,
  TituloEmLinhas,
  opacidadeDaCena,
  px,
  suave,
  useFasePeriodica,
  usarFontesDaMarca,
} from '../components/base';
import { FluxoPrisma } from '../components/FluxoPrisma';

const MARGEM = 96;
const TOTAL = DURACOES.hero;

/* ── Peças reutilizadas pelas cenas ──────────────────────────────────────── */

const Sublinha: React.FC<{ local: number; children: React.ReactNode; largura?: number }> = ({
  local,
  children,
  largura = 760,
}) => (
  <p
    style={{
      fontFamily: SANS,
      fontSize: 32,
      lineHeight: 1.5,
      color: C.tintaSuave,
      maxWidth: largura,
      margin: 0,
      opacity: suave(local, [0, 24], [0, 1]),
      transform: `translateY(${px(suave(local, [0, 28], [16, 0]))}px)`,
    }}
  >
    {children}
  </p>
);

/* ── Cena 1 · Abertura ───────────────────────────────────────────────────── */

const Emblema: React.FC<{ local: number }> = ({ local }) => {
  const fase = useFasePeriodica();
  const giro = (fase * 180) / Math.PI;
  const traco = (inicio: number, comprimento: number) => {
    const t = suave(local, [inicio, inicio + 40], [0, 1]);
    return { strokeDasharray: comprimento, strokeDashoffset: comprimento * (1 - t) };
  };

  return (
    <div
      style={{
        position: 'absolute',
        right: 118,
        top: 220,
        width: 640,
        height: 640,
        opacity: suave(local, [6, 40], [0, 1]),
      }}
    >
      <svg viewBox="0 0 640 640" style={{ position: 'absolute', inset: 0 }} aria-hidden>
        <g transform="translate(320 320)">
          <circle r={286} fill="none" stroke={C.borda} strokeWidth={2} {...traco(4, 1797)} />
          <circle
            r={244}
            fill="none"
            stroke={C.apoio}
            strokeWidth={2}
            opacity={0.6}
            strokeDasharray="12 10"
            transform={`rotate(${giro})`}
          />
          <circle r={182} fill="none" stroke={C.acento} strokeWidth={2.5} {...traco(16, 1144)} />

          {/* Marcações radiais — leitura de instrumento */}
          <g transform={`rotate(${-giro * 0.5})`}>
            {Array.from({ length: 60 }, (_, i) => {
              const grande = i % 5 === 0;
              const o = suave(local, [10 + i * 0.5, 26 + i * 0.5], [0, grande ? 0.85 : 0.4]);
              return (
                <line
                  key={i}
                  x1={0}
                  y1={-262}
                  x2={0}
                  y2={grande ? -282 : -274}
                  stroke={grande ? C.acento : C.tintaSuave}
                  strokeWidth={grande ? 3 : 1.6}
                  opacity={o}
                  transform={`rotate(${i * 6})`}
                />
              );
            })}
          </g>

          {/* Anéis proporcionais: de tudo que foi encontrado, o que sobrou */}
          {[
            { r: 148, arco: 0.62, cor: C.acento },
            { r: 120, arco: 0.34, cor: C.apoio },
            { r: 92, arco: 0.18, cor: C.claroAcento },
          ].map((anel, i) => {
            const circ = 2 * Math.PI * anel.r;
            const t = suave(local, [30 + i * 10, 76 + i * 10], [0, 1]);
            return (
              <circle
                key={anel.r}
                r={anel.r}
                fill="none"
                stroke={anel.cor}
                strokeWidth={12}
                strokeLinecap="butt"
                strokeDasharray={`${circ * anel.arco * t} ${circ}`}
                transform="rotate(-90)"
                opacity={0.92}
              />
            );
          })}
        </g>
      </svg>

      {/* A marca no centro, riscando-se sozinha */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Marca
          altura={128}
          cor={C.acento}
          corDoCabo={C.apoio}
          progresso={suave(local, [26, 62], [0, 1])}
        />
      </div>
    </div>
  );
};

const CenaAbertura: React.FC<{ local: number; duracao: number }> = ({ local, duracao }) => (
  <>
    <Camera local={local} duracao={duracao} zoom={[1.06, 1.0]} desloca={[0, 22]}>
      <Captura
        arquivo="02-protocolo-1280.webp"
        local={local}
        duracao={duracao}
        zoom={[1.3, 1.14]}
        foco={[70, 40]}
        opacidade={suave(local, [0, 40], [0, 0.2])}
        desfoque={5}
        mascara="suave"
      />
      <Emblema local={local} />
    </Camera>
    <div
      style={{
        position: 'absolute',
        left: MARGEM,
        top: 236,
        width: 1000,
        display: 'flex',
        flexDirection: 'column',
        gap: 30,
      }}
    >
      <Kicker local={local}>Como funciona</Kicker>
      <TituloEmLinhas
        local={local - 8}
        linhas={['Uma pergunta.', 'Cinco bases.', 'Um diagrama no fim.']}
        tamanho={82}
        atraso={9}
      />
      <Sublinha local={local - 44} largura={880}>
        E o motivo de cada decisão guardado no caminho.
      </Sublinha>
    </div>
    <AssinaturaRodape texto="Grátis · código aberto" />
  </>
);

/* ── Cena 2 · Buscar ─────────────────────────────────────────────────────── */

const BarraDeBase: React.FC<{
  local: number;
  entrada: number;
  nome: string;
  detalhe: string;
  valor: number;
  maximo: number;
  cor: string;
}> = ({ local, entrada, nome, detalhe, valor, maximo, cor }) => {
  const t = suave(local, [entrada, entrada + 34], [0, 1]);
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '250px 1fr 132px',
        alignItems: 'center',
        gap: 22,
        opacity: suave(local, [entrada - 6, entrada + 12], [0, 1]),
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <span style={{ fontFamily: SANS, fontSize: 31, fontWeight: 700, color: C.tinta }}>
          {nome}
        </span>
        <span
          style={{ fontFamily: MONO, fontSize: 21, color: C.tintaSuave, letterSpacing: '0.08em' }}
        >
          {detalhe}
        </span>
      </div>
      <div
        style={{
          height: 16,
          background: 'rgba(39,76,119,0.12)',
          border: `1px solid ${C.borda}`,
          borderRadius: 2,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${(valor / maximo) * 100 * t}%`,
            height: '100%',
            background: cor,
            boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.35)',
          }}
        />
      </div>
      <Contador
        local={local}
        ate={valor}
        inicio={entrada}
        duracao={34}
        estilo={{ fontSize: 44, fontWeight: 700, color: C.tinta, textAlign: 'right' }}
      />
    </div>
  );
};

const CenaBuscar: React.FC<{ local: number; duracao: number }> = ({ local, duracao }) => (
  <>
    <Camera local={local} duracao={duracao} zoom={[1.04, 1.0]} desloca={[-26, 0]}>
      <Captura
        arquivo="03-coleta-1280.webp"
        local={local}
        duracao={duracao}
        zoom={[1.3, 1.12]}
        foco={[36, 42]}
        opacidade={suave(local, [0, 34], [0, 0.94])}
        mascara="painel"
        estilo={{ left: 1004, right: -70, top: 132, bottom: 132 }}
      />
    </Camera>
    <div
      style={{
        position: 'absolute',
        left: MARGEM,
        top: 168,
        width: 900,
        display: 'flex',
        flexDirection: 'column',
        gap: 26,
      }}
    >
      <Kicker local={local}>01 · Buscar</Kicker>
      <TituloEmLinhas local={local - 6} linhas={['Cinco bases, uma busca só']} tamanho={62} />

      <div
        style={{
          background: 'rgba(255,255,255,0.94)',
          border: `2px solid ${C.borda}`,
          borderRadius: 2,
          padding: '18px 22px',
          boxShadow: 'inset 0 2px 4px rgba(39,76,119,0.1)',
          opacity: suave(local, [16, 34], [0, 1]),
        }}
      >
        <div
          style={{
            fontFamily: MONO,
            fontSize: 19,
            letterSpacing: '0.18em',
            color: C.acento,
            marginBottom: 8,
          }}
        >
          O QUE VOCÊ PROCURA
        </div>
        <Digitado
          local={local}
          inicio={22}
          porFrame={1.9}
          texto={'"arranjos produtivos locais" E "desenvolvimento regional"'}
          estilo={{ fontSize: 26, color: C.tinta, fontWeight: 500 }}
        />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 18, marginTop: 4 }}>
        <BarraDeBase
          local={local}
          entrada={54}
          nome="BDTD"
          detalhe="teses e dissertações"
          valor={142}
          maximo={142}
          cor={C.acento}
        />
        <BarraDeBase
          local={local}
          entrada={64}
          nome="SciELO"
          detalhe="periódicos da região"
          valor={89}
          maximo={142}
          cor={C.apoio}
        />
      </div>

      <div style={{ display: 'flex', gap: 12, marginTop: 2 }}>
        <Etiqueta texto="Scopus" local={local} entrada={78} />
        <Etiqueta texto="OpenAlex" local={local} entrada={84} />
        <Etiqueta texto="PubMed" local={local} entrada={90} />
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: 20, marginTop: 10 }}>
        <Contador
          local={local}
          ate={231}
          inicio={58}
          duracao={44}
          estilo={{ fontSize: 82, fontWeight: 700, color: C.acento, lineHeight: 1 }}
        />
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontFamily: SANS, fontSize: 33, fontWeight: 600, color: C.tinta }}>
            artigos encontrados
          </span>
          <span
            style={{ fontFamily: MONO, fontSize: 22, color: C.tintaSuave, letterSpacing: '0.08em' }}
          >
            com o dia e a hora de cada base
          </span>
        </div>
      </div>
    </div>
    <AssinaturaRodape texto="Inclui as bases brasileiras" />
  </>
);

/* ── Cena 3 · Decidir ────────────────────────────────────────────────────── */

const LinhaDoRegistro: React.FC<{
  local: number;
  entrada: number;
  campo: string;
  valor: string;
  cor?: string;
}> = ({ local, entrada, campo, valor, cor = C.tinta }) => (
  <div
    style={{
      display: 'grid',
      gridTemplateColumns: '330px 1fr',
      gap: 20,
      padding: '11px 0',
      borderBottom: `1px solid ${C.borda}`,
      opacity: suave(local, [entrada, entrada + 16], [0, 1]),
      transform: `translateX(${px(suave(local, [entrada, entrada + 20], [-14, 0]))}px)`,
    }}
  >
    <span style={{ fontFamily: MONO, fontSize: 23, letterSpacing: '0.10em', color: C.tintaSuave }}>
      {campo}
    </span>
    <span style={{ fontFamily: SANS, fontSize: 26, fontWeight: 600, color: cor }}>{valor}</span>
  </div>
);

const CenaDecidir: React.FC<{ local: number; duracao: number }> = ({ local, duracao }) => (
  <>
    <Camera local={local} duracao={duracao} zoom={[1.06, 1.0]} desloca={[18, -14]} gira={-0.35}>
      <Captura
        arquivo="01-triagem-1280.webp"
        local={local}
        duracao={duracao}
        zoom={[1.34, 1.16]}
        foco={[26, 40]}
        opacidade={suave(local, [0, 30], [0, 0.94])}
        mascara="painel"
        estilo={{ left: 1058, right: -80, top: 118, bottom: 118 }}
      />
    </Camera>
    <div
      style={{
        position: 'absolute',
        left: MARGEM,
        top: 150,
        width: 950,
        display: 'flex',
        flexDirection: 'column',
        gap: 24,
      }}
    >
      <Kicker local={local}>02 · Decidir</Kicker>
      <TituloEmLinhas local={local - 6} linhas={['Você decide, o Revsist anota']} tamanho={62} />

      <div style={{ display: 'flex', gap: 14, marginTop: 4, flexWrap: 'wrap' }}>
        <Etiqueta
          texto="Incluído"
          local={local}
          entrada={26}
          cor={C.branco}
          fundo={C.acento}
          borda={C.acento}
        />
        <Etiqueta texto="Fala de governança territorial" local={local} entrada={32} />
        <Etiqueta texto="É sobre o semiárido" local={local} entrada={38} />
      </div>

      <div style={{ marginTop: 8 }}>
        <LinhaDoRegistro
          local={local}
          entrada={46}
          campo="ARTIGO"
          valor="Dinâmica territorial e governança no APL de fruticultura"
        />
        <LinhaDoRegistro
          local={local}
          entrada={54}
          campo="QUEM DECIDIU"
          valor="Eduardo, com um segundo revisor conferindo"
        />
        <LinhaDoRegistro local={local} entrada={62} campo="QUANDO" valor="10/09/2026, às 20h15" />
        <LinhaDoRegistro
          local={local}
          entrada={70}
          campo="AJUDA DA IA"
          valor="Opinou sobre o resumo — a decisão foi humana"
          cor={C.acento}
        />
      </div>

      <div
        style={{
          marginTop: 10,
          background: C.tinta,
          borderRadius: 2,
          padding: '20px 24px',
          opacity: suave(local, [78, 94], [0, 1]),
        }}
      >
        <div
          style={{
            fontFamily: MONO,
            fontSize: 19,
            letterSpacing: '0.20em',
            color: C.claroAcento,
            marginBottom: 10,
          }}
        >
          SELO DE QUE NADA MUDOU DEPOIS
        </div>
        <Digitado
          local={local}
          inicio={86}
          porFrame={2.6}
          texto="9c3b4f51e0892acb7102e35a9812e4f01488c9f5d1a8e2074d2b9911e8c4a17b"
          estilo={{ fontSize: 22, color: C.branco, letterSpacing: '0.03em' }}
        />
      </div>
    </div>
    <AssinaturaRodape texto="Toda decisão fica guardada" />
  </>
);

/* ── Cena 4 · Anotar ─────────────────────────────────────────────────────── */

const COLUNAS_FICHA = ['Artigo', 'Onde foi estudado', 'Como se organiza', 'Indicador'];

const LINHAS_FICHA: string[][] = [
  ['BDTD 2023-1894', 'Petrolina (PE)', 'Consórcio público', 'PIB agrícola'],
  ['SciELO 2021-0412', 'Vale do São Francisco', 'Cooperativa', 'Emprego formal'],
  ['BDTD 2022-0771', 'Microrregião de Juazeiro', 'Arranjo formal', 'Renda média'],
  ['SciELO 2019-1188', 'Estado da Bahia', 'Câmara setorial', 'Exportações'],
  ['BDTD 2024-0233', 'Petrolina (PE)', 'Consórcio público', 'Área irrigada'],
];

const Ficha: React.FC<{ local: number }> = ({ local }) => {
  const largura = 900;
  const larguraCel = largura / COLUNAS_FICHA.length;

  return (
    <div
      style={{
        position: 'absolute',
        right: MARGEM,
        top: 268,
        width: largura,
        background: 'rgba(255,255,255,0.96)',
        border: `2px solid ${C.borda}`,
        borderRadius: 2,
        padding: '22px 26px 12px',
        boxShadow: '0 1px 0 rgba(255,255,255,0.9) inset, 0 10px 26px rgba(21,41,64,0.12)',
        opacity: suave(local, [8, 28], [0, 1]),
        transform: `translateY(${px(suave(local, [8, 34], [22, 0]))}px)`,
      }}
    >
      <div
        style={{
          fontFamily: MONO,
          fontSize: 19,
          letterSpacing: '0.20em',
          textTransform: 'uppercase',
          color: C.acento,
          marginBottom: 14,
        }}
      >
        A mesma ficha, 5 artigos
      </div>

      <div style={{ display: 'flex', borderBottom: `2px solid ${C.acento}`, paddingBottom: 9 }}>
        {COLUNAS_FICHA.map((c) => (
          <div
            key={c}
            style={{
              width: larguraCel,
              fontFamily: MONO,
              fontSize: 18,
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
              color: C.tintaSuave,
            }}
          >
            {c}
          </div>
        ))}
      </div>

      {LINHAS_FICHA.map((linha, l) => (
        <div key={linha[0]} style={{ display: 'flex' }}>
          {linha.map((valor, k) => {
            const entrada = 30 + (l * COLUNAS_FICHA.length + k) * 3.4;
            const t = suave(local, [entrada, entrada + 15], [0, 1]);
            return (
              <div
                key={valor + k}
                style={{
                  width: larguraCel,
                  height: 62,
                  display: 'flex',
                  alignItems: 'center',
                  borderBottom: `1px solid ${C.borda}`,
                  paddingRight: 12,
                  opacity: t,
                  transform: `translateX(${px((1 - t) * 12)}px)`,
                }}
              >
                <span
                  style={{
                    fontFamily: k === 0 ? MONO : SANS,
                    fontSize: k === 0 ? 20 : 22,
                    fontWeight: k === 0 ? 400 : 600,
                    color: k === 0 ? C.tintaSuave : C.tinta,
                  }}
                >
                  {valor}
                </span>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
};

const CenaAnotar: React.FC<{ local: number; duracao: number }> = ({ local, duracao }) => (
  <>
    <Camera local={local} duracao={duracao} zoom={[1.03, 1.0]} desloca={[0, -18]}>
      <Captura
        arquivo="05-extracao-1280.webp"
        local={local}
        duracao={duracao}
        zoom={[1.22, 1.1]}
        foco={[30, 50]}
        opacidade={suave(local, [0, 30], [0, 0.24])}
        desfoque={6}
        mascara="suave"
      />
    </Camera>
    <div
      style={{
        position: 'absolute',
        left: MARGEM,
        top: 240,
        width: 800,
        display: 'flex',
        flexDirection: 'column',
        gap: 26,
      }}
    >
      <Kicker local={local}>03 · Anotar</Kicker>
      <TituloEmLinhas
        local={local - 6}
        linhas={['Uma ficha igual', 'para todos os artigos']}
        tamanho={62}
      />
      <Sublinha local={local - 26} largura={720}>
        As perguntas saem do plano que você escreveu no começo. No fim, tudo vira tabela.
      </Sublinha>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <Etiqueta texto="Excel" local={local} entrada={54} />
        <Etiqueta texto="RIS" local={local} entrada={60} />
        <Etiqueta texto="BibTeX" local={local} entrada={66} />
      </div>
    </div>
    <Ficha local={local} />
    <AssinaturaRodape texto="Pronto para virar tabela" />
  </>
);

/* ── Cena 5 · Exportar ───────────────────────────────────────────────────── */

const CenaExportar: React.FC<{ local: number; duracao: number }> = ({ local, duracao }) => (
  <>
    <Camera local={local} duracao={duracao} zoom={[1.05, 1.0]} desloca={[0, 16]}>
      <Captura
        arquivo="06-exportacao-1280.webp"
        local={local}
        duracao={duracao}
        zoom={[1.24, 1.12]}
        foco={[50, 46]}
        opacidade={suave(local, [0, 30], [0, 0.16])}
        desfoque={7}
        mascara="suave"
      />
    </Camera>
    <div
      style={{
        position: 'absolute',
        left: MARGEM,
        top: 118,
        display: 'flex',
        flexDirection: 'column',
        gap: 20,
      }}
    >
      <Kicker local={local}>04 · Exportar</Kicker>
      <TituloEmLinhas local={local - 6} linhas={['O diagrama sai pronto']} tamanho={58} />
    </div>
    <FluxoPrisma local={local - 22} />
    <div
      style={{
        position: 'absolute',
        left: 1014,
        top: 856,
        width: 520,
        borderTop: `2px solid ${C.acento}`,
        paddingTop: 16,
        opacity: suave(local, [96, 118], [0, 1]),
      }}
    >
      <div style={{ fontFamily: SANS, fontSize: 27, fontWeight: 600, color: C.tinta }}>
        Os números são a conta do seu trabalho.
      </div>
      <div
        style={{
          fontFamily: MONO,
          fontSize: 20,
          color: C.tintaSuave,
          letterSpacing: '0.06em',
          marginTop: 6,
        }}
      >
        Você não digita nenhum deles.
      </div>
    </div>
    <AssinaturaRodape texto="Em PNG e SVG, para colar no texto" />
  </>
);

/* ── Cena 6 · Fecho ──────────────────────────────────────────────────────── */

// Sem câmera: a cena é só texto, e o zoom lento faria a assinatura tremer.
const CenaFecho: React.FC<{ local: number }> = ({ local }) => (
  <>
    <div
      style={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 30,
      }}
    >
      <div
        style={{
          opacity: suave(local, [0, 20], [0, 1]),
          transform: `translateY(${px(suave(local, [0, 26], [18, 0]))}px)`,
        }}
      >
        <Assinatura
          altura={104}
          cor={C.acento}
          corDoCabo={C.apoio}
          progresso={suave(local, [2, 34], [0, 1])}
        />
      </div>
      <div style={{ width: suave(local, [8, 36], [0, 420]), height: 3, background: C.apoio }} />
      <span
        style={{
          fontFamily: SANS,
          fontSize: 34,
          color: C.tintaSuave,
          opacity: suave(local, [14, 34], [0, 1]),
        }}
      >
        Sua revisão do começo ao fim, sem planilha
      </span>
      <span
        style={{
          fontFamily: MONO,
          fontSize: 24,
          letterSpacing: '0.22em',
          textTransform: 'uppercase',
          color: C.acento,
          opacity: suave(local, [22, 42], [0, 1]),
        }}
      >
        revsist.com · grátis
      </span>
    </div>
  </>
);

/* ── Montagem do laço ────────────────────────────────────────────────────── */

const Cena: React.FC<{
  frame: number;
  inicio: number;
  duracao: number;
  children: (local: number) => React.ReactNode;
}> = ({ frame, inicio, duracao, children }) => {
  const o = opacidadeDaCena(frame, inicio, duracao);
  if (o <= 0.001) return null;
  return <AbsoluteFill style={{ opacity: o }}>{children(frame - inicio)}</AbsoluteFill>;
};

export const HeroLoop: React.FC = () => {
  usarFontesDaMarca();
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ backgroundColor: C.papel, color: C.tinta, overflow: 'hidden' }}>
      <Atmosfera />

      {/* A cena de fecho é repetida um período antes para fechar o laço. */}
      {[SCENES.fecho.start - TOTAL, SCENES.fecho.start].map((inicio) => (
        <Cena key={`fecho-${inicio}`} frame={frame} inicio={inicio} duracao={SCENES.fecho.dur}>
          {(local) => <CenaFecho local={local} />}
        </Cena>
      ))}

      {/* E a de abertura é repetida um período depois, pelo mesmo motivo. */}
      {[SCENES.abertura.start, SCENES.abertura.start + TOTAL].map((inicio) => (
        <Cena
          key={`abertura-${inicio}`}
          frame={frame}
          inicio={inicio}
          duracao={SCENES.abertura.dur}
        >
          {(local) => <CenaAbertura local={local} duracao={SCENES.abertura.dur} />}
        </Cena>
      ))}

      <Cena frame={frame} inicio={SCENES.coleta.start} duracao={SCENES.coleta.dur}>
        {(local) => <CenaBuscar local={local} duracao={SCENES.coleta.dur} />}
      </Cena>

      <Cena frame={frame} inicio={SCENES.triagem.start} duracao={SCENES.triagem.dur}>
        {(local) => <CenaDecidir local={local} duracao={SCENES.triagem.dur} />}
      </Cena>

      <Cena frame={frame} inicio={SCENES.extracao.start} duracao={SCENES.extracao.dur}>
        {(local) => <CenaAnotar local={local} duracao={SCENES.extracao.dur} />}
      </Cena>

      <Cena frame={frame} inicio={SCENES.prisma.start} duracao={SCENES.prisma.dur}>
        {(local) => <CenaExportar local={local} duracao={SCENES.prisma.dur} />}
      </Cena>
    </AbsoluteFill>
  );
};
