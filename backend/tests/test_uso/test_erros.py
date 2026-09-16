#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Sanitização das ocorrências de erro (doc 52 §5.4, T-13).

O erro é o caminho mais provável de o conteúdo da pesquisa escapar para os
dados de uso: uma exceção que ecoa o título de um estudo, uma consulta que
leva o e-mail de alguém como parâmetro.
"""

from app.services.uso import erros


def test_mensagem_perde_conteudo_e_credencial():
    limpa = erros.sanitizar_mensagem(
        "KeyError",
        "Falhou 'Impactos da segurança pública' para joao@usp.br em https://x.org/a?b=1 "
        "com chave AIzaSyA1234567890abcdefghijklmnop e DOI 10123456789 id 7847417c-79df-4892-bdec-2257d019f65e",
    )
    for vazamento in ("Impactos", "joao@usp.br", "x.org", "AIzaSy", "10123456789", "7847417c"):
        assert vazamento not in limpa, vazamento


def test_erro_de_banco_grava_so_o_tipo():
    assert erros.sanitizar_mensagem("sqlalchemy.exc.IntegrityError", "UNIQUE failed: users.email maria@x.br") == ""


def test_mensagem_e_truncada():
    assert len(erros.sanitizar_mensagem("Erro", "a " * 1000)) <= erros.MAX_MENSAGEM


def test_pilha_python_so_arquivo_linha_funcao():
    pilha = (
        'Traceback (most recent call last):\n'
        '  File "C:\\Users\\Maria\\RSACV2\\backend\\app\\services\\screening_service.py", line 239, in screen_single_paper\n'
        '    result = await client.analyze_screening(paper_entity, protocol_entity)\n'
        '  File "/srv/revsist/backend/app/infrastructure/ai/gemini_client.py", line 452, in analyze_screening\n'
    )
    assert erros.sanitizar_pilha(pilha) == [
        "app/services/screening_service.py:239:screen_single_paper",
        "app/infrastructure/ai/gemini_client.py:452:analyze_screening",
    ]


def test_pilha_firefox():
    assert erros.sanitizar_pilha("triar@https://revsist.com/assets/index-abc.js:10:3") == ["assets/index-abc.js:10:triar"]


def test_impressao_ignora_numero_da_linha():
    """Uma linha acrescentada acima não pode transformar o mesmo defeito em outro."""
    a = erros.sanitizar("TypeError", "x", "at f (https://r.com/assets/i.js:10:1)")
    b = erros.sanitizar("TypeError", "y", "at f (https://r.com/assets/i.js:12:1)")
    c = erros.sanitizar("RangeError", "x", "at f (https://r.com/assets/i.js:10:1)")
    assert a.impressao == b.impressao
    assert a.impressao != c.impressao


def test_familia_do_navegador_nunca_a_string_inteira():
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
    assert erros.familia_do_navegador(ua) == "edge 131"
    assert erros.familia_do_navegador("") == ""
