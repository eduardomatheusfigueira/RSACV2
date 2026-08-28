#!/usr/bin/env python3
"""
Revsist — Gerador da Identidade Visual
======================================

Fonte única de verdade da marca. Tudo o que o usuário vê — o ícone do .exe, o
ícone do instalador NSIS, as artes das telas do instalador, o favicon, o
símbolo dentro do app e as artes de documentação — é derivado da mesma
geometria declarada aqui. Nenhum asset é desenhado à mão em outro lugar.

O MONOGRAMA "R-LUPA"
--------------------
O "R" do Revsist é construído com um traço monolinear único, em que o laço/curva
da letra é a LENTE de uma lupa e a perna diagonal é o CABO. Grade de 80 × 100,
traço 14, três primitivas e quatro pontos de controle inteiros:

    • Haste  — segmento vertical em x = 7, de y = 7 até a linha-base y = 93.
    • Lente  — circunferência de centro (32, 32) e raio 25, tangente à haste.
               A tangência acontece sobre a LINHA-DE-CENTRO dos dois traços,
               então a banda esquerda do anel coincide exatamente com a banda
               da haste: as formas se fundem em um traço só, sem emenda.
    • Cabo   — o próprio raio da lente, prolongado do anel até (73, 93). Por
               ser radial, a junção com o anel também é perfeita; por terminar
               na linha-base, a perna fecha o "R" como perna de letra.

Consequência da construção (não é ajuste manual): a caixa de tinta é
exatamente 0..80 × 0..100 — proporção 4:5, a mesma de um "R" de grotesca
geométrica. O laço ocupa 64% da altura-de-caixa e a contra-forma (o furo da
lente) tem 36% — aberta o bastante para a lupa sobreviver a 16 px.

Uso:  python3 brand/generate_brand_assets.py
Dep.: pip install cairosvg pillow
"""

from __future__ import annotations

import json
import math
import struct
from io import BytesIO
from pathlib import Path

import cairosvg
from PIL import Image

# ══════════════════════════════════════════════════════════════════════════
# CAMINHOS
# ══════════════════════════════════════════════════════════════════════════

BRAND = Path(__file__).resolve().parent
ROOT = BRAND.parent
FRONTEND = ROOT / "frontend"

DIR_SVG = BRAND / "svg"              # masters vetoriais versionados
DIR_BUILD = FRONTEND / "build"       # buildResources do electron-builder
DIR_RESOURCES = FRONTEND / "resources"  # assets embarcados em runtime
DIR_PUBLIC = FRONTEND / "public"     # servidos pelo Vite (favicon)

# ══════════════════════════════════════════════════════════════════════════
# PALETA DE MARCA — "Platinum & Dusk Blue", a paleta padrão fixa dos ícones
# ══════════════════════════════════════════════════════════════════════════
#
# Estes assets são estáticos (favicon, .ico/.icns do executável, arte do
# instalador) — carregados pelo SO/navegador antes do React montar, então
# não têm como reagir à paleta escolhida em tempo de execução como o
# monograma dentro do app (`RsacMark`, ver Brand.css) já faz. Por não poder
# ser dinâmico, o padrão fixo é a paleta "platinum-dusk" — ver o pedido do
# usuário e `[data-theme='platinum-dusk']` em `frontend/src/styles/globals.css`.
#
# Cada constante abaixo é o valor literal do token de mesmo nome nesse bloco
# (--black-forest, --olive-leaf, --cornsilk, --sunlit-clay, --copperwood):
# a paleta é propositalmente mais monocromática que a Organic Earth original
# (plataforma neutra + um único azul de acento), então algumas colapsam no
# mesmo tom — não é engano de digitação.

BLACK_FOREST = "#274c77"
FOREST_DEEP = "#1a3350"   # base do gradiente do contêiner (--color-bg-sidebar)
FOREST_LIFT = "#274c77"   # topo do gradiente do contêiner (--black-forest)
OLIVE_LEAF = "#6096ba"
CORNSILK = "#ffffff"
SUNLIT_CLAY = "#6096ba"
COPPERWOOD = "#274c77"
MUTED_CAPTION_ON_DARK = "#cbd8e4"  # legenda sobre o fundo escuro (--color-text-sidebar)

