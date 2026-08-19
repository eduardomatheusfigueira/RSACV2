#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Guarda de requisições de saída (doc 28 V-05, doc 29 §29.5.3).

O RSAC busca PDFs em endereços que o usuário fornece e conversa com o endpoint
de IA que o usuário configura. Sem guarda, isso faz do servidor um procurador:
quem controla a URL manda o backend requisitar o que quiser **de dentro da
rede onde ele está** — metadados de nuvem, serviços que só escutam em loopback,
a faixa privada da universidade.

Duas armadilhas que este módulo trata e uma verificação ingênua não trataria:

  * **DNS rebinding.** Validar o *nome* do host não basta: `evil.com` pode
    resolver para `127.0.0.1`. A checagem é feita sobre o IP resolvido, e o IP
    validado é reusado na conexão (`resolver_e_validar`), fechando a janela
    entre a checagem e o uso.
  * **Redirecionamento.** Um host público que devolve `302` para
    `http://169.254.169.254` contorna qualquer validação feita só na URL
    inicial. Por isso o seguimento de redirecionamento passa a ser manual, com
    revalidação a cada salto.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from app.config import settings

logger = logging.getLogger(__name__)

ESQUEMAS_PERMITIDOS = frozenset({"http", "https"})

# Portas de serviço web. Liberar portas arbitrárias transformaria o guarda em
# um scanner de serviços internos com retorno completo.
PORTAS_PERMITIDAS = frozenset({80, 443, 8080, 8443})

# Teto de saltos. Cinco cobre com folga o encadeamento DOI → editor → arquivo.
MAX_REDIRECIONAMENTOS = 5


class EgressBlocked(ValueError):
    """A URL de destino não passou pelo guarda de saída."""

    def __init__(self, url: str, motivo: str):
        self.url = url
        self.motivo = motivo
        super().__init__(f"Destino bloqueado ({motivo}): {url}")


@dataclass(frozen=True)
class DestinoValidado:
    """Resultado da validação: a URL e o IP que se deve efetivamente usar."""

    url: str
    host: str
    ip: str
    porta: int


def _ip_e_permitido(ip: ipaddress._BaseAddress) -> tuple[bool, str]:
    """
    O IP pode ser alcançado? Devolve `(permitido, motivo_da_recusa)`.

    A verificação é por propriedade do endereço, não por lista de faixas
    escritas à mão: `is_private` cobre 10/8, 172.16/12, 192.168/16 e os
    equivalentes IPv6 sem que ninguém precise lembrar de cada um.
    """
    if ip.is_loopback:
        return False, "loopback"
    if ip.is_link_local:
        # 169.254.0.0/16 — onde vivem os metadados de nuvem (AWS, GCP, Azure).
        return False, "link-local (metadados de nuvem)"
    if ip.is_private:
        return False, "rede privada"
    if ip.is_reserved or ip.is_multicast or ip.is_unspecified:
        return False, "faixa reservada"

    # IPv6 mapeando IPv4 (`::ffff:127.0.0.1`) contorna as checagens acima se
    # avaliado como IPv6 puro.
    mapeado = getattr(ip, "ipv4_mapped", None)
    if mapeado is not None:
        return _ip_e_permitido(mapeado)

    return True, ""


# Ponto de injeção da resolução de nomes.
#
# Os testes de unidade do resolvedor de PDF usam `httpx.MockTransport` com
# hosts fictícios: o transporte é falso, então o DNS também precisa ser. A
# suíte de segurança (`test_egress_guard.py`) exercita a resolução real — é lá
# que o comportamento de produção é verificado, não aqui.
_resolver_enderecos = socket.getaddrinfo


def _e_loopback(endereco: str) -> bool:
    """O IP resolvido é loopback?"""
    try:
        return ipaddress.ip_address(endereco).is_loopback
    except ValueError:
        return False


def _loopback_liberado() -> bool:
    """
    Loopback é destino legítimo em um caso só: LLM local (Ollama, LM Studio)
    no perfil desktop. No perfil `server` isso não vale — lá o loopback é a
    rede interna de quem hospeda, não a máquina do usuário.
    """
    if settings.is_server_profile:
        return False
    return settings.allow_private_egress


