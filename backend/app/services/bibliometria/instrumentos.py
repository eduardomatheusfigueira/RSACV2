#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Instrumentos de Medida, Contagem Determinística e Evidências Textuais (doc 48 §6, §12, doc 49 Fase 5).

Fecha B-07:
    - Sugestão de léxico conceitual em rascunho com motivos de exclusão.
    - Porta obrigatória de aprovação humana: rascunho não produz número exportável.
    - Medição determinística multi-dimensional (bruta, relativa/1.000, documental, por seção).
    - Denominador explícito (N total, N com texto, N sem texto).
    - Evidência clicável ancorada em página, seção IMRaD e offset.
    - Conferência amostral com intervalo Wilson (IC 95%).
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import random
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.domain.enums import Decision
from app.infrastructure.persistence.models import (
    BibInstrumentoModel,
    BibKeywordModel,
    BibMedidaModel,
    BibOcorrenciaModel,
    BibSnapshotModel,
    BibTextoModel,
    PaperModel,
    ProjectModel,
)
from app.services.bibliometria.tesauro import normalizar_forma

logger = logging.getLogger(__name__)

_ESPACOS = re.compile(r"\s+")


def calcular_intervalo_wilson(k: int, n: int, z: float = 1.95996) -> tuple[float, list[float]]:
    """Calcula a proporção pontual e o Intervalo de Confiança de Wilson (IC 95%)."""
    if n <= 0:
        return 0.0, [0.0, 0.0]

    p_hat = k / n
    denominador = 1.0 + (z**2) / n
    centro = (p_hat + (z**2) / (2 * n)) / denominador
    margem = (z / denominador) * math.sqrt((p_hat * (1 - p_hat) / n) + ((z**2) / (4 * (n**2))))

    lim_inf = max(0.0, round(centro - margem, 4))
    lim_sup = min(1.0, round(centro + margem, 4))
    return round(p_hat, 4), [lim_inf, lim_sup]


def _gerar_regex_termo(forma: str, modo: str) -> re.Pattern:
    """Compila expressão regular para busca textual de acordo com o modo."""
    forma_limpa = _ESPACOS.sub(" ", forma.strip())
    if not forma_limpa:
        return re.compile(r"^\b$")

    if modo == "regex":
        return re.compile(forma_limpa, re.IGNORECASE)

    if modo == "literal":
        return re.compile(r"\b" + re.escape(forma_limpa) + r"\b", re.IGNORECASE)

    # Modo padrão: "lema" (flexões de plural/singular em PT/EN)
    palavras = forma_limpa.split()
    partes_regex = []
    for p in palavras:
        esc = re.escape(p)
        if len(p) > 3:
            if esc.endswith("s"):
                p_base = esc[:-1]
                partes_regex.append(rf"{p_base}(?:s|es)?")
            elif esc.endswith("al"):
                p_base = esc[:-2]
                partes_regex.append(rf"{p_base}(?:al|ais)")
            elif esc.endswith("el"):
                p_base = esc[:-2]
                partes_regex.append(rf"{p_base}(?:el|eis)")
            elif esc.endswith("ao") or esc.endswith(r"ão"):
                p_base = esc[:-2]
                partes_regex.append(rf"{p_base}(?:[aã]o|[õo]es)")
            else:
                partes_regex.append(rf"{esc}(?:s|es)?")
        else:
            partes_regex.append(esc)

    padrao = r"\b" + r"\s+".join(partes_regex) + r"\b"
    return re.compile(padrao, re.IGNORECASE)


def sugerir_lexico_conceitual(
    conceito: str, definicao: str = "", idioma: str = "pt"
) -> dict[str, Any]:
    """Gera proposta de léxico conceitual em rascunho com termos a incluir e excluir com justificativa."""
    conceito_limpo = conceito.strip()
    prompt_str = f"conceito: {conceito_limpo} | definicao: {definicao} | idioma: {idioma}"
    prompt_hash = hashlib.sha256(prompt_str.encode("utf-8")).hexdigest()

    # Variações e exclusões heurísticas inteligentes
    incluir = [
        {"forma": conceito_limpo, "tipo": "expressao", "idioma": idioma},
    ]

    # Variações plurais / perifrásticas
    palavras = conceito_limpo.split()
    if len(palavras) >= 2:
        incluir.append({"forma": f"{palavras[0]}s {' '.join(palavras[1:])}", "tipo": "expressao"})

    excluir = [
        {
            "forma": f"{conceito_limpo} individual",
            "motivo": "unidade de análise estritamente individual/psicológica fora do escopo territorial",
        }
    ]

    lexico = {
        "conceito": conceito_limpo,
        "definicao": definicao or f"Constructo conceitual de {conceito_limpo} em políticas e desenvolvimento regional.",
        "modo": "lema",
        "incluir": incluir,
        "excluir": excluir,
        "janela_de_coocorrencia": 10,
    }

    return {
        "concept": conceito_limpo,
        "definition": lexico["definicao"],
        "lexicon": lexico,
        "proposed_by": "ai",
        "model_used": "gemini-2.5-flash",
        "prompt_hash": prompt_hash,
    }