# ══════════════════════════════════════════════════════════════════════════
# GEOMETRIA CANÔNICA DO MONOGRAMA  (grade 80 × 100)
# ══════════════════════════════════════════════════════════════════════════

W = 14.0                  # espessura do traço monolinear
SX = 7.0                  # x da haste
Y_TOP, Y_BASE = 7.0, 93.0  # topo da haste e linha-base
CX = CY = 32.0            # centro da lente
R = 25.0                  # raio da linha-de-centro da lente
LEG_END = (73.0, 93.0)    # ponta do cabo, na linha-base

# O cabo é radial: parte do ponto em que o raio C→LEG_END cruza o anel.
_dx, _dy = LEG_END[0] - CX, LEG_END[1] - CY
_len = math.hypot(_dx, _dy)
LEG_START = (CX + R * _dx / _len, CY + R * _dy / _len)

MARK_W, MARK_H = 80.0, 100.0
MARK_VIEWBOX = f"0 0 {MARK_W:.0f} {MARK_H:.0f}"
# Caixa quadrada com a marca centrada — para usos em linha e em ícones.
MARK_VIEWBOX_SQUARE = f"{-(MARK_H - MARK_W) / 2:.0f} 0 {MARK_H:.0f} {MARK_H:.0f}"


def mark_group(stroke: str = "currentColor", accent: str | None = None,
               width: float = W) -> str:
    """Os três traços do monograma. `accent` colore apenas o cabo da lupa."""
    leg = accent or stroke
    return (
        f'<g fill="none" stroke="{stroke}" stroke-width="{width}"'
        f' stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="M {SX:.0f} {Y_TOP:.0f} V {Y_BASE:.0f}"/>'
        f'<circle cx="{CX:.0f}" cy="{CY:.0f}" r="{R:.0f}"/>'
        f'<path d="M {LEG_START[0]:.3f} {LEG_START[1]:.3f}'
        f' L {LEG_END[0]:.0f} {LEG_END[1]:.0f}" stroke="{leg}"/>'
        f'</g>'
    )


# ══════════════════════════════════════════════════════════════════════════
# TIPOGRAFIA VETORIZADA — JetBrains Mono Bold, a fonte mono do design system
# ══════════════════════════════════════════════════════════════════════════

_GLYPHS = json.loads((BRAND / "wordmark_glyphs.json").read_text(encoding="utf-8"))

# A palavra da assinatura. Ficava escrita à mão em cinco lugares; virou
# constante quando o produto passou a se chamar **Revsist**, para que a troca
# fosse uma linha e não uma caça.
#
# O símbolo não muda: o monograma é o "R" de *Revisão* construído como lupa, e
# a leitura continua exata para Revsist. O que muda é só o logotipo ao lado.
WORDMARK = "REVSIST"


def text_group(text: str, size: float, x: float, y: float, fill: str,
               tracking: float = 0.0) -> tuple[str, float]:
    """Compõe texto com contornos vetoriais. `y` é a linha-base, `size` a
    altura-de-caixa. Devolve (svg, largura_de_tinta)."""
    s = size / 100.0
    parts, pen = [], 0.0
    for ch in text:
        g = _GLYPHS["glyphs"].get(ch)
        if g is None:
            pen += _GLYPHS["advance"] + tracking
            continue
        if g["d"]:
            parts.append(f'<path transform="translate({pen:.3f} 0)" d="{g["d"]}"/>')
        pen += g["adv"] + tracking
    width = (pen - tracking) * s
    svg = (f'<g transform="translate({x:.3f} {y:.3f}) scale({s:.6f})"'
           f' fill="{fill}">{"".join(parts)}</g>')
    return svg, width