def validar_url(url: str, *, permitir_loopback: Optional[bool] = None) -> DestinoValidado:
    """
    Valida uma URL de saída e devolve o destino com o IP já resolvido.

    Levanta `EgressBlocked` com o motivo — que o chamador deve tratar como
    categoria, não repassar cru ao cliente (§29.5.4).
    """
    if not url or not url.strip():
        raise EgressBlocked(url or "", "URL vazia")

    try:
        partes = urlparse(url.strip())
    except ValueError as exc:
        raise EgressBlocked(url, f"URL inválida: {exc}") from exc

    esquema = (partes.scheme or "").lower()
    if esquema not in ESQUEMAS_PERMITIDOS:
        # `file://`, `gopher://`, `ftp://` — leitura de disco e protocolos que
        # servem para contrabandear requisição, não para buscar artigo.
        raise EgressBlocked(url, f"esquema não permitido: {esquema or '(ausente)'}")

    host = partes.hostname
    if not host:
        raise EgressBlocked(url, "host ausente")

    porta = partes.port or (443 if esquema == "https" else 80)
    liberar_loopback = _loopback_liberado() if permitir_loopback is None else permitir_loopback

    # A resolução vem antes da regra de porta de propósito: o LLM local escuta
    # em porta arbitrária (Ollama em 11434, LM Studio em 1234), e aplicar o
    # teto de portas antes de saber que o destino é loopback inviabilizaria o
    # caso legítimo. Para destino externo — o que importa contra varredura — a
    # regra continua valendo, verificada logo abaixo.
    destino = resolver_e_validar(url, host, porta, permitir_loopback=liberar_loopback)

    if not _e_loopback(destino.ip) and porta not in PORTAS_PERMITIDAS:
        raise EgressBlocked(url, f"porta não permitida: {porta}")

    return destino


def resolver_e_validar(
    url: str, host: str, porta: int, *, permitir_loopback: bool = False
) -> DestinoValidado:
    """
    Resolve o host e valida **todos** os endereços devolvidos.

    Validar só o primeiro deixaria passar um nome que resolve para um endereço
    público e outro interno — o resolvedor pode entregar qualquer um deles na
    hora de conectar.
    """
    try:
        infos = _resolver_enderecos(host, porta, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise EgressBlocked(url, f"host não resolvido: {exc.strerror or exc}") from exc

    if not infos:
        raise EgressBlocked(url, "host sem endereço")

    primeiro_ip: Optional[str] = None
    for info in infos:
        endereco = info[4][0]
        try:
            ip = ipaddress.ip_address(endereco)
        except ValueError:
            raise EgressBlocked(url, f"endereço inválido: {endereco}") from None

        permitido, motivo = _ip_e_permitido(ip)
        if not permitido:
            if permitir_loopback and ip.is_loopback:
                # Único caso legítimo: LLM local no perfil desktop.
                pass
            else:
                raise EgressBlocked(url, motivo)

        if primeiro_ip is None:
            primeiro_ip = endereco

    assert primeiro_ip is not None
    return DestinoValidado(url=url, host=host, ip=primeiro_ip, porta=porta)


def url_e_permitida(url: str, *, permitir_loopback: Optional[bool] = None) -> bool:
    """Versão booleana, para filtrar listas de candidatos sem tratar exceção."""
    try:
        validar_url(url, permitir_loopback=permitir_loopback)
        return True
    except EgressBlocked:
        return False


# ── Categorias para a trilha de auditoria (§29.5.4) ───────────────────

CATEGORIAS = {
    "ok": "ok",
    "bloqueado": "bloqueado",
    "nao_encontrado": "nao_encontrado",
    "nao_e_pdf": "nao_e_pdf",
    "tempo_esgotado": "tempo_esgotado",
    "erro": "erro",
}

# Provedores acadêmicos conhecidos. Para estes, a trilha detalhada continua
# sendo devolvida ao usuário: é informação de diagnóstico legítima, e o host
# não é segredo. Para qualquer outro, no perfil `server`, sai só a categoria —
# do contrário a própria mensagem de erro vira um scanner com retorno.
HOSTS_ACADEMICOS_CONHECIDOS = (
    "doi.org", "arxiv.org", "scielo.br", "scielo.org", "ncbi.nlm.nih.gov",
    "europepmc.org", "api.crossref.org", "api.openalex.org", "api.unpaywall.org",
    "api.semanticscholar.org", "pubmed.ncbi.nlm.nih.gov", "bdtd.ibict.br",
    "link.springer.com", "onlinelibrary.wiley.com", "sciencedirect.com",
    "tandfonline.com", "nature.com", "plos.org", "frontiersin.org", "mdpi.com",
)


def host_e_academico_conhecido(url: str) -> bool:
    """O host pertence a um provedor acadêmico reconhecido?"""
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    if not host:
        return False
    return any(host == conhecido or host.endswith(f".{conhecido}") for conhecido in HOSTS_ACADEMICOS_CONHECIDOS)


def detalhe_publico(url: str, detalhe: str) -> str:
    """
    Reduz o detalhe de uma tentativa ao que pode sair para o cliente.

    No perfil `server`, host desconhecido só recebe a categoria: sem isso, a
    correção do SSRF ainda deixaria o atacante aprender pela mensagem de erro
    o que não conseguiu alcançar.
    """
    if not settings.is_server_profile:
        return detalhe
    if host_e_academico_conhecido(url):
        return detalhe
    return "Destino não elegível ou indisponível."
