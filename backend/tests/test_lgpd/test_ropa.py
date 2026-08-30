#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — ROPA: registro das operações de tratamento (doc 40 §40.5.2, L-60).

A regra que estes testes existem para defender é uma só, e está no plano em
negrito: **o ROPA registra que houve tratamento, nunca o conteúdo tratado.**

Ela é fácil de enunciar e fácil de violar. Basta alguém achar útil "guardar
qual e-mail foi exportado" para o registro virar mais um lugar de onde o dado
pessoal vaza — e o pior deles, porque o ROPA sobrevive de propósito ao
`DELETE /me`. Seria o único dado que o titular não consegue apagar.

Por isso a defesa não é um teste que procura e-mails no banco depois: é o
vocabulário fechado de `ropa_service`, que não tem por onde receber um valor.
Os testes abaixo conferem as duas coisas — que a porta é estreita, e que ela
continua deixando passar o que precisa passar.
"""

from __future__ import annotations

import json

import pytest

from app.infrastructure.persistence.models import ProcessingRecordModel
from app.services.ropa_service import (
    BASES_LEGAIS,
    CATEGORIAS,
    OPERACOES,
    RegistroInvalido,
    categorias_de,
    registrar,
)

# Valores que jamais podem chegar ao ROPA. Improváveis o bastante para que
# encontrá-los no banco não seja coincidência.
EMAIL = "ptolemaia.krieger@exemplo-improvavel.br"
NOME = "Ptolemaia Vasconcellos-Krieger"
IP = "203.0.113.207"
SENHA = "senha-que-nunca-deveria-aparecer-em-lugar-nenhum"


# ══════════════════════════════════════════════════════════════════════
# A regra dura
# ══════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("valor", [EMAIL, NOME, IP, SENHA])
def test_valor_nao_passa_por_categoria(db_session, valor):
    """
    Um dado pessoal oferecido como categoria é recusado, não gravado.

    É o caminho por onde o vazamento entraria: quem chama pensa em "categoria"
    como rótulo livre e escreve o valor. A lista fechada transforma isso em
    exceção na hora, e não em linha no banco descoberta numa auditoria.
    """
    with pytest.raises(RegistroInvalido) as erro:
        registrar(
            db_session,
            operation="login",
            legal_basis="art7_V_execucao_de_contrato",
            purpose="Autenticar o assinante",
            data_categories=["conexao", valor],
        )
    assert "o ROPA guarda a categoria, nunca o dado" in str(erro.value)


def test_nenhum_dado_pessoal_sobra_no_banco_apos_uso_normal(db_session):
    """
    Varredura do uso legítimo: nada do que identifica alguém pode estar lá.

    Complementa o teste acima por outro ângulo — aquele prova que a porta
    recusa; este prova que o que passa pela porta continua limpo depois de
    gravado, inclusive nas colunas que aceitam texto livre (`purpose`).
    """
    registrar(
        db_session,
        operation="ai_dispatch",
        legal_basis="art7_I_consentimento",
        purpose="Triagem assistida de referências bibliográficas",
        data_categories=["referencia_bibliografica", "conteudo_de_pesquisa"],
        user_id="conta-qualquer",
        recipient="google_gemini",
        international=True,
    )

    linhas = db_session.query(ProcessingRecordModel).all()
    assert linhas

    despejo = " ".join(
        f"{r.user_id} {r.operation} {r.legal_basis} {r.purpose} "
        f"{r.data_categories} {r.recipient}"
        for r in linhas
    )
    for proibido in (EMAIL, NOME, IP, SENHA):
        assert proibido not in despejo


def test_a_tabela_nao_tem_coluna_onde_caberia_conteudo(db_session):
    """
    O modelo não pode ganhar um `details`, `payload` ou `raw` amanhã.

    Uma coluna de texto livre sem vocabulário é o convite: quem precisar
    guardar "só um detalhezinho" vai usá-la. As colunas de texto que existem
    são `purpose` (finalidade declarada, escrita no código) e
    `data_categories` (vocabulário fechado). Qualquer terceira exige decisão
    consciente, e este teste é onde ela aparece.
    """
    colunas = {c.name for c in ProcessingRecordModel.__table__.columns}
    esperadas = {
        "id", "occurred_at", "user_id", "operation",
        "legal_basis", "purpose", "data_categories", "recipient", "international",
    }
    assert colunas == esperadas, (
        "coluna nova no ROPA: confira se ela não abre espaço para o conteúdo tratado"
    )


# ══════════════════════════════════════════════════════════════════════
# O vocabulário
# ══════════════════════════════════════════════════════════════════════

def test_operacao_desconhecida_e_recusada(db_session):
    with pytest.raises(RegistroInvalido, match="Operação desconhecida"):
        registrar(
            db_session,
            operation="fuçar_no_banco",
            legal_basis="art7_IX_legitimo_interesse",
            purpose="qualquer",
            data_categories=["conexao"],
        )


def test_base_legal_desconhecida_e_recusada(db_session):
    """
    Base legal inventada é pior do que base legal ausente: parece fundamento.

    Um `legal_basis="interesse_da_empresa"` gravado sem reclamação viraria,
    numa fiscalização, a afirmação de que o Revsist tratou o dado sob uma base
    que a lei não prevê.
    """
    with pytest.raises(RegistroInvalido, match="Base legal desconhecida"):
        registrar(
            db_session,
            operation="login",
            legal_basis="interesse_da_empresa",
            purpose="qualquer",
            data_categories=["conexao"],
        )


def test_finalidade_em_branco_e_recusada(db_session):
    """O art. 6º I exige propósito determinado; string vazia não é propósito."""
    with pytest.raises(RegistroInvalido, match="Finalidade em branco"):
        registrar(
            db_session,
            operation="login",
            legal_basis="art7_V_execucao_de_contrato",
            purpose="   ",
            data_categories=["conexao"],
        )


def test_lista_de_categorias_vazia_e_recusada(db_session):
    """
    Toda operação trata alguma categoria.

    Lista vazia quase sempre significa que quem chamou copiou a chamada de
    outro lugar e não parou para pensar em qual dado a operação toca — e o
    registro resultante não serviria para prestar contas de nada.
    """
    with pytest.raises(RegistroInvalido, match="lista vazia"):
        registrar(
            db_session,
            operation="login",
            legal_basis="art7_V_execucao_de_contrato",
            purpose="Autenticar",
            data_categories=[],
        )


def test_as_operacoes_do_plano_estao_previstas():
    """§40.5.2 e §43.14 listam operações previstas no ROPA."""
    assert OPERACOES == {
        "signup", "login", "data_export", "data_erasure",
        "ai_dispatch", "pdf_fetch", "consent_given", "consent_revoked",
        "team_invitation_issued", "team_membership_created", "team_membership_revoked",
    }


def test_bases_legais_sao_incisos_do_artigo_7():
    """O nome carrega o inciso para o registro se explicar sozinho na auditoria."""
    for base in BASES_LEGAIS:
        assert base.startswith("art7_"), base


# ══════════════════════════════════════════════════════════════════════
# Gravação
# ══════════════════════════════════════════════════════════════════════

def test_registro_guarda_o_que_prometeu(db_session):
    registro = registrar(
        db_session,
        operation="data_export",
        legal_basis="art7_VI_exercicio_de_direitos",
        purpose="Atender pedido de portabilidade do titular",
        data_categories=["identificacao", "conteudo_de_pesquisa"],
        user_id="conta-1",
    )

    assert registro.id
    assert registro.occurred_at is not None
    assert registro.user_id == "conta-1"
    assert registro.international is False
    assert registro.recipient is None
    assert categorias_de(registro) == ["conteudo_de_pesquisa", "identificacao"]


def test_categorias_sao_gravadas_sem_repeticao_e_em_ordem(db_session):
    """
    Ordem estável e sem repetidas: dois registros da mesma operação têm de ser
    comparáveis byte a byte, ou conferir o ROPA vira leitura de diff ruidoso.
    """
    registro = registrar(
        db_session,
        operation="signup",
        legal_basis="art7_V_execucao_de_contrato",
        purpose="Criar a conta",
        data_categories=["contato", "identificacao", "contato"],
    )
    assert json.loads(registro.data_categories) == ["contato", "identificacao"]


def test_registro_sem_titular_e_permitido(db_session):
    """
    Nem toda operação tem titular identificado.

    Uma tentativa de login que não resolve conta nenhuma trata dado de conexão
    de alguém, e precisa ser registrável mesmo sem se saber de quem.
    """
    registro = registrar(
        db_session,
        operation="login",
        legal_basis="art7_IX_legitimo_interesse",
        purpose="Conter tentativa de acesso por força bruta",
        data_categories=["conexao"],
    )
    assert registro.user_id is None


def test_sem_commit_o_registro_cai_junto_com_a_transacao(db_session):
    """
    `commit=False` é o que o `DELETE /me` usa.

    Se a eliminação falhar no meio, o registro dizendo que ela aconteceu não
    pode ficar de pé — seria uma prova de algo que não ocorreu.
    """
    registrar(
        db_session,
        operation="data_erasure",
        legal_basis="art7_VI_exercicio_de_direitos",
        purpose="Eliminar a conta a pedido do titular",
        data_categories=["identificacao"],
        user_id="conta-2",
        commit=False,
    )
    assert db_session.query(ProcessingRecordModel).count() == 1

    db_session.rollback()
    assert db_session.query(ProcessingRecordModel).count() == 0


def test_categorias_de_tolera_linha_corrompida(db_session):
    """Ler o ROPA não pode quebrar por causa de uma linha ruim."""
    registro = registrar(
        db_session,
        operation="login",
        legal_basis="art7_V_execucao_de_contrato",
        purpose="Autenticar",
        data_categories=["conexao"],
    )
    registro.data_categories = "{isto não é JSON"
    assert categorias_de(registro) == []


def test_todas_as_categorias_do_vocabulario_sao_aceitas(db_session):
    """Uma categoria listada mas recusada seria uma armadilha silenciosa."""
    registro = registrar(
        db_session,
        operation="signup",
        legal_basis="art7_V_execucao_de_contrato",
        purpose="Criar a conta",
        data_categories=sorted(CATEGORIAS),
    )
    assert set(categorias_de(registro)) == CATEGORIAS