def text_width(text: str, size: float, tracking: float = 0.0) -> float:
    adv = sum(_GLYPHS["glyphs"].get(c, {"adv": _GLYPHS["advance"]})["adv"] + tracking
              for c in text)
    return (adv - tracking) * size / 100.0


def text_centered(text: str, size: float, cx: float, baseline: float, fill: str,
                  tracking: float = 0.0, max_width: float | None = None) -> str:
    """Texto centrado horizontalmente, reduzido se estourar `max_width`."""
    if max_width is not None:
        w = text_width(text, size, tracking)
        if w > max_width:
            f = max_width / w
            size, tracking = size * f, tracking * f
    w = text_width(text, size, tracking)
    return text_group(text, size, cx - w / 2, baseline, fill, tracking)[0]


# ══════════════════════════════════════════════════════════════════════════
# SELO BETA — etiqueta de engenharia, cantos cirúrgicos como o design system
# ══════════════════════════════════════════════════════════════════════════

def beta_seal(cx: float, cy: float, height: float, bg: str = SUNLIT_CLAY,
              fg: str = BLACK_FOREST, border: str | None = None) -> str:
    """Selo BETA centrado em (cx, cy) com a altura total informada."""
    cap = height * 0.46
    track = 14.0
    tw = text_width("BETA", cap, track)
    pad = height * 0.42
    w = tw + pad * 2
    x, y = cx - w / 2, cy - height / 2
    stroke = f' stroke="{border}" stroke-width="{height*0.05:.3f}"' if border else ""
    txt, _ = text_group("BETA", cap, cx - tw / 2, cy + cap / 2, fg, track)
    return (f'<rect x="{x:.3f}" y="{y:.3f}" width="{w:.3f}" height="{height:.3f}"'
            f' rx="{height*0.16:.3f}" fill="{bg}"{stroke}/>{txt}')


# ══════════════════════════════════════════════════════════════════════════
# ÍCONE DE APLICATIVO
# ══════════════════════════════════════════════════════════════════════════

CORNER = 0.2237  # raio contínuo padrão de ícone de app (superelipse da Apple)


BETA_MIN_PX = 96
"""Menor tamanho de ícone em que o selo BETA ainda é legível.

Abaixo disso a etiqueta vira uma mancha, e uma mancha comunica menos que a
ausência dela: nesses tamanhos o selo some e o monograma cresce para ocupar o
espaço liberado. É o mesmo ajuste óptico por tamanho que qualquer família de
ícones profissional aplica — e o motivo pelo qual um `.ico` guarda arte
diferente por resolução, em vez de um único bitmap reescalado.
"""


def app_icon(size: int = 1024, beta: bool = True) -> str:
    """Ícone quadrado completo, com ou sem selo (ver `BETA_MIN_PX`)."""
    S = float(size)
    scale = 0.545 if beta else 0.640      # altura da marca / lado do ícone
    dy = -0.055 if beta else 0.0
    m = S * scale                          # altura da marca
    k = m / MARK_H                         # fator de escala da grade
    mx = (S - MARK_W * k) / 2
    my = (S - m) / 2 + S * dy

    # fg=CORNSILK (não o default BLACK_FOREST): o --sunlit-clay de platinum-dusk
    # é um azul médio, não o dourado claro da Organic Earth — texto escuro nele
    # mede ~2.5:1; branco mede ~4.4:1. Ver nota junto a SUNLIT_CLAY.
    seal = beta_seal(S / 2, S * 0.836, S * 0.132, fg=CORNSILK) if beta else ""

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S:.0f} {S:.0f}" width="{size}" height="{size}">
 <defs>
  <linearGradient id="bg" x1="0" y1="0" x2="0.42" y2="1">
   <stop offset="0" stop-color="{FOREST_LIFT}"/>
   <stop offset="1" stop-color="{FOREST_DEEP}"/>
  </linearGradient>
 </defs>
 <rect width="{S:.0f}" height="{S:.0f}" rx="{S*CORNER:.3f}" fill="url(#bg)"/>
 <g transform="translate({mx:.3f} {my:.3f}) scale({k:.6f})">{mark_group(CORNSILK, SUNLIT_CLAY)}</g>
 {seal}
