#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Configuração da Aplicação.
Utiliza Pydantic BaseSettings para gerenciamento centralizado de configurações
com suporte a variáveis de ambiente e valores padrão.
"""

from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import platformdirs
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode


class DeploymentProfile(str, Enum):
    """
    Perfil de exposição em que o backend está rodando (doc 29 §29.2).

    O Revsist nasceu assumindo que o único cliente era o Electron na mesma
    máquina. Quando o `server_launcher.py` passou a publicar o backend na
    internet, essa premissa deixou de valer sem que nada no código soubesse.
    O perfil torna o perímetro explícito: todo controle de segurança deriva
    dele, em vez de suposição implícita.
    """

    DESKTOP = "desktop"   # Electron ou navegador local falando com loopback
    SERVER = "server"     # publicado (túnel, rede local, Netlify)
    CI = "ci"             # testes automatizados


class Settings(BaseSettings):
    """Configurações globais da aplicação Revsist."""

    # ── Identificação ─────────────────────────────────────────────────
    #
    # O produto chama-se **Revsist**. `app_name` continua "RSAC" de propósito:
    # ele não é o nome do produto, é a **chave do armazenamento** — alimenta
    # `platformdirs.user_data_dir` mais abaixo, e portanto o caminho onde o
    # banco e os PDFs de quem já usa o programa estão gravados. Trocá-lo faria
    # essas pessoas abrirem o app e não encontrarem o próprio acervo.
    #
    # O nome visível vive em `display_name`; a decisão está registrada em
    # `brand/IDENTIDADE_VISUAL.md`.
    app_name: str = "RSAC"
    display_name: str = "Revsist"

    # Pasta de dados escolhida à mão. Vazio = o padrão do sistema, calculado
    # por `platformdirs` na propriedade `data_dir` mais abaixo.
    #
    # `scripts/launcher.py` lê `RSAC_DATA_DIR` desde sempre para achar o token
    # local; o backend a ignorava, e portanto os dois lados podiam discordar
    # sobre onde os dados estão — o launcher procurando numa pasta e o backend
    # gravando noutra. O `validation_alias` fixa o nome literal da variável,
    # sem o prefixo `RSAC_` da classe, que aqui duplicaria o `RSAC_`.
    data_dir_configurado: str = Field(
        "",
        validation_alias=AliasChoices("RSAC_DATA_DIR", "data_dir_configurado"),
    )
    app_version: str = "2.0.0"
    debug: bool = False

    # ── Perímetro de confiança ────────────────────────────────────────
    deployment_profile: DeploymentProfile = DeploymentProfile.DESKTOP

    # ── Rede de saída (doc 29 §29.5.3) ────────────────────────────────
    # Libera destinos em loopback para o caso legítimo do LLM local
    # (Ollama, LM Studio). Ignorado no perfil `server`, onde loopback é a rede
    # interna de quem hospeda, não a máquina do usuário.
    allow_private_egress: bool = True

    # Limites de recurso (doc 29 §29.7, doc 40 §40.7.5, doc 43 §43.17, O-25, O-26)
    max_upload_mb: int = 50
    max_account_storage_mb: int = 5120  # 5 GB por conta
    max_projects_per_user: int = 20     # 20 projetos por conta
    max_papers_per_project: int = 20000 # 20.000 papers por projeto
    max_members_per_project: int = 15   # 15 membros por projeto (doc 43 §43.17)
    max_active_invitations_per_project: int = 20  # 20 convites ativos por projeto
    project_invitation_expiry_days: int = 14      # Validade do convite de equipe (dias)
    rate_limit_enabled: bool = True

    # Hosts aceitos no cabeçalho `Host` (perfil `server`). Vazio = sem
    # restrição, porque o nome do túnel Cloudflare muda a cada execução e
    # exigir configuração aqui inviabilizaria o uso normal.
    trusted_hosts: Annotated[list[str], NoDecode] = []

    # ── Chave-mestra da cifra de segredos (doc 29 §29.4.1) ────────────
    # Obrigatória no perfil `server`: lá um arquivo de chave ao lado do banco
    # seria lido pela mesma falha que leria o banco. Fora do `server`, a
    # ausência faz o backend gerar `<data_dir>/master.key` com permissão 0600.
    secret_key: Optional[str] = None

    # ── Entrada com Google (doc 40 §40.4) ─────────────────────────────
    # Vazias desativam o login com Google; o backend continua subindo, e a tela
    # de login mostra apenas as vias disponíveis. É o que mantém o perfil
    # `desktop` — que entra pelo token local — sem nenhuma configuração extra.
    google_client_id: str = ""
    google_client_secret: str = ""
    # Endereço público do serviço, usado para montar o `redirect_uri` do OAuth.
    # Precisa coincidir **exatamente** com o cadastrado no Google Cloud.
    public_base_url: str = ""
    # Lista de admissão do autocadastro: domínios (`@usp.br`) ou endereços
    # completos, separados por vírgula. Vazia = qualquer conta Google entra.
    # É o modo "por convite" da v1, sem escrever código de convite.
    signup_allowlist: str = ""
    # Versão do Aviso de Privacidade e dos Termos vigente, registrada no aceite.
    terms_version: str = "2026-08"

    # ── Sessões (doc 29 §29.3.3) ──────────────────────────────────────
    # Validade da sessão, renovada por atividade: quem está triando não é
    # deslogado no meio do trabalho, mas uma aba esquecida aberta expira.
    session_ttl_hours: int = 12

    # ── Servidor ──────────────────────────────────────────────────────
    host: str = "127.0.0.1"
    port: int = 8000

    # ── Banco de Dados ────────────────────────────────────────────────
    database_url: Optional[str] = None

    # ── CORS ──────────────────────────────────────────────────────────
    # Origens extras autorizadas no perfil `server`. Aceita lista JSON ou
    # valores separados por vírgula em RSAC_CORS_ORIGINS. No perfil `desktop`
    # o loopback já é liberado por `cors_allow_origin_regex`.
    cors_origins: Annotated[list[str], NoDecode] = []

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

    # ── Perímetro derivado do perfil ──────────────────────────────────

    @field_validator("cors_origins", "trusted_hosts", mode="before")
    @classmethod
    def _lista_separada_por_virgula(cls, valor):
        """
        Aceita `a,b` além de `["a","b"]` nas listas vindas do ambiente.

        Sem isto, `RSAC_CORS_ORIGINS=https://rsac.exemplo.br` — que é a forma
        que qualquer pessoa escreve num arquivo `.env` — derruba a partida com
        `error parsing value for field "cors_origins"`, uma mensagem que não
        diz o que ela quer. O comentário destes campos já prometia as duas
        formas; o que faltava era cumprir.

        O `NoDecode` nas anotações é a metade indispensável: sem ele o
        pydantic-settings tenta desserializar JSON **antes** de qualquer
        validador, e a exceção acontece longe daqui.
        """
        import json

        if isinstance(valor, str):
            texto = valor.strip()
            if not texto:
                return []
            if texto.startswith("["):
                return json.loads(texto)
            return [parte.strip() for parte in texto.split(",") if parte.strip()]
        return valor

    @property
    def is_server_profile(self) -> bool:
        """Verdadeiro quando o backend está publicado fora do loopback."""
        return self.deployment_profile is DeploymentProfile.SERVER

    @property
    def cors_allow_origin_regex(self) -> Optional[str]:
        """
        Regex de origem permitida — apenas loopback, e apenas fora do perfil
        `server`. A porta é variável (Vite escolhe a que estiver livre), por
        isso o regex; o que ele não faz é aceitar host arbitrário.

        Sobre o `null`
        ==============
        O app empacotado carrega a interface de um arquivo em disco, e nenhum
        navegador manda `Origin: file://` — todos mandam a origem opaca
        `null`. O `file://` que estava aqui portanto nunca casou com nada, e a
        consequência era severa: no app instalado **toda** chamada da API era
        barrada pelo navegador antes de chegar ao Python. Verificado carregando
        uma página `file://` no Chromium contra o backend real; a resposta ao
        `Origin: null` era `400 Disallowed CORS origin`.

        A concessão é limitada porque `null` também é a origem de iframes em
        sandbox e de `data:` — ou seja, uma página hostil consegue apresentá-la.
        O que ela não consegue é se autenticar: o cookie de sessão é
        `SameSite=Strict` e não acompanha requisição de outro site, e o token
        local viaja em cabeçalho próprio, lido de um arquivo `0600` fora do
        alcance do navegador. Quem chegar por essa via leva 401. E nada disso
        vale no perfil `server`, onde o `return None` acima corta antes.
        """
        if self.is_server_profile:
            return None
        return r"^(https?://(localhost|127\.0\.0\.1)(:\d+)?|null)$"

    @property
    def effective_cors_origins(self) -> list[str]:
        """Lista finita de origens autorizadas, derivada do perfil."""
        if self.deployment_profile is DeploymentProfile.CI:
            return ["http://testserver"]
        return [o.strip().rstrip("/") for o in self.cors_origins if o and o.strip()]

    @property
    def google_login_enabled(self) -> bool:
        """Há credencial de aplicativo configurada para o Google?"""
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def dominios_admitidos(self) -> list[str]:
        """Lista de admissão do autocadastro, normalizada."""
        return [
            item.strip().lower()
            for item in self.signup_allowlist.split(",")
            if item.strip()
        ]

    @property
    def expose_api_docs(self) -> bool:
        """A documentação OpenAPI mapeia a API inteira — fechada quando exposta."""
        return not self.is_server_profile

    @property
    def data_dir(self) -> Path:
        """
        Diretório de dados da aplicação.

        Atenção ao que `platformdirs` devolve no Windows: sem `appauthor`, ele
        usa o próprio `appname` como autor e **duplica o nome** —
        `%LOCALAPPDATA%\\RSAC\\RSAC`, não `%LOCALAPPDATA%\\RSAC`. Quem
        reescreveu esse caminho à mão do lado do cliente errou por um nível, e
        o app não achava o token que o backend acabara de gravar. Por isso o
        caminho é anunciado em `local_token.descrever_para_log`, em vez de ser
        deduzido de novo em cada linguagem.
        """
        bruto = self.data_dir_configurado.strip()
        path = Path(bruto).expanduser() if bruto else Path(platformdirs.user_data_dir(self.app_name))
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
