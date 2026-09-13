/**
 * Revsist — Peças do e-mail de aprovação de convite.
 *
 * Três composições, um propósito: dizer a quem foi aprovado o que fazer a
 * seguir. Elas saem daqui como arquivos estáticos servidos pelo backend e
 * embutidos no e-mail.
 *
 *   `BoasVindas`     → GIF animado, o passo a passo acontecendo
 *   `ComoComecar`    → PNG, o mesmo caminho parado em três passos
 *   `SeloAssinatura` → PNG, a assinatura de quem envia
 *
 * Por que nada aqui usa `Atmosfera`: o grão e as curvas de nível que dão
 * textura aos laços da landing são ruído de alta frequência, e ruído é
 * exatamente o que a paleta indexada de um GIF não sabe comprimir — o mesmo
 * fundo que pesa 40 KB em vídeo passa de 2 MB em GIF. Aqui o fundo é chapado
 * de propósito, e é isso que mantém o anexo do e-mail em tamanho civilizado.
 */

import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';
import { C, MONO, SANS } from '../theme';
import { Marca, suave, usarFontesDaMarca } from '../components/base';

/** O código é ilustrativo: o real vai no texto do e-mail, não no pixel. */
const CODIGO_EXEMPLO = 'RSAC-2368-0A49';

const PASSOS = [
  {
    n: '1',
    titulo: 'Clique no botão',
    texto: 'O link deste e-mail já abre o Revsist com seu código preenchido.',
  },
  {
    n: '2',
    titulo: 'Confira seus dados',
    texto: 'Nome, e-mail e instituição. Escolha um usuário e uma senha.',
  },
  {
    n: '3',
    titulo: 'Comece a revisão',
    texto: 'Pronto — o ambiente abre com seu primeiro projeto à espera.',
  },
];

/* ══════════════════════════════════════════════════════════════════════
   Miniaturas de interface

   Desenhos chapados da tela real, não capturas: a captura traria a paleta
   inteira do app — milhares de cores — para dentro de um GIF de 256.
   ══════════════════════════════════════════════════════════════════════ */

const Janela: React.FC<{
  largura: number;
  altura: number;
  children: React.ReactNode;
}> = ({ largura, altura, children }) => (
  <div
    style={{
      width: largura,
      height: altura,
      background: C.superficie,
      border: `2px solid ${C.borda}`,
      borderRadius: 4,
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
    }}
  >
    <div
      style={{
        height: 26,
        background: C.papel,
        borderBottom: `2px solid ${C.borda}`,
        display: 'flex',
        alignItems: 'center',
        paddingLeft: 10,
        gap: 6,
        flexShrink: 0,
      }}
    >
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          style={{ width: 7, height: 7, borderRadius: 4, background: C.borda }}
        />
      ))}
    </div>
    <div style={{ flex: 1, position: 'relative' }}>{children}</div>
  </div>
);

const Campo: React.FC<{
  rotulo: string;
  valor?: string;
  mono?: boolean;
  destaque?: boolean;
  largura?: number | string;
}> = ({ rotulo, valor = '', mono = false, destaque = false, largura = '100%' }) => (
  <div style={{ width: largura }}>
    <div
      style={{
        fontFamily: SANS,
        fontSize: 11,
        fontWeight: 600,
        color: C.tintaSuave,
        marginBottom: 4,
      }}
    >
      {rotulo}
    </div>
    <div
      style={{
        height: 30,
        background: C.superficie,
        border: `2px solid ${destaque ? C.acento : C.borda}`,
        borderRadius: 3,
        display: 'flex',
        alignItems: 'center',
        paddingLeft: 8,
        fontFamily: mono ? MONO : SANS,
        fontSize: mono ? 14 : 12,
        fontWeight: mono ? 700 : 500,
        letterSpacing: mono ? '0.08em' : 0,
        color: valor ? C.tinta : C.borda,
      }}
    >
      {valor || ' '}
    </div>
  </div>
);

const Botao: React.FC<{
  texto: string;
  largura?: number | string;
  pressionado?: boolean;
}> = ({ texto, largura = '100%', pressionado = false }) => (
  <div
    style={{
      width: largura,
      height: 34,
      background: pressionado ? C.tintaProfunda : C.acento,
      borderRadius: 3,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: SANS,
      fontSize: 13,
      fontWeight: 700,
      color: C.branco,
      transform: pressionado ? 'scale(0.98)' : 'scale(1)',
    }}
  >
    {texto}
  </div>
);

