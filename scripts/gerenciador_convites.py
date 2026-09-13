#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Revsist — Gerenciador Interativo de Convites de Acesso.

Inicia um servidor local ultrarrápido com interface gráfica web embutida
para gerar, inspecionar, validar e revogar códigos de convite diretamente
no banco de dados SQLite do Revsist (rsac.db).
"""

import json
import os
import secrets
import socket
import sys
import urllib.parse
import webbrowser
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Ajustar caminho para importar a camada de banco do backend
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from app.config import settings
    from app.database import SessionLocal, engine
    from app.infrastructure.persistence.models import (
        FeedbackModel,
        InviteCodeModel,
        InviteRequestModel,
        UserModel,
        as_utc,
        generate_uuid,
    )
    from app.schema import aplicar_migracoes
except ImportError as err:
    print(f"[ERRO] Não foi possível importar os módulos do Revsist: {err}", file=sys.stderr)
    print("Certifique-se de executar com o ambiente virtual do backend (.venv).", file=sys.stderr)
    sys.exit(1)


def gerar_codigo_formatado(custom: str = "") -> str:
    """Gera código no formato RSAC-XXXX-XXXX ou higieniza código customizado."""
    if custom and custom.strip():
        cod = custom.strip().upper()
        if not cod.startswith("RSAC-"):
            cod = f"RSAC-{cod}"
        return cod
    p1 = secrets.token_hex(2).upper()
    p2 = secrets.token_hex(2).upper()
    return f"RSAC-{p1}-{p2}"


def formatar_data_br(dt: datetime | None) -> str:
    if not dt:
        return "Sem expiração"
    dt_utc = as_utc(dt)
    return dt_utc.strftime("%d/%m/%Y às %H:%M UTC")


def calcular_tempo_relativo(dt: datetime | None) -> str:
    if not dt:
        return "Permanente"
    agora = datetime.now(timezone.utc)
    dt_utc = as_utc(dt)
    diff = dt_utc - agora

    if diff.total_seconds() > 0:
        dias = diff.days
        horas = int(diff.seconds // 3600)
        minutos = int((diff.seconds % 3600) // 60)
        if dias > 0:
            return f"em {dias}d {horas}h"
        elif horas > 0:
            return f"em {horas}h {minutos}m"
        else:
            return f"em {max(1, minutos)} min"
    else:
        diff_passada = agora - dt_utc
        dias = diff_passada.days
        horas = int(diff_passada.seconds // 3600)
        if dias > 0:
            return f"expirou há {dias}d"
        elif horas > 0:
            return f"expirou há {horas}h"
        else:
            return "expirou há poucos minutos"


def obter_status_convite(c: InviteCodeModel) -> tuple[str, str]:
    """Retorna (status_chave, status_rotulo)."""
    agora = datetime.now(timezone.utc)
    if c.is_revoked:
        return "revogado", "Revogado"
    elif c.is_used:
        return "utilizado", "Utilizado"
    elif c.expires_at and as_utc(c.expires_at) < agora:
        return "expirado", "Expirado"
    else:
        return "disponivel", "Disponível"


def serializar_convite(c: InviteCodeModel, db) -> dict:
    chave, rotulo = obter_status_convite(c)
    usuario_info = None
    if c.used_by_user_id:
        u = db.query(UserModel).filter(UserModel.id == c.used_by_user_id).first()
        if u:
            usuario_info = {
                "id": u.id,
                "username": u.username,
                "email": u.email or "",
            }

    return {
        "id": c.id,
        "code": c.code,
        "status": chave,
        "status_label": rotulo,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "created_at_br": formatar_data_br(c.created_at),
        "expires_at": c.expires_at.isoformat() if c.expires_at else None,
        "expires_at_br": formatar_data_br(c.expires_at),
        "tempo_relativo": calcular_tempo_relativo(c.expires_at),
        "is_used": c.is_used,
        "used_at": c.used_at.isoformat() if c.used_at else None,
        "used_at_br": formatar_data_br(c.used_at) if c.used_at else None,
        "used_by": usuario_info,
        "is_revoked": c.is_revoked,
        "note": c.note or "",
    }


ROTULO_STATUS_PEDIDO = {
    "pendente": "Aguardando resposta",
    "aprovado": "Aprovado",
    "recusado": "Recusado",
}


def serializar_solicitacao(s: InviteRequestModel) -> dict:
    return {
        "id": s.id,
        "nome": s.nome,
        "email": s.email,
        "telefone": s.telefone,
        "onde_conheceu": s.onde_conheceu,
        "instituicao": s.instituicao or "",
        "status": s.status,
        "status_label": ROTULO_STATUS_PEDIDO.get(s.status, s.status),
        "created_at_br": formatar_data_br(s.created_at),
        "responded_at_br": formatar_data_br(s.responded_at) if s.responded_at else None,
        "invite_code_generated": s.invite_code_generated,
        "admin_notes": s.admin_notes or "",
    }


# ── Feedback do beta ──────────────────────────────────────────────────
#
# A mesma fila da aba "Feedback do beta" do painel do aplicativo, lida direto
# do banco. O que o botão do canto inferior direito envia chega aqui.

ROTULO_TIPO_FEEDBACK = {
    "problema": "Problema",
    "sugestao": "Sugestão",
    "elogio": "Elogio",
    "outro": "Outro",
}

ROTULO_STATUS_FEEDBACK = {
    "novo": "Novo",
    "em_andamento": "Em andamento",
    "resolvido": "Resolvido",
    "arquivado": "Arquivado",
}


def serializar_feedback(f: FeedbackModel, autor: UserModel | None) -> dict:
    nome = ""
    if autor:
        nome = (autor.full_name or autor.display_name or autor.username or "").strip()
    return {
        "id": f.id,
        "tipo": f.tipo,
        "tipo_label": ROTULO_TIPO_FEEDBACK.get(f.tipo, f.tipo),
        "mensagem": f.mensagem,
        "pagina": f.pagina or "",
        "navegador": f.navegador or "",
        "versao": f.versao or "",
        "status": f.status,
        "status_label": ROTULO_STATUS_FEEDBACK.get(f.status, f.status),
        "created_at_br": formatar_data_br(f.created_at),
        "admin_notes": f.admin_notes or "",
        "autor_nome": nome or "Conta removida",
        "autor_usuario": autor.username if autor else "",
        "autor_email": (autor.email or "") if autor else "",
    }


HTML_PAGE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Revsist — Gerenciador de Convites</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <style>
    :root {
      --bg-primary: #f6f8fa;
      --bg-secondary: #eef2f6;
      --bg-surface: #ffffff;
      --dusk-blue: #152940;
      --steel-blue: #274c77;
      --accent-soft: #6096ba;
      --accent-subtle: #e3edf5;
      --border: #d4e0eb;
      --border-subtle: #e6edf3;
      --text-main: #14213d;
      --text-muted: #536471;
      --text-light: #7c8ba1;
      --badge-green-bg: #d4edda;
      --badge-green-text: #155724;
      --badge-green-border: #c3e6cb;
      --badge-blue-bg: #cce5ff;
      --badge-blue-text: #004085;
      --badge-blue-border: #b8daff;
      --badge-orange-bg: #fff3cd;
      --badge-orange-text: #856404;
      --badge-orange-border: #ffeeba;
      --badge-red-bg: #f8d7da;
      --badge-red-text: #721c24;
      --badge-red-border: #f5c6cb;
      --radius: 8px;
      --radius-sm: 5px;
      --shadow: 0 4px 12px rgba(21, 41, 64, 0.06);
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      --font-mono: "JetBrains Mono", "Cascadia Code", Consolas, "Courier New", monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background-color: var(--bg-primary);
      color: var(--text-main);
      font-family: var(--font-sans);
      line-height: 1.5;
      padding-bottom: 3rem;
      -webkit-font-smoothing: antialiased;
    }

    /* Cabeçalho */
    header.top-nav {
      background: var(--dusk-blue);
      color: #fff;
      padding: 1rem 1.5rem;
      border-bottom: 2px solid var(--steel-blue);
      box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }
    .top-container {
      max-width: 1180px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 1rem;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .brand-title {
      font-size: 1.25rem;
      font-weight: 700;
      letter-spacing: -0.02em;
    }
    .brand-badge {
      background: rgba(255,255,255,0.15);
      font-size: 0.75rem;
      padding: 0.15rem 0.5rem;
      border-radius: var(--radius-sm);
      font-family: var(--font-mono);
      font-weight: 600;
    }
    .db-status {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.8125rem;
      color: #cbd5e1;
      background: rgba(0,0,0,0.25);
      padding: 0.35rem 0.75rem;
      border-radius: 20px;
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #22c55e;
      box-shadow: 0 0 6px #22c55e;
    }

    /* Layout Principal */
    .container {
      max-width: 1180px;
      margin: 1.5rem auto;
      padding: 0 1.25rem;
    }

    /* Métricas */
    .metrics-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1rem;
      margin-bottom: 1.5rem;
    }
    .metric-card {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.1rem;
      box-shadow: var(--shadow);
    }
    .metric-card .label {
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-muted);
      margin-bottom: 0.35rem;
      font-weight: 600;
    }
    .metric-card .value {
      font-size: 1.85rem;
      font-weight: 700;
      color: var(--dusk-blue);
      line-height: 1.1;
      font-family: var(--font-mono);
    }

    /* Grid de Ações: Gerador + Validador */
    .action-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
      margin-bottom: 2rem;
    }
    @media (max-width: 840px) {
      .action-grid { grid-template-columns: 1fr; }
    }

    .card {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.5rem;
      box-shadow: var(--shadow);
    }
    .card-header {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      margin-bottom: 1.25rem;
      padding-bottom: 0.75rem;
      border-bottom: 1px solid var(--border-subtle);
    }
    .card-title {
      font-size: 1.1rem;
      font-weight: 700;
      color: var(--dusk-blue);
    }
    .card-subtitle {
      font-size: 0.8125rem;
      color: var(--text-muted);
      margin-top: 0.15rem;
    }

    /* Formulários */
    .form-group {
      margin-bottom: 1.1rem;
    }
    label {
      display: block;
      font-size: 0.8125rem;
      font-weight: 600;
      margin-bottom: 0.4rem;
      color: var(--text-main);
    }
    input[type="text"], input[type="number"], select {
      width: 100%;
      padding: 0.65rem 0.85rem;
      font-size: 0.9375rem;
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      background: #fafbfd;
      color: var(--text-main);
      outline: none;
      transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    input[type="text"]:focus, input[type="number"]:focus, select:focus {
      border-color: var(--steel-blue);
      box-shadow: 0 0 0 3px rgba(39, 76, 119, 0.15);
      background: #fff;
    }

    /* Pílulas de expiração */
    .preset-pills {
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
      margin-top: 0.35rem;
    }
    .pill {
      background: var(--bg-secondary);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 0.35rem 0.85rem;
      font-size: 0.8125rem;
      cursor: pointer;
      font-weight: 500;
      color: var(--text-muted);
      transition: all 0.15s ease;
    }
    .pill:hover {
      border-color: var(--steel-blue);
      color: var(--steel-blue);
    }
    .pill.active {
      background: var(--steel-blue);
      color: #fff;
      border-color: var(--steel-blue);
      font-weight: 600;
    }

    .custom-time-row {
      display: none;
      gap: 0.5rem;
      margin-top: 0.6rem;
    }
    .custom-time-row.show {
      display: flex;
    }

    /* Botões */
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      padding: 0.65rem 1.25rem;
      font-size: 0.9375rem;
      font-weight: 600;
      border-radius: var(--radius-sm);
      border: none;
      cursor: pointer;
      transition: all 0.15s ease;
      text-decoration: none;
    }
    .btn-primary {
      background: var(--steel-blue);
      color: #fff;
    }
    .btn-primary:hover {
      background: var(--dusk-blue);
    }
    .btn-secondary {
      background: var(--bg-secondary);
      color: var(--text-main);
      border: 1px solid var(--border);
    }
    .btn-secondary:hover {
      background: #e2e8f0;
    }
    .btn-sm {
      padding: 0.35rem 0.7rem;
      font-size: 0.775rem;
    }
    .btn-danger-sm {
      background: var(--badge-red-bg);
      color: var(--badge-red-text);
      border: 1px solid var(--badge-red-border);
      padding: 0.25rem 0.55rem;
      font-size: 0.75rem;
    }
    .btn-danger-sm:hover {
      background: #f1b0b7;
    }

    /* Card de Sucesso / Código Gerado */
    .generated-box {
      display: none;
      margin-top: 1.25rem;
      padding: 1.25rem;
      background: var(--accent-subtle);
      border: 1px solid #b8daff;
      border-radius: var(--radius);
      animation: fadeIn 0.2s ease;
    }
    .code-display {
      font-family: var(--font-mono);
      font-size: 1.6rem;
      font-weight: 800;
      color: var(--dusk-blue);
      letter-spacing: 0.08em;
      margin: 0.4rem 0;
      user-select: all;
    }
    .copy-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-top: 0.75rem;
    }

    /* Card de Resultado da Validação */
    .validation-result {
      display: none;
      margin-top: 1.25rem;
      padding: 1.25rem;
      border-radius: var(--radius);
      border: 1px solid transparent;
      animation: fadeIn 0.2s ease;
    }
    .validation-result.disponivel {
      background: var(--badge-green-bg);
      color: var(--badge-green-text);
      border-color: var(--badge-green-border);
    }
    .validation-result.utilizado {
      background: var(--badge-blue-bg);
      color: var(--badge-blue-text);
      border-color: var(--badge-blue-border);
    }
    .validation-result.expirado {
      background: var(--badge-orange-bg);
      color: var(--badge-orange-text);
      border-color: var(--badge-orange-border);
    }
    .validation-result.revogado {
      background: var(--badge-red-bg);
      color: var(--badge-red-text);
      border-color: var(--badge-red-border);
    }
    .validation-result.invalido {
      background: #f3f4f6;
      color: #374151;
      border-color: #d1d5db;
    }

    /* Tabela de Convites */
    .table-section {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.5rem;
      box-shadow: var(--shadow);
    }
    .table-toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 1rem;
      margin-bottom: 1.25rem;
    }
    .filters-row {
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
    }
    .search-box {
      width: 240px;
    }
    .table-container {
      overflow-x: auto;
    }
    table.data-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.875rem;
    }
    table.data-table th, table.data-table td {
      padding: 0.75rem 0.85rem;
      text-align: left;
      border-bottom: 1px solid var(--border-subtle);
    }
    table.data-table th {
      background: var(--bg-secondary);
      font-weight: 600;
      color: var(--dusk-blue);
      font-size: 0.8125rem;
      letter-spacing: 0.02em;
    }
    table.data-table tr:hover td {
      background: #fafbfd;
    }

    .code-cell {
      font-family: var(--font-mono);
      font-weight: 700;
      letter-spacing: 0.04em;
      color: var(--steel-blue);
      white-space: nowrap;
    }

    /* Badges de Status */
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      font-size: 0.75rem;
      font-weight: 700;
      padding: 0.2rem 0.6rem;
      border-radius: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .badge-disponivel {
      background: var(--badge-green-bg);
      color: var(--badge-green-text);
      border: 1px solid var(--badge-green-border);
    }
    .badge-utilizado {
      background: var(--badge-blue-bg);
      color: var(--badge-blue-text);
      border: 1px solid var(--badge-blue-border);
    }
    .badge-expirado {
      background: var(--badge-orange-bg);
      color: var(--badge-orange-text);
      border: 1px solid var(--badge-orange-border);
    }
    .badge-revogado {
      background: var(--badge-red-bg);
      color: var(--badge-red-text);
      border: 1px solid var(--badge-red-border);
    }

    .user-info {
      font-size: 0.8125rem;
    }
    .user-name {
      font-weight: 600;
      color: var(--dusk-blue);
    }
    .user-email {
      color: var(--text-muted);
      font-size: 0.75rem;
    }

    /* Toast */
    #toast {
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      background: var(--dusk-blue);
      color: #fff;
      padding: 0.75rem 1.25rem;
      border-radius: var(--radius);
      box-shadow: 0 4px 14px rgba(0,0,0,0.25);
      font-size: 0.875rem;
      font-weight: 500;
      opacity: 0;
      transform: translateY(20px);
      transition: all 0.25s ease;
      pointer-events: none;
      z-index: 9999;
    }
    #toast.show {
      opacity: 1;
      transform: translateY(0);
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(-6px); }
      to { opacity: 1; transform: translateY(0); }
    }
  </style>
</head>
<body>

  <header class="top-nav">
    <div class="top-container">
      <div class="brand">
        <span class="brand-title">Revsist</span>
        <span class="brand-badge">Gestor de Convites</span>
      </div>
      <div class="db-status">
        <span class="status-dot"></span>
        <span id="db-path-label">rsac.db conectado</span>
      </div>
    </div>
  </header>

  <main class="container">

    <!-- Métricas -->
    <section class="metrics-row">
      <div class="metric-card">
        <div class="label">Total de Convites</div>
        <div class="value" id="m-total">0</div>
      </div>
      <div class="metric-card">
        <div class="label">Disponíveis para Uso</div>
        <div class="value" style="color: #15803d;" id="m-disponiveis">0</div>
      </div>
      <div class="metric-card">
        <div class="label">Já Utilizados</div>
        <div class="value" style="color: #1d4ed8;" id="m-utilizados">0</div>
      </div>
      <div class="metric-card">
        <div class="label">Expirados / Revogados</div>
        <div class="value" style="color: #b45309;" id="m-expirados">0</div>
      </div>
      <div class="metric-card">
        <div class="label">Pedidos Aguardando</div>
        <div class="value" style="color: #b91c1c;" id="m-pedidos">0</div>
      </div>
      <div class="metric-card">
        <div class="label">Feedback Novo</div>
        <div class="value" style="color: #7c3aed;" id="m-feedback">0</div>
      </div>
    </section>

    <!-- Grid: Gerador + Validador -->
    <section class="action-grid">

      <!-- GERADOR DE CONVITE -->
      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">Gerar Novo Convite</h2>
            <p class="card-subtitle">Crie um código de acesso de uso único para seu convidado</p>
          </div>
        </div>

        <form id="form-gerar">
          <div class="form-group">
            <label for="input-nota">Convidado / Destinatário (Nota)</label>
            <input type="text" id="input-nota" placeholder="Ex.: Profa. Dra. Elena (PPGDR), Avaliador da Banca...">
          </div>

          <div class="form-group">
            <label>Tempo de Expiração</label>
            <div class="preset-pills">
              <button type="button" class="pill" data-dias="1">24 horas</button>
              <button type="button" class="pill" data-dias="3">3 dias</button>
              <button type="button" class="pill" data-dias="7">7 dias</button>
              <button type="button" class="pill active" data-dias="14">14 dias (Recomendado)</button>
              <button type="button" class="pill" data-dias="30">30 dias</button>
              <button type="button" class="pill" data-dias="0">Sem expiração</button>
              <button type="button" class="pill" data-dias="custom">Personalizado...</button>
            </div>
            <div class="custom-time-row" id="custom-time-box">
              <input type="number" id="custom-dias" min="1" max="365" placeholder="Número de dias">
              <input type="number" id="custom-horas" min="0" max="23" placeholder="Horas extras">
            </div>
          </div>

          <div class="form-group">
            <label for="input-custom-code">Código Personalizado (Opcional)</label>
            <input type="text" id="input-custom-code" placeholder="Deixe em branco para gerar aleatório RSAC-XXXX-XXXX">
          </div>

          <button type="submit" class="btn btn-primary" style="width: 100%;">
            🎟️ Gerar Código de Convite
          </button>
        </form>

        <div class="generated-box" id="box-sucesso">
          <p style="font-size: 0.8125rem; font-weight: 600; color: var(--steel-blue);">CONVITE GERADO COM SUCESSO!</p>
          <div class="code-display" id="res-codigo">RSAC-0000-0000</div>
          <p style="font-size: 0.8125rem; color: var(--text-muted);" id="res-detalhes">Expira em: ...</p>

          <div class="copy-actions">
            <button type="button" class="btn btn-secondary btn-sm" id="btn-copiar-codigo">
              📋 Copiar Código
            </button>
            <button type="button" class="btn btn-primary btn-sm" id="btn-copiar-mensagem">
              ✉️ Copiar Convite para Enviar
            </button>
          </div>
        </div>
      </div>

      <!-- VALIDADOR DE CONVITE -->
      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">Validador de Código</h2>
            <p class="card-subtitle">Verifique se um código já foi usado, quem usou ou se expirou</p>
          </div>
        </div>

        <form id="form-validar">
          <div class="form-group">
            <label for="input-busca-codigo">Código do Convite</label>
            <div style="display: flex; gap: 0.5rem;">
              <input type="text" id="input-busca-codigo" placeholder="Cole aqui: ex. RSAC-A1B2-C3D4" style="font-family: var(--font-mono); font-weight: 600;">
              <button type="submit" class="btn btn-primary" style="flex-shrink: 0;">
                🔍 Verificar
              </button>
            </div>
          </div>
        </form>

        <div class="validation-result" id="box-validacao">
          <!-- Conteúdo dinâmico preenchido via JavaScript -->
        </div>

        <div style="margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid var(--border-subtle); font-size: 0.8125rem; color: var(--text-muted);">
          <p><strong>Dica:</strong> Convites do Revsist são de uso único. Uma vez concluído o cadastro do pesquisador, o código é marcado permanentemente como utilizado com carimbo de data/hora e o ID do usuário.</p>
        </div>
      </div>

    </section>

    <!-- FILA DE SOLICITAÇÕES VINDAS DA TELA DE LOGIN -->
    <section class="table-section" id="secao-pedidos">
      <div class="table-toolbar">
        <div>
          <h3 style="font-size: 1.1rem; color: var(--dusk-blue);">Pedidos de Convite Recebidos</h3>
          <p style="font-size: 0.8125rem; color: var(--text-muted);">
            Quem chega à tela de login sem convite pede acesso por lá; o pedido cai aqui.
            Aprovar gera o código e já o deixa pronto para copiar.
          </p>
        </div>

        <div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
          <button type="button" class="btn btn-secondary btn-sm" id="btn-recarregar-pedidos">
            🔄 Atualizar
          </button>
        </div>
      </div>

      <div class="filters-row" style="margin-bottom: 1rem;">
        <button class="pill active" data-fpedido="pendente">Aguardando (<span id="cntp-pendente">0</span>)</button>
        <button class="pill" data-fpedido="aprovado">Aprovados (<span id="cntp-aprovado">0</span>)</button>
        <button class="pill" data-fpedido="recusado">Recusados (<span id="cntp-recusado">0</span>)</button>
        <button class="pill" data-fpedido="todos">Todos (<span id="cntp-todos">0</span>)</button>
      </div>

      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Solicitante</th>
              <th>Contato</th>
              <th>Como conheceu</th>
              <th>Recebido em</th>
              <th>Situação</th>
              <th style="text-align: right;">Ações</th>
            </tr>
          </thead>
          <tbody id="tabela-pedidos">
            <tr>
              <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">
                Carregando pedidos...
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- FEEDBACK DO BETA (botão do canto inferior direito do aplicativo) -->
    <section class="table-section" id="secao-feedback">
      <div class="table-toolbar">
        <div>
          <h3 style="font-size: 1.1rem; color: var(--dusk-blue);">Feedback do Beta</h3>
          <p style="font-size: 0.8125rem; color: var(--text-muted);">
            Problemas, sugestões e elogios enviados pelo botão de feedback do aplicativo.
            Cada envio também chega ao seu e-mail.
          </p>
        </div>

        <div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
          <button type="button" class="btn btn-secondary btn-sm" id="btn-recarregar-feedback">
            🔄 Atualizar
          </button>
        </div>
      </div>

      <div class="filters-feedback" style="display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 1rem;">
        <button class="pill active" data-ffeedback="novo">Novos (<span id="cntf-novo">0</span>)</button>
        <button class="pill" data-ffeedback="em_andamento">Em andamento (<span id="cntf-em_andamento">0</span>)</button>
        <button class="pill" data-ffeedback="resolvido">Resolvidos (<span id="cntf-resolvido">0</span>)</button>
        <button class="pill" data-ffeedback="arquivado">Arquivados (<span id="cntf-arquivado">0</span>)</button>
        <button class="pill" data-ffeedback="todos">Todos (<span id="cntf-todos">0</span>)</button>
      </div>

      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Tipo</th>
              <th style="min-width: 320px;">Mensagem</th>
              <th>Quem enviou</th>
              <th>Tela / Versão</th>
              <th>Recebido em</th>
              <th>Situação</th>
              <th style="text-align: right;">Ações</th>
            </tr>
          </thead>
          <tbody id="tabela-feedback">
            <tr>
              <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">
                Carregando feedback...
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- TABELA DE CONVITES -->
    <section class="table-section">
      <div class="table-toolbar">
        <div>
          <h3 style="font-size: 1.1rem; color: var(--dusk-blue);">Histórico de Convites Cadastrados</h3>
          <p style="font-size: 0.8125rem; color: var(--text-muted);">Acompanhe todos os códigos emitidos no banco local</p>
        </div>

        <div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
          <input type="text" id="filtro-texto" class="search-box" placeholder="Buscar código ou nome...">
          <button type="button" class="btn btn-secondary btn-sm" id="btn-recarregar">
            🔄 Atualizar
          </button>
        </div>
      </div>

      <div class="filters-row" style="margin-bottom: 1rem;">
        <button class="pill active" data-filtro="todos">Todos (<span id="cnt-todos">0</span>)</button>
        <button class="pill" data-filtro="disponivel">Disponíveis (<span id="cnt-disponivel">0</span>)</button>
        <button class="pill" data-filtro="utilizado">Utilizados (<span id="cnt-utilizado">0</span>)</button>
        <button class="pill" data-filtro="expirado">Expirados (<span id="cnt-expirado">0</span>)</button>
        <button class="pill" data-filtro="revogado">Revogados (<span id="cnt-revogado">0</span>)</button>
      </div>

      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Código</th>
              <th>Status</th>
              <th>Convidado / Nota</th>
              <th>Criado em</th>
              <th>Expiração</th>
              <th>Utilizado por</th>
              <th style="text-align: right;">Ações</th>
            </tr>
          </thead>
          <tbody id="tabela-corpo">
            <tr>
              <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">
                Carregando histórico de convites...
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

  </main>

  <div id="toast">Ação executada com sucesso!</div>

  <script>
    let todosConvites = [];
    let todosPedidos = [];
    let filtroPedidoAtual = 'pendente';
    let todosFeedbacks = [];
    let filtroFeedbackAtual = 'novo';
    let filtroStatusAtual = 'todos';
    let diasSelecionados = 14;
    let ultimoConviteGerado = null;

    // Inicialização
    document.addEventListener('DOMContentLoaded', () => {
      carregarConvites();
      carregarPedidos();
      carregarFeedback();

      // Filtros da fila de feedback
      document.querySelectorAll('[data-ffeedback]').forEach(btn => {
        btn.addEventListener('click', () => {
          document.querySelectorAll('[data-ffeedback]').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          filtroFeedbackAtual = btn.getAttribute('data-ffeedback');
          renderizarFeedback();
        });
      });

      document.getElementById('btn-recarregar-feedback').addEventListener('click', () => {
        carregarFeedback();
        mostrarToast('Fila de feedback atualizada');
      });

      // Filtros da fila de pedidos
      document.querySelectorAll('[data-fpedido]').forEach(btn => {
        btn.addEventListener('click', () => {
          document.querySelectorAll('[data-fpedido]').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          filtroPedidoAtual = btn.getAttribute('data-fpedido');
          renderizarPedidos();
        });
      });

      document.getElementById('btn-recarregar-pedidos').addEventListener('click', () => {
        carregarPedidos();
        mostrarToast('Fila de pedidos atualizada');
      });

      // Pílulas de expiração
      document.querySelectorAll('.preset-pills .pill').forEach(btn => {
        btn.addEventListener('click', () => {
          document.querySelectorAll('.preset-pills .pill').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          const val = btn.getAttribute('data-dias');
          const customBox = document.getElementById('custom-time-box');
          if (val === 'custom') {
            diasSelecionados = 'custom';
            customBox.classList.add('show');
          } else {
            diasSelecionados = parseInt(val, 10);
            customBox.classList.remove('show');
          }
        });
      });

      // Filtros de status da tabela. Pelo atributo, e não por `.filters-row
      // .pill`: aquele seletor também pegava as pílulas da fila de pedidos, e
      // clicar nelas zerava o filtro — e esvaziava — a tabela de convites.
      document.querySelectorAll('[data-filtro]').forEach(btn => {
        btn.addEventListener('click', () => {
          document.querySelectorAll('[data-filtro]').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          filtroStatusAtual = btn.getAttribute('data-filtro');
          renderizarTabela();
        });
      });

      // Busca em tempo real
      document.getElementById('filtro-texto').addEventListener('input', () => {
        renderizarTabela();
      });

      // Recarregar
      document.getElementById('btn-recarregar').addEventListener('click', () => {
        carregarConvites();
        mostrarToast('Lista de convites atualizada');
      });

      // Submissão do Gerador
      document.getElementById('form-gerar').addEventListener('submit', async (e) => {
        e.preventDefault();
        await gerarConvite();
      });

      // Submissão do Validador
      document.getElementById('form-validar').addEventListener('submit', async (e) => {
        e.preventDefault();
        await validarCodigo();
      });

      // Validação automática ao teclar no input de busca
      document.getElementById('input-busca-codigo').addEventListener('keyup', (e) => {
        if (e.key === 'Enter') {
          validarCodigo();
        }
      });

      // Copiar código do box
      document.getElementById('btn-copiar-codigo').addEventListener('click', () => {
        if (ultimoConviteGerado) {
          copiarTexto(ultimoConviteGerado.code, 'Código copiado para a área de transferência!');
        }
      });

      // Copiar mensagem completa do box
      document.getElementById('btn-copiar-mensagem').addEventListener('click', () => {
        if (ultimoConviteGerado) {
          const msg = formatarMensagemConvite(ultimoConviteGerado);
          copiarTexto(msg, 'Mensagem de convite copiada!');
        }
      });
    });

    async function carregarConvites() {
      try {
        const res = await fetch('/api/convites');
        const data = await res.json();
        if (data.ok) {
          todosConvites = data.convites || [];
          atualizarMetricas(data.metricas);
          renderizarTabela();
        }
      } catch (err) {
        console.error('Erro ao carregar convites:', err);
      }
    }

    function atualizarMetricas(m) {
      if (!m) return;
      document.getElementById('m-total').textContent = m.total;
      document.getElementById('m-disponiveis').textContent = m.disponiveis;
      document.getElementById('m-utilizados').textContent = m.utilizados;
      document.getElementById('m-expirados').textContent = m.expirados + m.revogados;

      document.getElementById('cnt-todos').textContent = m.total;
      document.getElementById('cnt-disponivel').textContent = m.disponiveis;
      document.getElementById('cnt-utilizado').textContent = m.utilizados;
      document.getElementById('cnt-expirado').textContent = m.expirados;
      document.getElementById('cnt-revogado').textContent = m.revogados;
    }

    async function gerarConvite() {
      const nota = document.getElementById('input-nota').value.trim();
      const customCode = document.getElementById('input-custom-code').value.trim();

      let dias = diasSelecionados;
      let horas = 0;

      if (diasSelecionados === 'custom') {
        const dVal = parseInt(document.getElementById('custom-dias').value, 10);
        const hVal = parseInt(document.getElementById('custom-horas').value, 10);
        dias = isNaN(dVal) ? 0 : dVal;
        horas = isNaN(hVal) ? 0 : hVal;
      }

      try {
        const res = await fetch('/api/convites/gerar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ dias, horas, nota, codigo_custom: customCode })
        });
        const data = await res.json();

        if (!data.ok) {
          alert('Erro ao gerar convite: ' + (data.erro || 'Falha desconhecida'));
          return;
        }

        ultimoConviteGerado = data.convite;

        // Exibir box de sucesso
        const box = document.getElementById('box-sucesso');
        box.style.display = 'block';
        document.getElementById('res-codigo').textContent = data.convite.code;
        document.getElementById('res-detalhes').textContent =
          `Destinatário: ${data.convite.note || 'Não especificado'} · Validade: ${data.convite.expires_at_br} (${data.convite.tempo_relativo})`;

        mostrarToast(`Convite ${data.convite.code} gerado com sucesso!`);

        // Limpar campos
        document.getElementById('input-nota').value = '';
        document.getElementById('input-custom-code').value = '';

        // Recarregar tabela
        await carregarConvites();

      } catch (err) {
        alert('Falha na comunicação com o servidor local.');
        console.error(err);
      }
    }

    async function validarCodigo(codigoParaValidar = null) {
      const input = document.getElementById('input-busca-codigo');
      const codigo = (codigoParaValidar || input.value).trim().toUpperCase();

      if (!codigo) {
        mostrarToast('Digite um código para validar');
        return;
      }

      try {
        const res = await fetch('/api/convites/validar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ codigo })
        });
        const data = await res.json();

        const box = document.getElementById('box-validacao');
        box.style.display = 'block';
        box.className = 'validation-result ' + (data.status || 'invalido');

        if (!data.existe) {
          box.innerHTML = `
            <div style="font-weight: 700; font-size: 1.05rem; margin-bottom: 0.3rem;">❌ Código Inexistente</div>
            <p style="font-size: 0.875rem;">O código <strong>${escaparHtml(codigo)}</strong> não foi encontrado no banco de dados local.</p>
          `;
          return;
        }

        const c = data.convite;
        let html = '';

        if (c.status === 'disponivel') {
          html = `
            <div style="font-weight: 700; font-size: 1.05rem; margin-bottom: 0.3rem;">🟢 Convite Válido e Disponível</div>
            <p style="font-size: 0.875rem;">Código <strong>${c.code}</strong> pronto para ser usado.</p>
            <p style="font-size: 0.8125rem; margin-top: 0.4rem;">
              <strong>Expiração:</strong> ${c.expires_at_br} (${c.tempo_relativo})<br>
              ${c.note ? `<strong>Destinatário / Nota:</strong> ${escaparHtml(c.note)}<br>` : ''}
              <strong>Emitido em:</strong> ${c.created_at_br}
            </p>
          `;
        } else if (c.status === 'utilizado') {
          const userStr = c.used_by ? `${c.used_by.username} (${c.used_by.email})` : 'Usuário registrado';
          html = `
            <div style="font-weight: 700; font-size: 1.05rem; margin-bottom: 0.3rem;">🔵 Convite Já Utilizado</div>
            <p style="font-size: 0.875rem;">Este código já foi consumido para cadastrar um pesquisador.</p>
            <div style="background: rgba(255,255,255,0.7); padding: 0.6rem 0.8rem; border-radius: 4px; margin-top: 0.6rem; font-size: 0.8125rem;">
              <strong>Pesquisador:</strong> ${escaparHtml(userStr)}<br>
              <strong>Data de utilização:</strong> ${c.used_at_br || '—'}<br>
              ${c.note ? `<strong>Nota original:</strong> ${escaparHtml(c.note)}<br>` : ''}
              <strong>Código:</strong> <code>${c.code}</code>
            </div>
          `;
        } else if (c.status === 'expirado') {
          html = `
            <div style="font-weight: 700; font-size: 1.05rem; margin-bottom: 0.3rem;">🟠 Convite Expirado</div>
            <p style="font-size: 0.875rem;">O prazo de validade deste convite se encerrou.</p>
            <p style="font-size: 0.8125rem; margin-top: 0.4rem;">
              <strong>Data de expiração:</strong> ${c.expires_at_br} (${c.tempo_relativo})<br>
              ${c.note ? `<strong>Destinado a:</strong> ${escaparHtml(c.note)}<br>` : ''}
              <em>Para admitir este pesquisador, gere um novo convite.</em>
            </p>
          `;
        } else if (c.status === 'revogado') {
          html = `
            <div style="font-weight: 700; font-size: 1.05rem; margin-bottom: 0.3rem;">🔴 Convite Revogado</div>
            <p style="font-size: 0.875rem;">Este convite foi cancelado manualmente pelo administrador e não permite mais cadastros.</p>
            ${c.note ? `<p style="font-size: 0.8125rem; margin-top: 0.4rem;"><strong>Nota:</strong> ${escaparHtml(c.note)}</p>` : ''}
          `;
        }

        box.innerHTML = html;

      } catch (err) {
        console.error(err);
        alert('Falha ao validar código.');
      }
    }

    async function revogarConvite(codigo) {
      if (!confirm(`Tem certeza de que deseja revogar o convite ${codigo}? Ele não poderá mais ser usado para cadastro.`)) {
        return;
      }

      try {
        const res = await fetch('/api/convites/revogar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ codigo })
        });
        const data = await res.json();
        if (data.ok) {
          mostrarToast(`Convite ${codigo} revogado com sucesso.`);
          await carregarConvites();
        } else {
          alert('Erro ao revogar: ' + (data.erro || 'Desconhecido'));
        }
      } catch (err) {
        alert('Falha ao comunicar com o servidor.');
      }
    }

    async function carregarPedidos() {
      try {
        const res = await fetch('/api/solicitacoes');
        const data = await res.json();
        if (data.ok) {
          todosPedidos = data.solicitacoes || [];
          const m = data.metricas || {};
          document.getElementById('m-pedidos').textContent = m.pendentes || 0;
          document.getElementById('cntp-pendente').textContent = m.pendentes || 0;
          document.getElementById('cntp-aprovado').textContent = m.aprovados || 0;
          document.getElementById('cntp-recusado').textContent = m.recusados || 0;
          document.getElementById('cntp-todos').textContent = m.total || 0;
          renderizarPedidos();
        }
      } catch (err) {
        console.error('Erro ao carregar pedidos:', err);
      }
    }

    function renderizarPedidos() {
      const tbody = document.getElementById('tabela-pedidos');
      const filtrados = filtroPedidoAtual === 'todos'
        ? todosPedidos
        : todosPedidos.filter(p => p.status === filtroPedidoAtual);

      if (filtrados.length === 0) {
        const vazio = filtroPedidoAtual === 'pendente'
          ? 'Nenhum pedido aguardando resposta.'
          : 'Nenhum pedido nesta situação.';
        tbody.innerHTML = `
          <tr>
            <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">
              ${vazio}
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = filtrados.map(p => {
        const classeBadge = p.status === 'pendente' ? 'badge badge-expirado'
          : p.status === 'aprovado' ? 'badge badge-disponivel'
          : 'badge badge-revogado';

        let situacaoHtml = `<span class="${classeBadge}">${escaparHtml(p.status_label)}</span>`;
        if (p.status === 'aprovado' && p.invite_code_generated) {
          situacaoHtml += `
            <div style="margin-top: 0.35rem;">
              <a href="javascript:void(0)" onclick="copiarTexto('${p.invite_code_generated}', 'Código ${p.invite_code_generated} copiado!')"
                 style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--steel-blue);"
                 title="Copiar o código emitido para este pedido">
                ${p.invite_code_generated} 📋
              </a>
            </div>
          `;
        }
        if (p.status === 'recusado' && p.admin_notes) {
          situacaoHtml += `<div style="font-size: 0.7rem; color: var(--text-light); margin-top: 0.3rem;">${escaparHtml(p.admin_notes)}</div>`;
        }

        let acoesHtml = '<div style="display: flex; gap: 0.35rem; justify-content: flex-end; flex-wrap: wrap;">';
        if (p.status === 'pendente') {
          acoesHtml += `
            <button class="btn btn-primary btn-sm" onclick="aprovarPedido('${p.id}')" title="Gerar convite de uso único para este pedido">
              ✅ Aprovar
            </button>
            <button class="btn btn-secondary btn-sm" onclick="recusarPedido('${p.id}')" title="Recusar o pedido">
              Recusar
            </button>
          `;
        } else {
          acoesHtml += `
            <button class="btn btn-secondary btn-sm" onclick="reabrirPedido('${p.id}')" title="Devolver o pedido para a fila">
              ↩️ Reabrir
            </button>
            <button class="btn btn-danger-sm" onclick="excluirPedido('${p.id}')" title="Apagar o pedido e os dados de contato">
              Excluir
            </button>
          `;
        }
        acoesHtml += '</div>';

        return `
          <tr>
            <td>
              <div class="user-info">
                <span class="user-name">${escaparHtml(p.nome)}</span>
                ${p.instituicao ? `<div class="user-email">${escaparHtml(p.instituicao)}</div>` : ''}
              </div>
            </td>
            <td style="font-size: 0.8125rem;">
              <div><a href="mailto:${escaparHtml(p.email)}">${escaparHtml(p.email)}</a></div>
              <div style="color: var(--text-muted);">${escaparHtml(p.telefone)}</div>
            </td>
            <td style="font-size: 0.8125rem; color: var(--text-muted);">${escaparHtml(p.onde_conheceu)}</td>
            <td style="font-size: 0.8125rem; color: var(--text-muted);">${p.created_at_br}</td>
            <td>${situacaoHtml}</td>
            <td>${acoesHtml}</td>
          </tr>
        `;
      }).join('');
    }

    async function aprovarPedido(id) {
      const pedido = todosPedidos.find(p => p.id === id);
      if (!pedido) return;
      if (!confirm(`Aprovar o pedido de ${pedido.nome} (${pedido.email})?\n\nUm convite de uso único será gerado com validade de 14 dias.`)) {
        return;
      }
      try {
        const res = await fetch('/api/solicitacoes/aprovar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id, dias: 14 })
        });
        const data = await res.json();
        if (!data.ok) {
          alert('Erro ao aprovar: ' + (data.erro || 'Falha desconhecida'));
          return;
        }
        ultimoConviteGerado = data.convite;
        copiarTexto(formatarMensagemConvite(data.convite), `Convite ${data.convite.code} gerado — mensagem copiada!`);
        await Promise.all([carregarPedidos(), carregarConvites()]);
      } catch (err) {
        alert('Falha na comunicação com o servidor local.');
      }
    }

    async function recusarPedido(id) {
      const motivo = prompt('Motivo da recusa (opcional, fica só no seu banco):', '');
      if (motivo === null) return;
      await atualizarPedido(id, 'recusado', motivo.trim(), 'Pedido recusado');
    }

    async function reabrirPedido(id) {
      await atualizarPedido(id, 'pendente', '', 'Pedido devolvido para a fila');
    }

    async function atualizarPedido(id, status, notas, aviso) {
      try {
        const res = await fetch('/api/solicitacoes/atualizar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id, status, notas })
        });
        const data = await res.json();
        if (!data.ok) {
          alert('Erro: ' + (data.erro || 'Falha desconhecida'));
          return;
        }
        mostrarToast(aviso);
        await carregarPedidos();
      } catch (err) {
        alert('Falha na comunicação com o servidor local.');
      }
    }

    async function excluirPedido(id) {
      const pedido = todosPedidos.find(p => p.id === id);
      if (!pedido) return;
      if (!confirm(`Excluir definitivamente o pedido de ${pedido.nome}?\n\nNome, e-mail e telefone informados serão apagados do banco.`)) {
        return;
      }
      try {
        const res = await fetch('/api/solicitacoes/excluir', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id })
        });
        const data = await res.json();
        if (!data.ok) {
          alert('Erro ao excluir: ' + (data.erro || 'Falha desconhecida'));
          return;
        }
        mostrarToast('Pedido excluído');
        await carregarPedidos();
      } catch (err) {
        alert('Falha na comunicação com o servidor local.');
      }
    }

    async function carregarFeedback() {
      try {
        const res = await fetch('/api/feedback');
        const data = await res.json();
        if (data.ok) {
          todosFeedbacks = data.feedbacks || [];
          const m = data.metricas || {};
          document.getElementById('m-feedback').textContent = m.novo || 0;
          ['novo', 'em_andamento', 'resolvido', 'arquivado', 'todos'].forEach(chave => {
            document.getElementById('cntf-' + chave).textContent = m[chave] || 0;
          });
          renderizarFeedback();
        }
      } catch (err) {
        console.error('Erro ao carregar feedback:', err);
      }
    }

    function renderizarFeedback() {
      const tbody = document.getElementById('tabela-feedback');
      const filtrados = filtroFeedbackAtual === 'todos'
        ? todosFeedbacks
        : todosFeedbacks.filter(f => f.status === filtroFeedbackAtual);

      if (filtrados.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">
              ${filtroFeedbackAtual === 'novo' ? 'Nenhum feedback novo.' : 'Nenhum feedback nesta situação.'}
            </td>
          </tr>
        `;
        return;
      }

      const classeTipo = {
        problema: 'badge badge-revogado',
        sugestao: 'badge badge-utilizado',
        elogio: 'badge badge-disponivel',
        outro: 'badge badge-expirado',
      };
      const classeSituacao = {
        novo: 'badge badge-expirado',
        em_andamento: 'badge badge-utilizado',
        resolvido: 'badge badge-disponivel',
        arquivado: 'badge badge-revogado',
      };

      tbody.innerHTML = filtrados.map(f => {
        const assunto = encodeURIComponent('Re: seu feedback no Revsist');
        const contato = f.autor_email
          ? `<div class="user-email"><a href="mailto:${escaparHtml(f.autor_email)}?subject=${assunto}">${escaparHtml(f.autor_email)}</a></div>`
          : '';
        const notas = f.admin_notes
          ? `<div style="font-size: 0.7rem; color: var(--text-light); margin-top: 0.3rem;">📝 ${escaparHtml(f.admin_notes)}</div>`
          : '';

        let acoes = '<div style="display: flex; gap: 0.35rem; justify-content: flex-end; flex-wrap: wrap;">';
        if (f.status !== 'resolvido') {
          acoes += `<button class="btn btn-primary btn-sm" onclick="atualizarFeedback('${f.id}', 'resolvido')" title="Marcar como resolvido">✅ Resolvido</button>`;
        }
        if (f.status === 'novo') {
          acoes += `<button class="btn btn-secondary btn-sm" onclick="atualizarFeedback('${f.id}', 'em_andamento')" title="Marcar como em andamento">Em andamento</button>`;
        }
        if (f.status === 'novo' || f.status === 'em_andamento') {
          acoes += `<button class="btn btn-secondary btn-sm" onclick="atualizarFeedback('${f.id}', 'arquivado')" title="Arquivar sem ação">Arquivar</button>`;
        } else {
          acoes += `<button class="btn btn-secondary btn-sm" onclick="atualizarFeedback('${f.id}', 'novo')" title="Devolver para os novos">↩️ Reabrir</button>`;
        }
        acoes += `<button class="btn btn-secondary btn-sm" onclick="anotarFeedback('${f.id}')" title="Anotação interna">📝 Anotar</button>`;
        acoes += `<button class="btn btn-danger-sm" onclick="excluirFeedback('${f.id}')" title="Apagar este feedback">Excluir</button>`;
        acoes += '</div>';

        return `
          <tr>
            <td><span class="${classeTipo[f.tipo] || 'badge'}">${escaparHtml(f.tipo_label)}</span></td>
            <td style="font-size: 0.8125rem; white-space: pre-wrap; word-break: break-word; max-width: 420px;">${escaparHtml(f.mensagem)}${notas}</td>
            <td>
              <div class="user-info">
                <span class="user-name">${escaparHtml(f.autor_nome)}</span>
                ${f.autor_usuario ? `<div class="user-email">@${escaparHtml(f.autor_usuario)}</div>` : ''}
                ${contato}
              </div>
            </td>
            <td style="font-size: 0.75rem; color: var(--text-muted);">
              <div style="font-family: var(--font-mono);">${escaparHtml(f.pagina || '/')}</div>
              ${f.versao ? `<div>v${escaparHtml(f.versao)}</div>` : ''}
              ${f.navegador ? `<div title="${escaparHtml(f.navegador)}" style="max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escaparHtml(f.navegador)}</div>` : ''}
            </td>
            <td style="font-size: 0.8125rem; color: var(--text-muted);">${f.created_at_br}</td>
            <td><span class="${classeSituacao[f.status] || 'badge'}">${escaparHtml(f.status_label)}</span></td>
            <td>${acoes}</td>
          </tr>
        `;
      }).join('');
    }

    async function enviarAtualizacaoFeedback(corpo, aviso) {
      try {
        const res = await fetch('/api/feedback/atualizar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(corpo)
        });
        const data = await res.json();
        if (!data.ok) {
          alert('Erro: ' + (data.erro || 'Falha desconhecida'));
          return;
        }
        mostrarToast(aviso);
        await carregarFeedback();
      } catch (err) {
        alert('Falha na comunicação com o servidor local.');
      }
    }

    async function atualizarFeedback(id, status) {
      const avisos = {
        resolvido: 'Feedback marcado como resolvido',
        em_andamento: 'Feedback em andamento',
        arquivado: 'Feedback arquivado',
        novo: 'Feedback devolvido para os novos',
      };
      await enviarAtualizacaoFeedback({ id, status }, avisos[status] || 'Feedback atualizado');
    }

    async function anotarFeedback(id) {
      const item = todosFeedbacks.find(f => f.id === id);
      if (!item) return;
      const nota = prompt('Anotação interna (só fica no seu banco):', item.admin_notes || '');
      if (nota === null) return;
      await enviarAtualizacaoFeedback({ id, notas: nota.trim() }, 'Anotação salva');
    }

    async function excluirFeedback(id) {
      const item = todosFeedbacks.find(f => f.id === id);
      if (!item) return;
      if (!confirm(`Excluir definitivamente o feedback de ${item.autor_nome}?`)) {
        return;
      }
      try {
        const res = await fetch('/api/feedback/excluir', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id })
        });
        const data = await res.json();
        if (!data.ok) {
          alert('Erro ao excluir: ' + (data.erro || 'Falha desconhecida'));
          return;
        }
        mostrarToast('Feedback excluído');
        await carregarFeedback();
      } catch (err) {
        alert('Falha na comunicação com o servidor local.');
      }
    }

    function renderizarTabela() {
      const termo = document.getElementById('filtro-texto').value.toLowerCase().trim();
      const tbody = document.getElementById('tabela-corpo');

      const filtrados = todosConvites.filter(c => {
        // Filtro de aba
        if (filtroStatusAtual !== 'todos' && c.status !== filtroStatusAtual) {
          return false;
        }
        // Filtro de busca textual
        if (termo) {
          const matchCode = c.code.toLowerCase().includes(termo);
          const matchNote = (c.note || '').toLowerCase().includes(termo);
          const matchUser = c.used_by ? (c.used_by.username + ' ' + c.used_by.email).toLowerCase().includes(termo) : false;
          return matchCode || matchNote || matchUser;
        }
        return true;
      });

      if (filtrados.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">
              Nenhum convite encontrado com os filtros selecionados.
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = filtrados.map(c => {
        const badgeClass = `badge badge-${c.status}`;
        let usuarioHtml = '<span style="color: var(--text-light);">—</span>';
        if (c.used_by) {
          usuarioHtml = `
            <div class="user-info">
              <span class="user-name">${escaparHtml(c.used_by.username)}</span>
              <div class="user-email">${escaparHtml(c.used_by.email)}</div>
              <div style="font-size: 0.7rem; color: var(--text-light);">em ${c.used_at_br}</div>
            </div>
          `;
        }

        let acoesHtml = `
          <div style="display: flex; gap: 0.35rem; justify-content: flex-end;">
            <button class="btn btn-secondary btn-sm" onclick="copiarTexto('${c.code}', 'Código ${c.code} copiado!')" title="Copiar código">
              📋
            </button>
            <button class="btn btn-secondary btn-sm" onclick="copiarMensagemLinha('${c.code}')" title="Copiar mensagem de convite pronta">
              ✉️
            </button>
        `;

        if (c.status === 'disponivel') {
          acoesHtml += `
            <button class="btn btn-danger-sm" onclick="revogarConvite('${c.code}')" title="Revogar convite">
              Revogar
            </button>
          `;
        }

        acoesHtml += '</div>';

        return `
          <tr>
            <td class="code-cell">
              <a href="javascript:void(0)" onclick="verificarDireto('${c.code}')" style="color: inherit; text-decoration: none;" title="Clique para validar">
                ${c.code}
              </a>
            </td>
            <td><span class="${badgeClass}">${c.status_label}</span></td>
            <td>${escaparHtml(c.note) || '<span style="color: var(--text-light);">Sem anotação</span>'}</td>
            <td style="font-size: 0.8125rem; color: var(--text-muted);">${c.created_at_br}</td>
            <td style="font-size: 0.8125rem;">
              <div>${c.expires_at_br}</div>
              <div style="font-size: 0.725rem; color: var(--text-light);">${c.tempo_relativo}</div>
            </td>
            <td>${usuarioHtml}</td>
            <td>${acoesHtml}</td>
          </tr>
        `;
      }).join('');
    }

    function verificarDireto(cod) {
      document.getElementById('input-busca-codigo').value = cod;
      validarCodigo(cod);
      window.scrollTo({ top: 120, behavior: 'smooth' });
    }

    function copiarMensagemLinha(cod) {
      const c = todosConvites.find(item => item.code === cod);
      if (c) {
        const msg = formatarMensagemConvite(c);
        copiarTexto(msg, 'Mensagem pronta copiada!');
      }
    }

    function formatarMensagemConvite(c) {
      const expiraTexto = c.expires_at_br ? c.expires_at_br : 'Sem data de expiração';
      return `Olá! Você recebeu um convite exclusivo para acessar o Revsist (Plataforma de Revisão Sistemática).\n\n` +
             `🎟️ Seu código de acesso: ${c.code}\n` +
             `⏳ Validade: ${expiraTexto} (${c.tempo_relativo})\n` +
             `👤 Destinatário: ${c.note || 'Convidado Especial'}\n\n` +
             `Para ativar sua conta, abra o Revsist, clique em "Cadastrar-se" e informe este código no campo de convite.`;
    }

    function copiarTexto(texto, aviso = 'Copiado!') {
      navigator.clipboard.writeText(texto).then(() => {
        mostrarToast(aviso);
      }).catch(err => {
        prompt('Copie manualmente:', texto);
      });
    }

    function mostrarToast(texto) {
      const t = document.getElementById('toast');
      t.textContent = texto;
      t.classList.add('show');
      setTimeout(() => {
        t.classList.remove('show');
      }, 2500);
    }

    function escaparHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }
  </script>
</body>
</html>
"""


class InviteManagerHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silenciar logs verbosos no terminal para manter a janela limpa
        pass

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url_parsed = urllib.parse.urlparse(self.path)
        path = url_parsed.path

        if path in ("", "/"):
            self._send_html(HTML_PAGE)
            return

        if path == "/api/convites":
            db = SessionLocal()
            try:
                convites_raw = db.query(InviteCodeModel).order_by(InviteCodeModel.created_at.desc()).all()
                convites_list = [serializar_convite(c, db) for c in convites_raw]

                # Métricas
                total = len(convites_list)
                disponiveis = sum(1 for c in convites_list if c["status"] == "disponivel")
                utilizados = sum(1 for c in convites_list if c["status"] == "utilizado")
                expirados = sum(1 for c in convites_list if c["status"] == "expirado")
                revogados = sum(1 for c in convites_list if c["status"] == "revogado")

                self._send_json({
                    "ok": True,
                    "convites": convites_list,
                    "metricas": {
                        "total": total,
                        "disponiveis": disponiveis,
                        "utilizados": utilizados,
                        "expirados": expirados,
                        "revogados": revogados,
                    }
                })
            finally:
                db.close()
            return

        if path == "/api/solicitacoes":
            db = SessionLocal()
            try:
                pedidos_raw = (
                    db.query(InviteRequestModel)
                    .order_by(InviteRequestModel.created_at.desc())
                    .all()
                )
                pedidos = [serializar_solicitacao(x) for x in pedidos_raw]

                self._send_json({
                    "ok": True,
                    "solicitacoes": pedidos,
                    "metricas": {
                        "total": len(pedidos),
                        "pendentes": sum(1 for x in pedidos if x["status"] == "pendente"),
                        "aprovados": sum(1 for x in pedidos if x["status"] == "aprovado"),
                        "recusados": sum(1 for x in pedidos if x["status"] == "recusado"),
                    },
                })
            finally:
                db.close()
            return

        if path == "/api/feedback":
            db = SessionLocal()
            try:
                linhas = (
                    db.query(FeedbackModel, UserModel)
                    .outerjoin(UserModel, UserModel.id == FeedbackModel.user_id)
                    .order_by(FeedbackModel.created_at.desc())
                    .all()
                )
                feedbacks = [serializar_feedback(f, autor) for f, autor in linhas]
                metricas = {chave: 0 for chave in ROTULO_STATUS_FEEDBACK}
                for item in feedbacks:
                    metricas[item["status"]] = metricas.get(item["status"], 0) + 1
                metricas["todos"] = len(feedbacks)

                self._send_json({"ok": True, "feedbacks": feedbacks, "metricas": metricas})
            finally:
                db.close()
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Não encontrado")

    def do_POST(self):
        url_parsed = urllib.parse.urlparse(self.path)
        path = url_parsed.path

        content_len = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_len) if content_len > 0 else b"{}"

        try:
            payload = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            payload = {}

        if path == "/api/convites/gerar":
            dias = payload.get("dias")
            horas = payload.get("horas", 0)
            nota = (payload.get("nota") or "").strip()
            custom_code = (payload.get("codigo_custom") or "").strip()

            db = SessionLocal()
            try:
                codigo = gerar_codigo_formatado(custom_code)

                # Verificar se já existe
                if db.query(InviteCodeModel).filter(InviteCodeModel.code == codigo).first():
                    self._send_json({"ok": False, "erro": f"Código '{codigo}' já existe no banco."}, status=400)
                    return

                agora = datetime.now(timezone.utc)
                expira = None

                # Se dias for 0 e horas for 0, é sem expiração
                if dias or horas:
                    delta_dias = int(dias) if dias else 0
                    delta_horas = int(horas) if horas else 0
                    if delta_dias > 0 or delta_horas > 0:
                        expira = agora + timedelta(days=delta_dias, hours=delta_horas)

                novo = InviteCodeModel(
                    id=generate_uuid(),
                    code=codigo,
                    created_at=agora,
                    expires_at=expira,
                    is_used=False,
                    is_revoked=False,
                    note=nota,
                )
                db.add(novo)
                db.commit()
                db.refresh(novo)

                self._send_json({
                    "ok": True,
                    "convite": serializar_convite(novo, db)
                })
            except Exception as e:
                db.rollback()
                self._send_json({"ok": False, "erro": str(e)}, status=500)
            finally:
                db.close()
            return

        if path == "/api/convites/validar":
            codigo = (payload.get("codigo") or "").strip().upper()
            if not codigo:
                self._send_json({"ok": False, "erro": "Código não fornecido."}, status=400)
                return

            db = SessionLocal()
            try:
                c = db.query(InviteCodeModel).filter(InviteCodeModel.code == codigo).first()
                if not c:
                    self._send_json({
                        "ok": True,
                        "existe": False,
                        "codigo": codigo,
                        "status": "invalido",
                    })
                    return

                info = serializar_convite(c, db)
                self._send_json({
                    "ok": True,
                    "existe": True,
                    "status": info["status"],
                    "convite": info,
                })
            finally:
                db.close()
            return

        if path == "/api/convites/revogar":
            codigo = (payload.get("codigo") or "").strip().upper()
            db = SessionLocal()
            try:
                c = db.query(InviteCodeModel).filter(InviteCodeModel.code == codigo).first()
                if not c:
                    self._send_json({"ok": False, "erro": "Convite não encontrado."}, status=404)
                    return
                if c.is_used:
                    self._send_json({"ok": False, "erro": "Convites já utilizados não podem ser revogados."}, status=400)
                    return

                c.is_revoked = True
                db.commit()
                self._send_json({"ok": True, "codigo": codigo})
            except Exception as e:
                db.rollback()
                self._send_json({"ok": False, "erro": str(e)}, status=500)
            finally:
                db.close()
            return

        if path == "/api/solicitacoes/aprovar":
            pedido_id = (payload.get("id") or "").strip()
            dias = payload.get("dias", 14)

            db = SessionLocal()
            try:
                pedido = (
                    db.query(InviteRequestModel)
                    .filter(InviteRequestModel.id == pedido_id)
                    .first()
                )
                if not pedido:
                    self._send_json({"ok": False, "erro": "Pedido não encontrado."}, status=404)
                    return
                if pedido.status == "aprovado" and pedido.invite_code_generated:
                    self._send_json({
                        "ok": False,
                        "erro": f"Este pedido já foi aprovado com o convite {pedido.invite_code_generated}.",
                    }, status=400)
                    return

                agora = datetime.now(timezone.utc)
                codigo = gerar_codigo_formatado("")
                while db.query(InviteCodeModel).filter(InviteCodeModel.code == codigo).first():
                    codigo = gerar_codigo_formatado("")

                expira = agora + timedelta(days=int(dias)) if dias else None
                nota = f"Solicitação de {pedido.nome} ({pedido.email})"

                convite = InviteCodeModel(
                    id=generate_uuid(),
                    code=codigo,
                    created_at=agora,
                    expires_at=expira,
                    is_used=False,
                    is_revoked=False,
                    note=nota[:255],
                )
                db.add(convite)

                pedido.status = "aprovado"
                pedido.responded_at = agora
                pedido.invite_code_generated = codigo

                db.commit()
                db.refresh(convite)
                db.refresh(pedido)

                self._send_json({
                    "ok": True,
                    "convite": serializar_convite(convite, db),
                    "solicitacao": serializar_solicitacao(pedido),
                })
            except Exception as e:
                db.rollback()
                self._send_json({"ok": False, "erro": str(e)}, status=500)
            finally:
                db.close()
            return

        if path == "/api/solicitacoes/atualizar":
            pedido_id = (payload.get("id") or "").strip()
            novo_status = (payload.get("status") or "").strip().lower()
            notas = (payload.get("notas") or "").strip()

            if novo_status not in ("pendente", "aprovado", "recusado"):
                self._send_json({"ok": False, "erro": "Situação inválida."}, status=400)
                return

            db = SessionLocal()
            try:
                pedido = (
                    db.query(InviteRequestModel)
                    .filter(InviteRequestModel.id == pedido_id)
                    .first()
                )
                if not pedido:
                    self._send_json({"ok": False, "erro": "Pedido não encontrado."}, status=404)
                    return

                pedido.status = novo_status
                pedido.responded_at = (
                    datetime.now(timezone.utc) if novo_status != "pendente" else None
                )
                pedido.admin_notes = notas

                db.commit()
                db.refresh(pedido)
                self._send_json({"ok": True, "solicitacao": serializar_solicitacao(pedido)})
            except Exception as e:
                db.rollback()
                self._send_json({"ok": False, "erro": str(e)}, status=500)
            finally:
                db.close()
            return

        if path == "/api/solicitacoes/excluir":
            pedido_id = (payload.get("id") or "").strip()

            db = SessionLocal()
            try:
                pedido = (
                    db.query(InviteRequestModel)
                    .filter(InviteRequestModel.id == pedido_id)
                    .first()
                )
                if not pedido:
                    self._send_json({"ok": False, "erro": "Pedido não encontrado."}, status=404)
                    return

                db.delete(pedido)
                db.commit()
                self._send_json({"ok": True, "id": pedido_id})
            except Exception as e:
                db.rollback()
                self._send_json({"ok": False, "erro": str(e)}, status=500)
            finally:
                db.close()
            return

        if path == "/api/feedback/atualizar":
            feedback_id = (payload.get("id") or "").strip()
            novo_status = payload.get("status")
            notas = payload.get("notas")

            if novo_status is not None:
                novo_status = str(novo_status).strip().lower()
                if novo_status not in ROTULO_STATUS_FEEDBACK:
                    self._send_json({"ok": False, "erro": "Situação inválida."}, status=400)
                    return

            db = SessionLocal()
            try:
                item = db.query(FeedbackModel).filter(FeedbackModel.id == feedback_id).first()
                if not item:
                    self._send_json({"ok": False, "erro": "Feedback não encontrado."}, status=404)
                    return

                if novo_status is not None and novo_status != item.status:
                    item.status = novo_status
                    item.responded_at = (
                        datetime.now(timezone.utc) if novo_status != "novo" else None
                    )
                if notas is not None:
                    item.admin_notes = str(notas).strip()[:2000]

                db.commit()
                db.refresh(item)
                autor = db.query(UserModel).filter(UserModel.id == item.user_id).first()
                self._send_json({"ok": True, "feedback": serializar_feedback(item, autor)})
            except Exception as e:
                db.rollback()
                self._send_json({"ok": False, "erro": str(e)}, status=500)
            finally:
                db.close()
            return

        if path == "/api/feedback/excluir":
            feedback_id = (payload.get("id") or "").strip()

            db = SessionLocal()
            try:
                item = db.query(FeedbackModel).filter(FeedbackModel.id == feedback_id).first()
                if not item:
                    self._send_json({"ok": False, "erro": "Feedback não encontrado."}, status=404)
                    return

                db.delete(item)
                db.commit()
                self._send_json({"ok": True, "id": feedback_id})
            except Exception as e:
                db.rollback()
                self._send_json({"ok": False, "erro": str(e)}, status=500)
            finally:
                db.close()
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Endpoint não encontrado")


