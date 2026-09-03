#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""As rotas de vanguarda respondem — todas as cinco.

Três delas devolviam **500** em produção por consultarem
`BibThesaurusEntryModel.status`, coluna que nunca existiu no modelo: o critério
de aprovação é ter aprovador (`approved_by`), como o serviço de tesauro já
fazia. Bastava abrir a aba "Vanguarda & Sensibilidade" para ver
"Failed to fetch" — o navegador reporta o erro como CORS, porque a resposta de
500 não carrega os cabeçalhos, o que escondia a causa.

A lacuna era de cobertura: havia testes das funções, e nenhum que exercitasse
as rotas de ponta a ponta.
"""

import pytest

from app.domain.enums import Decision
from app.infrastructure.persistence.models import PaperModel, ProjectModel, ProtocolModel
from tests.conftest import OWNER_ID_TESTE

#: As cinco rotas da aba, com os parâmetros que a interface manda.
ROTAS_DE_VANGUARDA = [
    ("vanguarda/diagrama-estrategico", {}),
    ("vanguarda/rajadas", {"s": 2.0}),
    ("vanguarda/bootstrap-rankings", {"tipo_ranking": "periodicos", "n_boot": 50}),
    ("vanguarda/sensibilidade", {}),
    ("vanguarda/cobertura-campo", {}),
]


def _projeto_com_corpus(db_session, titulo="Projeto de vanguarda") -> str:
    proj = ProjectModel(owner_id=OWNER_ID_TESTE, title=titulo, methodology="PRISMA")
    db_session.add(proj)
    db_session.flush()
    db_session.add(ProtocolModel(project_id=proj.id, objective="Mapear X"))
    for i in range(12):
        db_session.add(
            PaperModel(
                project_id=proj.id,
                title=f"Mobilidade turística e governança territorial {i}",
                authors=f"Autor {i}; Coautor {i % 3}",
                year=str(2016 + (i % 8)),
                journal=f"Revista {i % 4}",
                abstract=(
                    "Resumo sobre mobilidade turística, governança territorial e "
                    f"políticas públicas de desenvolvimento regional, caso {i}."
                ),
                decision=Decision.INCLUDED.value,
            )
        )
    db_session.commit()
    return proj.id


@pytest.mark.anyio
@pytest.mark.parametrize("rota,params", ROTAS_DE_VANGUARDA)
async def test_rota_responde_sobre_corpus_real(async_client, db_session, rota, params):
    pid = _projeto_com_corpus(db_session)

    res = await async_client.get(
        f"/api/v1/projects/{pid}/bibliometria/{rota}", params=params
    )

    assert res.status_code == 200, f"{rota}: {res.status_code} {res.text[:200]}"


@pytest.mark.anyio
@pytest.mark.parametrize("rota,params", ROTAS_DE_VANGUARDA)
async def test_rota_responde_sobre_projeto_vazio(async_client, db_session, rota, params):
    """Projeto sem estudos não é erro — a aba abre antes de haver corpus."""
    proj = ProjectModel(owner_id=OWNER_ID_TESTE, title="Vazio", methodology="PRISMA")
    db_session.add(proj)
    db_session.flush()
    db_session.add(ProtocolModel(project_id=proj.id, objective="Mapear X"))
    db_session.commit()

    res = await async_client.get(
        f"/api/v1/projects/{proj.id}/bibliometria/{rota}", params=params
    )

    assert res.status_code == 200, f"{rota}: {res.status_code} {res.text[:200]}"


@pytest.mark.anyio
async def test_toda_resposta_de_vanguarda_declara_proveniencia(async_client, db_session):
    """Todo número da aba carrega sobre que corpus foi calculado (doc 48 §14.4)."""
    pid = _projeto_com_corpus(db_session, "Com proveniência")

    for rota, params in ROTAS_DE_VANGUARDA:
        corpo = (
            await async_client.get(
                f"/api/v1/projects/{pid}/bibliometria/{rota}", params=params
            )
        ).json()
        assert "provenance" in corpo, f"{rota} não declara proveniência."


@pytest.mark.anyio
async def test_tipo_de_ranking_invalido_e_recusado_com_400(async_client, db_session):
    """Recusa explicada, e não 500."""
    pid = _projeto_com_corpus(db_session, "Ranking inválido")

    res = await async_client.get(
        f"/api/v1/projects/{pid}/bibliometria/vanguarda/bootstrap-rankings",
        params={"tipo_ranking": "inexistente"},
    )

    assert res.status_code == 400
