"""
Deriva os tokens de texto medidos para as 13 paletas do RSAC.

    python3 scripts/derivar-tokens-de-contraste.py src/styles/globals.css

Roda sobre um globals.css que ainda NÃO tenha os tokens derivados — ele insere,
não atualiza. Para regerar depois de mexer numa paleta, restaure o arquivo ao
estado sem tokens derivados (ou remova as linhas `-text`, `-on-surface`,
`-on-accent`, `text-on-*`, `-on-olive`, `accent-text`) e rode de novo.

Por que existe: `color: var(--color-X)` sobre `background: var(--color-X-bg)` é
um par escolhido a olho, e 72 dos 91 pares semânticos reprovavam em 4.5:1. Cada
token daqui sai de uma medição de contraste, preservando o matiz da paleta — o
aviso continua âmbar, o erro continua vermelho.

A regra R8 do `lint-design-tokens.mjs` impede que os pares não medidos voltem.

Regra de ouro deste script: TODAS as posições são calculadas contra o texto
ORIGINAL, e as edições são aplicadas de trás para frente. Inserções na mesma
posição são concatenadas antes de aplicar — foi exatamente a ausência disso que
corrompeu 13 declarações na primeira tentativa.
"""
import re, sys, colorsys
from collections import defaultdict

# ── Colorimetria ──────────────────────────────────────────────────────────
def h2rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))

def rgb2h(r, g, b):
    return '#%02x%02x%02x' % tuple(max(0, min(255, round(c * 255))) for c in (r, g, b))

def lum(rgb):
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = [f(c) for c in rgb]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def cr(a, b):
    if isinstance(a, str): a = h2rgb(a)
    if isinstance(b, str): b = h2rgb(b)
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)

def compoe(valor, sob):
    """Resolve #rrggbb ou rgba(r,g,b,a) empilhado sobre `sob`."""
    valor = valor.strip()
    if valor.startswith('#'):
        return valor
    m = re.match(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)', valor)
    if not m:
        return None
    r, g, b = [int(m.group(i)) / 255 for i in (1, 2, 3)]
    a = float(m.group(4)) if m.group(4) else 1.0
    sr, sg, sb = h2rgb(sob)
    return rgb2h(r * a + sr * (1 - a), g * a + sg * (1 - a), b * a + sb * (1 - a))

ALVO = 4.9   # folga sobre 4.5 para superfícies intermediárias e arredondamento

def empurra(fg, fundos):
    """Afasta a luminosidade do texto do fundo, preservando matiz e saturação."""
    pior = min(cr(fg, b) for b in fundos)
    if pior >= ALVO:
        return fg, pior
    h, l, s = colorsys.rgb_to_hls(*h2rgb(fg))
    piorbg = min(fundos, key=lambda b: cr(fg, b))
    escurecer = lum(h2rgb(piorbg)) > 0.18
    melhor, mr = fg, pior
    for k in range(1, 901):
        nl = l * (1 - k / 900) if escurecer else l + (1 - l) * (k / 900)
        c = colorsys.hls_to_rgb(h, nl, s)
        r = min(cr(c, b) for b in fundos)
        if r > mr:
            melhor, mr = rgb2h(*c), r
        if r >= ALVO:
            return rgb2h(*c), r
    return melhor, mr

def puro(bg):
    """Preto ou branco — o que vencer contra o fundo."""
    return ('#ffffff', cr('#ffffff', bg)) if cr('#ffffff', bg) >= cr('#000000', bg) \
        else ('#000000', cr('#000000', bg))

# ── Leitura ───────────────────────────────────────────────────────────────
CAMINHO = sys.argv[1]
src = open(CAMINHO).read()

blocos = [('__root__', re.search(r'^:root \{', src, re.M).start())]
for m in re.finditer(r"^\[data-theme='([\w-]+)'\]", src, re.M):
    blocos.append((m.group(1), m.start()))
blocos.sort(key=lambda x: x[1])

SEM = ['success', 'warning', 'error', 'info']
DEC = {'included': 'success', 'excluded': 'error', 'pending': 'warning'}
PARES = SEM + list(DEC)

