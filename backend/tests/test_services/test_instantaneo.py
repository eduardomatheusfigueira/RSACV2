#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Instantâneo do corpus — o conjunto parado sobre o qual se mede.

O acervo muda todo dia, legitimamente. O que o instantâneo garante não é
imutabilidade: é que toda mudança seja **percebida e dita**, em vez de o mesmo
indicador devolver outro número sem explicação (doc 47 §B-05, doc 48 §3).
"""

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    PaperModel,
    PaperSourceModel,
    ProjectModel,
    ProtocolModel,
)
from app.services.bibliometria import instantaneo as ins
from tests.conftest import OWNER_ID_TESTE


def _projeto(db_session, titulo="Projeto do instantâneo") -> ProjectModel:
    proj = ProjectModel(owner_id=OWNER_ID_TESTE, title=titulo, methodology="PRISMA")
    db_session.add(proj)
    db_session.flush()
    db_session.add(ProtocolModel(project_id=proj.id, objective="Mapear X"))
    db_session.flush()
    return proj


def _papers(db_session, proj, quantos=3, decisao=Decision.INCLUDED.value):
    criados = []
    for i in range(quantos):
        p = PaperModel(
            project_id=proj.id,
            title=f"Estudo {i}",
            authors=f"Autor {i}",
            year=str(2020 + i),
            journal="Revista X",
            abstract=f"Resumo do estudo {i}.",
            decision=decisao,
        )
        db_session.add(p)
        criados.append(p)
    db_session.commit()
    return criados


# ── Identidade do corpus ────────────────────────────────────────────────


def test_hash_e_estavel_entre_execucoes(db_session):
    """A mesma consulta, duas vezes, produz a mesma identidade.

    É a propriedade que sustenta tudo: sem ela, "reproduzir o número" seria
    impossível já na segunda tentativa.
    """
    proj = _projeto(db_session)
    _papers(db_session, proj)

    a = ins.criar(db_session, proj.id)
    b = ins.criar(db_session, proj.id)

    assert a.corpus_hash == b.corpus_hash
    assert a.id != b.id, "São dois instantâneos, ainda que do mesmo corpus."


def test_ordem_de_insercao_nao_afeta_o_hash(db_session):
    """O manifesto é ordenado, então o corpus não depende do plano de consulta."""
    proj = _projeto(db_session)
    papers = _papers(db_session, proj, quantos=4)

    esperado = ins.criar(db_session, proj.id).corpus_hash

    _manifesto, hash_invertido = ins.montar_manifesto(list(reversed(papers)))
    assert hash_invertido == esperado


def test_hash_muda_quando_o_conteudo_muda(db_session):
    proj = _projeto(db_session)
    papers = _papers(db_session, proj)
    antes = ins.criar(db_session, proj.id).corpus_hash

    papers[0].title = "Estudo 0 — título corrigido"
    db_session.commit()

    assert ins.criar(db_session, proj.id).corpus_hash != antes


def test_hash_muda_quando_o_conjunto_muda(db_session):
    proj = _projeto(db_session)
    _papers(db_session, proj)
    antes = ins.criar(db_session, proj.id).corpus_hash

    _papers(db_session, proj, quantos=1)

    assert ins.criar(db_session, proj.id).corpus_hash != antes


def test_separador_impede_colisao_entre_campos(db_session):
    """Sem separador, "ab"+"c" e "a"+"bc" seriam o mesmo corpus.

    Dois documentos diferentes com a mesma identidade fariam o instantâneo
    mentir exatamente onde ele existe para não mentir.
    """
    proj = _projeto(db_session)
    a = PaperModel(
        project_id=proj.id, title="ab", authors="c", decision=Decision.INCLUDED.value
    )
    db_session.add(a)
    db_session.commit()
    hash_a = ins.criar(db_session, proj.id).corpus_hash

    a.title, a.authors = "a", "bc"
    db_session.commit()

    assert ins.criar(db_session, proj.id).corpus_hash != hash_a


# ── Escopo ──────────────────────────────────────────────────────────────


def test_escopo_recorta_o_corpus(db_session):
    proj = _projeto(db_session)
    _papers(db_session, proj, quantos=3, decisao=Decision.INCLUDED.value)
    _papers(db_session, proj, quantos=2, decisao=Decision.EXCLUDED.value)

    incluidos = ins.criar(
        db_session, proj.id, escopo=ins.Escopo(decision=Decision.INCLUDED.value)
    )
    todos = ins.criar(db_session, proj.id, escopo=ins.Escopo(decision=None))

    assert incluidos.n_documents == 3
    assert todos.n_documents == 5
    assert incluidos.corpus_hash != todos.corpus_hash


def test_duplicata_fica_de_fora(db_session):
    """Mesmo critério da fila de triagem e do contador do projeto."""
    proj = _projeto(db_session)
    _papers(db_session, proj, quantos=2)
    db_session.add(
        PaperModel(
            project_id=proj.id,
            title="Duplicata",
            decision=Decision.INCLUDED.value,
            is_duplicate=True,
        )
    )
    db_session.commit()

    assert ins.criar(db_session, proj.id).n_documents == 2


def test_escopo_sobrevive_a_ida_e_volta_do_json():
    escopo = ins.Escopo(decision="Incluído", source="SciELO", year_from=2015, year_to=2024)
    assert ins.Escopo.de_json(escopo.como_json()) == escopo


def test_escopo_por_base_de_coleta(db_session):
    proj = _projeto(db_session)
    papers = _papers(db_session, proj, quantos=3)
    db_session.add_all(
        [
            PaperSourceModel(paper_id=papers[0].id, source_name="SciELO"),
            PaperSourceModel(paper_id=papers[1].id, source_name="BDTD"),
            PaperSourceModel(paper_id=papers[2].id, source_name="SciELO"),
        ]
    )
    db_session.commit()

    inst = ins.criar(db_session, proj.id, escopo=ins.Escopo(source="SciELO"))
    assert inst.n_documents == 2


# ── Conferência: o que mudou desde o congelamento ───────────────────────


def test_corpus_intocado_confere_identico(db_session):
    proj = _projeto(db_session)
    _papers(db_session, proj)

    conf = ins.conferir(db_session, ins.criar(db_session, proj.id))

    assert conf.estado == "identico"
    assert conf.confiavel is True


def test_metadado_editado_e_apontado_por_documento(db_session):
    """Não basta dizer que mudou: é preciso dizer o quê.

    Metadado corrigido em três documentos costuma ser inofensivo para um
    ranking de periódicos e fatal para uma contagem de termos — quem decide é
    a pessoa, e ela precisa da lista.
    """
    proj = _projeto(db_session)
    papers = _papers(db_session, proj)
    inst = ins.criar(db_session, proj.id)

    papers[1].abstract = "Resumo reescrito depois do congelamento."
    db_session.commit()

    conf = ins.conferir(db_session, inst)

    assert conf.estado == "conteudo_alterado"
    assert conf.documentos_alterados == (papers[1].id,)
    assert conf.confiavel is False


def test_documento_novo_no_escopo_e_conjunto_alterado(db_session):
    proj = _projeto(db_session)
    _papers(db_session, proj)
    inst = ins.criar(db_session, proj.id)

    novos = _papers(db_session, proj, quantos=1)

    conf = ins.conferir(db_session, inst)

    assert conf.estado == "conjunto_alterado"
    assert conf.documentos_adicionados == (novos[0].id,)
    assert conf.documentos_removidos == ()


def test_documento_que_sai_do_escopo_e_conjunto_alterado(db_session):
    """Triar um estudo o tira do escopo "Incluído" — e isso muda o denominador."""
    proj = _projeto(db_session)
    papers = _papers(db_session, proj)
    inst = ins.criar(db_session, proj.id)

    papers[0].decision = Decision.EXCLUDED.value
    db_session.commit()

    conf = ins.conferir(db_session, inst)

    assert conf.estado == "conjunto_alterado"
    assert conf.documentos_removidos == (papers[0].id,)


def test_conjunto_alterado_tem_precedencia_sobre_conteudo(db_session):
    """Documento que entra ou sai é a notícia maior, e é a que se dá primeiro."""
    proj = _projeto(db_session)
    papers = _papers(db_session, proj)
    inst = ins.criar(db_session, proj.id)

    papers[0].title = "Outro título"
    _papers(db_session, proj, quantos=1)

    assert ins.conferir(db_session, inst).estado == "conjunto_alterado"


# ── Manifesto e proveniência ────────────────────────────────────────────


def test_manifesto_guarda_um_par_por_documento(db_session):
    proj = _projeto(db_session)
    papers = _papers(db_session, proj, quantos=5)
    inst = ins.criar(db_session, proj.id)

    lido = ins.ler_manifesto(inst.manifest)

    assert set(lido) == {p.id for p in papers}
    assert all(len(h) == 64 for h in lido.values())


def test_manifesto_comprime(db_session):
    """Quatro megabytes de manifesto no acervo real justificam a compressão."""
    proj = _projeto(db_session)
    _papers(db_session, proj, quantos=60)
    inst = ins.criar(db_session, proj.id)

    pares = ins.ler_manifesto(inst.manifest)
    cru = len("\n".join(k + ins.SEPARADOR + v for k, v in pares.items()))
    assert len(inst.manifest) < cru


def test_manifesto_nao_carrega_a_hora_da_compressao(db_session):
    """gzip grava um carimbo de tempo por padrão, e ele quebraria a igualdade
    byte a byte de dois manifestos do mesmo corpus."""
    proj = _projeto(db_session)
    _papers(db_session, proj)
    papers = db_session.query(PaperModel).order_by(PaperModel.id).all()

    primeiro, _ = ins.montar_manifesto(papers)
    segundo, _ = ins.montar_manifesto(papers)

    assert primeiro == segundo


def test_proveniencia_traz_o_que_a_figura_precisa_declarar(db_session):
    proj = _projeto(db_session)
    _papers(db_session, proj)
    inst = ins.criar(db_session, proj.id, rotulo="Análise principal")

    prov = ins.proveniencia(inst)

    assert prov["snapshot_id"] == inst.id
    assert prov["corpus_hash"] == inst.corpus_hash
    assert prov["n_documents"] == 3
    assert prov["engine_version"] == ins.VERSAO_DO_MOTOR
    assert prov["frozen_at"], "Sem data de congelamento não há o que declarar."
    assert prov["scope"]["decision"] == Decision.INCLUDED.value


def test_projeto_vazio_gera_instantaneo_valido(db_session):
    """Corpus vazio é um corpus, e tem identidade — não é um erro."""
    proj = _projeto(db_session)

    inst = ins.criar(db_session, proj.id)

    assert inst.n_documents == 0
    assert len(inst.corpus_hash) == 64
    assert ins.conferir(db_session, inst).estado == "identico"