</svg>'''


# ══════════════════════════════════════════════════════════════════════════
# ASSINATURA HORIZONTAL (marca + logotipo + selo)
# ══════════════════════════════════════════════════════════════════════════

def lockup(on_dark: bool = True, with_beta: bool = True) -> str:
    """Marca + logotipo + designação de versão + selo, alinhados pela
    linha-base do logotipo com a linha-base do monograma."""
    ink = CORNSILK if on_dark else BLACK_FOREST
    accent = SUNLIT_CLAY if on_dark else COPPERWOOD
    sub = MUTED_CAPTION_ON_DARK if on_dark else OLIVE_LEAF

    H = MARK_H
    cap = 44.0                     # altura-de-caixa do logotipo
    gap = 26.0                     # respiro entre marca e logotipo
    track = 4.0
    x_text = MARK_W + gap
    base = 62.0                    # linha-base do logotipo
    tw = text_width(WORDMARK, cap, track)
    word, _ = text_group(WORDMARK, cap, x_text, base, ink, track)

    vcap = 17.0
    ver, _ = text_group("V2", vcap, x_text + 1.5, base + 26, sub, 8.0)
    vw = text_width("V2", vcap, 8.0)

    seal, seal_w = "", 0.0
    if with_beta:
        sh = 25.0
        sw = text_width("BETA", sh * 0.46, 14.0) + sh * 0.84
        seal_w = sw + 14.0
        seal = beta_seal(x_text + tw + 14.0 + sw / 2, base - cap / 2 + 1.0, sh,
                         accent, BLACK_FOREST if on_dark else CORNSILK)

    total_w = x_text + max(tw + seal_w, vw + 1.5)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w:.2f} {H:.0f}" width="{total_w:.0f}" height="{H:.0f}">
 {mark_group(ink, accent)}
 {word}{ver}{seal}
</svg>'''


# ══════════════════════════════════════════════════════════════════════════
# RASTERIZAÇÃO
# ══════════════════════════════════════════════════════════════════════════

def png(svg: str, size: int) -> Image.Image:
    data = cairosvg.svg2png(bytestring=svg.encode("utf-8"),
                            output_width=size, output_height=size)
    return Image.open(BytesIO(data)).convert("RGBA")


def icon_png(size: int) -> Image.Image:
    """Renderiza sempre a partir do master do tamanho pedido, para que o
    ajuste óptico (com/sem selo) seja aplicado por tamanho."""
    return png(app_icon(1024, beta=size >= BETA_MIN_PX), size)


ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
PNG_SIZES = [16, 24, 32, 48, 64, 128, 256, 512, 1024]


def write_ico(path: Path, sizes=ICO_SIZES) -> None:
    frames = [icon_png(s) for s in sizes]
    frames[-1].save(path, format="ICO",
                    sizes=[(s, s) for s in sizes],
                    append_images=frames[:-1])


ICNS_TYPES = [(b"icp4", 16), (b"icp5", 32), (b"ic07", 128), (b"ic08", 256),
              (b"ic09", 512), (b"ic10", 1024), (b"ic11", 32), (b"ic12", 64),
              (b"ic13", 256), (b"ic14", 512)]


def write_icns(path: Path) -> None:
    """Container ICNS: cabeçalho 'icns' + tamanho total, seguido de entradas
    (tipo, tamanho, PNG). Evita depender do iconutil (exclusivo do macOS)."""
    blocks = []
    for otype, size in ICNS_TYPES:
        buf = BytesIO()
        icon_png(size).save(buf, format="PNG")
        data = buf.getvalue()
        blocks.append(otype + struct.pack(">I", len(data) + 8) + data)
    body = b"".join(blocks)
    path.write_bytes(b"icns" + struct.pack(">I", len(body) + 8) + body)


