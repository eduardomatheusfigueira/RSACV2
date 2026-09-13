/**
 * Revsist — Camada de base dos vídeos: fontes, marca, atmosfera texturizada,
 * câmera virtual, capturas com bordas desvanecidas e tipografia animada.
 *
 * Nada aqui desenha molduras, players ou cromo de janela: o vídeo é sangrado
 * até a borda e as capturas entram mascaradas por gradiente.
 */

import React, { useEffect, useState } from 'react';
import {
  Easing,
  Img,
  continueRender,
  delayRender,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import { C, MONO, SANS } from '../theme';

/* ── Fontes da marca (auto-hospedadas, iguais às da landing) ─────────────── */

export const usarFontesDaMarca = (): void => {
  const [handle] = useState(() => delayRender('Fontes da marca Revsist'));

  useEffect(() => {
    const face = (nome: string, arquivo: string, peso: string) =>
      new FontFace(nome, `url(${staticFile(arquivo)}) format('woff2-variations')`, {
        weight: peso,
        style: 'normal',
      });

    Promise.all([
      face('Inter', 'fonts/inter-variable.woff2', '400 800').load(),
      face('JetBrains Mono', 'fonts/jetbrains-mono-variable.woff2', '400 700').load(),
    ])
      .then((carregadas) => {
        carregadas.forEach((f) => document.fonts.add(f));
        return document.fonts.ready;
      })
      .then(() => continueRender(handle))
      .catch(() => continueRender(handle));
  }, [handle]);
};

/* ── Marca oficial ───────────────────────────────────────────────────────── */

/**
 * Monograma "R-Lupa", cópia fiel de brand/svg/rsac-mark.svg. As coordenadas
 * vêm da construção geométrica descrita em brand/IDENTIDADE_VISUAL.md — a haste
 * é tangente à lente e o cabo é o raio da lente prolongado. Redesenhar quebra
 * as duas junções, então não redesenhe.
 */
export const Marca: React.FC<{
  altura: number;
  cor?: string;
  corDoCabo?: string;
  opacidade?: number;
  /** Fração do traço já desenhada, de 0 a 1, para a marca aparecer riscando. */
  progresso?: number;
}> = ({ altura, cor = C.acento, corDoCabo = C.apoio, opacidade = 1, progresso = 1 }) => {
  const risca = (comprimento: number) => ({
    strokeDasharray: comprimento,
    strokeDashoffset: comprimento * (1 - Math.max(0, Math.min(1, progresso))),
  });

  return (
    <svg
      viewBox="0 0 80 100"
      width={altura * 0.8}
      height={altura}
      style={{ opacity: opacidade, overflow: 'visible' }}
      aria-hidden
    >
      <g fill="none" strokeWidth={14} strokeLinecap="round" strokeLinejoin="round">
        <path d="M 7 7 V 93" stroke={cor} {...risca(86)} />
        <circle cx={32} cy={32} r={25} stroke={cor} {...risca(157)} />
        <path d="M 45.946 52.749 L 73 93" stroke={corDoCabo} {...risca(49)} />
      </g>
    </svg>
  );
};

/** Assinatura completa: marca + logotipo, na ordem definida pelo manual. */
export const Assinatura: React.FC<{
  altura: number;
  cor?: string;
  corDoCabo?: string;
  progresso?: number;
}> = ({ altura, cor = C.acento, corDoCabo = C.apoio, progresso = 1 }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: altura * 0.34 }}>
    <Marca altura={altura} cor={cor} corDoCabo={corDoCabo} progresso={progresso} />
    <span
      style={{
        fontFamily: MONO,
        fontSize: altura * 0.74,
        fontWeight: 700,
        letterSpacing: '0.14em',
        textTransform: 'uppercase',
        color: cor,
      }}
    >
      Revsist
    </span>
  </div>
);

/* ── Utilidades de tempo ─────────────────────────────────────────────────── */

/** Fase periódica no período do laço: garante emenda invisível. */
export const useFasePeriodica = (voltas = 1): number => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return ((frame / durationInFrames) * Math.PI * 2 * voltas) % (Math.PI * 2);
};

export const suave = (frame: number, entrada: number[], saida: number[]): number =>
  interpolate(frame, entrada, saida, {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.22, 1, 0.36, 1),
  });

