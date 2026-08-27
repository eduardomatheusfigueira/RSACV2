#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Bordas da coleta SciELO/BDTD: as situações em que a fonte volta vazia.

Zero registros tem causas incompatíveis entre si — busca legítima sem
resultados, bloqueio do portal, mudança de layout e filtro restritivo demais —
e apenas a primeira é sucesso. Tratar todas como "coleta concluída" publica um
número falso no fluxograma PRISMA, que é o que estes testes impedem.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.harvesters.base import HarvestQuery, HarvestSourceError
from app.harvesters.bdtd import BDTDHarvester, normalize_language, sanitize_bdtd_filters
from app.harvesters.html_parser import make_soup
from app.harvesters.scielo import SciELOHarvester


def _cliente_mock(resposta) -> MagicMock:
    """Cliente httpx assíncrono que devolve sempre a mesma resposta."""
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    client.get.return_value = resposta
    return client


def _resposta_html(html: str, status: int = 200) -> MagicMock:
    res = MagicMock()
    res.status_code = status
    res.text = html
    return res


def _resposta_json(payload: dict, status: int = 200) -> MagicMock:
    res = MagicMock()
    res.status_code = status
    res.json.return_value = payload
    return res


async def _coletar(harvester, query) -> list:
    return [registro async for registro in harvester.harvest(query)]


# ── Parser de HTML ─────────────────────────────────────────────────────


def test_make_soup_degrada_sem_lxml():
    """Sem lxml a raspagem continua com o parser da biblioteca padrão."""
    with patch("app.harvesters.html_parser.parser_preferido", return_value="parser-inexistente"):
        soup = make_soup("<div class='item'><div class='title'>Título</div></div>")
    assert soup.find(class_="title").text == "Título"


# ── SciELO ─────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_scielo_falha_de_rede_nao_vira_coleta_vazia():
    """5xx em todas as tentativas precisa falhar de forma visível, não retornar zero."""
    harvester = SciELOHarvester()
    harvester.MAX_TENTATIVAS = 1  # encurta o backoff exponencial no teste

    with patch("httpx.AsyncClient", return_value=_cliente_mock(_resposta_html("", status=503))), \
            patch("asyncio.sleep", new=AsyncMock()):
        with pytest.raises(HarvestSourceError) as exc:
            await _coletar(harvester, HarvestQuery(descriptors=["turismo"]))

    assert "nenhuma página de resultados" in str(exc.value)
    assert exc.value.source_name == "SciELO"


@pytest.mark.anyio
async def test_scielo_bloqueio_403_e_reportado():
    """403 do WAF é reportado como falha da fonte, e não como busca sem resultados."""
    harvester = SciELOHarvester()
    harvester.MAX_TENTATIVAS = 1

    with patch("httpx.AsyncClient", return_value=_cliente_mock(_resposta_html("", status=403))), \
            patch("asyncio.sleep", new=AsyncMock()):
        with pytest.raises(HarvestSourceError):
            await _coletar(harvester, HarvestQuery(descriptors=["turismo"]))


@pytest.mark.anyio
async def test_scielo_busca_legitimamente_vazia_nao_e_erro():
    """A página de 'nenhum resultado' é resposta válida: zero registros, sem exceção."""
    harvester = SciELOHarvester()
    html = "<html><body><p>Nenhum resultado encontrado para a sua busca.</p></body></html>"

    with patch("httpx.AsyncClient", return_value=_cliente_mock(_resposta_html(html))), \
            patch("asyncio.sleep", new=AsyncMock()):
        registros = await _coletar(harvester, HarvestQuery(descriptors=["termo inexistente"]))

    assert registros == []


@pytest.mark.anyio
async def test_scielo_layout_alterado_e_denunciado():
    """A página anuncia resultados mas nenhum item casa com o parser → falha explícita."""
    harvester = SciELOHarvester()
    html = """
    <html><body>
      <div id="TotalHits">128</div>
      <section class="resultado"><article class="novo-layout">Trabalho</article></section>
    </body></html>
    """

    with patch("httpx.AsyncClient", return_value=_cliente_mock(_resposta_html(html))), \
            patch("asyncio.sleep", new=AsyncMock()):
        with pytest.raises(HarvestSourceError) as exc:
            await _coletar(harvester, HarvestQuery(descriptors=["turismo"]))

    assert "layout" in str(exc.value).lower()


@pytest.mark.anyio
async def test_scielo_avisa_descritor_incompleto_sem_perder_o_que_veio():
    """Um descritor que falha não pode derrubar o que os outros trouxeram."""
    harvester = SciELOHarvester()
    harvester.MAX_TENTATIVAS = 1

    html_ok = """
    <html><body>
      <div id="TotalHits">1</div>
      <div class="item" id="S0103-20032024000100005">
        <div class="title"><a href="#">Turismo fluvial na fronteira</a></div>
        <div class="source"><a href="#">Revista Regional</a></div>
      </div>
    </body></html>
    """

    respostas = [
        _resposta_html(html_ok),          # aquecimento
        _resposta_html(html_ok),          # descritor 1
        _resposta_html("", status=500),   # descritor 2 falha
    ]

    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    client.get = AsyncMock(side_effect=respostas + [_resposta_html("", status=500)] * 10)

    avisos = []

    async def on_progress(progresso):
        if progresso.error:
            avisos.append(progresso.error)

    with patch("httpx.AsyncClient", return_value=client), patch("asyncio.sleep", new=AsyncMock()):
        registros = [
            r
            async for r in harvester.harvest(
                HarvestQuery(descriptors=["turismo", "fronteira"]), on_progress=on_progress
            )
        ]

    assert len(registros) == 1
    assert avisos, "a coleta parcial precisa ser anunciada no evento de conclusão"
    assert "incompletos" in avisos[-1]


