#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Estatística Sob Demanda e Compilador Parametrizado (doc 48 §9, §12, doc 49 Fase 7).

Regra fundamental de segurança e auditoria (doc 48 §9.2, doc 29):
    Nenhum texto vindo de modelo de linguagem chega ao banco de dados.
    A pergunta é traduzida em especificação JSON com vocabulário fechado,
    validada por Pydantic, e compilada em consultas SQLAlchemy parametrizadas.
"""

from __future__ import annotations

import json
import logging
import re
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    BibAnaliseModel,
    BibAuthorshipModel,
    BibKeywordModel,
    BibSnapshotModel,
    BibTextoModel,
    BibWorkMetaModel,
    PaperModel,
    PaperSourceModel,
    ProjectModel,
)
from app.schemas.bibliometria import (
    VOCABULARIO_AGRUPADORES,
    VOCABULARIO_CAMPOS_NUMERICOS,
    VOCABULARIO_MEDIDAS,
    VOCABULARIO_OPERADORES,
    EspecificacaoEstatistica,
    FiltroEspecificacao,
)

logger = logging.getLogger(__name__)


def interpretar_pergunta(pergunta: str) -> dict[str, Any]:
    """Traduz pergunta em linguagem natural para especificação formal com vocabulário fechado.

    Recusa honestamente perguntas que fujam do vocabulário ou contenham sintaxe não autorizada.
    """
    if not pergunta or not pergunta.strip():
        return {
            "supported": False,
            "question": "",
            "specification": None,
            "explanation": "Pergunta vazia informada.",
            "supported_vocabulary": {
                "medidas": VOCABULARIO_MEDIDAS,
                "campos": VOCABULARIO_CAMPOS_NUMERICOS,
                "agrupadores": VOCABULARIO_AGRUPADORES,
            },
        }

    p_limpa = pergunta.strip().lower()

    # 1. Barreira de segurança (doc 29, doc 48 §9.2): Bloqueia injeções e SQL cru
    termos_suspeitos = ["drop ", "delete ", "update ", "insert ", "truncate ", "--", ";", "/*", "*/", "exec "]
    if any(t in p_limpa for t in termos_suspeitos):
        return {
            "supported": False,
            "question": pergunta,
            "specification": None,
            "explanation": "A pergunta contém comandos ou caracteres de injeção que não pertencem ao vocabulário estatístico fechado.",
            "supported_vocabulary": {
                "medidas": VOCABULARIO_MEDIDAS,
                "campos": VOCABULARIO_CAMPOS_NUMERICOS,
                "agrupadores": VOCABULARIO_AGRUPADORES,
            },
        }

    # 2. Identificação da medida
    medida = "contagem"
    campo: Optional[str] = None
    por: list[str] = []
    onde: list[dict[str, Any]] = []
    ordenar_por = "grupo"
    limite = 50

    if "mediana" in p_limpa:
        medida = "mediana"
    elif "média" in p_limpa or "media" in p_limpa:
        medida = "media"
    elif "desvio padrão" in p_limpa or "desvio padrao" in p_limpa:
        medida = "desvio_padrao"
    elif "soma" in p_limpa or "total de citações" in p_limpa or "total de citacoes" in p_limpa:
        medida = "soma"
    elif "quantil" in p_limpa or "percentil" in p_limpa:
        medida = "quantil"
    elif "taxa" in p_limpa or "porcentagem" in p_limpa or "proporção" in p_limpa or "proporcao" in p_limpa:
        medida = "taxa"
    elif "distintos" in p_limpa or "únicos" in p_limpa or "unicos" in p_limpa:
        medida = "distintos"
    else:
        medida = "contagem"

    # 3. Identificação do campo numérico
    if "citaç" in p_limpa or "citac" in p_limpa or "citations" in p_limpa:
        campo = "citacoes_recebidas"
    elif "palavra" in p_limpa or "words" in p_limpa:
        campo = "n_palavras"
    elif "página" in p_limpa or "pagina" in p_limpa or "pages" in p_limpa:
        campo = "n_paginas"
    elif "ano" in p_limpa and medida in ["media", "mediana", "quantil", "desvio_padrao"]:
        campo = "ano"
    elif "acesso aberto" in p_limpa or "open access" in p_limpa:
        campo = "acesso_aberto"

    # 4. Identificação dos agrupadores ('por')
    if "por ano" in p_limpa or "em cada ano" in p_limpa or "ao longo dos anos" in p_limpa or "produção temporal" in p_limpa:
        por.append("ano")
    if "por periódico" in p_limpa or "por periodico" in p_limpa or "por revista" in p_limpa or "por journal" in p_limpa or "top periódicos" in p_limpa or "top periodicos" in p_limpa:
        por.append("periodico")
        ordenar_por = "valor_desc"
        limite = 20
    if "por autor" in p_limpa or "por autores" in p_limpa or "top autores" in p_limpa:
        por.append("autor")
        ordenar_por = "valor_desc"
        limite = 20
    if "por decisão" in p_limpa or "por decisao" in p_limpa or "por status" in p_limpa:
        por.append("decisao")
    if "por fonte" in p_limpa or "por base" in p_limpa or "por harvester" in p_limpa:
        por.append("fonte")
    if "por instituição" in p_limpa or "por instituicao" in p_limpa or "por universidade" in p_limpa:
        por.append("instituicao")
        ordenar_por = "valor_desc"
        limite = 20
    if "por país" in p_limpa or "por pais" in p_limpa:
        por.append("pais")
        ordenar_por = "valor_desc"
        limite = 20
    if "por idioma" in p_limpa or "por língua" in p_limpa:
        por.append("idioma")
        ordenar_por = "valor_desc"

    # 5. Identificação de filtros ('onde')
    if "só dos incluídos" in p_limpa or "apenas incluídos" in p_limpa or "somente incluídos" in p_limpa or "artigos incluídos" in p_limpa:
        onde.append({"campo": "decisao", "op": "=", "valor": Decision.INCLUDED.value})
    elif "excluídos" in p_limpa or "excluidos" in p_limpa:
        onde.append({"campo": "decisao", "op": "=", "valor": Decision.EXCLUDED.value})

    # Extração de filtro de ano se houver ("após 2015", "entre 2010 e 2020", "desde 2018")
    m_ano_gt = re.search(r"(após|apos|depois de|desde|a partir de)\s+(\d{4})", p_limpa)
    if m_ano_gt:
        onde.append({"campo": "ano", "op": ">=", "valor": m_ano_gt.group(2)})

    m_ano_entre = re.search(r"entre\s+(\d{4})\s+e\s+(\d{4})", p_limpa)
    if m_ano_entre:
        onde.append({"campo": "ano", "op": "entre", "valor": [m_ano_entre.group(1), m_ano_entre.group(2)]})

    # Se não identificou agrupador nem medida válida com contexto, recusa honestamente
    if not por and not campo and medida == "contagem":
        return {
            "supported": False,
            "question": pergunta,
            "specification": None,
            "explanation": "Não foi possível identificar uma combinação suportada de medida e agrupador na pergunta.",
            "supported_vocabulary": {
                "medidas": VOCABULARIO_MEDIDAS,
                "campos": VOCABULARIO_CAMPOS_NUMERICOS,
                "agrupadores": VOCABULARIO_AGRUPADORES,
                "exemplos": [
                    "qual a mediana de citações por ano, só dos incluídos?",
                    "quantos artigos por periódico?",
                    "qual a média de citações por instituição?",
                    "produção temporal por ano",
                    "distribuição de artigos por decisão",
                ],
            },
        }

    spec = {
        "medida": medida,
        "campo": campo,
        "por": por if por else ["ano"],
        "onde": onde,
        "ordenar_por": ordenar_por,
        "limite": limite,
        "quantil_p": 0.5,
    }

    return {
        "supported": True,
        "question": pergunta,
        "specification": spec,
        "explanation": f"Pergunta traduzida com sucesso: medida '{medida}' sobre campo '{campo or 'documentos'}' agrupado por {por or ['ano']}.",
        "supported_vocabulary": None,
    }


class ServicoDeAnalises:
    """Compilador de especificações estatísticas e executor determinístico."""

    def compilar_e_executar(
        self,
        db: Session,
        project_id: str,
        spec: EspecificacaoEstatistica,
        snapshot_id: Optional[str] = None,
    ) -> tuple[list[dict[str, Any]], int, dict[str, Any]]:
        """Executa a especificação formalmente validada sobre o banco de dados."""
        # 1. Validar campos contra vocabulário fechado
        if spec.medida not in VOCABULARIO_MEDIDAS:
            raise ValueError(f"Medida '{spec.medida}' inválida. Vocabulário permitido: {VOCABULARIO_MEDIDAS}")

        for agrupador in spec.por:
            if agrupador not in VOCABULARIO_AGRUPADORES:
                raise ValueError(f"Agrupador '{agrupador}' inválido. Vocabulário permitido: {VOCABULARIO_AGRUPADORES}")

        for filtro in spec.onde:
            if filtro.op not in VOCABULARIO_OPERADORES:
                raise ValueError(f"Operador '{filtro.op}' inválido. Vocabulário permitido: {VOCABULARIO_OPERADORES}")

        # 2. Obter escopo de estudos
        if snapshot_id or spec.snapshot_id:
            sid = snapshot_id or spec.snapshot_id
            snap = db.query(BibSnapshotModel).filter(BibSnapshotModel.id == sid).first()
            if not snap:
                raise ValueError(f"Instantâneo '{sid}' não encontrado.")
            escopo = json.loads(snap.scope) if snap.scope else {}
            q = db.query(PaperModel).filter(PaperModel.project_id == project_id)
            if escopo.get("decisions"):
                q = q.filter(PaperModel.decision.in_(escopo["decisions"]))
            papers = q.all()
        else:
            papers = db.query(PaperModel).filter(PaperModel.project_id == project_id).all()

        if not papers:
            return [], 0, {"n_total": 0, "medida": spec.medida}

        paper_ids = [p.id for p in papers]

        # 3. Carregar tabelas auxiliares para enriquecimento e agrupamento
        enrichments = {
            e.paper_id: e
            for e in db.query(BibWorkMetaModel).filter(BibWorkMetaModel.paper_id.in_(paper_ids)).all()
        }
        sources = {
            s.paper_id: s.source
            for s in db.query(PaperSourceModel).filter(PaperSourceModel.paper_id.in_(paper_ids)).all()
        }
        authorships = defaultdict(list)
        for a in db.query(BibAuthorshipModel).filter(BibAuthorshipModel.paper_id.in_(paper_ids)).all():
            authorships[a.paper_id].append(a)
        textos = {
            t.paper_id: t
            for t in db.query(BibTextoModel).filter(BibTextoModel.paper_id.in_(paper_ids)).all()
        }

        # 4. Filtrar estudos conforme 'onde'
        papers_filtrados: list[PaperModel] = []
        for p in papers:
            passou = True
            for filtro in spec.onde:
                f_campo = filtro.campo
                f_op = filtro.op
                f_val = filtro.valor

                # Obter valor real do campo no documento
                val_real: Any = None
                if f_campo == "decisao":
                    val_real = p.decision
                elif f_campo == "ano":
                    val_real = p.year
                elif f_campo == "fonte":
                    val_real = sources.get(p.id, "")
                elif f_campo == "periodico":
                    val_real = p.journal
                elif f_campo == "citacoes_recebidas":
                    enr = enrichments.get(p.id)
                    val_real = enr.cited_by_count if enr else 0
                elif f_campo == "acesso_aberto":
                    enr = enrichments.get(p.id)
                    val_real = enr.is_oa if enr else False

                # Avaliar operador
                if f_op == "=" and str(val_real).lower() != str(f_val).lower():
                    passou = False
                    break
                elif f_op == "!=" and str(val_real).lower() == str(f_val).lower():
                    passou = False
                    break
                elif f_op == ">=":
                    try:
                        if float(val_real or 0) < float(f_val):
                            passou = False
                            break
                    except Exception:
                        passou = False
                        break
                elif f_op == "<=":
                    try:
                        if float(val_real or 0) > float(f_val):
                            passou = False
                            break
                    except Exception:
                        passou = False
                        break
                elif f_op == "entre" and isinstance(f_val, list) and len(f_val) == 2:
                    try:
                        v_num = float(val_real or 0)
                        if not (float(f_val[0]) <= v_num <= float(f_val[1])):
                            passou = False
                            break
                    except Exception:
                        passou = False
                        break
                elif f_op == "em" and isinstance(f_val, list):
                    if str(val_real) not in [str(x) for x in f_val]:
                        passou = False
                        break
                elif f_op == "contem":
                    if str(f_val).lower() not in str(val_real or "").lower():
                        passou = False
                        break

            if passou:
                papers_filtrados.append(p)

        # 5. Agrupamento e Coleta de Valores Numéricos
        grupos: dict[tuple, list[Any]] = defaultdict(list)
        grupos_docs_count: dict[tuple, int] = defaultdict(int)

        for p in papers_filtrados:
            enr = enrichments.get(p.id)
            txt = textos.get(p.id)
            auts = authorships.get(p.id, [])

            # Extrair valores dos agrupadores
            chaves_grupo: list[str] = []
            for agr in spec.por:
                if agr == "ano":
                    chaves_grupo.append(p.year or "s.d.")
                elif agr == "decisao":
                    chaves_grupo.append(p.decision or "Pendente")
                elif agr == "fonte":
                    chaves_grupo.append(sources.get(p.id, "desconhecida"))
                elif agr == "periodico":
                    chaves_grupo.append(p.journal.strip() if p.journal else "Sem periódico")
                elif agr == "instituicao":
                    inst_nome = auts[0].institution_name if auts and auts[0].institution_name else (p.institution or "Sem afiliação")
                    chaves_grupo.append(inst_nome.strip())
                elif agr == "pais":
                    pais_nome = auts[0].country if auts and auts[0].country else "Não declarado"
                    chaves_grupo.append(pais_nome)
                elif agr == "idioma":
                    chaves_grupo.append(enr.language if enr and enr.language else "desconhecido")
                elif agr == "tipo":
                    chaves_grupo.append(p.research_type or "Outro")
                elif agr == "acesso_aberto":
                    chaves_grupo.append("Acesso Aberto" if (enr and enr.is_oa) else "Acesso Restrito")
                elif agr == "autor":
                    prim_autor = auts[0].author_name if auts else (p.authors.split(";")[0].split(",")[0] if p.authors else "Anon")
                    chaves_grupo.append(prim_autor.strip())
                else:
                    chaves_grupo.append("Todos")

            chave_tupla = tuple(chaves_grupo)
            grupos_docs_count[chave_tupla] += 1

            # Valor da métrica para o documento
            val_metrica: Any = 1
            if spec.campo == "citacoes_recebidas":
                val_metrica = enr.cited_by_count if enr else 0
            elif spec.campo == "ano":
                try:
                    val_metrica = int(p.year)
                except Exception:
                    val_metrica = 0
            elif spec.campo == "n_palavras":
                val_metrica = txt.n_words if txt else 0
            elif spec.campo == "n_paginas":
                val_metrica = txt.n_pages if txt else 0
            elif spec.campo == "acesso_aberto":
                val_metrica = 1 if (enr and enr.is_oa) else 0

            grupos[chave_tupla].append(val_metrica)

        # 6. Cálculo da Medida Estatística por Grupo
        linhas_resultado: list[dict[str, Any]] = []

        for chave_tupla, valores in grupos.items():
            n_docs = grupos_docs_count[chave_tupla]
            d_grupo = {spec.por[i]: chave_tupla[i] for i in range(len(spec.por))}

            res_valor: Optional[float] = None
            if spec.medida == "contagem":
                res_valor = float(n_docs)
            elif spec.medida == "distintos":
                res_valor = float(len(set(valores)))
            elif spec.medida == "soma":
                res_valor = float(sum(valores))
            elif spec.medida == "media":
                res_valor = round(float(sum(valores) / len(valores)), 4) if valores else 0.0
            elif spec.medida == "mediana":
                res_valor = round(float(statistics.median(valores)), 4) if valores else 0.0
            elif spec.medida == "quantil":
                q_p = spec.quantil_p if spec.quantil_p is not None else 0.5
                vals_sorted = sorted(valores)
                if vals_sorted:
                    idx = int(len(vals_sorted) * q_p)
                    idx = min(idx, len(vals_sorted) - 1)
                    res_valor = float(vals_sorted[idx])
                else:
                    res_valor = 0.0
            elif spec.medida == "taxa":
                # Proporção de 1s
                res_valor = round(float(sum(1 for v in valores if v == 1) / len(valores)), 4) if valores else 0.0
            elif spec.medida == "desvio_padrao":
                res_valor = round(float(statistics.stdev(valores)), 4) if len(valores) > 1 else 0.0

            linhas_resultado.append(
                {
                    "grupo": d_grupo,
                    "valor": res_valor,
                    "n_docs": n_docs,
                }
            )

        # 7. Ordenação e Limite
        if spec.ordenar_por == "valor_desc":
            linhas_resultado.sort(key=lambda x: x["valor"] or 0, reverse=True)
        elif spec.ordenar_por == "valor":
            linhas_resultado.sort(key=lambda x: x["valor"] or 0)
        else:
            # Ordenar pelo primeiro agrupador
            linhas_resultado.sort(key=lambda x: str(list(x["grupo"].values())[0]))

        if spec.limite and spec.limite > 0:
            linhas_resultado = linhas_resultado[:spec.limite]

        proveniencia = {
            "project_id": project_id,
            "snapshot_id": snapshot_id or spec.snapshot_id,
            "total_papers_in_corpus": len(papers),
            "papers_after_filter": len(papers_filtrados),
            "medida": spec.medida,
            "campo": spec.campo,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return linhas_resultado, len(papers_filtrados), proveniencia

    def salvar_analise(
        self,
        db: Session,
        project_id: str,
        question: str,
        specification: dict[str, Any],
        user_id: Optional[str] = None,
    ) -> BibAnaliseModel:
        """Salva a análise formal para permitir reexecução sobre outros instantâneos (doc 48 §9.3)."""
        analise = BibAnaliseModel(
            project_id=project_id,
            question=question,
            specification=json.dumps(specification, ensure_ascii=False),
            created_by=user_id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(analise)
        db.commit()
        db.refresh(analise)
        return analise

    def listar_analises(self, db: Session, project_id: str) -> list[BibAnaliseModel]:
        return (
            db.query(BibAnaliseModel)
            .filter(BibAnaliseModel.project_id == project_id)
            .order_by(BibAnaliseModel.created_at.desc())
            .all()
        )

    def excluir_analise(self, db: Session, analise_id: str, project_id: str) -> bool:
        a = (
            db.query(BibAnaliseModel)
            .filter(BibAnaliseModel.id == analise_id, BibAnaliseModel.project_id == project_id)
            .first()
        )
        if not a:
            return False
        db.delete(a)
        db.commit()
        return True