/**
 * Deslocamento de texto em pixel inteiro. O Chrome encaixa os glifos na grade
 * de pixels, mas não as caixas e bordas: com deslocamento fracionário o texto
 * pula de pixel em pixel enquanto a caixa desliza, e isso aparece como tremida
 * no fim de toda entrada suavizada, quando o movimento fica abaixo de 1 px.
 */
export const px = (valor: number): number => Math.round(valor);

/** Opacidade de uma cena com crossfade nas duas pontas. */
export const opacidadeDaCena = (
  frame: number,
  inicio: number,
  duracao: number,
  fade = 22,
): number => {
  const local = frame - inicio;
  if (local < -fade || local > duracao + fade) return 0;
  return (
    interpolate(local, [-fade * 0.4, fade], [0, 1], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.out(Easing.cubic),
    }) *
    interpolate(local, [duracao - fade, duracao + fade * 0.4], [1, 0], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.in(Easing.cubic),
    })
  );
};

/* ── Atmosfera: papel, grão, curvas de nível e vinheta ───────────────────── */

export const Atmosfera: React.FC<{ contornos?: boolean }> = ({ contornos = true }) => {
  const fase = useFasePeriodica();
  const deriva = Math.sin(fase) * 26;
  const derivaLenta = Math.cos(fase) * 14;

  const contorno = (indice: number): string => {
    const base = 96 + indice * 58;
    const pontos: string[] = [];
    for (let x = -80; x <= 2000; x += 40) {
      const y =
        base +
        Math.sin(x / 320 + fase + indice * 0.42) * 26 +
        Math.sin(x / 138 + fase * 2 + indice) * 8;
      pontos.push(`${x},${y.toFixed(1)}`);
    }
    return `M${pontos.join(' L')}`;
  };

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          // Faixa estreita de propósito: o vídeo aparece embutido numa página
          // de fundo #e7ecef, e um degradê mais amplo desenharia um retângulo
          // claro visível no meio da seção.
          background: `radial-gradient(120% 90% at ${48 + derivaLenta * 0.4}% ${
            34 + derivaLenta * 0.2
          }%, #edf1f4 0%, ${C.papel} 52%, #dfe6ea 100%)`,
        }}
      />

      <div
        style={{
          position: 'absolute',
          inset: -60,
          transform: `translate3d(${deriva * 0.5}px, ${derivaLenta * 0.5}px, 0)`,
          backgroundImage:
            'repeating-linear-gradient(0deg, rgba(39,76,119,0.07) 0 1px, transparent 1px 56px), repeating-linear-gradient(90deg, rgba(39,76,119,0.07) 0 1px, transparent 1px 56px)',
        }}
      />

      {contornos ? (
        <svg
          viewBox="0 0 1920 1080"
          preserveAspectRatio="none"
          style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
          aria-hidden
        >
          <g
            fill="none"
            stroke={C.apoio}
            strokeWidth={1.4}
            opacity={0.24}
            transform={`translate(${deriva * -0.6}, ${derivaLenta})`}
          >
            {Array.from({ length: 17 }, (_, i) => (
              <path key={i} d={contorno(i)} />
            ))}
          </g>
        </svg>
      ) : null}

      <svg
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          opacity: 0.06,
          mixBlendMode: 'multiply',
        }}
        aria-hidden
      >
        <filter id="grao-papel">
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.9"
            numOctaves="3"
            stitchTiles="stitch"
          />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter="url(#grao-papel)" />
      </svg>

      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(ellipse 78% 68% at 50% 44%, rgba(21,41,64,0) 46%, rgba(21,41,64,0.10) 100%)',
        }}
      />
    </div>
  );
};

/* ── Câmera virtual: zoom lento, deslocamento e inclinação sutil ─────────── */

/**
 * Só para camadas sem texto (capturas, formas). Um scale/rotate que desacelera
 * até parar passa dezenas de quadros variando milésimos: o Chrome rerasteriza o
 * texto a cada quadro com outro encaixe de glifos, e letras e etiquetas tremem.
 * Texto e interface ficam fora da câmera, parados sobre ela.
 */
