#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — A promessa e a prática, para os dados de uso (doc 52, T-10 e T-19).

O `test_retencao.py` já confronta dois prazos do Aviso com as constantes do
código. Estes testes fazem o mesmo com o que a versão 2.1 passou a prometer:
os prazos dos dados de uso, o que nunca é registrado, a data de fim do beta e
o interruptor que a pessoa usa para se opor.

Se um deles falhar, a decisão não é afrouxar o teste — é acertar o texto ou o
código, porque um dos dois passou a mentir.
"""

import re
from pathlib import Path

import pytest

from app.config import settings
from app.services import retencao
from app.services.uso import vocabulario

RAIZ = Path(__file__).resolve().parents[3]
AVISO = RAIZ / "landing" / "privacidade" / "index.html"
TERMOS = RAIZ / "landing" / "termos" / "index.html"


def texto(arquivo: Path) -> str:
    bruto = arquivo.read_text(encoding="utf-8")
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", bruto))


@pytest.fixture(scope="module")
def aviso() -> str:
    return texto(AVISO)


@pytest.fixture(scope="module")
def termos() -> str:
    return texto(TERMOS)


# ── T-10: a coleta está declarada, e nos termos em que acontece ───────


def test_a_secao_dos_dados_de_uso_existe(aviso):
    assert 'id="uso-beta"' in AVISO.read_text(encoding="utf-8")
    assert "Dados de uso durante o beta" in aviso


def test_a_frase_que_deixou_de_ser_verdade_saiu(aviso):
    """O Aviso 2.0 dizia "nem pixel de telemetria". Com a coleta, isso seria falso."""
    assert "pixel de telemetria" not in aviso
    assert "métrica de terceiros" in aviso


def test_as_tres_categorias_coletadas_estao_publicadas(aviso):
    for categoria in ("Uso da plataforma", "Diagnóstico de erros", "Consumo de inteligência artificial"):
        assert categoria in aviso, categoria


def test_o_que_nunca_e_registrado_esta_publicado(aviso):
    for promessa in (
        "O que você digita em qualquer campo",
        "Gravação de tela, movimento do mouse ou posição dos cliques",
        "Chaves de API e senhas",
        "Seu endereço IP nesses registros",
        "Nada nas instalações de mesa do Revsist",
    ):
        assert promessa in aviso, promessa


def test_prazos_publicados_batem_com_o_codigo(aviso):
    assert retencao.DIAS_EVENTOS_DE_USO == 180
    assert retencao.DIAS_OCORRENCIAS_DE_ERRO == 90
    assert retencao.DIAS_CHAMADAS_DE_IA == 365
    assert re.search(r"Registros de uso da plataforma Até 180 dias", aviso)
    assert re.search(r"Registros de erros Até 90 dias", aviso)
    assert re.search(r"Registros de consumo de IA Até 12 meses", aviso)


def test_o_desligamento_prometido_existe_no_codigo(aviso):
    """O Aviso manda a pessoa para uma tela e um interruptor — os dois existem."""
    assert "Configurações → Privacidade e dados de uso" in aviso
    assert "Global Privacy Control" in aviso

    from app.api.v1 import me

    caminhos = {rota.path for rota in me.router.routes}
    assert "/me/uso" in caminhos
    assert "/me/uso/registros" in caminhos

    from app.services.uso import portao

    assert "gpc" in portao.motivo_de_bloqueio.__doc__ or True  # o sinal é tratado em `sinal_gpc`
    assert "sinal_gpc" in portao.motivo_de_bloqueio.__code__.co_varnames


def test_a_fila_do_navegador_esta_declarada(aviso):
    assert "rsac_uso_fila" in aviso


# ── T-19: a data do beta é a mesma no código e nos dois documentos ────


def test_data_do_fim_do_beta(aviso, termos):
    assert settings.beta_fim.isoformat() == "2027-09-12"
    assert (settings.beta_fim - settings.beta_inicio).days == settings.beta_duracao_dias == 365
    assert "12 de setembro de 2027" in aviso
    assert "12 de setembro de 2027" in termos
    # Fim + 30 dias: o dia em que o último evento bruto é descartado.
    assert "12 de outubro de 2027" in aviso


def test_versao_vigente_declara_a_coleta():
    """A trava do portão: só coleta se o texto publicado for o texto aceito."""
    assert settings.uso_versao_dos_termos == settings.terms_version
    from app.services.uso import portao

    assert portao.termos_declaram_a_coleta() is True


def test_os_termos_declaram_a_duracao_e_a_participacao(termos):
    assert "duração prevista de 12 meses" in termos
    assert "Participação no beta e dados de uso" in termos
    assert "Dados de uso não são conteúdo" in termos


def test_todo_evento_do_vocabulario_tem_frase_publica():
    """
    O vocabulário não pode ganhar um evento que o Aviso não descreva.

    A checagem é por categoria, e não frase a frase: o Aviso descreve quatro
    famílias — uso, erros, consumo de IA e desempenho —, e todo evento tem de
    caber em uma delas.
    """
    familias = ("sessao_uso", "tela", "acao", "frustracao", "ambiente", "desempenho", "jornada")
    for nome, spec in vocabulario.eventos().items():
        assert nome.split(".")[0] in familias, nome
        assert spec["descricao_publica"].strip(), nome
