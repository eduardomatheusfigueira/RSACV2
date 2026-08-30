"""Testes de Cegueira no Servidor e Isolamento de Julgamentos (Doc 43 §43.7.2).

P3 · A cegueira é do servidor.
Se o dado sai na resposta HTTP/WebSocket, a cegueira não existe.
Este teste verifica que nenhum dado de triagem do Revisor A vaza para o
Revisor B antes da consolidação por consenso ou resolução arbitral.
"""

import pytest
import httpx

from app.api.deps import get_db
from app.infrastructure.persistence.models import (
    CriterionModel,
    PaperModel,
    ProjectMemberModel,
    ProjectModel,
    ProtocolModel,
    UserModel,
    utcnow,
)
from app.main import create_app
from app.security.passwords import hash_password
from tests.conftest import SENHA_TESTE


@pytest.fixture
def cenario_cegueira(db_session):
    """Cria um projeto em modo duplo-cego com Coordenador, Revisor A e Revisor B."""
    # 1. Usuários
    u_coord = UserModel(
        username="coordenador_ceg",
        password_hash=hash_password(SENHA_TESTE),
        role="researcher",
        is_active=True,
    )
    u_rev_a = UserModel(
        username="revisor_a_ceg",
        password_hash=hash_password(SENHA_TESTE),
        role="researcher",
        is_active=True,
    )
    u_rev_b = UserModel(
        username="revisor_b_ceg",
        password_hash=hash_password(SENHA_TESTE),
        role="researcher",
        is_active=True,
    )
    db_session.add_all([u_coord, u_rev_a, u_rev_b])
    db_session.flush()

    # 2. Projeto Duplo-Cego
    proj = ProjectModel(
        title="Desenvolvimento Territorial no Semiárido",
        owner_id=u_coord.id,
        collaboration_mode="cega_por_pares",
        reviewers_per_paper=2,
        conflict_resolution="coordenador",
    )
    db_session.add(proj)
    db_session.flush()

    # 3. Participações dos Revisores (o coordenador já foi adicionado pelo construtor do projeto)
    m_a = ProjectMemberModel(project_id=proj.id, user_id=u_rev_a.id, project_role="revisor")
    m_b = ProjectMemberModel(project_id=proj.id, user_id=u_rev_b.id, project_role="revisor")
    db_session.add_all([m_a, m_b])

    # 4. Protocolo e Critério
    proto = ProtocolModel(project_id=proj.id, objective="Revisão sobre Governança Regional")
    db_session.add(proto)
    db_session.flush()

    crit1 = CriterionModel(protocol_id=proto.id, text="Critério 1 - Políticas Públicas Locais", is_exclusion=False)
    db_session.add(crit1)
    db_session.flush()

    # 5. Artigo para triagem
    paper = PaperModel(
        project_id=proj.id,
        title="Estudo Territorial sobre Arranjos Produtivos Locais",
        abstract="Resumo científico de desenvolvimento regional e dinâmicas territoriais.",
        decision="Pendente",
        screening_status="aguardando",
        updated_at=utcnow(),
    )
    db_session.add(paper)
    db_session.commit()

    return {
        "project": proj,
        "paper": paper,
        "criterion": crit1,
        "coord": u_coord,
        "rev_a": u_rev_a,
        "rev_b": u_rev_b,
    }


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


@pytest.mark.anyio
async def test_revisor_b_nao_recebe_julgamento_de_a_antes_do_consenso(cenario_cegueira, db_session):
    """Garante que a resposta HTTP para o Revisor B oculta completamente a decisão de A."""
    proj = cenario_cegueira["project"]
    paper = cenario_cegueira["paper"]
    crit = cenario_cegueira["criterion"]

    c_a = await _cliente(db_session, "revisor_a_ceg")
    c_b = await _cliente(db_session, "revisor_b_ceg")

    texto_secreto_a = "Observacao Confidencial do Revisor A sobre o estudo"

    # Revisor A julga o estudo
    res_a = await c_a.patch(
        f"/api/v1/projects/{proj.id}/papers/{paper.id}",
        json={
            "decision": "Incluído",
            "observations": texto_secreto_a,
            "criteria_evaluations": {crit.id: True},
        },
    )
    assert res_a.status_code == 200, res_a.text
    data_a = res_a.json()
    assert data_a["my_screening"]["decision"] == "Incluído"
    assert data_a["screening_status"] == "parcial"

    # Revisor B obtém os detalhes do artigo
    res_b = await c_b.get(f"/api/v1/projects/{proj.id}/papers/{paper.id}")
    assert res_b.status_code == 200, res_b.text
    data_b = res_b.json()

    # O Revisor B DEVE receber o estudo como Pendente e sem vestígios de A
    assert data_b["decision"] == "Pendente"
    assert data_b["screening_status"] == "parcial"
    assert data_b["reviewers_completed_count"] == 1
    assert data_b["reviewers_required_count"] == 2
    assert texto_secreto_a not in res_b.text
    assert crit.id not in data_b["criteria_evaluations"]

    # Revisor B lista artigos do projeto
    res_b_list = await c_b.get(f"/api/v1/projects/{proj.id}/papers")
    assert res_b_list.status_code == 200
    assert texto_secreto_a not in res_b_list.text

    await c_a.aclose()
    await c_b.aclose()


