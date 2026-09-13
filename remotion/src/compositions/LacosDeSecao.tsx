/**
 * Revsist — Laços curtos das seções da landing.
 *
 * São três animações mudas de 9 a 10 s, cada uma explicando um único assunto da
 * página onde aparece. Mesma linguagem visual do laço do hero — papel
 * texturizado, sem molduras, sem controles desenhados — e mesma linguagem
 * textual da landing: segunda pessoa e nenhum jargão de método.
 *
 * Emenda do laço: o conteúdo é montado duas vezes, deslocado de um período, com
 * a duração encurtada o suficiente para que a opacidade chegue exatamente a
 * zero no fim. Assim o último quadro é idêntico ao primeiro.
 */

import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { C, DURACOES, MONO, SANS } from '../theme';
import {
  AssinaturaRodape,
  Atmosfera,
  Contador,
  Digitado,
  Kicker,
  TituloEmLinhas,
  opacidadeDaCena,
  px,
  suave,
  usarFontesDaMarca,
} from '../components/base';
import { FluxoPrisma } from '../components/FluxoPrisma';

const FADE = 14;

/**
 * Monta o conteúdo duas vezes, deslocado de um período, para fechar o laço.
 * A duração encurtada garante opacidade zero no quadro final — sem isso, o
 * primeiro e o último quadro não coincidem e o laço pisca a cada volta.
 */
const Laco: React.FC<{ children: (local: number) => React.ReactNode }> = ({ children }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const duracao = durationInFrames - FADE;

  return (
    <>
      {[0, durationInFrames].map((inicio) => {
        const o = opacidadeDaCena(frame, inicio, duracao, FADE);
        if (o <= 0.001) return null;
        return (
          <AbsoluteFill key={inicio} style={{ opacity: o }}>
            {children(frame - inicio)}
          </AbsoluteFill>
        );
      })}
    </>
  );
};

const Palco: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  usarFontesDaMarca();
  return (
    <AbsoluteFill style={{ backgroundColor: C.papel, color: C.tinta, overflow: 'hidden' }}>
      <Atmosfera />
      {children}
    </AbsoluteFill>
  );
};

/* ═══ 1 · Uma busca, cinco bases ══════════════════════════════════════════ */

type Base = {
  nome: string;
  detalhe: string;
  resultado: string;
  artigos: number;
  brasileira: boolean;
};

const BASES: Base[] = [
  { nome: 'BDTD', detalhe: 'teses e dissertações', resultado: '142 artigos', artigos: 142, brasileira: true },
  { nome: 'SciELO', detalhe: 'periódicos da região', resultado: '89 artigos', artigos: 89, brasileira: true },
  { nome: 'Scopus', detalhe: 'base internacional', resultado: 'nada sobre o tema', artigos: 0, brasileira: false },
  { nome: 'OpenAlex', detalhe: 'base internacional', resultado: 'nada sobre o tema', artigos: 0, brasileira: false },
  { nome: 'PubMed', detalhe: 'área da saúde', resultado: 'nada sobre o tema', artigos: 0, brasileira: false },
];

const CartaoDeBase: React.FC<{ local: number; base: Base; indice: number }> = ({
  local,
  base,
  indice,
}) => {
  const entrada = 62 + indice * 6;
  const buscando = entrada + 16;
  const respondeu = buscando + 30;

  const aparece = suave(local, [entrada, entrada + 18], [0, 1]);
  const progresso = suave(local, [buscando, respondeu], [0, 1]);
  const revela = suave(local, [respondeu, respondeu + 18], [0, 1]);

  return (
    <div
      style={{
        width: 272,
        height: 196,
        padding: '22px 22px 18px',
        display: 'flex',
        flexDirection: 'column',
        background: base.brasileira ? C.superficie : 'rgba(255,255,255,0.62)',
        border: `2px solid ${base.brasileira ? C.acento : C.borda}`,
        borderRadius: 2,
        boxShadow: base.brasileira
          ? '0 1px 0 rgba(255,255,255,0.9) inset, 0 10px 24px -14px rgba(21,41,64,0.4)'
          : 'none',
        opacity: aparece,
        transform: `translateY(${px((1 - aparece) * 16)}px)`,
      }}
    >
      <div style={{ fontFamily: SANS, fontSize: 32, fontWeight: 700, color: C.tinta }}>
        {base.nome}
      </div>
      <div
        style={{
          fontFamily: MONO,
          fontSize: 18,
          color: C.tintaSuave,
          letterSpacing: '0.06em',
          marginTop: 2,
        }}
      >
        {base.detalhe}
      </div>

      <div style={{ flex: 1 }} />

      {/* Barra de "procurando", que se apaga quando o resultado chega */}
      <div
        style={{
          height: 8,
          background: 'rgba(39,76,119,0.12)',
          borderRadius: 2,
          overflow: 'hidden',
          opacity: 1 - revela,
        }}
      >
        <div style={{ width: `${progresso * 100}%`, height: '100%', background: C.apoio }} />
      </div>

      <div style={{ marginTop: 12, minHeight: 44, opacity: revela }}>
        {base.artigos > 0 ? (
          <Contador
            local={local}
            ate={base.artigos}
            inicio={respondeu}
            duracao={22}
            estilo={{ fontSize: 44, fontWeight: 700, color: C.acento, lineHeight: 1 }}
          />
        ) : (
          <span style={{ fontFamily: SANS, fontSize: 24, color: C.tintaSuave }}>
            {base.resultado}
          </span>
        )}
        {base.artigos > 0 ? (
          <span
            style={{
              fontFamily: SANS,
              fontSize: 24,
              color: C.tintaSuave,
              marginLeft: 10,
            }}
          >
            artigos
          </span>
        ) : null}
      </div>
    </div>
  );
};

