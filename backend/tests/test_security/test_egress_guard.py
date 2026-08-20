#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Guarda de requisições de saída — SSRF (doc 28 V-05, doc 29 §29.5.3).

O RSAC busca PDFs em endereços que o usuário fornece e fala com o endpoint de
IA que o usuário configura. Sem guarda, o servidor vira procurador: quem
controla a URL manda o backend requisitar o que quiser de dentro da rede onde
ele está.

Estes testes usam `dns_real` para exercitar a resolução de verdade — é ela que
fecha o *DNS rebinding*, e testá-la com um resolvedor falso não provaria nada.
"""

import httpx
import pytest

from app.config import DeploymentProfile, Settings
from app.security.egress import (
    EgressBlocked,
    detalhe_publico,
    host_e_academico_conhecido,
    url_e_permitida,
    validar_url,
)
from app.security.safe_http import get_com_guarda

pytestmark = pytest.mark.dns_real


# ── A tabela de destinos do doc 30 ────────────────────────────────────

@pytest.mark.parametrize(
    "url,motivo_esperado",
    [
        ("file:///etc/passwd", "esquema"),
        ("gopher://evil.example/x", "esquema"),
        ("ftp://evil.example/x", "esquema"),
        ("http://169.254.169.254/latest/meta-data/", "link-local"),
        ("http://[fd00::1]/x", "rede privada"),
        ("http://10.0.0.1/interno", "rede privada"),
        ("http://192.168.1.1/roteador", "rede privada"),
        ("http://172.16.0.1/x", "rede privada"),
        ("http://127.0.0.1/x", "loopback"),
        ("http://[::1]/x", "loopback"),
        ("http://[::ffff:127.0.0.1]/x", "loopback"),
        ("http://0.0.0.0/x", ""),
        ("", "vazia"),
        ("http:///semhost", "host"),
    ],
)
def test_destinos_internos_sao_recusados(url, motivo_esperado):
    with pytest.raises(EgressBlocked) as exc:
        validar_url(url, permitir_loopback=False)
    if motivo_esperado:
        assert motivo_esperado in exc.value.motivo.lower()


def test_porta_de_servico_interno_e_recusada():
    """Liberar porta arbitrária transformaria o guarda num scanner com retorno."""
    for porta in (22, 3306, 5432, 6379, 9200, 11211):
        with pytest.raises(EgressBlocked, match="porta"):
            validar_url(f"http://example.com:{porta}/x", permitir_loopback=False)


@pytest.mark.parametrize(
    "url",
    [
        "https://arxiv.org/pdf/2401.00001",
        "https://doi.org/10.1590/1234",
        "https://www.scielo.br/j/rap/a/xyz/",
    ],
)
def test_destinos_academicos_legitimos_passam(url):
    """O guarda não pode quebrar o uso normal do produto."""
    assert url_e_permitida(url, permitir_loopback=False)


def test_nome_que_resolve_para_ip_privado_e_recusado(monkeypatch):
    """
    DNS rebinding: validar o *nome* não basta, porque `evil.com` pode resolver
    para `127.0.0.1`. A checagem é sobre o IP.
    """
    import socket

    import app.security.egress as egress

    def _resolve_para_interno(host, porta, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.1.2.3", porta))]

    monkeypatch.setattr(egress, "_resolver_enderecos", _resolve_para_interno)

    with pytest.raises(EgressBlocked, match="privada"):
        validar_url("https://host-aparentemente-publico.example/x", permitir_loopback=False)


def test_host_com_um_ip_publico_e_outro_interno_e_recusado(monkeypatch):
    """
    O resolvedor pode entregar qualquer um dos endereços na hora de conectar,
    então validar só o primeiro deixaria a porta aberta.
    """
    import socket

    import app.security.egress as egress

    def _dois_enderecos(host, porta, *args, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", porta)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", porta)),
        ]

    monkeypatch.setattr(egress, "_resolver_enderecos", _dois_enderecos)

    with pytest.raises(EgressBlocked, match="loopback"):
        validar_url("https://host-misto.example/x", permitir_loopback=False)


# ── Loopback: legítimo apenas para o LLM local, e só no desktop ───────

def test_llm_local_e_permitido_no_desktop():
    """Ollama e LM Studio escutam em loopback, em porta arbitrária."""
    assert url_e_permitida("http://localhost:11434/v1", permitir_loopback=True)
    assert url_e_permitida("http://127.0.0.1:1234/v1", permitir_loopback=True)


def test_loopback_nao_e_permitido_no_perfil_server(monkeypatch):
    """No servidor, loopback é a rede interna de quem hospeda."""
    import app.security.egress as egress

    monkeypatch.setattr(
        egress, "settings", Settings(deployment_profile=DeploymentProfile.SERVER)
    )
    assert not url_e_permitida("http://localhost:11434/v1")
    assert not url_e_permitida("http://127.0.0.1:6379")


def test_loopback_liberado_nao_abre_a_rede_privada():
    """Permitir loopback é permitir a própria máquina, não a rede local."""
    assert not url_e_permitida("http://10.0.0.1:11434", permitir_loopback=True)
    assert not url_e_permitida("http://192.168.0.10", permitir_loopback=True)
    assert not url_e_permitida("http://169.254.169.254/", permitir_loopback=True)


# ── Redirecionamento: o caso que pega implementação ingênua ───────────

@pytest.mark.anyio
async def test_redirecionamento_para_destino_interno_e_bloqueado():
    """
    Host público que responde `302 Location: http://169.254.169.254/`.

    É o caso decisivo: uma validação feita só na URL inicial deixa passar, e
    `follow_redirects=True` do httpx faria exatamente isso.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "example.com":
            return httpx.Response(
                302, headers={"location": "http://169.254.169.254/latest/meta-data/"}
            )
        return httpx.Response(200, text="METADADOS SECRETOS DA NUVEM")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(EgressBlocked, match="link-local"):
            await get_com_guarda(client, "https://example.com/artigo", permitir_loopback=False)


