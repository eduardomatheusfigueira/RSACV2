#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Revsist — Tesauro Controlado e Fusões Aprovadas (doc 48 §5, §6.1, doc 49 Fase 4).

Fecha B-06:
    - Tesauro por projeto para unificação léxica.
    - Proposta de variantes assistida ou heurística.
    - Porta obrigatória de aprovação humana: entradas nascem em rascunho e
      nenhuma fusão é aplicada antes da aprovação explícita.
"""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import (
    BibThesaurusEntryModel,
    BibThesaurusModel,
    ProjectModel,
)

logger = logging.getLogger(__name__)

_ESPACOS = re.compile(r"\s+")


def normalizar_forma(texto: str) -> str:
    """Normaliza texto para chave de agrupamento léxico."""
    return _ESPACOS.sub(" ", (texto or "").strip()).casefold()


def radical_simplificado(texto: str) -> str:
    """Extrai chave léxica unificada normalizando plurais comuns em português e inglês."""
    palavras = normalizar_forma(texto).split()
    radicais = []
    for p in palavras:
        if len(p) <= 3:
            radicais.append(p)
            continue
        p_norm = p
        # Português: -ais, -eis, -ois -> -al, -el, -ol (ex: regionais -> regional, locais -> local)
        p_norm = re.sub(r"ais\b", "al", p_norm)
        p_norm = re.sub(r"eis\b", "el", p_norm)
        p_norm = re.sub(r"ois\b", "ol", p_norm)
        # Português: -ões, -oes, -ães, -aes, -ãos, -aos -> -ao
        p_norm = re.sub(r"(ões|oes|ães|aes|ãos|aos)\b", "ao", p_norm)
        # Plurais regulares em -es ou -s
        if p_norm.endswith("es") and len(p_norm) > 4:
            p_norm = p_norm[:-2]
        elif p_norm.endswith("s") and len(p_norm) > 3:
            p_norm = p_norm[:-1]
        radicais.append(p_norm)
    return " ".join(radicais)


class ServicoDeTesauro:
    """Gerencia tesauros controlados e normalização determinística por projeto."""

    def obter_ou_criar_tesauro_padrao(
        self, db: Session, project_id: str, user_id: Optional[str] = None
    ) -> BibThesaurusModel:
        """Retorna o tesauro principal do projeto ou cria um padrão caso não exista."""
        t = db.query(BibThesaurusModel).filter(BibThesaurusModel.project_id == project_id).first()
        if t:
            return t

        novo = BibThesaurusModel(
            project_id=project_id,
            name="Tesauro Geral do Projeto",
            description="Vocabulário controlado e fusões de termos aprovadas para o projeto.",
            created_by=user_id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(novo)
        db.commit()
        db.refresh(novo)
        return novo

    def listar_entradas(
        self, db: Session, thesaurus_id: str, apenas_aprovadas: bool = False
    ) -> list[BibThesaurusEntryModel]:
        """Lista entradas de um tesauro."""
        q = db.query(BibThesaurusEntryModel).filter(BibThesaurusEntryModel.thesaurus_id == thesaurus_id)
        if apenas_aprovadas:
            q = q.filter(BibThesaurusEntryModel.approved_by.isnot(None))
        return q.order_by(BibThesaurusEntryModel.preferred_term).all()

    def adicionar_entrada(
        self,
        db: Session,
        thesaurus_id: str,
        preferred_term: str,
        variants: list[str],
        scope: str = "",
        proposed_by: str = "manual",
        approved_by: Optional[str] = None,
    ) -> BibThesaurusEntryModel:
        """Adiciona ou atualiza uma entrada de tesauro."""
        pref_limpo = preferred_term.strip()
        variantes_limpas = sorted(list(set(v.strip() for v in variants if v and v.strip() != pref_limpo)))

        # Verificar se já existe entrada com o mesmo termo preferido
        existente = (
            db.query(BibThesaurusEntryModel)
            .filter(
                BibThesaurusEntryModel.thesaurus_id == thesaurus_id,
                BibThesaurusEntryModel.preferred_term == pref_limpo,
            )
            .first()
        )

        agora = datetime.now(timezone.utc)
        if existente:
            var_existentes = set()
            try:
                var_existentes = set(json.loads(existente.variants))
            except Exception:
                pass
            var_existentes.update(variantes_limpas)
            existente.variants = json.dumps(sorted(list(var_existentes)), ensure_ascii=False)
            existente.scope = scope or existente.scope
            if approved_by:
                existente.approved_by = approved_by
                existente.approved_at = agora
            db.commit()
            db.refresh(existente)
            return existente

        aprov_em = agora if approved_by else None
        nova = BibThesaurusEntryModel(
            thesaurus_id=thesaurus_id,
            preferred_term=pref_limpo,
            variants=json.dumps(variantes_limpas, ensure_ascii=False),
            scope=scope,
            proposed_by=proposed_by,
            approved_by=approved_by,
            approved_at=aprov_em,
            created_at=agora,
        )
        db.add(nova)
        db.commit()
        db.refresh(nova)
        return nova

    def aprovar_entradas(
        self, db: Session, entry_ids: list[str], user_id: str
    ) -> list[BibThesaurusEntryModel]:
        """Aprova formalmente um conjunto de entradas de tesauro (porta obrigatória doc 48 §6.1)."""
        agora = datetime.now(timezone.utc)
        entradas = (
            db.query(BibThesaurusEntryModel)
            .filter(BibThesaurusEntryModel.id.in_(entry_ids))
            .all()
        )
        for e in entradas:
            e.approved_by = user_id
            e.approved_at = agora
        db.commit()
        return entradas

    def propor_fusoes_automaticas(
        self,
        db: Session,
        thesaurus_id: str,
        termos: list[str],
        proposed_by: str = "ai",
    ) -> list[BibThesaurusEntryModel]:
        """Agrupa variantes léxicas óbvias (plural/singular, acentos, pontuação) como sugestão em rascunho."""
        agrupamentos: dict[str, list[str]] = defaultdict(list)

        for t in termos:
            t_limpo = t.strip()
            if not t_limpo:
                continue
            chave = radical_simplificado(t_limpo)
            agrupamentos[chave].append(t_limpo)

        criadas: list[BibThesaurusEntryModel] = []
        for chave_base, lista_formas in agrupamentos.items():
            if len(set(normalizar_forma(f) for f in lista_formas)) > 1:
                # Ordena pela forma mais curta ou mais canônica
                ordenadas = sorted(lista_formas, key=lambda x: (len(x), x))
                termo_preferido = ordenadas[0]
                variantes = [f for f in lista_formas if f != termo_preferido]

                entrada = self.adicionar_entrada(
                    db,
                    thesaurus_id=thesaurus_id,
                    preferred_term=termo_preferido,
                    variants=variantes,
                    scope="sugestão léxica",
                    proposed_by=proposed_by,
                    approved_by=None,  # SEMPRE rascunho
                )
                criadas.append(entrada)

        return criadas


    def aplicar_tesauro(
        self, termos: list[str], entradas_aprovadas: list[BibThesaurusEntryModel]
    ) -> list[str]:
        """Aplica substituições determinísticas de termos por seus termos preferidos aprovados."""
        if not entradas_aprovadas:
            return termos

        # Montar mapa: variante normalizada -> termo preferido
        mapa_substituicao: dict[str, str] = {}
        for e in entradas_aprovadas:
            pref = e.preferred_term
            mapa_substituicao[normalizar_forma(pref)] = pref
            try:
                vars_list = json.loads(e.variants)
                for v in vars_list:
                    mapa_substituicao[normalizar_forma(v)] = pref
            except Exception:
                pass

        resultado: list[str] = []
        for t in termos:
            t_norm = normalizar_forma(t)
            if t_norm in mapa_substituicao:
                resultado.append(mapa_substituicao[t_norm])
            else:
                resultado.append(t)

        return resultado
