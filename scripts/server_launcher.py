#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RSAC V2 — Server Launcher
Inicia o backend Python (FastAPI), o túnel seguro da Cloudflare,
captura a URL pública, copia para a área de transferência, exibe o QR Code
para acesso no celular e monitora os serviços.
"""

import atexit
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

# Configuração de encoding UTF-8 para console Windows
if sys.platform == "win32":
    os.system("")  # Ativa códigos de escape ANSI
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def get_base_dir() -> Path:
    """Retorna a pasta raiz do projeto RSACV2."""
    if getattr(sys, "frozen", False):
        # Executável PyInstaller
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "backend").exists():
            return exe_dir
        return exe_dir
    else:
        # Script em scripts/
        return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
CONFIG_FILE = BASE_DIR / "server_config.json"

# Processos filhos gerenciados
_backend_proc: subprocess.Popen | None = None
_cloudflared_proc: subprocess.Popen | None = None
_is_shutting_down = False


def load_config() -> dict:
    """Carrega ou cria as configurações do servidor."""
    default_cfg = {
        "port": 8000,
        "auto_open_browser": False,
        "netlify_url": "",
        "cloudflared_path": "",
        # SHA-256 do cloudflared autorizado. Preenchido na primeira execução,
        # após confirmação do usuário; depois disso, binário diferente é
        # recusado (doc 29 §29.11.1).
        "cloudflared_sha256": "",
        # Origens de navegador autorizadas a falar com a API neste servidor.
        # Vazio = só o próprio túnel (a SPA servida pelo backend). Inclua aqui
        # o endereço do Netlify se for usar a interface hospedada lá.
        "cors_origins": [],
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_cfg.update(data)
        except Exception:
            pass
    return default_cfg


def copy_to_clipboard(text: str) -> bool:
    """Copia o texto fornecido para a área de transferência do Windows."""
    try:
        if sys.platform == "win32":
            proc = subprocess.Popen(
                ["clip.exe"],
                stdin=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                shell=True,
            )
            proc.communicate(input=text.encode("utf-16le"))
            return proc.returncode == 0
    except Exception:
        pass
    return False


def print_qr_code(url: str):
    """Gera e exibe um QR code UTF-8 no terminal para leitura via celular."""
    try:
        import qrcode

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1,
        )
        qr.add_data(url)
        qr.make(fit=True)

        print("\033[93m  📱 QR Code para Celular (Aponte a câmera):\033[0m")
        print("\033[97m")
        qr.print_ascii(invert=True)
        print("\033[0m")
    except Exception:
        pass


def find_cloudflared(custom_path: str = "") -> str | None:
    """Procura o executável cloudflared no sistema ou baixa se necessário."""
    candidates = [
        custom_path,
        str(BASE_DIR / "cloudflared.exe"),
        str(BASE_DIR / "scripts" / "cloudflared.exe"),
        r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
        r"C:\Program Files\cloudflared\cloudflared.exe",
        shutil.which("cloudflared"),
        shutil.which("cloudflared.exe"),
    ]

    for p in candidates:
        if p and os.path.isfile(p):
            return p

    return None


# Versão fixada do cloudflared.
#
# `latest/download/` era um alvo móvel: o binário mudava sem aviso, e não havia
# como verificar nada contra ele. Fixar a versão é o que torna a verificação
# possível — o artefato passa a ser determinístico.
CLOUDFLARED_VERSAO = "2026.8.0"
CLOUDFLARED_URL = (
    "https://github.com/cloudflare/cloudflared/releases/download/"
    f"{CLOUDFLARED_VERSAO}/cloudflared-windows-amd64.exe"
)


def caminho_da_chave_mestra() -> Path:
    """
    Onde a chave-mestra do servidor é guardada.

    Na pasta de dados do usuário — a mesma que o backend usa para o banco —, e
    não no diretório do projeto: `server_config.json` é versionado, e uma chave
    ali viraria commit.
    """
    try:
        import platformdirs

        base = Path(platformdirs.user_data_dir("RSAC"))
    except ImportError:
        if sys.platform == "win32":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "RSAC"
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support" / "RSAC"
        else:
            base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "RSAC"

    return base / "server_secret.key"


def obter_ou_criar_chave_mestra() -> str:
    """Devolve a chave-mestra do servidor, criando-a na primeira execução."""
    do_ambiente = (os.environ.get("RSAC_SECRET_KEY") or "").strip()
    if do_ambiente:
        return do_ambiente

    caminho = caminho_da_chave_mestra()
    if caminho.exists():
        try:
            existente = caminho.read_text(encoding="utf-8").strip()
            if existente:
                return existente
        except OSError:
            pass

    import base64
    import stat as stat_mod

    chave = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")
    try:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(chave, encoding="utf-8")
        os.chmod(caminho, stat_mod.S_IRUSR | stat_mod.S_IWUSR)
    except OSError as exc:
        print(f"\033[93m[!] Não foi possível gravar a chave-mestra: {exc}\033[0m")

    print("\033[93m[!] Chave-mestra de cifra gerada em:\033[0m")
    print(f"\033[97m    {caminho}\033[0m")
    print("\033[93m    Sem ela as chaves de API gravadas não podem ser decifradas —")
    print("    guarde uma cópia fora desta máquina.\033[0m\n")

    return chave


def sha256_do_arquivo(caminho: Path) -> str:
    """SHA-256 de um arquivo, lido em blocos."""
    import hashlib

    digest = hashlib.sha256()
    with open(caminho, "rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def download_cloudflared(dest_path: Path, config: dict) -> bool:
    """
    Baixa o cloudflared e **verifica sua integridade** antes de usá-lo.

    O binário baixado é executado com os privilégios do usuário e recebe acesso
    ao backend; gravá-lo sem verificar nada é uma dependência de cadeia de
    suprimentos fora de controle (doc 28 V-09, doc 29 §29.11.1).

    A verificação usa o SHA-256 registrado em `server_config.json`. Na primeira
    vez não há valor registrado: o lançador mostra o hash calculado, pede
    confirmação explícita e o grava. Da segunda em diante, um binário diferente
    é recusado sem perguntar.

    O modelo é o de confiança na primeira utilização, e é honesto quanto ao que
    entrega: não protege contra um artefato adulterado **já** no primeiro
    download, e por isso o caminho recomendado continua sendo instalar o
    cloudflared pelo instalador oficial e apontar `cloudflared_path`.
    """
    esperado = (config.get("cloudflared_sha256") or "").strip().lower()

    print("\033[93m[!] cloudflared não encontrado no sistema.\033[0m")
    print("\033[96m[*] Recomendado: instale o cloudflared oficial e informe o caminho")
    print("    em 'cloudflared_path' no server_config.json.\033[0m")
    print(f"\033[96m[*] Baixando cloudflared {CLOUDFLARED_VERSAO} da Cloudflare...\033[0m")

    temporario = dest_path.with_suffix(".parcial")
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(CLOUDFLARED_URL, headers={"User-Agent": "RSAC-Launcher"})
        with urllib.request.urlopen(req, timeout=60) as response, open(temporario, "wb") as saida:
            shutil.copyfileobj(response, saida)
    except Exception as e:
        print(f"\033[91m[X] Falha ao baixar cloudflared: {e}\033[0m")
        temporario.unlink(missing_ok=True)
        return False

    obtido = sha256_do_arquivo(temporario)

    if esperado:
        if obtido != esperado:
            print("\033[91m[X] O binário baixado NÃO corresponde ao hash registrado.\033[0m")
            print(f"\033[91m    esperado: {esperado}\033[0m")
            print(f"\033[91m    obtido:   {obtido}\033[0m")
            print("\033[91m    Download descartado — não será executado.\033[0m")
            temporario.unlink(missing_ok=True)
            return False
        print("\033[92m[✓] Integridade verificada contra o hash registrado.\033[0m")
    else:
        print("\033[93m[!] Nenhum hash registrado para este binário.\033[0m")
        print(f"\033[97m    SHA-256 do arquivo baixado:\033[0m")
        print(f"\033[97m    {obtido}\033[0m")
        print("\033[93m    Confira este valor na página oficial de releases da Cloudflare:")
        print(f"    https://github.com/cloudflare/cloudflared/releases/tag/{CLOUDFLARED_VERSAO}\033[0m")
        try:
            resposta = input("\n    O hash confere? Executar este binário? [s/N] ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            resposta = "n"

        if resposta not in ("s", "sim", "y", "yes"):
            print("\033[91m[X] Download descartado a pedido do usuário.\033[0m")
            temporario.unlink(missing_ok=True)
            return False

        config["cloudflared_sha256"] = obtido
        salvar_config(config)
        print("\033[92m[✓] Hash registrado — as próximas execuções serão verificadas.\033[0m")

    temporario.replace(dest_path)
    print(f"\033[92m[✓] cloudflared pronto: {dest_path}\033[0m\n")
    return True


def verificar_cloudflared_existente(caminho: str, config: dict) -> bool:
    """
    Confere um cloudflared já presente contra o hash registrado.

    Sem isto, o binário verificado no primeiro download poderia ser trocado
    depois e o lançador o executaria sem notar.
    """
    esperado = (config.get("cloudflared_sha256") or "").strip().lower()
    if not esperado:
        return True

    try:
        obtido = sha256_do_arquivo(Path(caminho))
    except OSError:
        return True

    if obtido != esperado:
        print("\033[91m[X] O cloudflared encontrado não corresponde ao hash registrado.\033[0m")
        print(f"\033[91m    esperado: {esperado}\033[0m")
        print(f"\033[91m    obtido:   {obtido}\033[0m")
        print("\033[93m    Se você atualizou o cloudflared de propósito, limpe o campo")
        print("    'cloudflared_sha256' no server_config.json e rode de novo.\033[0m")
        return False

    return True


def salvar_config(config: dict) -> None:
    """Grava o server_config.json preservando o que já estava lá."""
    try:
        atual = {}
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                atual = json.load(f)
        atual.update(config)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(atual, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except Exception as exc:
        print(f"\033[93m[!] Não foi possível gravar {CONFIG_FILE}: {exc}\033[0m")


def ensure_frontend_build() -> bool:
    """Garante que a interface web compilada exista antes de iniciar."""
    dist_index = FRONTEND_DIR / "dist" / "index.html"
    if dist_index.exists():
        return True

    print("\033[93m[*] Interface estática não encontrada. Compilando frontend Web SPA...\033[0m")
    try:
        npm_bin = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
        proc = subprocess.run(
            f'"{npm_bin}" run build:web',
            cwd=str(FRONTEND_DIR),
            shell=True,
            capture_output=True,
            text=True,
        )
        if dist_index.exists():
            print("\033[92m[✓] Build do frontend concluído com sucesso!\033[0m\n")
            return True
        else:
            print(f"\033[91m[X] Falha no build do frontend:\n{proc.stderr or proc.stdout}\033[0m\n")
            return False
    except Exception as e:
        print(f"\033[91m[X] Erro ao invocar build do frontend: {e}\033[0m\n")
        return False


def is_port_in_use(port: int) -> bool:
    """Verifica se o backend já está respondendo na porta especificada."""
    try:
        url = f"http://127.0.0.1:{port}/api/v1/health"
        req = urllib.request.Request(url, headers={"User-Agent": "RSAC-Launcher"})
        with urllib.request.urlopen(req, timeout=1.5) as res:
            if res.status == 200:
                return True
    except Exception:
        pass
    return False


def start_backend(port: int, config: dict | None = None) -> bool:
    """Inicia o backend Python em segundo plano se ainda não estiver ativo."""
    global _backend_proc

    config = config or {}

    if is_port_in_use(port):
        print(f"\033[92m[✓] Backend já está em execução na porta {port}.\033[0m")
        return True

    print(f"\033[96m[*] Iniciando Backend FastAPI na porta {port}...\033[0m")

    # Localizar python
    python_exe = sys.executable
    if getattr(sys, "frozen", False):
        system_python = shutil.which("python") or shutil.which("python3")
        if not system_python:
            common_pythons = [
                r"C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe",
                r"C:\Program Files\Python312\python.exe",
                r"C:\Python312\python.exe",
            ]
            for cp in common_pythons:
                if os.path.isfile(cp):
                    system_python = cp
                    break
        python_exe = system_python or "python"

    run_script = BACKEND_DIR / "run.py"
    if not run_script.exists():
        print(f"\033[91m[X] Arquivo backend/run.py não encontrado em {run_script}\033[0m")
        return False

    cmd = [
        python_exe,
        str(run_script),
        "--port",
        str(port),
    ]

    # Este lançador publica o backend na internet, então ele sobe no perfil
    # `server`: CORS restrito à lista declarada e documentação OpenAPI fechada
    # (doc 29 §29.2.2). Sem isto o processo assumiria o perfil `desktop` e
    # liberaria loopback e docs num endereço público.
    env = os.environ.copy()
    env["RSAC_DEPLOYMENT_PROFILE"] = "server"

    # Chave-mestra da cifra de segredos (doc 29 §29.4.1). No perfil `server` o
    # backend se recusa a subir sem ela — e como o lançador é quem sobe o
    # processo, é aqui que ela precisa existir.
    #
    # Fica **fora do repositório**, na pasta de dados do usuário: gravá-la em
    # `server_config.json`, que é versionado, faria o pesquisador enviar a
    # própria chave-mestra para o GitHub no commit seguinte.
    env["RSAC_SECRET_KEY"] = obter_ou_criar_chave_mestra()
    cors_origins = config.get("cors_origins") or []
    if cors_origins:
        env["RSAC_CORS_ORIGINS"] = json.dumps(cors_origins)

    _backend_proc = subprocess.Popen(
        cmd,
        cwd=str(BACKEND_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )

    # Aguardar até 15 segundos pelo health check
    for _ in range(30):
        time.sleep(0.5)
        if is_port_in_use(port):
            print(f"\033[92m[✓] Backend inicializado com sucesso (PID: {_backend_proc.pid}).\033[0m")
            return True

    print("\033[91m[X] Tempo limite ao aguardar o backend iniciar.\033[0m")
    return False


def auth_status(port: int) -> dict | None:
    """Consulta o estado da autenticação no backend já em execução."""
    try:
        url = f"http://127.0.0.1:{port}/api/v1/auth/status"
        req = urllib.request.Request(url, headers={"User-Agent": "RSAC-Launcher"})
        with urllib.request.urlopen(req, timeout=5) as res:
            return json.loads(res.read().decode("utf-8"))
    except Exception:
        return None


def provisionar_conta_interativa() -> bool:
    """
    Cria a primeira conta administradora antes de publicar o servidor.

    A alternativa — publicar e deixar o usuário criar a conta pela interface —
    exigiria uma rota de "primeiro administrador" aberta na internet, que é
    justamente o buraco que a autenticação fecha.
    """
    print("\033[93m[!] Nenhuma conta de acesso provisionada nesta instalação.\033[0m")
    print("\033[96m[*] O servidor não pode ser publicado sem autenticação.\033[0m\n")

    try:
        usuario = input("    Nome de usuário da conta administradora: ").strip()
    except (KeyboardInterrupt, EOFError):
        return False

    if not usuario:
        print("\033[91m[X] Nome de usuário vazio.\033[0m")
        return False

    cmd = [sys.executable, "-m", "app.cli", "create-user", usuario, "--role", "owner"]
    try:
        resultado = subprocess.run(cmd, cwd=str(BACKEND_DIR), text=True)
        if resultado.returncode != 0:
            print("\033[91m[X] Falha ao criar a conta.\033[0m")
            return False
    except Exception as exc:
        print(f"\033[91m[X] Falha ao criar a conta: {exc}\033[0m")
        return False

    print("\033[92m[✓] Conta criada. Anote a senha exibida acima — ela não será mostrada de novo.\033[0m")
    try:
        input("\n    Pressione Enter depois de anotar a senha para continuar...")
    except (KeyboardInterrupt, EOFError):
        return False
    return True


def cleanup():
    """Encerra com segurança todos os processos filhos."""
    global _is_shutting_down, _backend_proc, _cloudflared_proc
    if _is_shutting_down:
        return
    _is_shutting_down = True

    print("\n\033[93m[*] Encerrando serviços do RSAC V2 com segurança...\033[0m")

    if _cloudflared_proc and _cloudflared_proc.poll() is None:
        try:
            _cloudflared_proc.terminate()
            _cloudflared_proc.wait(timeout=3)
        except Exception:
            _cloudflared_proc.kill()

    if _backend_proc and _backend_proc.poll() is None:
        try:
            _backend_proc.terminate()
            _backend_proc.wait(timeout=3)
        except Exception:
            _backend_proc.kill()

    print("\033[92m[✓] Todos os serviços foram finalizados. Até logo!\033[0m")


atexit.register(cleanup)


def signal_handler(sig, frame):
    cleanup()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def main():
    global _cloudflared_proc

    config = load_config()
    port = config.get("port", 8000)

    # Limpar tela
    os.system("cls" if sys.platform == "win32" else "clear")

    print("\033[92m" + "=" * 70)
    print("        🚀 RSAC V2 — SERVIDOR WEB & ACESSO REMOTO (CLOUDFLARE)")
    print("=" * 70 + "\033[0m\n")

    ensure_frontend_build()

    # 1. Iniciar Backend
    if not start_backend(port, config):
        print("\033[91m[X] Não foi possível iniciar o backend. Pressione Enter para sair.\033[0m")
        input()
        sys.exit(1)

    # 2. Portão de publicação (doc 29 §29.11.6)
    #
    # O túnel não sobe se o backend não exigir autenticação ou se não houver
    # conta provisionada. É a diferença entre publicar um ambiente de pesquisa
    # e publicar o controle dele.
    estado = auth_status(port)
    if estado is None:
        print("\033[91m[X] Não foi possível verificar o estado da autenticação do backend.\033[0m")
        input()
        cleanup()
        sys.exit(1)

    if not estado.get("authentication_enabled", False):
        print("\033[91m[X] O backend está com a autenticação desativada. Túnel cancelado.\033[0m")
        input()
        cleanup()
        sys.exit(1)

    if not estado.get("has_accounts", False):
        if not provisionar_conta_interativa():
            print("\033[91m[X] Sem conta de acesso o servidor não será publicado.\033[0m")
            input()
            cleanup()
            sys.exit(1)

    # 3. Localizar Cloudflared
    cloudflared_bin = find_cloudflared(config.get("cloudflared_path", ""))
    if not cloudflared_bin:
        download_target = BASE_DIR / "cloudflared.exe"
        if download_cloudflared(download_target, config):
            cloudflared_bin = str(download_target)
        else:
            print("\033[91m[X] Instale o cloudflared ou configure o caminho no server_config.json.\033[0m")
            input()
            sys.exit(1)

    # Um binário já presente também precisa conferir com o hash registrado:
    # sem isso, o que foi verificado no primeiro download poderia ser trocado
    # depois e executado sem que ninguém notasse.
    if not verificar_cloudflared_existente(cloudflared_bin, config):
        input()
        cleanup()
        sys.exit(1)

    print(f"\033[96m[*] Iniciando túnel seguro Cloudflare na porta {port}...\033[0m")

    # 4. Iniciar Cloudflared e capturar URL
    tunnel_cmd = [
        cloudflared_bin,
        "tunnel",
        "--url",
        f"http://127.0.0.1:{port}",
    ]

    _cloudflared_proc = subprocess.Popen(
        tunnel_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    public_url = None
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    # Ler saída do cloudflared até achar a URL
    start_time = time.time()
    while time.time() - start_time < 30:
        if _cloudflared_proc.poll() is not None:
            break
        line = _cloudflared_proc.stdout.readline()
        if not line:
            time.sleep(0.1)
            continue
        match = url_pattern.search(line)
        if match:
            public_url = match.group(0)
            break

    if not public_url:
        print("\033[91m[X] Não foi possível obter a URL pública da Cloudflare a tempo.\033[0m")
        input()
        cleanup()
        sys.exit(1)

    # Thread para consumir saída restante do cloudflared sem travar o buffer
    def discard_output():
        try:
            for _ in _cloudflared_proc.stdout:
                if _is_shutting_down:
                    break
        except Exception:
            pass

    threading.Thread(target=discard_output, daemon=True).start()

    # Copiar para área de transferência
    copied = copy_to_clipboard(public_url)

    # Exibir Painel Visual Principal
    os.system("cls" if sys.platform == "win32" else "clear")
    print("\033[92m" + "═" * 70)
    print("        🚀 RSAC V2 — SERVIDOR ONLINE & DISPONÍVEL NA NUVEM")
    print("═" * 70 + "\033[0m\n")

    print("\033[97m  STATUS DOS SERVIÇOS:\033[0m")
    print(f"  \033[92m[✓]\033[0m Backend FastAPI:     \033[96mhttp://127.0.0.1:{port}\033[0m (\033[92mOnline\033[0m)")
    print("  \033[92m[✓]\033[0m Interface Web SPA:   \033[92mIntegrada ao Servidor\033[0m")
    print(f"  \033[92m[✓]\033[0m Túnel Cloudflare:    \033[92mSeguro (HTTPS Ativo)\033[0m")
    print("  \033[92m[✓]\033[0m Banco de Dados:      \033[92mSQLite Conectado\033[0m\n")

    print("\033[91m" + "─" * 70 + "\033[0m")
    print("  \033[93m⚠  ESTE LINK PUBLICA O SERVIDOR NA INTERNET\033[0m")
    print("  \033[93m   O acesso exige usuário e senha — compartilhe as credenciais apenas")
    print("     com quem deve operar a revisão, e encerre o servidor ao terminar.\033[0m")
    print("\033[91m" + "─" * 70 + "\033[0m\n")

    print("\033[92m" + "─" * 70 + "\033[0m")
    print("  \033[93m🌐 ACESSE O RSAC V2 DE QUALQUER LUGAR (PC, CELULAR, TABLET):\033[0m\n")
    print(f"  👉 \033[1;92m{public_url}\033[0m\n")

    if copied:
        print("  \033[96m📋 Link copiado automaticamente para a sua Área de Transferência!\033[0m\n")

    # Link Netlify (se houver)
    netlify_url = config.get("netlify_url", "").strip()
    if netlify_url:
        clean_net = netlify_url.rstrip("/")
        net_full = f"{clean_net}/#/?api_url={public_url}"
        print(f"  🌐 \033[94mLink Netlify Direto:\033[0m\n     {net_full}\n")

    # QR Code no terminal
    print_qr_code(public_url)

    print("\033[92m" + "═" * 70 + "\033[0m")
    print("  \033[97m[O]\033[0m Abrir no Navegador    \033[97m[C]\033[0m Copiar Link    \033[97m[Q]\033[0m Encerrar Servidor")
    print("\033[92m" + "═" * 70 + "\033[0m\n")

    if config.get("auto_open_browser", False):
        webbrowser.open(public_url)

    # Loop de comandos interativos
    while not _is_shutting_down:
        try:
            choice = input("\033[93mComando [O/C/Q] > \033[0m").strip().lower()
            if choice in ("o", "open"):
                webbrowser.open(public_url)
                print("\033[92m[*] Abrindo link no navegador padrão...\033[0m")
            elif choice in ("c", "copy"):
                copy_to_clipboard(public_url)
                print("\033[92m[✓] Link copiado para a Área de Transferência!\033[0m")
            elif choice in ("q", "quit", "exit"):
                break
            else:
                print("\033[90mOpções válidas: [O] Abrir no navegador, [C] Copiar link, [Q] Sair\033[0m")
        except (KeyboardInterrupt, EOFError):
            break

    cleanup()


if __name__ == "__main__":
    main()