export const LacoBusca: React.FC = () => (
  <Palco>
    <Laco>
      {(local) => (
        <>
          <div
            style={{
              position: 'absolute',
              left: 72,
              right: 72,
              top: 74,
              display: 'flex',
              flexDirection: 'column',
              gap: 22,
            }}
          >
            <Kicker local={local}>Uma busca só</Kicker>
            <TituloEmLinhas
              local={local - 6}
              linhas={['Cinco bases ao mesmo tempo']}
              tamanho={56}
            />

            <div
              style={{
                marginTop: 4,
                background: 'rgba(255,255,255,0.94)',
                border: `2px solid ${C.borda}`,
                borderRadius: 2,
                padding: '16px 20px',
                boxShadow: 'inset 0 2px 4px rgba(39,76,119,0.1)',
                opacity: suave(local, [18, 34], [0, 1]),
              }}
            >
              <Digitado
                local={local}
                inicio={24}
                porFrame={2.4}
                texto={'"arranjos produtivos locais" E "desenvolvimento regional"'}
                estilo={{ fontSize: 26, color: C.tinta, fontWeight: 500 }}
              />
            </div>
          </div>

          <div
            style={{
              position: 'absolute',
              left: 72,
              right: 72,
              top: 376,
              display: 'flex',
              gap: 24,
            }}
          >
            {BASES.map((base, i) => (
              <CartaoDeBase key={base.nome} local={local} base={base} indice={i} />
            ))}
          </div>

          <div
            style={{
              position: 'absolute',
              left: 72,
              right: 72,
              top: 626,
              display: 'flex',
              alignItems: 'baseline',
              gap: 20,
              opacity: suave(local, [166, 188], [0, 1]),
            }}
          >
            <Contador
              local={local}
              ate={231}
              inicio={166}
              duracao={34}
              estilo={{ fontSize: 88, fontWeight: 700, color: C.acento, lineHeight: 1 }}
            />
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontFamily: SANS, fontSize: 34, fontWeight: 600, color: C.tinta }}>
                artigos para ler — e todos vieram das bases brasileiras
              </span>
              <span
                style={{
                  fontFamily: SANS,
                  fontSize: 26,
                  color: C.tintaSuave,
                  marginTop: 4,
                  opacity: suave(local, [200, 222], [0, 1]),
                }}
              >
                É por isso que a BDTD e a SciELO vêm junto: sem elas, esta pesquisa não teria
                encontrado nada.
              </span>
            </div>
          </div>

          <AssinaturaRodape texto="Uma busca, cinco bases" />
        </>
      )}
    </Laco>
  </Palco>
);

/* ═══ 2 · O que fica guardado quando você decide ══════════════════════════ */

const LinhaGuardada: React.FC<{
  local: number;
  entrada: number;
  campo: string;
  valor: string;
  nota?: string;
}> = ({ local, entrada, campo, valor, nota }) => {
  const t = suave(local, [entrada, entrada + 18], [0, 1]);
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '340px 1fr',
        gap: 24,
        padding: '18px 0',
        borderBottom: `1px solid ${C.borda}`,
        opacity: t,
        transform: `translateX(${px((1 - t) * -16)}px)`,
      }}
    >
      <span style={{ fontFamily: MONO, fontSize: 22, letterSpacing: '0.10em', color: C.acento }}>
        {campo}
      </span>
      <span>
        <span style={{ fontFamily: SANS, fontSize: 28, fontWeight: 600, color: C.tinta }}>
          {valor}
        </span>
        {nota ? (
          <span
            style={{
              display: 'block',
              fontFamily: SANS,
              fontSize: 22,
              color: C.tintaSuave,
              marginTop: 4,
            }}
          >
            {nota}
          </span>
        ) : null}
      </span>
    </div>
  );
};