def write_bmp(path: Path, svg: str, w: int, h: int) -> None:
    """BMP 24 bits sem alfa — o único formato que o NSIS aceita nas telas."""
    data = cairosvg.svg2png(bytestring=svg.encode("utf-8"),
                            output_width=w, output_height=h)
    im = Image.open(BytesIO(data)).convert("RGBA")
    flat = Image.new("RGB", im.size, FOREST_DEEP)
    flat.paste(im, mask=im.split()[3])
    flat.save(path, format="BMP")


# ══════════════════════════════════════════════════════════════════════════
# ARTES DO INSTALADOR NSIS
# ══════════════════════════════════════════════════════════════════════════

def installer_sidebar(w: int = 164, h: int = 314) -> str:
    """Painel lateral das telas de boas-vindas e de conclusão do NSIS."""
    mh = 84.0                       # altura da marca
    k = mh / MARK_H
    mx, my = (w - MARK_W * k) / 2, 58.0
    y = my + mh

    inner = w - 20.0
    word = text_centered(WORDMARK, 22.0, w / 2, y + 40, CORNSILK, 6.0, inner)
    ver = text_centered("V2", 9.5, w / 2, y + 58, MUTED_CAPTION_ON_DARK, 7.0, inner)
    tag1 = text_centered("PLATAFORMA DE REVISÃO", 6.5, w / 2, h - 30, OLIVE_LEAF, 3.0, inner)
    tag2 = text_centered("SISTEMÁTICA ASSISTIDA", 6.5, w / 2, h - 20, OLIVE_LEAF, 3.0, inner)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
 <defs><linearGradient id="g" x1="0" y1="0" x2="0.6" y2="1">
  <stop offset="0" stop-color="{FOREST_LIFT}"/><stop offset="1" stop-color="{FOREST_DEEP}"/>
 </linearGradient></defs>
 <rect width="{w}" height="{h}" fill="url(#g)"/>
 <rect x="0" y="0" width="{w}" height="3" fill="{SUNLIT_CLAY}"/>
 <g transform="translate({mx:.2f} {my:.2f}) scale({k:.5f})">{mark_group(CORNSILK, SUNLIT_CLAY)}</g>
 {word}{ver}
 <rect x="{w*0.30:.1f}" y="{y+76:.1f}" width="{w*0.40:.1f}" height="1" fill="{OLIVE_LEAF}"/>
 {beta_seal(w / 2, y + 100, 19, SUNLIT_CLAY, CORNSILK)}
 {tag1}{tag2}
</svg>'''


def installer_header(w: int = 150, h: int = 57) -> str:
    """Faixa superior das demais telas do instalador NSIS."""
    mh = 34.0
    k = mh / MARK_H
    x_text = 12 + MARK_W * k + 10
    sh = 13.0
    sw = text_width("BETA", sh * 0.46, 14.0) + sh * 0.84

    # A faixa do NSIS tem largura fixa (150 px), e o logotipo cresceu de quatro
    # para sete letras com a mudança de nome. Em vez de reajustar o corpo à mão
    # — que voltaria a quebrar na próxima troca —, o tamanho é calculado a
    # partir do que sobra: marca, respiro, palavra, selo e margem direita.
    # Sem isto o selo BETA saía cortado pela borda.
    disponivel = w - x_text - 10.0 - 9.0 - sw
    cap = 14.0
    largura_natural = text_width(WORDMARK, cap, 5.0)
    if largura_natural > disponivel:
        cap *= disponivel / largura_natural
    tracking = 5.0 * cap / 14.0
    tw = text_width(WORDMARK, cap, tracking)
    word, _ = text_group(WORDMARK, cap, x_text, 26, CORNSILK, tracking)
    vcap = 7.0
    ver, _ = text_group("V2", vcap, x_text + 1, 39, MUTED_CAPTION_ON_DARK, 5.0)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
 <rect width="{w}" height="{h}" fill="{FOREST_DEEP}"/>
 <g transform="translate(12 {(h - mh) / 2:.2f}) scale({k:.5f})">{mark_group(CORNSILK, SUNLIT_CLAY)}</g>
 {word}{ver}
 {beta_seal(x_text + tw + 9 + sw / 2, 21, sh, SUNLIT_CLAY, CORNSILK)}
 <rect x="0" y="{h - 2}" width="{w}" height="2" fill="{SUNLIT_CLAY}"/>
</svg>'''


