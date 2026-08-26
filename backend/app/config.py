#!/usr/bin/env python

"""
RSAC V2 — Configuração da Aplicação.
Utiliza Pydantic BaseSettings para gerenciamento centralizado de configurações
com suporte a variáveis de ambiente e valores padrão.
"""

from pathlib import Path

import platformdirs
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configurações globais da aplicação RSAC V2.

    O perímetro é fixo: **o backend só atende em loopback, na máquina de quem
    o instalou**. Havia aqui um `DeploymentProfile` com três valores — desktop,
    server e ci — que existia porque o backend também podia ser publicado por
    túnel, e todo controle de segurança derivava dele. Com a publicação
    removida, o enum passaria a ter um valor real só; o que era um perímetro
    variável virou uma premissa, e uma premissa não precisa de configuração
    para ser declarada.
    """

    # ── Identificação ─────────────────────────────────────────────────
    app_name: str = "RSAC"
    app_version: str = "2.0.0"
    debug: bool = False

    # ── Rede de saída (doc 29 §29.5.3) ────────────────────────────────
    # Libera destinos em loopback para o caso legítimo do LLM local
    # (Ollama, LM Studio).
    allow_private_egress: bool = True

    # Limites de recurso (doc 29 §29.7)
    max_upload_mb: int = 100
    rate_limit_enabled: bool = True

    # ── Chave-mestra da cifra de segredos (doc 29 §29.4.1) ────────────
    # Obrigatória no perfil `server`: lá um arquivo de chave ao lado do banco
    # seria lido pela mesma falha que leria o banco. Fora do `server`, a
    # ausência faz o backend gerar `<data_dir>/master.key` com permissão 0600.
    secret_key: str | None = None

    # ── Servidor ──────────────────────────────────────────────────────
    host: str = "127.0.0.1"
    port: int = 8000

    # ── Pasta de dados ────────────────────────────────────────────────
    # Onde ficam banco, PDFs, logs, `master.key` e `runtime_token`. Vazio
    # significa "a pasta padrão do sistema operacional" (via platformdirs),
    # que é o caminho normal do app de mesa.
    #
    # O override é a única forma de tirar a revisão da pasta padrão do sistema
    # — para pô-la noutro disco, ou numa pasta sincronizada. Quem define a
    # variável manda; o backend não escolhe outro lugar por conta própria,
    # porque isso partiria a revisão em duas instalações sem ninguém notar.
    data_dir_override: Path | None = Field(default=None, validation_alias="RSAC_DATA_DIR")

    # ── Banco de Dados ────────────────────────────────────────────────
    database_url: str | None = None

    # ── Aquisição de PDFs ─────────────────────────────────────────────
    # E-mail de contato usado nas APIs acadêmicas de acesso aberto.
    # Unpaywall o exige; OpenAlex e Crossref dão prioridade de fila
    # ("polite pool") a quem se identifica. Sem ele, a via Unpaywall é pulada.
    contact_email: str = ""
    # Tempo total (s) de busca por trabalho, somando todas as vias tentadas.
    pdf_search_timeout: float = 120.0
    # Tempo (s) de cada requisição isolada durante a busca.
    pdf_request_timeout: float = 25.0
    # Trabalhos buscados simultaneamente na aquisição em lote.
    pdf_batch_concurrency: int = 3

    # ── Contexto de IA ────────────────────────────────────────────────
    # Orçamento de caracteres do texto do estudo enviado à IA na extração.
    # ~28k caracteres ≈ 7–9k tokens, folgado para janelas de 32k em diante.
    ai_context_budget_chars: int = 28000

    # ── Origens autorizadas ───────────────────────────────────────────

    @property
    def cors_allow_origin_regex(self) -> str:
        """
        Regex das origens que podem falar com a API.

        Só loopback e a origem opaca do app empacotado. A porta é variável (o
        Electron sorteia uma a cada execução, e o Vite escolhe a que estiver
        livre), por isso o regex; o que ele não faz é aceitar host arbitrário.

        `null` é o que o Chromium envia quando a página vem de `file://` — o
        caso do app instalado, onde o Electron carrega o `index.html` do disco.
        A entrada `file://` que existia aqui nunca chegou a casar com nada: o
        navegador não manda o esquema, manda a palavra `null`, e por isso
        **toda** chamada da API era barrada no app instalado. As duas ficam:
        `file://` para clientes que a enviem, `null` para o Chromium.

        Um sítio hostil também consegue produzir origem `null`, via iframe em
        sandbox — e o que o detém não é a origem, é a credencial: a API só
        responde a quem apresentar o token do arquivo `runtime_token`, que só o
        dono da máquina consegue ler. Sem ele, o que se alcança por essa via é
        401 em tudo, menos `/health` e `/auth/status`, que não expõem dado de
        revisão.
        """
        return r"^(https?://(localhost|127\.0\.0\.1)(:\d+)?|file://|null)$"

    @property
    def data_dir(self) -> Path:
        """
        Diretório de dados da aplicação.

        `RSAC_DATA_DIR` tem precedência; sem ela, a pasta padrão do sistema.
        A ordem importa: quem fixa a variável está dizendo onde os dados devem
        estar, e mudar isso por conta própria separaria a revisão em duas
        instalações sem que o usuário percebesse.
        """
        path = self.data_dir_override or Path(platformdirs.user_data_dir(self.app_name))
        path = Path(path).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def database_path(self) -> Path:
        """Caminho do banco SQLite."""
        return self.data_dir / "rsac.db"

    @property
    def pdf_storage_dir(self) -> Path:
        """Diretório de armazenamento de PDFs locais."""
        path = self.data_dir / "pdfs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def effective_database_url(self) -> str:
        """URL efetiva do banco (permite override via env ou argumento)."""
        if self.database_url:
            return self.database_url
        return f"sqlite:///{self.database_path}"

    model_config = {
        "env_prefix": "RSAC_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


# Singleton de configuração
settings = Settings()
