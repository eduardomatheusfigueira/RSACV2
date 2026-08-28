#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Isolamento entre assinantes (doc 40 §40.3, doc 41 Fase 1).

Este é o portão do bloqueante crítico. Até a Fase 1, `ProjectModel` não tinha
dono e **nenhuma** rota filtrava por usuário: qualquer conta autenticada lia,
editava e apagava o acervo de qualquer outra. Enquanto o único cliente era o
Electron na própria máquina isso era irrelevante; publicado o serviço para dois
assinantes, é entregar o acervo de um ao outro — e, como o RSAC ocupa a posição
de **operador** (doc 37 §37.2.2), vazamento entre controladores distintos.

O teste que importa aqui é `test_nenhuma_rota_de_projeto_escapa_do_isolamento`:
em vez de listar as rotas à mão — lista que envelheceria no primeiro PR —, ele
**enumera `app.routes`** e exige 404 de todas. Uma rota nova sem isolamento
quebra a suíte sem que ninguém precise lembrar de acrescentá-la aqui.
"""

from __future__ import annotations

import httpx
import pytest
from app.api.deps import get_db
from app.infrastructure.persistence.models import (
    PaperModel,
    ProjectModel,
    UserModel,
)
from app.main import create_app
from app.security.passwords import hash_password
from tests.conftest import OWNER_ID_TESTE, OWNER_USERNAME, SENHA_TESTE

INTRUSO_ID = "conta-intrusa"
INTRUSO_USERNAME = "intruso_teste"

# Métodos que alteram estado e não vale a pena exercitar às cegas: um POST em
# `/harvest` dispararia coleta de verdade. O que se verifica é a barreira, e
# ela é a mesma para todos os métodos — vem da dependência do router.
METODOS_SEGUROS = {"GET", "DELETE", "PATCH", "PUT"}


@pytest.fixture
def acervo(db_session):
    """Um projeto com um estudo, pertencente à conta dona."""
    projeto = ProjectModel(
        id="projeto-do-dono",
        owner_id=OWNER_ID_TESTE,
        title="Revisão do titular",
        methodology="PRISMA-ScR",
    )
    paper = PaperModel(
        id="estudo-do-dono",
        project_id="projeto-do-dono",
        title="Estudo que não é de todo mundo",
    )
    db_session.add_all([projeto, paper])
    db_session.commit()
    return {"projeto": projeto, "paper": paper}


@pytest.fixture
def intruso(db_session):
    """Uma segunda conta, legítima e sem nenhuma relação com o acervo acima."""
    conta = UserModel(
        id=INTRUSO_ID,
        username=INTRUSO_USERNAME,
        password_hash=hash_password(SENHA_TESTE),
        role="owner",  # o papel mais alto — a barreira não é de papel, é de dono
    )
    db_session.add(conta)
    db_session.commit()
    return conta


async def _cliente(db_session, username: str) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    cliente = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    )
    res = await cliente.post(
        "/api/v1/auth/login", json={"username": username, "password": SENHA_TESTE}
    )
    assert res.status_code == 200, res.text
    cliente.headers["Authorization"] = f"Bearer {res.json()['access_token']}"
    return cliente


def _rotas_de_projeto(app) -> list[tuple[str, str]]:
    """
    Toda rota HTTP cujo caminho carrega `{project_id}`, com um método seguro.

    A enumeração sai do **esquema OpenAPI**, e não de `app.routes`. Andar pela
    árvore de rotas exigiria alcançar `_IncludedRouter.original_router`, um
    atributo interno do FastAPI que já mudou de forma entre versões: um teste
    que dependesse dele passaria a encontrar zero rotas depois de um upgrade —
    e continuaria verde, dando a impressão de cobertura sem tê-la. O esquema é
    API pública e lista exatamente o que o servidor expõe.
    """
    esquema = app.openapi()
    encontradas: list[tuple[str, str]] = []
    for caminho, operacoes in esquema.get("paths", {}).items():
        if "{project_id}" not in caminho:
            continue
        for metodo in operacoes:
            if metodo.upper() in METODOS_SEGUROS:
                encontradas.append((metodo.upper(), caminho))
    return sorted(set(encontradas))


@pytest.mark.anyio
async def test_nenhuma_rota_de_projeto_escapa_do_isolamento(db_session, acervo, intruso):
    """
    Para **toda** rota com `{project_id}`, o intruso recebe 404.

    A enumeração é o ponto: uma rota nova que esqueça a dependência de
    titularidade aparece aqui sozinha, e falha. Fosse uma lista escrita à mão,
    envelheceria no primeiro PR e daria a impressão de cobertura sem tê-la.
    """
    cliente = await _cliente(db_session, INTRUSO_USERNAME)
    app_rotas = create_app()
    rotas = _rotas_de_projeto(app_rotas)

    assert len(rotas) >= 15, f"a enumeração encontrou poucas rotas ({len(rotas)})"

    escaparam: list[str] = []
    for metodo, molde in rotas:
        caminho = (
            molde.replace("{project_id}", acervo["projeto"].id)
            .replace("{paper_id}", acervo["paper"].id)
            .replace("{source_name}", "SCOPUS")
            .replace("{provider}", "gemini")
        )
        if "{" in caminho:  # parâmetro que este teste não sabe preencher
            continue

        resposta = await cliente.request(metodo, caminho)
        if resposta.status_code != 404:
            escaparam.append(f"{metodo} {caminho} -> {resposta.status_code}")
    await cliente.aclose()

    assert not escaparam, "rotas que não isolaram o acervo:\n  " + "\n  ".join(escaparam)


@pytest.mark.anyio
async def test_o_dono_alcanca_o_proprio_acervo(db_session, acervo, intruso):
    """A barreira não pode ser um 404 universal: para o dono, tudo responde."""
    cliente = await _cliente(db_session, OWNER_USERNAME)
    projeto = await cliente.get(f"/api/v1/projects/{acervo['projeto'].id}")
    papers = await cliente.get(f"/api/v1/projects/{acervo['projeto'].id}/papers")
    await cliente.aclose()

    assert projeto.status_code == 200
    assert projeto.json()["title"] == "Revisão do titular"
    assert papers.status_code == 200
    assert papers.json()["total"] == 1


@pytest.mark.anyio
async def test_listagem_mostra_so_o_que_e_do_usuario(db_session, acervo, intruso):
    """O intruso não vê o projeto alheio na própria listagem."""
    cliente = await _cliente(db_session, INTRUSO_USERNAME)
    antes = await cliente.get("/api/v1/projects")
    criado = await cliente.post(
        "/api/v1/projects",
        json={"title": "Revisão do intruso", "methodology": "PRISMA 2020"},
    )
    depois = await cliente.get("/api/v1/projects")
    await cliente.aclose()

    assert antes.json()["total"] == 0, "o acervo alheio apareceu na listagem"
    assert criado.status_code == 201
    titulos = [p["title"] for p in depois.json()["items"]]
    assert titulos == ["Revisão do intruso"]


@pytest.mark.anyio
async def test_projeto_criado_pertence_a_quem_o_criou(db_session, intruso):
    """A titularidade é gravada na criação, não inferida depois."""
    cliente = await _cliente(db_session, INTRUSO_USERNAME)
    res = await cliente.post(
        "/api/v1/projects",
        json={"title": "Projeto novo", "methodology": "PRISMA-P"},
    )
    await cliente.aclose()
    assert res.status_code == 201

    gravado = (
        db_session.query(ProjectModel).filter(ProjectModel.id == res.json()["id"]).first()
    )
    assert gravado.owner_id == INTRUSO_ID


@pytest.mark.anyio
async def test_a_resposta_e_404_e_nunca_403(db_session, acervo, intruso):
    """
    Negar a existência é a resposta que não entrega nada.

    Um 403 confirmaria que aquele projeto existe. Como o identificador é um
    UUID, confirmar a existência é a única informação que quem sonda ainda não
    tem — e é justamente o que não se deve dar.
    """
    cliente = await _cliente(db_session, INTRUSO_USERNAME)
    existente = await cliente.get(f"/api/v1/projects/{acervo['projeto'].id}")
    inexistente = await cliente.get("/api/v1/projects/nao-existe-em-lugar-nenhum")
    await cliente.aclose()

    assert existente.status_code == 404
    assert inexistente.status_code == 404
    assert existente.json() == inexistente.json(), (
        "a resposta distingue projeto alheio de projeto inexistente"
    )


@pytest.mark.anyio
async def test_excluir_projeto_apaga_os_pdfs_do_disco(db_session, acervo, intruso, tmp_path):
    """
    A eliminação alcança o disco, não só o banco (item L-24 do doc 38).

    A cascata era rigorosa nas tabelas e ignorava o sistema de arquivos: o PDF
    — a peça com maior densidade de dado pessoal do acervo, porque traz nomes,
    vínculos e às vezes dados de saúde de terceiros — sobrevivia à exclusão do
    projeto que o trouxe. O art. 16 da LGPD exige que a eliminação alcance
    todos os repositórios, e um arquivo esquecido em disco é exatamente o que
    ele proíbe.
    """
    from app.api.v1 import projects as rota_projects

    rota_projects.pdf_service.storage_dir = tmp_path
    caminho = rota_projects.pdf_service.get_pdf_path(
        acervo["projeto"].id, acervo["paper"].id
    )
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(b"%PDF-1.4 conteudo de teste")
    assert caminho.exists()

    cliente = await _cliente(db_session, OWNER_USERNAME)
    resposta = await cliente.delete(f"/api/v1/projects/{acervo['projeto'].id}")
    await cliente.aclose()

    assert resposta.status_code == 204
    assert not caminho.exists(), "o PDF sobreviveu à exclusão do projeto"