def valores_do_bloco(b):
    v = {}
    for k in ['bg-primary', 'bg-secondary', 'bg-tertiary', 'accent'] + PARES:
        m = re.search(rf'--color-{k}:\s*(#[0-9a-fA-F]{{6}})', b)
        if m: v[k] = m.group(1)
    for k in PARES:
        m = re.search(rf'--color-{k}-bg:\s*([^;]+);', b)
        if m: v[k + '_bg'] = m.group(1)
    m = re.search(r'--color-accent-subtle:\s*([^;]+);', b)
    if m: v['accent_sub'] = m.group(1)
    m = re.search(r'--olive-leaf:\s*(#[0-9a-fA-F]{6})', b)
    if m: v['olive'] = m.group(1)
    m = re.search(r'--black-forest:\s*(#[0-9a-fA-F]{6})', b)
    if m: v['chrome'] = m.group(1)
    return v

raiz = valores_do_bloco(src[blocos[0][1]:blocos[1][1]])

# ── Planejamento das edições ──────────────────────────────────────────────
subs = []                      # (ini, fim, texto)  — substituições
ins  = defaultdict(list)       # pos -> [texto, ...] — inserções

for i, (nome, ini) in enumerate(blocos):
    fim = blocos[i + 1][1] if i + 1 < len(blocos) else len(src)
    b = src[ini:fim]
    v = dict(raiz); v.update(valores_do_bloco(b))
    if 'bg-primary' not in v or 'accent' not in v:
        continue
    superficies = [v[k] for k in ['bg-primary', 'bg-secondary', 'bg-tertiary'] if k in v]

    # 1) texto SOBRE o acento — preto ou branco, medido
    m = re.search(r'( *)--color-text-on-accent:\s*(#[0-9a-fA-F]{6});([^\n]*)', b)
    if m and cr(m.group(2), v['accent']) < ALVO:
        cor, r = puro(v['accent'])
        subs.append((ini + m.start(), ini + m.end(),
                     f"{m.group(1)}--color-text-on-accent: {cor}; /* {r:.2f}:1 sobre {v['accent']} */"))

    # 2) texto sobre --olive-leaf (pílulas no verde de marca)
    m = re.search(r'( *)--olive-leaf:\s*(#[0-9a-fA-F]{6});[^\n]*', b)
    if m:
        cor, r = puro(m.group(2))
        ins[ini + m.end()].append(
            f"\n{m.group(1)}--color-text-on-olive: {cor}; /* {r:.2f}:1 sobre {m.group(2)} */")

    # 3) terciário com margem sobre as superfícies da paleta
    m = re.search(r'( *)--color-text-tertiary:\s*(#[0-9a-fA-F]{6});([^\n]*)', b)
    if m:
        novo, r = empurra(m.group(2), superficies)
        if novo != m.group(2):
            subs.append((ini + m.start(), ini + m.end(),
                         f"{m.group(1)}--color-text-tertiary: {novo}; /* {r:.2f}:1 no pior fundo da paleta */"))

    # 4) acento como TEXTO: conteúdo, chrome escuro e tinta do acento
    m = re.search(r'( *)--color-accent:\s*#[0-9a-fA-F]{6};[^\n]*', b)
    if m and re.search(r'--color-accent:', b):
        ind = m.group(1)
        a_sup, r_sup = empurra(v['accent'], superficies)
        linhas = [f"\n{ind}--color-accent-on-surface: {a_sup}; /* {r_sup:.2f}:1 nas superfícies de conteúdo */"]
        if 'chrome' in v:
            a_chr, r_chr = empurra(v['accent'], [v['chrome']])
            linhas.append(f"\n{ind}--color-accent-on-chrome: {a_chr}; /* {r_chr:.2f}:1 sobre o chrome escuro */")
        if 'accent_sub' in v:
            tintas = [c for c in (compoe(v['accent_sub'], s0) for s0 in superficies) if c]
            if tintas:
                a_tin, r_tin = empurra(v['accent'], tintas)
                linhas.append(f"\n{ind}--color-accent-text: {a_tin}; /* {r_tin:.2f}:1 na tinta do acento */")
        ins[ini + m.end()].extend(linhas)

    # 5) tintas próprias para as paletas escuras que herdavam as claras do :root
    escura = lum(h2rgb(v['bg-primary'])) <= 0.25
    for k in SEM:
        if re.search(rf'--color-{k}-bg:', b) or not escura:
            continue
        m = re.search(rf'( *)--color-{k}:\s*(#[0-9a-fA-F]{{6}});[^\n]*', b)
        if not m:
            continue
        rr, gg, bb = [int(m.group(2).lstrip('#')[j:j+2], 16) for j in (0, 2, 4)]
        v[k + '_bg'] = f'rgba({rr}, {gg}, {bb}, 0.22)'
        ins[ini + m.end()].append(
            f"\n{m.group(1)}--color-{k}-bg: {v[k + '_bg']}; /* tinta própria: herdar a do :root deixava faixa clara com texto claro */")

    # 6) trio de tokens por família semântica
    for k in PARES:
        if k not in v or k + '_bg' not in v:
            continue
        # âncora: o -bg do próprio bloco, senão a cor cheia do próprio bloco
        m = re.search(rf'( *)--color-{k}-bg:\s*[^;]+;[^\n]*', b) or \
            re.search(rf'( *)--color-{k}:\s*#[0-9a-fA-F]{{6}};[^\n]*', b)
        if not m:
            continue
        ind = m.group(1)
        tintas = [c for c in (compoe(v[k + '_bg'], s0) for s0 in superficies) if c]
        linhas = []
        if tintas:
            t_txt, r_txt = empurra(v[k], tintas)
            linhas.append(f"\n{ind}--color-{k}-text: {t_txt}; /* {r_txt:.2f}:1 na tinta, composta sobre as superfícies */")
        if k in SEM:
            s_txt, r_s = empurra(v[k], superficies)
            linhas.append(f"\n{ind}--color-{k}-on-surface: {s_txt}; /* {r_s:.2f}:1 nas superfícies de conteúdo */")
        else:
            linhas.append(f"\n{ind}--color-{k}-on-surface: var(--color-{DEC[k]}-on-surface);")
        cor, r_on = puro(v[k])
        linhas.append(f"\n{ind}--color-text-on-{k}: {cor}; /* {r_on:.2f}:1 sobre {v[k]} */")
        ins[ini + m.end()].extend(linhas)