/** Cursor do mouse, desenhado — o render não tem ponteiro para capturar. */
const Cursor: React.FC<{ x: number; y: number; clicando?: boolean }> = ({
  x,
  y,
  clicando = false,
}) => (
  <div
    style={{
      position: 'absolute',
      left: x,
      top: y,
      width: 22,
      height: 22,
      zIndex: 50,
      transform: clicando ? 'scale(0.85)' : 'scale(1)',
    }}
  >
    {clicando && (
      <div
        style={{
          position: 'absolute',
          left: -9,
          top: -9,
          width: 34,
          height: 34,
          borderRadius: 20,
          border: `2px solid ${C.apoio}`,
          opacity: 0.9,
        }}
      />
    )}
    <svg viewBox="0 0 24 24" width={22} height={22}>
      <path
        d="M 4 2 L 4 18 L 8.5 14 L 11.5 20.5 L 14.5 19 L 11.5 12.8 L 17.5 12.5 Z"
        fill={C.tinta}
        stroke={C.branco}
        strokeWidth={1.6}
        strokeLinejoin="round"
      />
    </svg>
  </div>
);

/* ══════════════════════════════════════════════════════════════════════
   Cena 1 — o e-mail e o clique no botão
   ══════════════════════════════════════════════════════════════════════ */