export const Camera: React.FC<{
  local: number;
  duracao: number;
  zoom?: [number, number];
  desloca?: [number, number];
  gira?: number;
  children: React.ReactNode;
}> = ({ local, duracao, zoom = [1.05, 1], desloca = [0, 0], gira = 0, children }) => {
  const t = interpolate(local, [0, duracao], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 0.84, 0.28, 1),
  });
  const escala = zoom[0] + (zoom[1] - zoom[0]) * t;

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        transform: `scale(${escala}) translate3d(${desloca[0] * (1 - t)}px, ${
          desloca[1] * (1 - t)
        }px, 0) rotate(${gira * (1 - t)}deg)`,
        transformOrigin: '50% 50%',
        willChange: 'transform',
      }}
    >
      {children}
    </div>
  );
};

/* ── Captura de tela sem moldura: bordas desvanecidas e Ken Burns ────────── */

type Mascara = 'suave' | 'painel' | 'base';

const MASCARAS: Record<Mascara, string> = {
  /** Vinheta de sangria total — para capturas usadas como textura de fundo. */
  suave:
    'radial-gradient(ellipse 74% 72% at 50% 50%, #000 34%, rgba(0,0,0,0.55) 66%, transparent 96%)',
  /**
   * Desvanece as quatro bordas do próprio elemento: a captura dissolve no papel.
   * Dois gradientes lineares cruzados (e não um radial) porque a porcentagem de
   * um radial é relativa à caixa inteira — num painel largo ele nunca chegaria a
   * transparente nas laterais, deixando um corte reto visível.
   */
  painel:
    'linear-gradient(90deg, transparent 0%, #000 13%, #000 87%, transparent 100%), linear-gradient(180deg, transparent 0%, #000 11%, #000 89%, transparent 100%)',
  base: 'linear-gradient(180deg, transparent 0%, #000 32%, #000 76%, transparent 100%)',
};

export const Captura: React.FC<{
  arquivo: string;
  local: number;
  duracao: number;
  zoom?: [number, number];
  foco?: [number, number];
  opacidade?: number;
  mascara?: Mascara;
  /** Desfoque em px. Capturas de fundo precisam dele para não disputar leitura. */
  desfoque?: number;
  estilo?: React.CSSProperties;
}> = ({
  arquivo,
  local,
  duracao,
  zoom = [1.18, 1.04],
  foco = [50, 50],
  opacidade = 1,
  mascara = 'suave',
  desfoque = 0,
  estilo,
}) => {
  const t = interpolate(local, [0, duracao], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.2, 0.7, 0.3, 1),
  });
  const escala = zoom[0] + (zoom[1] - zoom[0]) * t;

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        overflow: 'hidden',
        opacity: opacidade,
        WebkitMaskImage: MASCARAS[mascara],
        maskImage: MASCARAS[mascara],
        ...(mascara === 'painel'
          ? { WebkitMaskComposite: 'source-in', maskComposite: 'intersect' }
          : null),
        ...estilo,
      }}
    >
      <Img
        src={staticFile(`telas/${arquivo}`)}
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          objectPosition: `${foco[0]}% ${foco[1]}%`,
          transform: `scale(${escala})`,
          transformOrigin: `${foco[0]}% ${foco[1]}%`,
          filter: `saturate(0.96) contrast(1.02)${desfoque ? ` blur(${desfoque}px)` : ''}`,
        }}
      />
    </div>
  );
};

/* ── Tipografia animada ──────────────────────────────────────────────────── */

export const Kicker: React.FC<{ local: number; children: React.ReactNode; cor?: string }> = ({
  local,
  children,
  cor = C.acento,
}) => (
  <div
    style={{
      fontFamily: MONO,
      fontSize: 26,
      fontWeight: 500,
      letterSpacing: '0.30em',
      textTransform: 'uppercase',
      color: cor,
      opacity: suave(local, [0, 20], [0, 1]),
      transform: `translateY(${px(suave(local, [0, 24], [14, 0]))}px)`,
      display: 'flex',
      alignItems: 'center',
      gap: 16,
    }}
  >
    {/* Cresce por scaleX, não por width: mudar a largura empurraria o texto ao
        lado em frações de pixel a cada quadro. */}
    <span
      style={{
        display: 'inline-block',
        width: 52,
        height: 2,
        background: cor,
        transform: `scaleX(${suave(local, [4, 34], [0, 1])})`,
        transformOrigin: '0 50%',
      }}
    />
    {children}
  </div>
);

