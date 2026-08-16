#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Harvester Factory & Source Registry.
Registro centralizado e fábrica para instanciação dinâmica de coletores científicos
com injeção de credenciais e capacidades.
"""

import logging
from typing import Any, Dict, List, Optional, Type
from app.harvesters.base import BaseHarvester, HarvesterCapabilities

logger = logging.getLogger(__name__)

_HARVESTER_REGISTRY: Dict[str, Type[BaseHarvester]] = {}


def register_harvester(source_name: str):
    """Decorador para registrar classes de harvesters no catálogo."""
    def decorator(cls: Type[BaseHarvester]):
        _HARVESTER_REGISTRY[source_name.upper()] = cls
        return cls
    return decorator


class HarvesterFactory:
    """Fábrica extensível para instanciar coletores suportados."""

    @classmethod
    def register(cls, source_name: str, harvester_cls: Type[BaseHarvester]) -> None:
        _HARVESTER_REGISTRY[source_name.upper()] = harvester_cls

    @classmethod
    def get_harvester(
        cls,
        source: str,
        api_key: Optional[str] = None,
        inst_token: Optional[str] = None,
        custom_endpoint: Optional[str] = None,
        timeout: float = 35.0,
        **kwargs: Any,
    ) -> BaseHarvester:
        # Importar dinamicamente coletores para garantir registro dos módulos
        from app.harvesters.bdtd import BDTDHarvester
        from app.harvesters.scielo import SciELOHarvester
        from app.harvesters.openalex import OpenAlexHarvester
        from app.harvesters.pubmed import PubMedHarvester
        from app.harvesters.scopus import ScopusHarvester

        source_upper = source.upper()
        harvester_cls = _HARVESTER_REGISTRY.get(source_upper)

        if not harvester_cls:
            raise ValueError(f"Fonte de coleta '{source}' não está registrada ou não é suportada.")

        # Passar credenciais relevantes com base na classe
        if source_upper == "SCOPUS":
            return harvester_cls(api_key=api_key, inst_token=inst_token, timeout=timeout, **kwargs)
        elif source_upper == "PUBMED":
            return harvester_cls(api_key=api_key, timeout=timeout, **kwargs)
        elif source_upper == "OPENALEX":
            return harvester_cls(api_key=api_key, timeout=timeout, **kwargs)
        else:
            return harvester_cls(timeout=timeout, **kwargs)

    @classmethod
    def get_capabilities(cls, source: str) -> HarvesterCapabilities:
        from app.harvesters.bdtd import BDTDHarvester
        from app.harvesters.scielo import SciELOHarvester
        from app.harvesters.openalex import OpenAlexHarvester
        from app.harvesters.pubmed import PubMedHarvester
        from app.harvesters.scopus import ScopusHarvester

        harvester_cls = _HARVESTER_REGISTRY.get(source.upper())
        if harvester_cls:
            return getattr(harvester_cls, "capabilities", HarvesterCapabilities())
        return HarvesterCapabilities()

    @classmethod
    def get_all_available(cls) -> List[str]:
        return ["BDTD", "SciELO", "OpenAlex", "PubMed", "Scopus"]