# ══════════════════════════════════════════════════════════════════════════
# EXECUÇÃO
# ══════════════════════════════════════════════════════════════════════════

def main() -> None:
    for d in (DIR_SVG, DIR_BUILD, DIR_RESOURCES, DIR_PUBLIC):
        d.mkdir(parents=True, exist_ok=True)

    written: list[str] = []

    def note(p: Path) -> None:
        written.append(str(p.relative_to(ROOT)))

    # ── Masters vetoriais ────────────────────────────────────────────────
    mark_svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{MARK_VIEWBOX}"'
                f' width="80" height="100">{mark_group()}</svg>')
    (DIR_SVG / "rsac-mark.svg").write_text(mark_svg, encoding="utf-8")
    note(DIR_SVG / "rsac-mark.svg")

    duo_svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{MARK_VIEWBOX_SQUARE}"'
               f' width="100" height="100">{mark_group(BLACK_FOREST, COPPERWOOD)}</svg>')
    (DIR_SVG / "rsac-mark-duotone.svg").write_text(duo_svg, encoding="utf-8")
    note(DIR_SVG / "rsac-mark-duotone.svg")

    for name, svg in (("rsac-icon.svg", app_icon(1024, beta=True)),
                      ("rsac-icon-compact.svg", app_icon(1024, beta=False)),
                      ("rsac-lockup-dark.svg", lockup(on_dark=True)),
                      ("rsac-lockup-light.svg", lockup(on_dark=False)),
                      ("rsac-installer-sidebar.svg", installer_sidebar()),
                      ("rsac-installer-header.svg", installer_header())):
        (DIR_SVG / name).write_text(svg, encoding="utf-8")
        note(DIR_SVG / name)

    # ── Favicon servido pelo Vite ────────────────────────────────────────
    (DIR_PUBLIC / "favicon.svg").write_text(app_icon(512, beta=True), encoding="utf-8")
    note(DIR_PUBLIC / "favicon.svg")

    # ── buildResources do electron-builder ───────────────────────────────
    icon_png(1024).save(DIR_BUILD / "icon.png")
    note(DIR_BUILD / "icon.png")

    write_ico(DIR_BUILD / "icon.ico")
    note(DIR_BUILD / "icon.ico")

    write_icns(DIR_BUILD / "icon.icns")
    note(DIR_BUILD / "icon.icns")

    # O instalador e o desinstalador reaproveitam `icon.ico` e
    # `installerSidebar.bmp`: as chaves do electron-builder.yml apontam para os
    # mesmos arquivos, em vez de duplicar arte idêntica dentro do repositório.
    write_bmp(DIR_BUILD / "installerSidebar.bmp", installer_sidebar(), 164, 314)
    note(DIR_BUILD / "installerSidebar.bmp")
    write_bmp(DIR_BUILD / "installerHeader.bmp", installer_header(), 150, 57)
    note(DIR_BUILD / "installerHeader.bmp")

    # Ícone da janela do instalador — só tamanhos pequenos, portanto sempre
    # na variante compacta (ver BETA_MIN_PX).
    icon_png(48).save(DIR_BUILD / "installerHeaderIcon.ico", format="ICO",
                      sizes=[(16, 16), (32, 32), (48, 48)])
    note(DIR_BUILD / "installerHeaderIcon.ico")

    # ── Ícones embarcados no app (janela, Linux, dev) ────────────────────
    for size in (256, 512):
        icon_png(size).save(DIR_RESOURCES / f"icon-{size}.png")
        note(DIR_RESOURCES / f"icon-{size}.png")
    icon_png(512).save(DIR_RESOURCES / "icon.png")
    note(DIR_RESOURCES / "icon.png")

    print("Identidade visual gerada:\n  " + "\n  ".join(written))


if __name__ == "__main__":
    main()