const CenaEmail: React.FC<{ local: number }> = ({ local }) => {
  // O cursor desce até o botão e clica no frame 46.
  const x = suave(local, [8, 44], [430, 268]);
  const y = suave(local, [8, 44], [92, 250]);
  const clicando = local >= 44 && local <= 56;

  return (
    <div style={{ position: 'relative', width: 520, height: 330 }}>
        <Janela largura={520} altura={330}>
          <div style={{ padding: '18px 26px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Marca altura={20} />
              <span
                style={{
                  fontFamily: MONO,
                  fontSize: 13,
                  fontWeight: 700,
                  letterSpacing: '0.14em',
                  color: C.acento,
                }}
              >
                REVSIST
              </span>
            </div>

            <div
              style={{
                fontFamily: SANS,
                fontSize: 20,
                fontWeight: 800,
                color: C.tinta,
                marginTop: 16,
              }}
            >
              Seu acesso foi aprovado
            </div>

            <div
              style={{
                fontFamily: SANS,
                fontSize: 13,
                color: C.tintaSuave,
                marginTop: 6,
              }}
            >
              Seu código de convite:
            </div>

            <div
              style={{
                marginTop: 8,
                padding: '10px 14px',
                background: C.papel,
                border: `2px dashed ${C.apoio}`,
                borderRadius: 3,
                fontFamily: MONO,
                fontSize: 19,
                fontWeight: 700,
                letterSpacing: '0.12em',
                color: C.acento,
                textAlign: 'center',
              }}
            >
              {CODIGO_EXEMPLO}
            </div>

            <div style={{ marginTop: 18, display: 'flex', justifyContent: 'center' }}>
              <Botao texto="Entrar no Revsist  →" largura={220} pressionado={clicando} />
            </div>
          </div>
        </Janela>
        <Cursor x={x} y={y} clicando={clicando} />
    </div>
  );
};

/* ══════════════════════════════════════════════════════════════════════
   Cena 2 — a tela de acesso, com o código já preenchido pelo link
   ══════════════════════════════════════════════════════════════════════ */

const CenaCodigo: React.FC<{ local: number }> = ({ local }) => {
  // O código "digita" sozinho: é o link que preenche, e a animação precisa
  // deixar isso óbvio sem uma linha de legenda.
  const letras = Math.round(
    interpolate(local, [10, 40], [0, CODIGO_EXEMPLO.length], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    }),
  );
  const preenchido = CODIGO_EXEMPLO.slice(0, letras);
  const completo = letras >= CODIGO_EXEMPLO.length;
  const selo = suave(local, [46, 62], [0, 1]);

  return (
    <Janela largura={520} altura={330}>
        <div
          style={{
            padding: '22px 26px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <Marca altura={26} />
          <div
            style={{
              fontFamily: SANS,
              fontSize: 15,
              fontWeight: 700,
              color: C.tinta,
              marginTop: 10,
            }}
          >
            Acesso ao ambiente de revisão
          </div>

          <div style={{ display: 'flex', gap: 6, marginTop: 14 }}>
            {['Já sou cadastrado', 'Tenho um convite', 'Quero um convite'].map((t, i) => (
              <div
                key={t}
                style={{
                  padding: '6px 10px',
                  borderRadius: 3,
                  fontFamily: SANS,
                  fontSize: 10,
                  fontWeight: i === 1 ? 700 : 500,
                  background: i === 1 ? C.papel : 'transparent',
                  border: `1.5px solid ${i === 1 ? C.apoio : 'transparent'}`,
                  color: i === 1 ? C.acento : C.tintaSuave,
                }}
              >
                {t}
              </div>
            ))}
          </div>

          <div style={{ width: 300, marginTop: 18 }}>
            <Campo
              rotulo="Código do convite"
              valor={preenchido}
              mono
              destaque={completo}
            />
          </div>

          <div
            style={{
              marginTop: 12,
              height: 22,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              opacity: selo,
            }}
          >
            <svg viewBox="0 0 24 24" width={17} height={17}>
              <circle cx={12} cy={12} r={10} fill="none" stroke={C.acento} strokeWidth={2.4} />
              <path
                d="M 7.5 12.4 L 10.6 15.4 L 16.5 9"
                fill="none"
                stroke={C.acento}
                strokeWidth={2.4}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <span
              style={{
                fontFamily: SANS,
                fontSize: 12,
                fontWeight: 700,
                color: C.acento,
              }}
            >
              Convite válido
            </span>
          </div>
        </div>
    </Janela>
  );
};

/* ══════════════════════════════════════════════════════════════════════
   Cena 3 — o cadastro
   ══════════════════════════════════════════════════════════════════════ */

const CenaCadastro: React.FC<{ local: number }> = ({ local }) => {
  const linha = (atraso: number) => suave(local, [atraso, atraso + 14], [0, 1]);
  const enviando = local >= 66;

  return (
    <Janela largura={520} altura={330}>
        <div style={{ padding: '20px 26px' }}>
          <div
            style={{
              fontFamily: SANS,
              fontSize: 11,
              fontWeight: 800,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: C.acento,
              borderBottom: `1.5px solid ${C.borda}`,
              paddingBottom: 5,
            }}
          >
            Seus dados
          </div>

          <div style={{ display: 'flex', gap: 12, marginTop: 12, opacity: linha(6) }}>
            <Campo rotulo="Nome completo" valor="Maria Souza" largura="58%" />
            <Campo rotulo="Instituição" valor="UFRGS" largura="42%" />
          </div>

          <div style={{ display: 'flex', gap: 12, marginTop: 10, opacity: linha(20) }}>
            <Campo rotulo="Usuário" valor="maria.souza" largura="50%" />
            <Campo rotulo="Senha" valor="••••••••••" largura="50%" />
          </div>

          <div style={{ marginTop: 18, opacity: linha(38) }}>
            <Botao texto="Concluir cadastro e entrar" pressionado={enviando} />
          </div>
        </div>
    </Janela>
  );
};

/* ══════════════════════════════════════════════════════════════════════
   Cena 4 — fecho
   ══════════════════════════════════════════════════════════════════════ */

const CenaFecho: React.FC<{ local: number }> = ({ local }) => {
  const p = suave(local, [0, 34], [0, 1]);
  return (
    <div
      style={{
        width: 520,
        height: 330,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
      }}
    >
      <Marca altura={80} progresso={p} />
      <div
        style={{
          fontFamily: MONO,
          fontSize: 26,
          fontWeight: 700,
          letterSpacing: '0.2em',
          color: C.acento,
          marginTop: 20,
          opacity: suave(local, [20, 40], [0, 1]),
        }}
      >
        REVSIST
      </div>
      <div
        style={{
          fontFamily: SANS,
          fontSize: 15,
          color: C.tintaSuave,
          marginTop: 10,
          opacity: suave(local, [28, 48], [0, 1]),
        }}
      >
        Bem-vindo à sua revisão sistemática.
      </div>
    </div>
  );
};

/* ══════════════════════════════════════════════════════════════════════
   Montagem do GIF
   ══════════════════════════════════════════════════════════════════════ */

const CENAS = [
  { comp: CenaEmail, inicio: 0, dur: 70, legenda: '1. Clique no botão do e-mail' },
  { comp: CenaCodigo, inicio: 70, dur: 75, legenda: '2. Seu código entra sozinho' },
  { comp: CenaCadastro, inicio: 145, dur: 85, legenda: '3. Complete o cadastro' },
  { comp: CenaFecho, inicio: 230, dur: 55, legenda: 'revsist.com' },
];

export const BoasVindas: React.FC = () => {
  usarFontesDaMarca();
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ background: C.papel }}>
      {/* Filete superior: a única cor de marca que atravessa o quadro inteiro. */}
      <div style={{ height: 6, background: C.acento, flexShrink: 0 }} />

      {/* As cenas sao desenhadas em 520×330 — a medida em que os tamanhos de
          fonte da interface real fazem sentido — e ampliadas para preencher o
          quadro. Desenhar direto no tamanho final exigiria reescalar cada
          fonte, borda e espaçamento à mão, e a primeira divergência de
          arredondamento estragaria o alinhamento. */}
      <AbsoluteFill
        style={{
          top: 6,
          bottom: 58,
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
       <div style={{ transform: 'scale(1.66)', transformOrigin: 'center' }}>
        {CENAS.map(({ comp: Cena, inicio, dur }, i) => {
          // Corte seco entre cenas, sem crossfade: a dissolvência cria quadros
          // intermediários com cores que não existem na paleta de nenhuma das
          // duas cenas, e cada uma dessas cores custa espaço no GIF.
          const visivel = frame >= inicio && frame < inicio + dur;
          if (!visivel) return null;
          return <Cena key={i} local={frame - inicio} />;
        })}
       </div>
      </AbsoluteFill>

      {/* Legenda do passo corrente */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 0,
          height: 58,
          background: C.tinta,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {CENAS.map(({ inicio, dur, legenda }, i) => {
          const visivel = frame >= inicio && frame < inicio + dur;
          if (!visivel || !legenda) return null;
          return (
            <span
              key={i}
              style={{
                fontFamily: SANS,
                fontSize: 21,
                fontWeight: 700,
                color: C.branco,
                letterSpacing: '0.01em',
              }}
            >
              {legenda}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

/* ══════════════════════════════════════════════════════════════════════
   PNG estático — os três passos de uma vez

   É o que sustenta a mensagem onde o GIF não anima: o Outlook mostra só o
   primeiro quadro, e um leitor que só visse esse quadro ficaria sem o passo
   2 e o 3. Aqui eles estão todos, parados.
   ══════════════════════════════════════════════════════════════════════ */

export const ComoComecar: React.FC = () => {
  usarFontesDaMarca();

  return (
    <AbsoluteFill style={{ background: C.superficie }}>
      <div style={{ height: 8, background: C.acento }} />
      <div
        style={{
          flex: 1,
          display: 'flex',
          alignItems: 'stretch',
          padding: '38px 44px',
          gap: 28,
        }}
      >
        {PASSOS.map((p, i) => (
          <React.Fragment key={p.n}>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <div
                style={{
                  width: 52,
                  height: 52,
                  borderRadius: 4,
                  background: C.acento,
                  color: C.branco,
                  fontFamily: MONO,
                  fontSize: 26,
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {p.n}
              </div>
              <div
                style={{
                  fontFamily: SANS,
                  fontSize: 27,
                  fontWeight: 800,
                  color: C.tinta,
                  marginTop: 20,
                  lineHeight: 1.2,
                }}
              >
                {p.titulo}
              </div>
              <div
                style={{
                  fontFamily: SANS,
                  fontSize: 19,
                  fontWeight: 400,
                  color: C.tintaSuave,
                  marginTop: 12,
                  lineHeight: 1.5,
                }}
              >
                {p.texto}
              </div>
            </div>

            {i < PASSOS.length - 1 && (
              <div
                style={{
                  width: 2,
                  background: C.borda,
                  alignSelf: 'stretch',
                  flexShrink: 0,
                }}
              />
            )}
          </React.Fragment>
        ))}
      </div>
    </AbsoluteFill>
  );
};

/* ══════════════════════════════════════════════════════════════════════
   PNG estático — selo de assinatura
   ══════════════════════════════════════════════════════════════════════ */

export const SeloAssinatura: React.FC = () => {
  usarFontesDaMarca();

  return (
    <AbsoluteFill
      style={{
        background: C.superficie,
        flexDirection: 'row',
        alignItems: 'center',
        padding: '0 36px',
        gap: 28,
      }}
    >
      <div
        style={{
          width: 122,
          height: 122,
          borderRadius: 6,
          border: `3px solid ${C.acento}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        <Marca altura={68} />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <div
          style={{
            fontFamily: SANS,
            fontSize: 34,
            fontWeight: 800,
            color: C.tinta,
            letterSpacing: '-0.01em',
          }}
        >
          Eduardo Matheus Figueira
        </div>
        <div
          style={{
            fontFamily: SANS,
            fontSize: 21,
            fontWeight: 500,
            color: C.tintaSuave,
            marginTop: 6,
          }}
        >
          Coordenação do Revsist
        </div>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            marginTop: 16,
            paddingTop: 14,
            borderTop: `2px solid ${C.borda}`,
          }}
        >
          <span
            style={{
              fontFamily: MONO,
              fontSize: 19,
              fontWeight: 700,
              letterSpacing: '0.18em',
              color: C.acento,
            }}
          >
            REVSIST
          </span>
          <span style={{ width: 1, height: 18, background: C.borda }} />
          <span
            style={{
              fontFamily: SANS,
              fontSize: 18,
              color: C.tintaSuave,
            }}
          >
            revsist.com
          </span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