@pytest.mark.anyio
async def test_redirecionamento_para_loopback_e_bloqueado():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "example.com":
            return httpx.Response(302, headers={"location": "http://127.0.0.1:6379/"})
        return httpx.Response(200, text="conteúdo do redis")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(EgressBlocked):
            await get_com_guarda(client, "https://example.com/artigo", permitir_loopback=False)


@pytest.mark.anyio
async def test_redirecionamento_legitimo_e_seguido():
    """O guarda não pode quebrar a cadeia DOI → editor → arquivo."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "doi.org":
            return httpx.Response(302, headers={"location": "https://arxiv.org/pdf/2401.1"})
        return httpx.Response(200, content=b"%PDF-1.7 conteudo")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        resposta = await get_com_guarda(client, "https://doi.org/10.1/x", permitir_loopback=False)

    assert resposta.status_code == 200
    assert resposta.content.startswith(b"%PDF")


@pytest.mark.anyio
async def test_laco_de_redirecionamento_e_interrompido():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://doi.org/loop"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(EgressBlocked, match="laço|redirecionamentos"):
            await get_com_guarda(client, "https://doi.org/loop", permitir_loopback=False)


@pytest.mark.anyio
async def test_cadeia_longa_demais_e_interrompida():
    contador = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        contador["n"] += 1
        return httpx.Response(
            302, headers={"location": f"https://arxiv.org/salto/{contador['n']}"}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(EgressBlocked, match="redirecionamentos"):
            await get_com_guarda(client, "https://doi.org/x", permitir_loopback=False)

    assert contador["n"] <= 7, "seguiu saltos demais antes de desistir"


# ── A trilha deixa de ser oráculo (§29.5.4) ───────────────────────────

def test_trilha_detalhada_para_host_academico(monkeypatch):
    import app.security.egress as egress

    monkeypatch.setattr(
        egress, "settings", Settings(deployment_profile=DeploymentProfile.SERVER)
    )
    detalhe = "HTTP 403 (conteúdo restrito por assinatura)"
    assert detalhe_publico("https://arxiv.org/pdf/1", detalhe) == detalhe


def test_trilha_reduzida_para_host_desconhecido_no_server(monkeypatch):
    """Sem isso, a mensagem de erro ainda entregaria o mapa da rede interna."""
    import app.security.egress as egress

    monkeypatch.setattr(
        egress, "settings", Settings(deployment_profile=DeploymentProfile.SERVER)
    )
    detalhe = "HTTP 401 — servidor interno de RH respondeu"
    publico = detalhe_publico("https://intranet.empresa.local/x", detalhe)

    assert publico != detalhe
    assert "RH" not in publico
    assert "401" not in publico


def test_trilha_completa_no_desktop(monkeypatch):
    """No app de mesa não há terceiro para enganar — o detalhe ajuda o usuário."""
    import app.security.egress as egress

    monkeypatch.setattr(
        egress, "settings", Settings(deployment_profile=DeploymentProfile.DESKTOP)
    )
    detalhe = "HTTP 404 no repositório institucional"
    assert detalhe_publico("https://qualquer.host/x", detalhe) == detalhe


def test_reconhecimento_de_host_academico():
    assert host_e_academico_conhecido("https://arxiv.org/pdf/1")
    assert host_e_academico_conhecido("https://www.scielo.br/j/x/")
    assert host_e_academico_conhecido("https://pubmed.ncbi.nlm.nih.gov/1/")
    assert not host_e_academico_conhecido("https://arxiv.org.evil.com/x")
    assert not host_e_academico_conhecido("https://intranet.local/x")
