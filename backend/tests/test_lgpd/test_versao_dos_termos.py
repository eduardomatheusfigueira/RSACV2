#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — A versão dos documentos precisa ser a mesma em todo lugar.

A versão vigente decide quando o aceite é pedido de novo, e ela está copiada
em sete lugares: a configuração do backend, o aceite da aplicação, o aceite da
landing, o script de `<head>` de três páginas e o gerador do blog. As cópias
existem por necessidade — o script de `<head>` precisa decidir antes de
qualquer módulo carregar — e é exatamente por isso que precisam de guarda.

Uma cópia esquecida produz um defeito silencioso e irritante: o visitante
aceita, a página guarda uma versão, e a outra metade do site, lendo outra,
pergunta de novo a cada visita.
"""

from pathlib import Path

import pytest

from app.config import settings

RAIZ = Path(__file__).resolve().parents[3]

COPIAS = [
    ("frontend/src/components/aceite/AceiteDeTermos.tsx", "const VERSAO = '{v}'"),
    ("landing/src/scripts/aceite.js", "const VERSAO = '{v}';"),
    ("landing/index.html", "JSON.parse(b).versao === '{v}'"),
    ("landing/termos/index.html", "JSON.parse(b).versao === '{v}'"),
    ("landing/privacidade/index.html", "JSON.parse(b).versao === '{v}'"),
    ("landing/scripts/gerar-blog.mjs", "JSON.parse(b).versao === '{v}'"),
]


@pytest.mark.parametrize("arquivo,trecho", COPIAS, ids=[c[0] for c in COPIAS])
def test_copia_da_versao_bate_com_a_configuracao(arquivo, trecho):
    conteudo = (RAIZ / arquivo).read_text(encoding="utf-8")
    esperado = trecho.format(v=settings.terms_version)
    assert esperado in conteudo, (
        f"{arquivo} não traz a versão vigente {settings.terms_version!r}. "
        "Atualize todas as cópias juntas."
    )
