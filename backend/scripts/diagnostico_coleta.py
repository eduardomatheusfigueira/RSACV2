#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Diagnóstico ao vivo da coleta SciELO e BDTD.

Roda fora da aplicação e responde, em uma execução, por que uma das duas fontes
volta zerada. Verifica, em ordem:

  1. ambiente (parser de HTML disponível — o executável empacotado já subiu sem
     `lxml`, o que derruba a raspagem das duas bases);
  2. alcance de rede e status HTTP de cada endpoint;
  3. se a resposta tem a estrutura que o coletor espera (itens do SciELO,
     `records` da BDTD);
  4. se os filtros do protocolo (faixa de anos, idiomas) estão zerando o
     resultado — a faixa entre aspas e o rótulo de idioma são as duas armadilhas
     conhecidas;
  5. o coletor de verdade, ponta a ponta, com um descritor curto.

Uso:
    python backend/scripts/diagnostico_coleta.py
    python backend/scripts/diagnostico_coleta.py --descritor "turismo náutico"
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from app.harvesters.base import HarvestQuery, HarvestSourceError  # noqa: E402
from app.harvesters.bdtd import BDTDHarvester  # noqa: E402
from app.harvesters.html_parser import LXML_DISPONIVEL, make_soup  # noqa: E402
from app.harvesters.scielo import SciELOHarvester  # noqa: E402

OK = "\033[92m[OK]\033[0m"
FALHA = "\033[91m[FALHA]\033[0m"
AVISO = "\033[93m[AVISO]\033[0m"

NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def titulo(texto: str) -> None:
    print("\n" + "=" * 72)
    print(f"  {texto}")
    print("=" * 72)



def verificar_ambiente() -> None:
    titulo("1. Ambiente de execução")
    print(f"  Python           : {sys.version.split()[0]}")
    print(f"  Executável        : {sys.executable}")
    print(f"  Empacotado (exe)  : {getattr(sys, 'frozen', False)}")
    if LXML_DISPONIVEL:
        print(f"{OK} lxml disponível — raspagem de HTML em modo rápido.")
    else:
        print(
            f"{AVISO} lxml AUSENTE. A raspagem cai para 'html.parser' (mais lenta, "
            "porém funcional). No executável empacotado, compile com "
            "--hidden-import=lxml."
        )
    proxies = {k: v for k, v in os.environ.items() if k.lower() in ("http_proxy", "https_proxy", "no_proxy")}
    if proxies:
        print(f"{AVISO} Proxy configurado no ambiente: {proxies}")


async def diagnosticar_scielo(descritor: str) -> None:
    titulo("2. SciELO — Crossref REST API (Membros SciELO)")
    harvester = SciELOHarvester()
    member_filter = ",".join(f"member:{m}" for m in harvester.MEMBER_IDS)
    params = {"query": descritor, "filter": member_filter, "rows": "5", "cursor": "*"}

    async with httpx.AsyncClient(timeout=40.0, follow_redirects=True, headers=harvester.headers) as client:
        try:
            res = await client.get(harvester.BASE_URL, params=params)
        except Exception as e:
            print(f"{FALHA} Não foi possível alcançar {harvester.BASE_URL}: {type(e).__name__}: {e}")
            print("       → sem rota de rede até a API (firewall, proxy ou DNS).")
            return

        print(f"  API Crossref SciELO   : HTTP {res.status_code} · {len(res.text)} bytes")
        if res.status_code == 403:
            print(f"{FALHA} 403: bloqueio de acesso.")
            return
        if res.status_code != 200:
            print(f"{FALHA} Status inesperado HTTP {res.status_code}.")
            return

        try:
            data = res.json()
        except Exception as e:
            print(f"{FALHA} Resposta não é JSON válido: {e}")
            return

        message = data.get("message", {})
        total_results = message.get("total-results", 0)
        itens = message.get("items", [])
        print(f"  total-results         : {total_results}")
        print(f"  itens na página       : {len(itens)}")

        if not itens:
            print(f"{AVISO} Nenhum item retornado para o descritor '{descritor}'.")
            return

        from app.harvesters.scielo import parse_crossref_scielo_item

        registro = parse_crossref_scielo_item(itens[0], descriptor=descritor)
        print(f"{OK} Primeiro registro: {registro.title[:80]!r} ({registro.year}) DOI={registro.doi}")
        print(f"       Periódico: {registro.journal}")
        print(f"       Autores: {registro.authors[:70]}")