# ── BDTD ───────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_bdtd_api_indisponivel_nao_vira_coleta_vazia():
    harvester = BDTDHarvester()

    with patch("httpx.AsyncClient", return_value=_cliente_mock(_resposta_json({}, status=503))), \
            patch("asyncio.sleep", new=AsyncMock()):
        with pytest.raises(HarvestSourceError) as exc:
            await _coletar(harvester, HarvestQuery(descriptors=["turismo"], fetch_details=False))

    assert "nenhuma consulta" in str(exc.value)


def test_bdtd_faixa_de_anos_vai_sem_aspas():
    """Com aspas o VuFind lê '[2010 TO 2024]' como frase literal e a busca zera."""
    api_filters, _ = sanitize_bdtd_filters(["publishDate:[2010 TO 2024]"])
    assert api_filters == ["publishDate:[2010 TO 2024]"]


@pytest.mark.anyio
async def test_bdtd_filtro_de_ano_montado_sem_aspas():
    harvester = BDTDHarvester()
    payload = {"status": "OK", "resultCount": 0, "records": []}
    client = _cliente_mock(_resposta_json(payload))

    with patch("httpx.AsyncClient", return_value=client), patch("asyncio.sleep", new=AsyncMock()):
        await _coletar(
            harvester,
            HarvestQuery(descriptors=["turismo"], year_start=2010, year_end=2024, fetch_details=False),
        )

    filtros = client.get.call_args.kwargs["params"]["filter[]"]
    assert filtros == ["publishDate:[2010 TO 2024]"]


def test_normalize_language_reconhece_rotulos_e_codigos():
    for valor in ("por", "pt", "pt-BR", "Português", "Portuguese"):
        assert normalize_language(valor) == "por"
    assert normalize_language("English") == "eng"
    assert normalize_language("Español") == "spa"


@pytest.mark.anyio
async def test_bdtd_filtro_de_idioma_aceita_rotulo_de_exibicao():
    """A base devolve 'Português' onde o protocolo pede 'pt' — o registro deve passar."""
    harvester = BDTDHarvester()
    payload = {
        "status": "OK",
        "resultCount": 2,
        "records": [
            {
                "id": "REC_1",
                "title": "Turismo fluvial na tríplice fronteira",
                "publicationDates": ["2022"],
                "languages": ["Português"],
                "formats": ["Dissertação"],
                "summary": ["Resumo."],
            },
            {
                "id": "REC_2",
                "title": "Border tourism study",
                "publicationDates": ["2022"],
                "languages": ["English"],
                "formats": ["Tese"],
                "summary": ["Summary."],
            },
        ],
    }

    with patch("httpx.AsyncClient", return_value=_cliente_mock(_resposta_json(payload))), \
            patch("asyncio.sleep", new=AsyncMock()):
        registros = await _coletar(
            harvester,
            HarvestQuery(descriptors=["turismo"], languages=["pt"], fetch_details=False),
        )

    assert [r.title for r in registros] == ["Turismo fluvial na tríplice fronteira"]


@pytest.mark.anyio
async def test_bdtd_avisa_quando_o_filtro_de_idioma_zera_a_coleta():
    harvester = BDTDHarvester()
    payload = {
        "status": "OK",
        "resultCount": 1,
        "records": [
            {
                "id": "REC_1",
                "title": "Border tourism study",
                "publicationDates": ["2022"],
                "languages": ["eng"],
                "formats": ["Tese"],
                "summary": ["Summary."],
            }
        ],
    }

    avisos = []

    async def on_progress(progresso):
        if progresso.error:
            avisos.append(progresso.error)

    with patch("httpx.AsyncClient", return_value=_cliente_mock(_resposta_json(payload))), \
            patch("asyncio.sleep", new=AsyncMock()):
        registros = [
            r
            async for r in harvester.harvest(
                HarvestQuery(descriptors=["turismo"], languages=["pt"], fetch_details=False),
                on_progress=on_progress,
            )
        ]

    assert registros == []
    assert avisos and "filtro de idioma" in avisos[-1]


@pytest.mark.anyio
async def test_bdtd_registro_guarda_o_acervo_de_origem():
    """BDTD e OasisBR são acervos distintos: o registro precisa dizer de qual veio."""
    harvester = BDTDHarvester()
    payload = {
        "status": "OK",
        "resultCount": 1,
        "records": [
            {
                "id": "UFAM_1",
                "title": "Policiamento fluvial integrado",
                "publicationDates": ["2025"],
                "languages": ["por"],
                "formats": ["Dissertação"],
                "summary": ["Resumo."],
            }
        ],
    }

    with patch("httpx.AsyncClient", return_value=_cliente_mock(_resposta_json(payload))), \
            patch("asyncio.sleep", new=AsyncMock()):
        registros = await _coletar(
            harvester, HarvestQuery(descriptors=["turismo"], fetch_details=False)
        )

    assert registros[0].extra_metadata["acervo"] == "https://bdtd.ibict.br"
    assert registros[0].download_url.startswith("https://bdtd.ibict.br/vufind/Record/")
