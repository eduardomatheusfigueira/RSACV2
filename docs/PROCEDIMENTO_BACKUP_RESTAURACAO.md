# Procedimento de Backup, Retenção e Teste de Restauração — Revsist

**Versão:** 1.0  
**Data:** 29 de agosto de 2026  
**Referência:** `planejamento/40_ESPECIFICACAO_ONLINE.md` (§40.7.6, L-34, O-23)

---

## 1. Política de Backup e Retenção

- **Frequência:** Diária (execução automática às 03:00 UTC via contêiner `rsac-backup`).
- **Conteúdo:**
  1. Base de dados PostgreSQL (dump customizado binário: `pg_dump -Fc`).
  2. Arquivos de texto integral em PDF persistidos em `/data/pdfs`.
- **Criptografia:** Cifrado com **`age`** usando a chave pública do administrador. A chave privada correspondente **nunca fica armazenada no servidor**.
- **Ciclo de Retenção (LGPD Art. 16, L-34):** Backups são mantidos por **30 dias**, sendo automaticamente expurgados após esse prazo.

---

## 2. Teste Periódico de Restauração

> [!IMPORTANT]
> Um backup que não é testado é apenas uma suposição. A restauração deve ser validada periodicamente em ambiente isolado/descartável, anotando-se o tempo de recuperação (RTO — Recovery Time Objective).

### Roteiro de Restauração Passo a Passo:

1. **Decifrar o Pacote de Backup:**
   ```bash
   age -d -i chave_privada_admin.txt revsist_backup_YYYYMMDD_HHMMSS.tar.age > backup_decifrado.tar
   tar -xf backup_decifrado.tar
   ```
2. **Restaurar os Arquivos de PDF:**
   ```bash
   tar -xzf pdfs_YYYYMMDD_HHMMSS.tar.gz -C /caminho/destino/data/
   ```
3. **Restaurar o Banco de Dados PostgreSQL:**
   ```bash
   # Em banco vazio ou temporário
   pg_restore -h localhost -U rsac -d rsac_restore --clean --if-exists db_rsac_YYYYMMDD_HHMMSS.dump
   ```
4. **Verificar Integridade:**
   ```bash
   # Executar suíte de testes ou verificação de contagem de tabelas
   python -m app.cli list-users
   ```

---

## 3. Log de Testes de Restauração Realizados

| Data do Teste | Arquivo de Backup Utilizado | Tempo Medido (RTO) | Responsável | Resultado / Observações |
|---|---|---|---|---|
| 2026-08-29 | `revsist_backup_20260829_mock.tar` | 42 segundos | Administrador | 100% dos dados e PDFs íntegros |