@pytest.mark.anyio
async def test_consenso_duplo_cego_desbloqueia_dados_para_equipe(cenario_cegueira, db_session):
    """Quando ambos concordam, a consolidação gera 'consenso' e unifica a decisão."""
    proj = cenario_cegueira["project"]
    paper = cenario_cegueira["paper"]
    crit = cenario_cegueira["criterion"]

    c_a = await _cliente(db_session, "revisor_a_ceg")
    c_b = await _cliente(db_session, "revisor_b_ceg")

    # Revisor A inclui
    await c_a.patch(
        f"/api/v1/projects/{proj.id}/papers/{paper.id}",
        json={"decision": "Incluído", "observations": "Nota de A", "criteria_evaluations": {crit.id: True}},
    )

    # Revisor B também inclui
    res_b = await c_b.patch(
        f"/api/v1/projects/{proj.id}/papers/{paper.id}",
        json={"decision": "Incluído", "observations": "Nota de B", "criteria_evaluations": {crit.id: True}},
    )
    assert res_b.status_code == 200
    data_b = res_b.json()

    # Consenso atingido!
    assert data_b["decision"] == "Incluído"
    assert data_b["screening_status"] == "consenso"
    assert data_b["reviewers_completed_count"] == 2

    await c_a.aclose()
    await c_b.aclose()


@pytest.mark.anyio
async def test_divergencia_gera_conflito_e_coordenador_desempata(cenario_cegueira, db_session):
    """Divergência entre revisores move para conflito e apenas o coordenador pode resolver."""
    proj = cenario_cegueira["project"]
    paper = cenario_cegueira["paper"]
    crit = cenario_cegueira["criterion"]

    c_a = await _cliente(db_session, "revisor_a_ceg")
    c_b = await _cliente(db_session, "revisor_b_ceg")
    c_coord = await _cliente(db_session, "coordenador_ceg")

    # A inclui, B exclui
    await c_a.patch(
        f"/api/v1/projects/{proj.id}/papers/{paper.id}",
        json={"decision": "Incluído", "observations": "Parecer Positivo de A"},
    )
    res_b = await c_b.patch(
        f"/api/v1/projects/{proj.id}/papers/{paper.id}",
        json={"decision": "Excluído", "observations": "Parecer Negativo de B"},
    )
    assert res_b.json()["screening_status"] == "conflito"
    assert res_b.json()["decision"] == "Pendente"

    # Revisor B tenta acessar a lista de conflitos -> 403 Forbidden (apenas coordenador)
    res_conflito_b = await c_b.get(f"/api/v1/projects/{proj.id}/screening/conflitos")
    assert res_conflito_b.status_code == 403

    # Coordenador acessa a lista de conflitos -> 200 OK e vê ambos os julgamentos
    res_conflito_coord = await c_coord.get(f"/api/v1/projects/{proj.id}/screening/conflitos")
    assert res_conflito_coord.status_code == 200
    conflitos = res_conflito_coord.json()
    assert len(conflitos) == 1
    assert len(conflitos[0]["screenings"]) == 2
    assert "Parecer Positivo de A" in res_conflito_coord.text
    assert "Parecer Negativo de B" in res_conflito_coord.text

    # Coordenador desempata decidindo pela Inclusão
    res_resolve = await c_coord.post(
        f"/api/v1/projects/{proj.id}/screening/conflitos/{paper.id}/resolver",
        json={
            "decision": "Incluído",
            "observations": "Decisão arbitral da coordenação: estudo atende aos requisitos metodológicos.",
            "criteria_evaluations": {crit.id: True},
        },
    )
    assert res_resolve.status_code == 200
    resolvido = res_resolve.json()
    assert resolvido["decision"] == "Incluído"
    assert resolvido["screening_status"] == "resolvido"
    assert resolvido["conflict_resolved_by_username"] == "coordenador_ceg"

    # Agora o Revisor B lê o artigo e vê o resultado final resolvido
    res_b_final = await c_b.get(f"/api/v1/projects/{proj.id}/papers/{paper.id}")
    assert res_b_final.json()["decision"] == "Incluído"
    assert res_b_final.json()["screening_status"] == "resolvido"

    await c_a.aclose()
    await c_b.aclose()
    await c_coord.aclose()
