# ==============================================================================
# Revsist Backend — Dockerfile Multi-Stage de Produção
# ==============================================================================
# 
# Estágio 1 (builder): Instala compiladores e dependências em virtualenv isolado.
# Estágio 2 (runner):  Imagem slim mínima sem compiladores, executando como
#                     usuário não-privilegiado (appuser, UID 1000) com HEALTHCHECK.
# ==============================================================================

# ── Estágio 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Dependências de compilação temporárias
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Criação do virtualenv isolado
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml .
# Instalação das dependências de produção
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# ── Estágio 2: Runner de Produção ─────────────────────────────────────────────
FROM python:3.12-slim AS runner

# Metadados da imagem
LABEL maintainer="Eduardo Matheus Figueira <contato@revsist.org>"
LABEL description="Revsist Backend API — Revisão Sistemática Assistida por Computador"

# Dependências mínimas de runtime (curl para o HEALTHCHECK)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Criação de usuário sem privilégios (princípio do menor privilégio)
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -s /bin/bash -m appuser

# Copiar virtualenv pronto do estágio builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    RSAC_DEPLOYMENT_PROFILE=server \
    RSAC_DATA_DIR=/data

WORKDIR /app

# Criar diretório de dados persistentes e ajustar propriedade
RUN mkdir -p /data/logs /data/pdfs && \
    chown -R appuser:appuser /data /app

# Copiar código-fonte da aplicação
COPY --chown=appuser:appuser app /app/app
COPY --chown=appuser:appuser alembic /app/alembic
COPY --chown=appuser:appuser alembic.ini /app/alembic.ini
COPY --chown=appuser:appuser pyproject.toml /app/pyproject.toml

# Executar como usuário appuser (não-root)
USER appuser

# Expor a porta interna da API (8000)
EXPOSE 8000

# Healthcheck nativo
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Comando de inicialização em produção:
# NOTA CRÍTICA (§40.6): uvicorn roda com --workers 1. Estados em memória
# (HarvestJobManager, WebSocketManager, RateLimiter) exigem processo único.
# A concorrência assíncrona do FastAPI/anyio atende o tráfego com alta eficiência.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
