#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""RSAC V2 — Harvester Factory."""

from typing import Dict, List, Optional
from app.domain.enums import HarvesterSource
from app.harvesters.base import BaseHarvester
from app.harvesters.bdtd import BDTDHarvester
from app.harvesters.openalex import OpenAlexHarvester
from app.harvesters.pubmed import PubMedHarvester
from app.harvesters.scielo import SciELOHarvester
from app.harvesters.scopus import ScopusHarvester


class HarvesterFactory:
    """Factory para instanciar coletores suportados."""

    @staticmethod
    def get_harvester(
        source: str,
        pubmed_api_key: Optional[str] = None,
        scopus_api_key: Optional[str] = None,
    ) -> BaseHarvester:
        source_normalized = source.upper()

        if source_normalized == "BDTD":
            return BDTDHarvester()
        elif source_normalized == "SCIELO":
            return SciELOHarvester()
        elif source_normalized == "OPENALEX":
            return OpenAlexHarvester()
        elif source_normalized == "PUBMED":
            return PubMedHarvester(api_key=pubmed_api_key)
        elif source_normalized == "SCOPUS":
            return ScopusHarvester(api_key=scopus_api_key)
        else:
            raise ValueError(f"Fonte de coleta '{source}' não é suportada.")

    @staticmethod
    def get_all_available() -> List[str]:
        return ["BDTD", "SciELO", "OpenAlex", "PubMed", "Scopus"]
