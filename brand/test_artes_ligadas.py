"""
Toda arte gerada tem quem a consuma — e todo consumidor aponta para arte que existe.

Por que este arquivo existe
===========================
As artes do instalador estavam certas: `installerSidebar.bmp` trazia REVSIST,
com a geometria nova, gerada e versionada. E mesmo assim quem instalava o
programa não via a marca em lugar nenhum, porque `scripts/installer.iss` nunca
as mencionou — o Inno Setup usava as imagens de fábrica dele. O arquivo estava
lá, correto, e ninguém o pedia.

É a mesma classe do defeito que fazia o Electron abrir sempre na tela de login:
não é erro de lógica, é **ausência de ligação**. Nenhum teste de comportamento
pega isso, porque cada peça, isolada, está certa. O que pega é confrontar as
duas listas — o que se produz e o que se consome — e exigir que fechem.

A tabela abaixo é a ligação escrita por extenso. Acrescentar uma arte nova
quebra o teste até que ela seja atribuída a um consumidor, o que obriga a
decisão a ser tomada em vez de esquecida.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

# ══════════════════════════════════════════════════════════════════════════
# Quem consome o quê
# ══════════════════════════════════════════════════════════════════════════
#
# Chave: caminho da arte, relativo à raiz do repositório.
# Valor: arquivos que a referenciam. Lista vazia é proibida — ou a arte tem
# consumidor, ou não deveria estar sendo gerada.

CONSUMO: dict[str, list[str]] = {
    # ---- Ícone do aplicativo -------------------------------------------
    # Um só .ico no projeto. Houve um segundo em `brand/icon.ico`, derivado de
    # um PNG de 256 px por `build_executables.py`, que nada regerava: foi essa
    # cópia que ficou com a marca antiga.
    "frontend/build/icon.ico": [
        "scripts/installer.iss",           # ícone do Setup.exe
        "frontend/electron-builder.yml",   # ícone do executável no Windows
        "scripts/build_executables.py",    # ícone do .exe do PyInstaller
    ],
    "frontend/build/icon.icns": ["frontend/electron-builder.yml"],
    "frontend/build/icon.png": ["frontend/electron-builder.yml"],

    # ---- Assistente do Inno Setup (o instalador que realmente sai) -------
    "frontend/build/innoWizardImage.bmp": ["scripts/installer.iss"],
    "frontend/build/innoWizardImage2x.bmp": ["scripts/installer.iss"],
    "frontend/build/innoWizardImage3x.bmp": ["scripts/installer.iss"],
    "frontend/build/innoWizardSmall.bmp": ["scripts/installer.iss"],
    "frontend/build/innoWizardSmall2x.bmp": ["scripts/installer.iss"],
    "frontend/build/innoWizardSmall3x.bmp": ["scripts/installer.iss"],

    # ---- Assistente do NSIS ---------------------------------------------
    # O electron-builder acha estes três pelo nome, sem serem declarados no
    # .yml — daí não aparecerem em busca textual. Só entram em jogo se alguém
    # rodar o electron-builder sem `--dir`; o build oficial usa o Inno.
    "frontend/build/installerHeader.bmp": ["<convenção do electron-builder>"],
    "frontend/build/installerSidebar.bmp": ["<convenção do electron-builder>"],
    "frontend/build/installerHeaderIcon.ico": ["<convenção do electron-builder>"],

    # ---- Embarcados em tempo de execução --------------------------------
    "frontend/resources/icon.png": [
        "frontend/electron-builder.yml",   # copiado para extraResources
        "frontend/electron/main.ts",       # ícone da janela no Linux e em dev
    ],
    "frontend/public/favicon.svg": ["frontend/index.html"],
}

# Diretórios varridos em busca de arte órfã.
DIRETORIOS = ["frontend/build", "frontend/resources", "frontend/public"]

# Referências por convenção não são textuais; não há o que procurar no arquivo.
POR_CONVENCAO = "<convenção do electron-builder>"

# O Vite publica o conteúdo de `public/` na raiz do site, então o index.html
# escreve `./favicon.svg` — sem o `public/`. É referência legítima; a exceção
# fica aqui, nomeada, e não como uma frouxidão na busca que valeria para todos.
BUSCA = {"frontend/public/favicon.svg": "favicon.svg"}


# O caminho aparece escrito de três jeitos diferentes, conforme a linguagem:
#   installer.iss   ..\frontend\build\icon.ico
#   *.py            ROOT_DIR / "frontend" / "build" / "icon.ico"
#   *.yml, *.ts     build/icon.ico
# Normalizar os dois primeiros para o terceiro é o que permite procurar uma
# coisa só. Sem isso o teste acusaria como órfã uma arte perfeitamente ligada,
# o que seria pior do que não ter teste: ensinaria a ignorá-lo.
def _texto(rel: str) -> str:
    """Conteúdo do consumidor, com todas as formas de caminho normalizadas."""
    bruto = (RAIZ / rel).read_text(encoding="utf-8")
    return bruto.replace("\\", "/").replace('" / "', "/")


@pytest.mark.parametrize("arte", sorted(CONSUMO))
def test_arte_declarada_existe_no_disco(arte: str) -> None:
    assert (RAIZ / arte).is_file(), (
        f"{arte} está na tabela mas não existe. "
        f"Rode: python brand/generate_brand_assets.py"
    )


@pytest.mark.parametrize("arte", sorted(CONSUMO))
def test_arte_tem_ao_menos_um_consumidor(arte: str) -> None:
    assert CONSUMO[arte], f"{arte} é gerada e nada a usa — não deveria ser gerada."


@pytest.mark.parametrize(
    "arte,consumidor",
    sorted((a, c) for a, cs in CONSUMO.items() for c in cs if c != POR_CONVENCAO),
)
def test_consumidor_realmente_menciona_a_arte(arte: str, consumidor: str) -> None:
    """
    O nome do arquivo aparece no consumidor?

    Busca pelos dois últimos segmentos (`build/icon.ico`) e não só pelo nome,
    porque há dois `icon.png` no projeto — um em `build/`, outro em
    `resources/` — e o nome sozinho confundiria um com o outro. Foi
    exatamente essa confusão que me fez, numa primeira olhada, dar o
    `installer.iss` por ligado quando ele apontava para outro arquivo.
    """
    sufixo = BUSCA.get(arte, "/".join(Path(arte).parts[-2:]))
    assert sufixo in _texto(consumidor), (
        f"{consumidor} não menciona {sufixo}. A arte existe e ninguém a pede — "
        f"foi assim que o instalador ficou sem a marca."
    )


@pytest.mark.parametrize("diretorio", DIRETORIOS)
def test_nenhuma_arte_no_disco_ficou_de_fora_da_tabela(diretorio: str) -> None:
    no_disco = {
        f"{diretorio}/{p.name}"
        for p in (RAIZ / diretorio).iterdir()
        if p.is_file() and not p.name.startswith(".")
    }
    orfas = sorted(no_disco - set(CONSUMO))
    assert not orfas, (
        f"Arte sem consumidor declarado: {orfas}. "
        f"Ou ligue a algum arquivo de build e registre aqui, ou pare de gerá-la."
    )


# ══════════════════════════════════════════════════════════════════════════
# Medidas que o Inno Setup exige
# ══════════════════════════════════════════════════════════════════════════
#
# O Inno não recusa um BMP fora de medida: ele estica. O resultado é uma arte
# deformada que só se nota instalando — tarde demais. Daí conferir aqui.
#
# 164x314 e 55x55 são as medidas de referência; a lista por escala existe para
# o Inno escolher conforme o DPI. Sem 2x e 3x a arte sai borrada em tela 150%.

MEDIDAS_INNO = {
    "innoWizardImage": (164, 314),
    "innoWizardSmall": (55, 55),
}


def _medidas_bmp(caminho: Path) -> tuple[int, int]:
    """Largura e altura do cabeçalho BITMAPINFOHEADER, sem depender do Pillow."""
    cab = caminho.read_bytes()[:26]
    assert cab[:2] == b"BM", f"{caminho.name} não é BMP"
    largura, altura = struct.unpack("<ii", cab[18:26])
    return largura, abs(altura)


@pytest.mark.parametrize(
    "base,escala",
    [(b, e) for b in MEDIDAS_INNO for e in (1, 2, 3)],
)
def test_arte_do_inno_tem_a_medida_certa(base: str, escala: int) -> None:
    nome = f"{base}.bmp" if escala == 1 else f"{base}{escala}x.bmp"
    lw, lh = MEDIDAS_INNO[base]
    assert _medidas_bmp(RAIZ / "frontend" / "build" / nome) == (lw * escala, lh * escala)


def test_installer_iss_declara_as_tres_escalas() -> None:
    """
    Uma escala só não é erro para o Inno — é só arte borrada em metade dos
    computadores. Como não falha em lugar nenhum, falha aqui.
    """
    iss = _texto("scripts/installer.iss")
    for chave, base in (("WizardImageFile", "innoWizardImage"),
                        ("WizardSmallImageFile", "innoWizardSmall")):
        linha = next((n for n in iss.splitlines() if n.startswith(chave + "=")), None)
        assert linha, f"{chave} ausente: o Inno cairia nas imagens de fábrica dele."
        for escala in (1, 2, 3):
            nome = f"{base}.bmp" if escala == 1 else f"{base}{escala}x.bmp"
            assert nome in linha, f"{chave} não declara {nome}"
