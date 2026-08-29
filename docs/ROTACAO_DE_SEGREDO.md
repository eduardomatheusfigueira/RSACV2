# Procedimento de Rotação da Chave Mestra (RSAC_SECRET_KEY) — Revsist

**Versão:** 1.0  
**Data:** 29 de agosto de 2026  
**Referência:** `planejamento/40_ESPECIFICACAO_ONLINE.md` (§40.7.3, doc 41 Tarefa 4.14)

---

## 1. Visão Geral

A chave mestra (`RSAC_SECRET_KEY`) é utilizada para criptografar chaves de API externas (Google Gemini, Alibaba Qwen) e credenciais de bases bibliográficas (Scopus, etc.) armazenadas nas tabelas `ai_settings` e `source_credentials`.

Em caso de suspeita de comprometimento da chave mestra ou como rotina anual de segurança, a chave deve ser rotacionada sem causar indisponibilidade ou perda dos dados dos usuários.

---

## 2. Procedimento Operacional de Rotação

### Passo 1: Gerar Nova Chave com Alta Entropia
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
*Exemplo:* `k7N2v8P1q9..._NOVA_CHAVE_MESTRA`

### Passo 2: Executar o Utilitário de Rotação
No servidor de produção, execute o script `scripts/rotacionar_chave_mestra.py`:
```bash
docker compose exec api python /app/scripts/rotacionar_chave_mestra.py \
    --old-key "CHAVE_ANTIGA_ATUAL" \
    --new-key "NOVA_CHAVE_MESTRA_GERADA"
```

O script:
1. Conecta ao banco de dados em uma **transação atômica**.
2. Decifra todas as colunas protegidas com a chave anterior.
3. Recifra imediatamente todos os valores com a nova chave.
4. Faz o `commit` apenas se 100% dos registros forem migrados com sucesso. Em caso de qualquer erro, efetua `rollback` completo automático.

### Passo 3: Atualizar o Arquivo `.env` e Reiniciar
1. Edite o arquivo `.env`:
   ```bash
   RSAC_SECRET_KEY=NOVA_CHAVE_MESTRA_GERADA
   ```
2. Reinicie o contêiner da API para carregar a nova chave:
   ```bash
   docker compose restart api
   ```
3. Teste a integridade chamando `/api/v1/health` e verificando os logs:
   ```bash
   docker compose logs api
   ```
