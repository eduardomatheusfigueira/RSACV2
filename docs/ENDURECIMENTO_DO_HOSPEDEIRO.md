# Guia de Endurecimento do Hospedeiro e Implantação — Revsist

**Versão:** 1.0  
**Data:** 29 de agosto de 2026  
**Referência:** `planejamento/40_ESPECIFICACAO_ONLINE.md` (§40.7.4)

Este documento estabelece os procedimentos obrigatórios para configuração e endurecimento (*hardening*) do servidor VPS / Bare Metal que hospeda o Revsist em produção.

---

## 1. Segurança do Sistema Operacional e Acesso

### 1.1 Acesso SSH Restrito por Chave Criptográfica
- Desativar autenticação por senha no arquivo `/etc/ssh/sshd_config`:
  ```bash
  PasswordAuthentication no
  PermitRootLogin prohibit-password
  PubkeyAuthentication yes
  ```
- Reiniciar o serviço: `sudo systemctl restart sshd`.

### 1.2 Firewall do Hospedeiro (UFW)
Apenas as portas estritamente necessárias devem estar abertas:
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP Caddy'
sudo ufw allow 443/tcp comment 'HTTPS Caddy'
sudo ufw allow 443/udp comment 'HTTP/3 QUIC Caddy'
sudo ufw enable
```
> **Atenção:** O PostgreSQL (`5432`) **nunca** deve ser publicado no firewall nem exposto para a internet.

### 1.3 Prevenção de Intrusão (Fail2ban)
Instalar e habilitar proteção automática contra ataques de força bruta no SSH:
```bash
sudo apt-get update && sudo apt-get install -y fail2ban
sudo systemctl enable --now fail2ban
```

### 1.4 Atualizações Automáticas de Segurança
```bash
sudo apt-get install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 1.5 Fuso Horário UTC
Garantir que os logs e carimbos de data/hora do sistema estejam em UTC:
```bash
sudo timedatectl set-timezone UTC
```

---

## 2. Criptografia em Repouso do Volume de Dados (LGPD Art. 48 §3º, L-49)

Para garantir proteção integral contra acesso indevido em caso de descarte físico ou invasão do disco de armazenamento:
1. Utilizar partição de dados formatada com **LUKS (Linux Unified Key Setup)**:
   ```bash
   cryptsetup luksFormat /dev/sdb
   cryptsetup open /dev/sdb revsist_storage
   mkfs.ext4 /dev/mapper/revsist_storage
   mount /dev/mapper/revsist_storage /var/lib/docker/volumes
   ```
2. Ou utilizar o recurso nativo de *Volume Encryption (AES-256)* do provedor de infraestrutura (ex: AWS EBS Encrypted, Vultr Encrypted Block Storage, Magalu Cloud).

---

## 3. Roteiro de Implantação e Deploy

### 3.1 Primeira Implantação (Setup Inicial)
1. Clonar o repositório em `/opt/revsist`:
   ```bash
   git clone https://github.com/eduardomatheusfigueira/RSACV2.git /opt/revsist
   cd /opt/revsist
   ```
2. Criar e configurar o arquivo `.env`:
   ```bash
   cp .env.production.example .env
   # Editar segredos obrigatórios
   chmod 0600 .env
   chown root:root .env
   ```
3. Construir e inicializar a composição:
   ```bash
   docker compose up -d --build
   ```
4. Verificar status de integridade:
   ```bash
   curl -f https://revsist.com/api/v1/health
   ```
5. Provisionar o primeiro usuário proprietário (`owner`):
   ```bash
   docker compose exec api python -m app.cli create-user admin --role owner
   ```

### 3.2 Atualizações Contínuas (Deploy com Rollback)
```bash
cd /opt/revsist
git fetch origin main
git pull origin main
docker compose build api
docker compose up -d --no-deps api
docker compose ps
```
**Plano de Rollback:** Em caso de anomalia, reverter para a tag ou commit anterior do repositório e executar `docker compose up -d --build`.