export const TituloEmLinhas: React.FC<{
  local: number;
  linhas: string[];
  tamanho?: number;
  atraso?: number;
  cor?: string;
  destaque?: string;
}> = ({ local, linhas, tamanho = 86, atraso = 8, cor = C.tinta, destaque }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
    {linhas.map((linha, i) => {
      const l = local - i * atraso;
      return (
        <div key={linha} style={{ overflow: 'hidden', paddingBottom: 8 }}>
          <div
            style={{
              fontFamily: SANS,
              fontSize: tamanho,
              fontWeight: 700,
              lineHeight: 1.06,
              letterSpacing: '-0.028em',
              color: linha === destaque ? C.acento : cor,
              transform: `translateY(${px(suave(l, [0, 30], [tamanho * 1.1, 0]))}px)`,
              opacity: suave(l, [0, 18], [0, 1]),
            }}
          >
            {linha}
          </div>
        </div>
      );
    })}
  </div>
);

export const Digitado: React.FC<{
  local: number;
  texto: string;
  inicio?: number;
  porFrame?: number;
  estilo?: React.CSSProperties;
}> = ({ local, texto, inicio = 0, porFrame = 1.6, estilo }) => {
  const n = Math.max(0, Math.min(texto.length, Math.floor((local - inicio) * porFrame)));
  const digitando = n < texto.length && local > inicio;
  return (
    <span style={{ fontFamily: MONO, ...estilo }}>
      {texto.slice(0, n)}
      <span
        style={{
          display: 'inline-block',
          width: '0.55em',
          height: '1.05em',
          marginLeft: 2,
          verticalAlign: '-0.16em',
          background: C.acento,
          // Some ao terminar: um cursor piscando num texto já pronto, repetido a
          // cada volta do laço, lê-se como defeito de renderização.
          opacity: digitando ? 1 : 0,
        }}
      />
    </span>
  );
};

export const Contador: React.FC<{
  local: number;
  ate: number;
  inicio?: number;
  duracao?: number;
  estilo?: React.CSSProperties;
}> = ({ local, ate, inicio = 0, duracao = 42, estilo }) => {
  const v = Math.round(suave(local, [inicio, inicio + duracao], [0, ate]));
  return (
    <span style={{ fontFamily: MONO, fontVariantNumeric: 'tabular-nums', ...estilo }}>
      {v.toLocaleString('pt-BR')}
    </span>
  );
};

/** Etiqueta de engenharia, no padrão do design system. */
export const Etiqueta: React.FC<{
  texto: string;
  local: number;
  entrada: number;
  cor?: string;
  fundo?: string;
  borda?: string;
  tamanho?: number;
}> = ({
  texto,
  local,
  entrada,
  cor = C.tinta,
  fundo = 'rgba(255,255,255,0.9)',
  borda = C.borda,
  tamanho = 23,
}) => (
  <span
    style={{
      fontFamily: MONO,
      fontSize: tamanho,
      letterSpacing: '0.14em',
      textTransform: 'uppercase',
      color: cor,
      background: fundo,
      border: `2px solid ${borda}`,
      borderRadius: 2,
      padding: '9px 16px',
      opacity: suave(local, [entrada, entrada + 16], [0, 1]),
      transform: `translateY(${px(suave(local, [entrada, entrada + 20], [10, 0]))}px)`,
      display: 'inline-block',
    }}
  >
    {texto}
  </span>
);

/** Selo discreto de rodapé, presente em todas as cenas. */
export const AssinaturaRodape: React.FC<{ texto: string }> = ({ texto }) => {
  const fase = useFasePeriodica(2);
  return (
    <div
      style={{
        position: 'absolute',
        left: 96,
        right: 96,
        bottom: 54,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontFamily: MONO,
        fontSize: 22,
        letterSpacing: '0.16em',
        textTransform: 'uppercase',
        color: C.tintaSuave,
        opacity: 0.62 + Math.sin(fase) * 0.05,
      }}
    >
      <span style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <Marca altura={26} cor={C.tintaSuave} corDoCabo={C.apoio} />
        Revsist
      </span>
      <span style={{ color: C.acento }}>{texto}</span>
    </div>
  );
};