def encontrar_porta_livre(porta_inicial: int = 8765, max_tentativas: int = 15) -> int:
    for p in range(porta_inicial, porta_inicial + max_tentativas):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return porta_inicial


def main():
    print("=" * 72)
    print("   REVSIST — GERENCIADOR INTERATIVO DE CÓDIGOS DE CONVITE")
    print("=" * 72)

    # Garantir schema atualizado
    try:
        aplicar_migracoes(engine)
        print(" [OK] Banco de dados inicializado e migrações verificadas.")
    except Exception as e:
        print(f" [AVISO] Falha ao verificar migrações: {e}")

    db_path = getattr(settings, "database_path", "rsac.db")
    print(f" [BD] Conectado ao arquivo: {db_path}")

    porta = encontrar_porta_livre(8765)
    url = f"http://127.0.0.1:{porta}"

    server = ThreadingHTTPServer(("127.0.0.1", porta), InviteManagerHandler)

    print("-" * 72)
    print(f" [>>] Interface gráfica aberta no seu navegador:")
    print(f"      {url}")
    print("-" * 72)
    print(" Dica: Você pode gerar convites com tempo de expiração customizado,")
    print("       validar códigos recebidos e acompanhar quem já se cadastrou.")
    print("       Os pedidos enviados pela tela de login aparecem na fila do topo,")
    print("       e o feedback do botão do aplicativo, logo abaixo deles.")
    print(" Pressione Ctrl+C nesta janela quando desejar fechar o aplicativo.")
    print("=" * 72)

    # Abrir navegador automaticamente
    try:
        webbrowser.open(url)
    except Exception:
        pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Encerrando o Gerenciador de Convites. Até logo!")
        server.server_close()


if __name__ == "__main__":
    main()
