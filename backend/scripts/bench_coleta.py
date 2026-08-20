#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Banco de medição da coleta (sem rede).

Mede, com transporte HTTP simulado de latência conhecida, o que os coletores
BDTD e SciELO fazem com o tempo, e o que a deduplicação incremental custa e
erra. Existe para que "está lento" e "está confiável" deixem de ser impressão
e passem a ser número reproduzível — e para servir de teste de regressão de
desempenho quando o plano do doc 35 for executado.

Uso:
    python scripts/bench_coleta.py            # todas as medições
    python scripts/bench_coleta.py rede       # só coletores
    python scripts/bench_coleta.py dedup      # só deduplicação

Nada aqui toca a internet: httpx.MockTransport responde no lugar das bases,
com `LATENCIA_S` de atraso por requisição. O número que importa não é o tempo
absoluto (depende da latência simulada) e sim a **concorrência de pico** e a
fração do relógio gasta fora da rede.
"""

import asyncio
import os
import random
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from app.harvesters.base import HarvestQuery, RawPaperRecord  # noqa: E402

# ── Parâmetros do cenário ─────────────────────────────────────────────

LATENCIA_S = 0.2       # atraso por requisição simulada (otimista para as duas bases)
BDTD_REGISTROS = 200   # 2 páginas de 100
SCIELO_DESCRITORES = 10
SCIELO_PAGINAS = 4     # páginas por descritor


class Sonda:
    """Contador de requisições e de concorrência de pico do transporte simulado."""

    def __init__(self) -> None:
        self.em_voo = 0
        self.pico = 0
        self.total = 0

    async def latencia(self) -> None:
        self.em_voo += 1
        self.pico = max(self.pico, self.em_voo)
        self.total += 1
        try:
            await asyncio.sleep(LATENCIA_S)
        finally:
            self.em_voo -= 1


# ── Medição 1 · BDTD: o custo da raspagem de detalhes ─────────────────

_HTML_REGISTRO = (
    "<html><head>"
    '<meta name="dc.contributor.advisor" content="Souza, Maria"/>'
    '<meta name="instname_str" content="Universidade Federal de Santa Catarina"/>'
    "</head><body><table><tr><th>Orientador(a):</th><td>Souza, Maria</td></tr>"
    "</table></body></html>"
)


def _pagina_vufind(pagina: int, tamanho: int) -> list[dict]:
    inicio = (pagina - 1) * tamanho
    return [
        {
            "id": f"REC_{inicio + i}",
            "title": f"Trabalho {inicio + i}",
            "authors": {"primary": {"Silva, João": {}}},
            "publicationDates": ["2023"],
            "formats": ["Tese"],
            "institutions": ["UFSC"],
            "summary": ["Resumo do trabalho."],
            "languages": ["por"],
            "urls": [{"url": "https://repositorio.exemplo/1"}],
        }
        for i in range(tamanho)
    ]


async def medir_bdtd(fetch_details: bool) -> tuple[int, float, int, int]:
    import app.harvesters.bdtd as mod
    from app.harvesters.bdtd import BDTDHarvester

    sonda = Sonda()
    tamanho = BDTDHarvester.capabilities.default_page_size

    async def responder(request: httpx.Request) -> httpx.Response:
        await sonda.latencia()
        if "/api/v1/search" in request.url.path:
            pagina = int(dict(request.url.params).get("page", 1))
            vazio = (pagina - 1) * tamanho >= BDTD_REGISTROS
            return httpx.Response(
                200,
                json={
                    "status": "OK",
                    "resultCount": BDTD_REGISTROS,
                    "records": [] if vazio else _pagina_vufind(pagina, tamanho),
                },
            )
        return httpx.Response(200, text=_HTML_REGISTRO)

    original = httpx.AsyncClient
    transporte = httpx.MockTransport(responder)
    mod.httpx.AsyncClient = lambda *a, **kw: original(*a, transport=transporte, **kw)
    try:
        coletor = BDTDHarvester()
        consulta = HarvestQuery(descriptors=["descritor de teste"], fetch_details=fetch_details)
        t0 = time.perf_counter()
        n = 0
        async for _ in coletor.harvest(consulta):
            n += 1
        decorrido = time.perf_counter() - t0
    finally:
        mod.httpx.AsyncClient = original
    return n, decorrido, sonda.total, sonda.pico


# ── Medição 2 · SciELO: quanto do relógio é pausa fixa ────────────────

def _pagina_scielo(offset: int, tamanho: int, total: int) -> str:
    itens = "".join(
        f'<div class="item" id="S0103-2003202400010{i:04d}">'
        f'<div class="title"><a href="https://scielo.exemplo/a/{i}">Trabalho {offset + i}</a></div>'
        f'<div class="source"><a href="#">Revista X</a></div>'
        f'<div class="abstract">Resumo do trabalho.</div>'
        f'<span class="DOIResults">10.1590/abc{offset + i}</span></div>'
        for i in range(tamanho)
    )
    return f"<html><body><div id='TotalHits'>{total}</div>{itens}</body></html>"


async def medir_scielo() -> tuple[int, float, int, int]:
    import app.harvesters.scielo as mod
    from app.harvesters.scielo import SciELOHarvester

    sonda = Sonda()
    tamanho = SciELOHarvester.capabilities.default_page_size
    total = tamanho * SCIELO_PAGINAS

    async def responder(request: httpx.Request) -> httpx.Response:
        await sonda.latencia()
        offset = int(dict(request.url.params).get("from", 1))
        if offset > total:
            return httpx.Response(200, text="<html><body></body></html>")
        return httpx.Response(200, text=_pagina_scielo(offset, tamanho, total))

    original = httpx.AsyncClient
    transporte = httpx.MockTransport(responder)
    mod.httpx.AsyncClient = lambda *a, **kw: original(*a, transport=transporte, **kw)
    try:
        coletor = SciELOHarvester()
        consulta = HarvestQuery(descriptors=[f"descritor {i}" for i in range(SCIELO_DESCRITORES)])
        t0 = time.perf_counter()
        n = 0
        async for _ in coletor.harvest(consulta):
            n += 1
        decorrido = time.perf_counter() - t0
    finally:
        mod.httpx.AsyncClient = original
    return n, decorrido, sonda.total, sonda.pico


# ── Banco de dados temporário para as medições de deduplicação ────────

def _engine_temporario(nome: str):
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker

    from app.infrastructure.persistence.models import Base, ProjectModel

    caminho = Path(os.environ.get("TMPDIR", "/tmp")) / nome
    for sufixo in ("", "-wal", "-shm"):
        alvo = Path(str(caminho) + sufixo)
        if alvo.exists():
            alvo.unlink()

    engine = create_engine(
        f"sqlite:///{caminho}", connect_args={"check_same_thread": False, "timeout": 30}
    )

    @event.listens_for(engine, "connect")
    def _pragmas(conexao, _registro):  # noqa: ANN001
        cursor = conexao.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA cache_size=-64000")
        cursor.close()

    Base.metadata.create_all(engine)
    criar_sessao = sessionmaker(bind=engine, expire_on_commit=False)
    sessao = criar_sessao()
    sessao.add(ProjectModel(id="bench", title="Medição"))
    sessao.commit()
    sessao.close()
    return criar_sessao


_VOCABULARIO = [
    "agricultura", "territorio", "saneamento", "governanca", "semiarido", "cooperativa",
    "irrigacao", "docencia", "florestal", "pesqueiro", "urbanismo", "migracao", "tributacao",
    "vigilancia", "epidemia", "curriculo", "assentamento", "hidrico", "carbono", "turismo",
    "industria", "cadeia", "quilombola", "indigena", "bioma", "credito", "logistica", "porto",
]


# ── Medição 3 · Deduplicação incremental: escala ──────────────────────

def medir_dedup_escala(n_total: int = 8000, lote: int = 25) -> list[tuple[int, float, float]]:
    from app.services.dedup_service import DeduplicationService

    criar_sessao = _engine_temporario("rsac_bench_dedup.db")
    servico = DeduplicationService()
    aleatorio = random.Random(7)

    registros = [
        RawPaperRecord(
            title=" ".join(random.Random(i).sample(_VOCABULARIO, 6)),
            year="2020",
            source_name="BDTD",
            source_id=f"S{i}",
            doi=f"10.1590/x{i}" if i % 3 == 0 else None,
        )
        for i in range(n_total)
    ]
    aleatorio.shuffle(registros)

    marcos = [m for m in (500, 1000, 2000, 4000, 8000) if m <= n_total]
    medidos: dict[int, float] = {}
    t0 = time.perf_counter()
    for inicio in range(0, n_total, lote):
        sessao = criar_sessao()
        try:
            servico.process_batch(sessao, "bench", registros[inicio : inicio + lote])
        finally:
            sessao.close()
        if (inicio + lote) in marcos:
            medidos[inicio + lote] = time.perf_counter() - t0

    linhas = []
    n_anterior, t_anterior = 0, 0.0
    for marco in sorted(medidos):
        linhas.append(
            (marco, medidos[marco], (marco - n_anterior) / (medidos[marco] - t_anterior))
        )
        n_anterior, t_anterior = marco, medidos[marco]
    return linhas


# ── Medição 4 · Deduplicação sob duas fontes simultâneas ──────────────

def medir_dedup_corrida(n_titulos: int = 300) -> tuple[int, int]:
    from app.infrastructure.persistence.models import PaperModel
    from app.services.dedup_service import DeduplicationService

    criar_sessao = _engine_temporario("rsac_bench_corrida.db")
    servico = DeduplicationService()
    aleatorio = random.Random(3)
    titulos = list(
        dict.fromkeys(" ".join(aleatorio.sample(_VOCABULARIO, 6)) for _ in range(n_titulos))
    )

    def trabalhador(fonte: str) -> None:
        registros = [
            RawPaperRecord(
                title=t, year="2021", source_name=fonte, source_id=f"{fonte}-{i}",
                doi=f"10.1590/z{i}",
            )
            for i, t in enumerate(titulos)
        ]
        for inicio in range(0, len(registros), 25):
            sessao = criar_sessao()
            try:
                servico.process_batch(sessao, "bench", registros[inicio : inicio + 25])
            except Exception as erro:  # noqa: BLE001
                print(f"    [{fonte}] {type(erro).__name__}: {str(erro)[:80]}")
            finally:
                sessao.close()

    threads = [threading.Thread(target=trabalhador, args=(f,)) for f in ("BDTD", "SciELO")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    sessao = criar_sessao()
    gravados = sessao.query(PaperModel).filter(PaperModel.project_id == "bench").count()
    sessao.close()
    return len(titulos), gravados


# ── Medição 5 · Falsos positivos da similaridade de título ────────────

_PARES = [
    ("Avaliação do programa X no Nordeste: parte I",
     "Avaliação do programa X no Nordeste: parte II"),
    ("Dinâmicas territoriais do semiárido: volume 1",
     "Dinâmicas territoriais do semiárido: volume 2"),
    ("Saneamento básico em Recife entre 2010 e 2015",
     "Saneamento básico em Recife entre 2016 e 2020"),
    ("Efeitos da seca sobre a agricultura familiar",
     "Efeitos da chuva sobre a agricultura familiar"),
    ("Análise do uso do solo urbano em Fortaleza",
     "Análise do uso do solo rural em Fortaleza"),
]


def medir_falsos_positivos(limiar: float = 92.0) -> list[tuple[float, bool, str, str]]:
    from rapidfuzz import fuzz

    from app.services.dedup_service import DeduplicationService as D

    saida = []
    for a, b in _PARES:
        na, nb = D.normalize_title(a), D.normalize_title(b)
        mesma_chave = D.generate_blocking_key(na) == D.generate_blocking_key(nb)
        razao = fuzz.token_sort_ratio(na, nb)
        saida.append((razao, bool(razao >= limiar and mesma_chave), a, b))
    return saida


# ── Relatório ─────────────────────────────────────────────────────────

def _cabecalho(texto: str) -> None:
    print(f"\n{texto}\n{'─' * len(texto)}")


async def bloco_rede() -> None:
    _cabecalho(f"1 · Coletores — latência simulada de {LATENCIA_S * 1000:.0f} ms por requisição")
    print(f"{'cenário':<34}{'reg':>6}{'req':>6}{'tempo':>9}{'reg/s':>9}{'pico':>7}")
    for detalhes in (False, True):
        n, dt, req, pico = await medir_bdtd(detalhes)
        rotulo = f"BDTD fetch_details={str(detalhes).lower()}"
        print(f"{rotulo:<34}{n:>6}{req:>6}{dt:>8.2f}s{n / dt:>9.1f}{pico:>7}")

    n, dt, req, pico = await medir_scielo()
    rede = req * LATENCIA_S
    rotulo = f"SciELO {SCIELO_DESCRITORES} descritores"
    print(f"{rotulo:<34}{n:>6}{req:>6}{dt:>8.2f}s{n / dt:>9.1f}{pico:>7}")
    print(
        f"\n  SciELO: {rede:.1f}s de rede em {dt:.1f}s de relógio — "
        f"{(dt - rede) / dt * 100:.0f}% do tempo é pausa fixa, não requisição."
    )
    print("  'pico' é a concorrência máxima observada no transporte. 1 = execução serial.")


def bloco_dedup() -> None:
    _cabecalho("2 · Deduplicação incremental — escala")
    print(f"{'N acumulado':>12}{'tempo (s)':>12}{'reg/s no trecho':>18}")
    for marco, acumulado, taxa in medir_dedup_escala():
        print(f"{marco:>12}{acumulado:>12.2f}{taxa:>18.0f}")

    _cabecalho("3 · Deduplicação sob duas fontes simultâneas")
    esperado, gravados = medir_dedup_corrida()
    print(f"  títulos distintos enviados : {esperado}")
    print(f"  papers gravados            : {gravados}")
    print(f"  duplicatas que escaparam   : {gravados - esperado}")

    _cabecalho("4 · Falsos positivos da similaridade de título (limiar 92)")
    for razao, funde, a, b in medir_falsos_positivos():
        marca = "FUNDE" if funde else " ok  "
        print(f"  {razao:5.1f}  {marca}  {a[:52]!r}\n{'':16}{b[:52]!r}")


async def principal() -> None:
    alvo = sys.argv[1] if len(sys.argv) > 1 else "tudo"
    print("RSAC V2 — banco de medição da coleta (sem rede)")
    if alvo in ("tudo", "rede"):
        await bloco_rede()
    if alvo in ("tudo", "dedup"):
        bloco_dedup()
    print()


if __name__ == "__main__":
    asyncio.run(principal())