export const LacoRegistro: React.FC = () => (
  <Palco>
    <Laco>
      {(local) => (
        <>
          <div
            style={{
              position: 'absolute',
              left: 72,
              right: 72,
              top: 74,
              display: 'flex',
              flexDirection: 'column',
              gap: 20,
            }}
          >
            <Kicker local={local}>Quando alguém perguntar</Kicker>
            <TituloEmLinhas
              local={local - 6}
              linhas={['Cada decisão vira um registro']}
              tamanho={54}
            />
          </div>

          <div
            style={{
              position: 'absolute',
              left: 72,
              right: 72,
              top: 262,
              background: 'rgba(255,255,255,0.96)',
              border: `2px solid ${C.borda}`,
              borderRadius: 2,
              padding: '10px 34px 26px',
              boxShadow: '0 1px 0 rgba(255,255,255,0.9) inset, 0 14px 30px -18px rgba(21,41,64,0.4)',
              opacity: suave(local, [22, 42], [0, 1]),
              transform: `translateY(${px(suave(local, [22, 46], [22, 0]))}px)`,
            }}
          >
            <LinhaGuardada
              local={local}
              entrada={44}
              campo="QUAL ERA O ARTIGO"
              valor="Dinâmica territorial e cooperação no APL de manga e uva"
              nota="Tese da UFPE, de 2023, encontrada na BDTD"
            />
            <LinhaGuardada
              local={local}
              entrada={62}
              campo="O QUE FOI CONFERIDO"
              valor="Atendeu os dois critérios de inclusão"
              nota="Fala de governança territorial e é sobre o semiárido"
            />
            <LinhaGuardada
              local={local}
              entrada={80}
              campo="QUEM DECIDIU, E QUANDO"
              valor="Eduardo, com um segundo revisor conferindo"
              nota="10 de setembro de 2026, às 20h15"
            />

            <div
              style={{
                marginTop: 26,
                background: C.tinta,
                borderRadius: 2,
                padding: '22px 26px',
                opacity: suave(local, [104, 124], [0, 1]),
              }}
            >
              <div
                style={{
                  fontFamily: MONO,
                  fontSize: 20,
                  letterSpacing: '0.20em',
                  color: C.claroAcento,
                  marginBottom: 12,
                }}
              >
                E UM SELO DE QUE NADA MUDOU DEPOIS
              </div>
              <Digitado
                local={local}
                inicio={116}
                porFrame={2.4}
                texto="9c3b4f51e0892acb7102e35a9812e4f01488c9f5d1a8e2074d2b9911e8c4a17b"
                estilo={{ fontSize: 24, color: C.branco, letterSpacing: '0.03em' }}
              />
            </div>
          </div>

          <div
            style={{
              position: 'absolute',
              left: 72,
              right: 72,
              bottom: 132,
              opacity: suave(local, [186, 210], [0, 1]),
            }}
          >
            <span style={{ fontFamily: SANS, fontSize: 32, fontWeight: 600, color: C.tinta }}>
              Se alguém alterar qualquer coisa nesse registro, o código muda.
            </span>
            <span
              style={{
                display: 'block',
                fontFamily: SANS,
                fontSize: 26,
                color: C.tintaSuave,
                marginTop: 6,
                opacity: suave(local, [206, 228], [0, 1]),
              }}
            >
              É assim que se prova, meses depois, que o que está guardado é o original.
            </span>
          </div>

          <AssinaturaRodape texto="Você não precisa lembrar" />
        </>
      )}
    </Laco>
  </Palco>
);

/* ═══ 3 · O diagrama que sai pronto ═══════════════════════════════════════ */

export const LacoDiagrama: React.FC = () => (
  <Palco>
    <Laco>
      {(local) => (
        <>
          <div
            style={{
              position: 'absolute',
              left: 96,
              top: 108,
              display: 'flex',
              flexDirection: 'column',
              gap: 20,
            }}
          >
            <Kicker local={local}>No fim</Kicker>
            <TituloEmLinhas
              local={local - 6}
              linhas={['O diagrama monta-se sozinho']}
              tamanho={58}
            />
          </div>

          <FluxoPrisma local={local - 26} />

          <div
            style={{
              position: 'absolute',
              left: 1014,
              top: 872,
              width: 640,
              borderTop: `2px solid ${C.acento}`,
              paddingTop: 18,
              opacity: suave(local, [176, 200], [0, 1]),
            }}
          >
            <div style={{ fontFamily: SANS, fontSize: 30, fontWeight: 600, color: C.tinta }}>
              Cada número é a conta do seu trabalho.
            </div>
            <div
              style={{
                fontFamily: SANS,
                fontSize: 24,
                color: C.tintaSuave,
                marginTop: 8,
                opacity: suave(local, [196, 220], [0, 1]),
              }}
            >
              Mudou uma decisão? Gere de novo.
            </div>
          </div>

          <AssinaturaRodape texto="Baixe em PNG ou SVG" />
        </>
      )}
    </Laco>
  </Palco>
);

/** Reexportado só para deixar explícito de onde vêm as durações. */
export const DURACAO_BUSCA = DURACOES.busca;
export const DURACAO_REGISTRO = DURACOES.registro;
export const DURACAO_DIAGRAMA = DURACOES.diagrama;