async def diagnosticar_bdtd(descritor: str) -> None:
    titulo("3. BDTD — API VuFind")
    harvester = BDTDHarvester()

    async with httpx.AsyncClient(timeout=50.0, follow_redirects=True, headers=harvester.headers) as client:
        base_ok = None
        for base_url in harvester.BASE_URLS:
            params = {
                "lookfor": descritor,
                "type": "AllFields",
                "page": 1,
                "limit": 5,
                "field[]": harvester.REQUEST_FIELDS,
            }
            try:
                res = await client.get(base_url, params=params)
            except Exception as e:
                print(f"{FALHA} {base_url}: {type(e).__name__}: {e}")
                continue

            print(f"  {base_url} → HTTP {res.status_code}")
            if res.status_code == 403:
                print(f"{FALHA} 403: bloqueio do WAF (o cookie de verificação pode ter expirado).")
                continue
            if res.status_code == 429:
                print(f"{AVISO} 429: limite de requisições atingido.")
                continue
            if res.status_code != 200:
                continue

            try:
                data = res.json()
            except Exception as e:
                print(f"{FALHA} Resposta não é JSON: {e}")
                continue

            print(f"  resultCount           : {data.get('resultCount')}")
            registros = data.get("records", [])
            print(f"  registros na página   : {len(registros)}")
            if registros:
                idiomas = registros[0].get("languages", [])
                print(f"{OK} Primeiro registro: {str(registros[0].get('title'))[:70]!r}")
                print(f"       Idiomas declarados pela base: {idiomas}")
                print(
                    "       → estes são os valores comparados com o filtro de idioma "
                    "do protocolo (normalizados por `normalize_language`)."
                )
                base_ok = base_url
                break

        if not base_ok:
            print(f"{FALHA} Nenhum endpoint da BDTD respondeu com registros.")
            return

        # Armadilha conhecida: faixa de anos entre aspas anula a busca
        titulo("4. BDTD — efeito dos filtros de faixa de ano")
        for rotulo, filtro in (
            ("sem aspas (correto)", "publishDate:[2010 TO 2024]"),
            ("com aspas (defeito antigo)", 'publishDate:"[2010 TO 2024]"'),
        ):
            params = {
                "lookfor": descritor,
                "type": "AllFields",
                "page": 1,
                "limit": 5,
                "filter[]": [filtro],
            }
            try:
                res = await client.get(base_ok, params=params)
                total = res.json().get("resultCount") if res.status_code == 200 else f"HTTP {res.status_code}"
            except Exception as e:
                total = f"{type(e).__name__}: {e}"
            print(f"  {rotulo:28s} → resultCount = {total}")


async def diagnosticar_coletores(descritor: str) -> None:
    titulo("5. Coletores ponta a ponta (máx. 5 registros por descritor)")
    for nome, harvester in (("SciELO", SciELOHarvester()), ("BDTD", BDTDHarvester())):
        query = HarvestQuery(descriptors=[descritor], max_records_per_descriptor=5, fetch_details=False)
        total = 0
        try:
            async for registro in harvester.harvest(query):
                total += 1
                if total == 1:
                    print(f"  [{nome}] primeiro: {registro.title[:70]!r}")
        except HarvestSourceError as e:
            print(f"{FALHA} {e}")
            continue
        except Exception as e:
            print(f"{FALHA} [{nome}] erro inesperado: {type(e).__name__}: {e}")
            continue

        if total:
            print(f"{OK} [{nome}] {total} registros recuperados.")
        else:
            print(f"{AVISO} [{nome}] zero registros — busca legítima sem resultados para este descritor.")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnóstico ao vivo da coleta SciELO/BDTD.")
    parser.add_argument("--descritor", default="turismo", help="Descritor usado nas sondagens.")
    args = parser.parse_args()

    print("\n Revsist — Diagnóstico de coleta (SciELO e BDTD)")
    print(f" Descritor de sondagem: {args.descritor!r}")

    verificar_ambiente()
    await diagnosticar_scielo(args.descritor)
    await diagnosticar_bdtd(args.descritor)
    await diagnosticar_coletores(args.descritor)

    titulo("Fim do diagnóstico")
    print(
        "  Envie a saída acima ao suporte técnico do projeto: ela distingue "
        "bloqueio do portal, mudança de layout, ausência de parser e filtro "
        "restritivo demais.\n"
    )


if __name__ == "__main__":
    asyncio.run(main())