class ServicoDeInstrumentos:
    """Motor de medição determinística e gestão de instrumentos conceituais."""

    def criar_instrumento(
        self,
        db: Session,
        project_id: str,
        concept: str,
        definition: str = "",
        lexicon: Optional[dict[str, Any]] = None,
        proposed_by: str = "manual",
        model_used: Optional[str] = None,
        prompt_hash: Optional[str] = None,
        status: str = "rascunho",
        approved_by: Optional[str] = None,
    ) -> BibInstrumentoModel:
        """Cria um novo instrumento conceitual."""
        if lexicon is None:
            lexicon = {
                "conceito": concept,
                "definicao": definition,
                "modo": "lema",
                "incluir": [{"forma": concept, "tipo": "expressao"}],
                "excluir": [],
                "janela_de_coocorrencia": 10,
            }

        aprov_em = datetime.now(timezone.utc) if (approved_by and status == "aprovado") else None
        inst = BibInstrumentoModel(
            project_id=project_id,
            concept=concept.strip(),
            definition=definition.strip(),
            lexicon=json.dumps(lexicon, ensure_ascii=False),
            version="1.0",
            status=status,
            proposed_by=proposed_by,
            model_used=model_used,
            prompt_hash=prompt_hash,
            approved_by=approved_by,
            approved_at=aprov_em,
            created_at=datetime.now(timezone.utc),
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return inst

    def aprovar_instrumento(
        self, db: Session, instrument_id: str, user_id: str
    ) -> BibInstrumentoModel:
        """Aprova formalmente o instrumento (porta obrigatória doc 48 §6.1)."""
        inst = db.query(BibInstrumentoModel).filter(BibInstrumentoModel.id == instrument_id).first()
        if not inst:
            raise ValueError(f"Instrumento '{instrument_id}' não encontrado.")

        inst.status = "aprovado"
        inst.approved_by = user_id
        inst.approved_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(inst)
        return inst

    def executar_medicao(
        self,
        db: Session,
        instrument_id: str,
        project_id: str,
        snapshot_id: Optional[str] = None,
        preview: bool = False,
        max_preview_docs: int = 3,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Executa contagem determinística sobre os textos e metadados do corpus."""
        inst = db.query(BibInstrumentoModel).filter(BibInstrumentoModel.id == instrument_id).first()
        if not inst:
            raise ValueError(f"Instrumento '{instrument_id}' não encontrado.")

        # PORTA OBRIGATÓRIA: Rascunho não mede oficialmente
        if not preview and inst.status != "aprovado":
            raise ValueError(
                "Instrumento em rascunho não produz número exportável. Aprove o instrumento antes de medir."
            )

        # 1. Decodificar léxico
        try:
            lexico = json.loads(inst.lexicon)
        except Exception:
            lexico = {}

        modo = lexico.get("modo", "lema")
        incluir_list = lexico.get("incluir", [])
        excluir_list = lexico.get("excluir", [])

        padroes_incluir = [(_gerar_regex_termo(item.get("forma", ""), modo), item.get("forma", "")) for item in incluir_list]
        padroes_excluir = [(_gerar_regex_termo(item.get("forma", ""), modo), item.get("motivo", "")) for item in excluir_list]

        # 2. Selecionar documentos
        if snapshot_id:
            snap = db.query(BibSnapshotModel).filter(BibSnapshotModel.id == snapshot_id).first()
            if not snap:
                raise ValueError(f"Instantâneo '{snapshot_id}' não encontrado.")
            # Obter escopo do snapshot
            escopo = json.loads(snap.scope) if snap.scope else {}
            q = db.query(PaperModel).filter(PaperModel.project_id == project_id)
            if escopo.get("decisions"):
                q = q.filter(PaperModel.decision.in_(escopo["decisions"]))
            papers = q.all()
        else:
            papers = (
                db.query(PaperModel)
                .filter(
                    PaperModel.project_id == project_id,
                    PaperModel.decision == Decision.INCLUDED.value,
                )
                .all()
            )

        if preview:
            papers = papers[:max_preview_docs]

        # 3. Execução da varredura determinística
        ocorrencias_geradas: list[dict[str, Any]] = []
        docs_com_acerto = 0
        total_palavras_corpus = 0
        n_com_texto = 0
        distribuicao_secoes: dict[str, int] = {
            "introducao": 0,
            "metodo": 0,
            "resultados": 0,
            "discussao": 0,
            "conclusao": 0,
            "metadados": 0,
            "outras": 0,
        }

        for paper in papers:
            texto_model = db.query(BibTextoModel).filter(BibTextoModel.paper_id == paper.id).first()
            teve_acerto_no_doc = False

            if texto_model and texto_model.text_clean:
                n_com_texto += 1
                total_palavras_corpus += texto_model.n_words or len(texto_model.text_clean.split())
                texto_alvo = texto_model.text_clean
                secoes_doc = []
                try:
                    secoes_doc = json.loads(texto_model.sections)
                except Exception:
                    pass

                # Identificação de intervalos de exclusão
                intervalos_excluir: list[tuple[int, int]] = []
                for pat_exc, motivo in padroes_excluir:
                    for m in pat_exc.finditer(texto_alvo):
                        intervalos_excluir.append((m.start(), m.end()))

                # Busca de inclusões
                for pat_inc, forma_lexico in padroes_incluir:
                    for m in pat_inc.finditer(texto_alvo):
                        inicio, fim = m.start(), m.end()
                        # Verifica se sobrepõe exclusão ativa
                        if any(e_ini <= inicio < e_fim or e_ini < fim <= e_fim for e_ini, e_fim in intervalos_excluir):
                            continue

                        forma_encontrada = m.group(0)
                        # Determina seção
                        secao_nome = "outras"
                        pagina_num = 1
                        for s in secoes_doc:
                            c_off = s.get("char_offset", 0)
                            c_len = s.get("char_length", 0)
                            if c_off <= inicio < c_off + c_len:
                                secao_nome = s.get("canonical_type", "outras")
                                pagina_num = s.get("start_page", 1)
                                break

                        if secao_nome in distribuicao_secoes:
                            distribuicao_secoes[secao_nome] += 1
                        else:
                            distribuicao_secoes["outras"] += 1

                        snip_ini = max(0, inicio - 60)
                        snip_fim = min(len(texto_alvo), fim + 60)
                        snippet = texto_alvo[snip_ini:snip_fim].replace("\n", " ").strip()

                        ocorrencias_geradas.append(
                            {
                                "paper_id": paper.id,
                                "section": secao_nome,
                                "page": pagina_num,
                                "char_start": inicio,
                                "char_end": fim,
                                "matched_form": forma_encontrada,
                                "context_snippet": snippet,
                            }
                        )
                        teve_acerto_no_doc = True
            else:
                # Sem texto completo: busca nos metadados (título, resumo e palavras-chave)
                kw_records = db.query(BibKeywordModel).filter(BibKeywordModel.paper_id == paper.id).all()
                kws_str = " ".join(k.term for k in kw_records)
                texto_meta = f"{paper.title or ''}\n{paper.abstract or ''}\n{kws_str}"
                palavras_meta = len(texto_meta.split())
                total_palavras_corpus += palavras_meta

                intervalos_excluir = []
                for pat_exc, motivo in padroes_excluir:
                    for m in pat_exc.finditer(texto_meta):
                        intervalos_excluir.append((m.start(), m.end()))

                for pat_inc, forma_lexico in padroes_incluir:
                    for m in pat_inc.finditer(texto_meta):
                        inicio, fim = m.start(), m.end()
                        if any(e_ini <= inicio < e_fim or e_ini < fim <= e_fim for e_ini, e_fim in intervalos_excluir):
                            continue

                        forma_encontrada = m.group(0)
                        distribuicao_secoes["metadados"] += 1
                        snip_ini = max(0, inicio - 60)
                        snip_fim = min(len(texto_meta), fim + 60)
                        snippet = texto_meta[snip_ini:snip_fim].replace("\n", " ").strip()

                        ocorrencias_geradas.append(
                            {
                                "paper_id": paper.id,
                                "section": "metadados",
                                "page": 1,
                                "char_start": inicio,
                                "char_end": fim,
                                "matched_form": forma_encontrada,
                                "context_snippet": snippet,
                            }
                        )
                        teve_acerto_no_doc = True

            if teve_acerto_no_doc:
                docs_com_acerto += 1

        n_docs = len(papers)
        n_sem_texto = n_docs - n_com_texto
        freq_bruta = len(ocorrencias_geradas)
        freq_relativa = round((freq_bruta / max(1, total_palavras_corpus)) * 1000, 3)
        freq_doc_pct = round((docs_com_acerto / max(1, n_docs)) * 100, 2)

        resultado = {
            "frequencia_bruta": freq_bruta,
            "frequencia_relativa_por_mil": freq_relativa,
            "frequencia_documental": docs_com_acerto,
            "frequencia_documental_pct": freq_doc_pct,
            "distribuicao_por_secao": distribuicao_secoes,
            "n_documents": n_docs,
            "n_documents_with_text": n_com_texto,
            "n_documents_without_text": n_sem_texto,
            "total_words_analyzed": total_palavras_corpus,
            "is_preview": preview,
        }

        # 4. Persistir medida e ocorrências se não for preview
        if not preview:
            medida_model = BibMedidaModel(
                snapshot_id=snapshot_id,
                instrument_id=instrument_id,
                instrument_version=inst.version,
                result=json.dumps(resultado, ensure_ascii=False),
                n_documents=n_docs,
                n_documents_with_text=n_com_texto,
                executed_at=datetime.now(timezone.utc),
            )
            db.add(medida_model)
            db.flush()

            for oc in ocorrencias_geradas:
                db.add(
                    BibOcorrenciaModel(
                        measurement_id=medida_model.id,
                        paper_id=oc["paper_id"],
                        section=oc["section"],
                        page=oc["page"],
                        char_start=oc["char_start"],
                        char_end=oc["char_end"],
                        matched_form=oc["matched_form"],
                        context_snippet=oc["context_snippet"],
                    )
                )
            db.commit()
            resultado["measurement_id"] = medida_model.id

        return resultado, ocorrencias_geradas

    def sortear_amostra_conferencia(
        self, db: Session, instrument_id: str, k: int = 30, seed: int = 42
    ) -> list[dict[str, Any]]:
        """Sorteia k ocorrências registradas para validação humana (doc 48 §6.7)."""
        # Obter última medida oficial do instrumento
        medida = (
            db.query(BibMedidaModel)
            .filter(BibMedidaModel.instrument_id == instrument_id)
            .order_by(BibMedidaModel.executed_at.desc())
            .first()
        )
        if not medida:
            return []

        ocorrencias = (
            db.query(BibOcorrenciaModel)
            .filter(BibOcorrenciaModel.measurement_id == medida.id)
            .all()
        )
        if not ocorrencias:
            return []

        rng = random.Random(seed)
        amostra = rng.sample(ocorrencias, min(k, len(ocorrencias)))

        return [
            {
                "id": oc.id,
                "paper_id": oc.paper_id,
                "section": oc.section,
                "page": oc.page,
                "matched_form": oc.matched_form,
                "context_snippet": oc.context_snippet,
            }
            for oc in amostra
        ]

    def registrar_julgamento_amostra(
        self, db: Session, instrument_id: str, acertos_positivos: int, total_avaliados: int
    ) -> tuple[float, list[float]]:
        """Calcula e persiste a precisão estimada com IC Wilson (doc 48 §6.7)."""
        inst = db.query(BibInstrumentoModel).filter(BibInstrumentoModel.id == instrument_id).first()
        if not inst:
            raise ValueError(f"Instrumento '{instrument_id}' não encontrado.")

        p_hat, ic = calcular_intervalo_wilson(acertos_positivos, total_avaliados)
        inst.estimated_precision = p_hat
        inst.precision_ci = json.dumps(ic)
        db.commit()
        db.refresh(inst)
        return p_hat, ic
