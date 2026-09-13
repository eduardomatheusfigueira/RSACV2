#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Prova de fogo do e-mail de convite aprovado.

Monta a mensagem exatamente como a aprovação monta — mesmo HTML, mesmas três
imagens embutidas, mesmo remetente — e manda para um endereço à sua escolha.
É o jeito de descobrir que a Senha de app está errada aqui, no terminal, e não
depois, quando alguém já estiver esperando o convite.

    python scripts/testar_email_convite.py                 # manda para você
    python scripts/testar_email_convite.py outro@email.br  # manda para outro

A senha nunca aparece na tela: o script confirma que ela *existe* e qual o seu
comprimento, e nada mais.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BACKEND = RAIZ / "backend"
sys.path.insert(0, str(BACKEND))

# O `.env` do backend é resolvido pelo pydantic-settings a partir do diretório
# de execução, e este script é chamado da raiz do repositório. Carregar o
# arquivo aqui, antes de importar `settings`, é o que faz o teste enxergar a
# mesma configuração que o servidor enxerga — sem isso ele acusaria "faltam as
# variáveis" com o .env preenchido do lado.
_env = BACKEND / ".env"
if _env.is_file():
    import os
    for linha in _env.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))

try:
    from app.config import settings
    from app.services import convite_mensagens, email_service
except ImportError as err:
    print(f"[ERRO] Não consegui importar o backend: {err}")
    print("Rode com o Python do ambiente virtual: backend/.venv/Scripts/python.exe")
    sys.exit(1)


def barra(titulo: str) -> None:
    print()
    print("=" * 68)
    print(f"  {titulo}")
    print("=" * 68)


def main() -> int:
    barra("REVSIST — TESTE DO E-MAIL DE CONVITE APROVADO")

    # ── O que está configurado ────────────────────────────────────────
    senha = settings.smtp_password or ""
    print(f"  Servidor    : {settings.smtp_host or '(vazio)'}:{settings.smtp_port}")
    print(f"  Usuário     : {settings.smtp_user or '(vazio)'}")
    print(f"  Remetente   : {settings.smtp_from_name} <{settings.smtp_from_email}>")
    print(f"  Senha de app: {'*' * len(senha)}  ({len(senha)} caracteres)")
    print(f"  Link base   : {convite_mensagens._base_publica()}")

    if not email_service.email_configurado():
        print()
        print("  [PARADO] Faltam RSAC_SMTP_HOST e/ou RSAC_SMTP_FROM_EMAIL.")
        print("           Confira o arquivo backend/.env.")
        return 1

    if not senha:
        print()
        print("  [PARADO] RSAC_SMTP_PASSWORD está vazia.")
        print("           Cole a Senha de app do Gmail em backend/.env.")
        return 1

    # O erro mais comum: colar os 16 caracteres com os espaços que o Google
    # mostra na tela. O Gmail recusa, e a mensagem de erro dele não diz isso.
    if len(senha) != 16:
        print()
        print(f"  [AVISO] Senha de app do Gmail tem 16 caracteres; esta tem {len(senha)}.")
        if " " in senha:
            print("          Há espaços nela — o Google mostra em grupos de 4, mas")
            print("          é para colar tudo junto, sem espaço.")
        print("          Seguindo assim mesmo para ver o que o servidor responde.")

    # ── As peças ──────────────────────────────────────────────────────
    barra("PEÇAS EMBUTIDAS")
    total = 0
    faltando = False
    for peca in convite_mensagens.pecas_do_email():
        if peca.caminho.is_file():
            tam = peca.caminho.stat().st_size
            total += tam
            print(f"  [ok]    {peca.caminho.name:<22} {tam // 1024:>4} KB")
        else:
            faltando = True
            print(f"  [FALTA] {peca.caminho.name:<22} — rode os renders do Remotion")
    print(f"  {'':>10}{'total':<22} {total // 1024:>4} KB")

    if faltando:
        print()
        print("  Para gerar as peças que faltam:")
        print("    cd remotion && npm run render:email")
        return 1

    # ── Envio ─────────────────────────────────────────────────────────
    destino = sys.argv[1] if len(sys.argv) > 1 else settings.smtp_from_email
    mensagens = convite_mensagens.montar_tudo(
        nome="Maria Souza",
        telefone="(51) 99999-8888",
        codigo="RSAC-TESTE-0000",
    )

    barra(f"ENVIANDO PARA {destino}")
    print("  (mensagem idêntica à de uma aprovação real, com código fictício)")
    print()

    resultado = email_service.enviar(
        destinatario=destino,
        assunto=f"[TESTE] {mensagens.email_assunto}",
        texto=mensagens.email_texto,
        html=mensagens.email_html,
        imagens=convite_mensagens.pecas_do_email(),
    )

    if resultado.enviado:
        print("  [SUCESSO] O servidor aceitou a mensagem.")
        print()
        print(f"  Confira a caixa de entrada de {destino}.")
        print("  Repare se as três imagens aparecem no corpo (e não como anexo")
        print("  solto no rodapé) e se o botão 'Entrar no Revsist' leva para:")
        print(f"    {mensagens.link_direto}")
        print()
        print("  O envio de verdade já está funcionando. Nada mais a fazer.")
        return 0

    print(f"  [FALHOU] {resultado.detalhe}")
    print()
    print("  Causas mais comuns, em ordem:")
    print("   1. A senha não é uma Senha de app — a senha normal da conta")
    print("      Google não funciona em SMTP desde 2022.")
    print("   2. A Senha de app foi colada com os espaços dos grupos de 4.")
    print("   3. A verificação em duas etapas não está ativa na conta (sem ela")
    print("      o Google nem oferece a opção de gerar Senha de app).")
    print("   4. RSAC_SMTP_FROM_EMAIL difere de RSAC_SMTP_USER.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