# 7) chrome atenuado: 62% caía a 4.41:1 na synthwave-neon (mínimo medido: 65%)
alvo = '  --color-chrome-text-muted: color-mix(in srgb, var(--color-text-sidebar-active) 62%, transparent);'
assert src.count(alvo) == 1
p = src.index(alvo)
subs.append((p, p + len(alvo),
             '  /* 70%, não 62%: a 62% a synthwave-neon caía para 4.41:1 e a\n'
             '     platinum-dusk raspava em 4.50:1. Pior mínimo medido entre as 13\n'
             '     paletas: 65%. */\n'
             '  --color-chrome-text-muted: color-mix(in srgb, var(--color-text-sidebar-active) 70%, transparent);'))

# ── Aplicação: uma passada, de trás para frente, sem sobreposição ─────────
edicoes = [(a, z, t) for a, z, t in subs] + [(p, p, ''.join(ls)) for p, ls in ins.items()]
edicoes.sort(key=lambda e: -e[0])
# checagem de sobreposição
for j in range(len(edicoes) - 1):
    if edicoes[j][0] < edicoes[j + 1][1]:
        raise SystemExit(f'EDIÇÕES SOBREPOSTAS em {edicoes[j+1]} e {edicoes[j]}')
for a, z, t in edicoes:
    src = src[:a] + t + src[z:]

open(CAMINHO, 'w').write(src)
print(f'substituições: {len(subs)} · pontos de inserção: {len(ins)} · '
      f'linhas inseridas: {sum(len(v) for v in ins.values())}')
