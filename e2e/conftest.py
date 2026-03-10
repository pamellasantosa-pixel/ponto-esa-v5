import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_http_ready(url: str, timeout_seconds: int = 60) -> None:
    deadline = time.time() + timeout_seconds
    last_err = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return
        except Exception as exc:
            last_err = exc
            time.sleep(0.5)
    raise RuntimeError(f"App nao respondeu em {url}: {last_err}")


def _seed_runtime_database(workspace_root: Path, runtime_dir: Path) -> None:
    import hashlib
    from datetime import date

    if str(workspace_root) not in sys.path:
        sys.path.insert(0, str(workspace_root))

    from ponto_esa_v5.database import (
        SQL_PLACEHOLDER,
        get_connection,
        init_db,
        return_connection,
    )

    init_db()

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            f"DELETE FROM registros_ponto WHERE usuario = {SQL_PLACEHOLDER}",
            ("funcionario",),
        )
        cur.execute(
            f"DELETE FROM solicitacoes_horas_extras WHERE usuario IN ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})",
            ("funcionario", "e2e_user"),
        )

        senha_func = hashlib.sha256("senha_func_123".encode("utf-8")).hexdigest()
        senha_gestor = hashlib.sha256("senha_gestor_123".encode("utf-8")).hexdigest()

        cur.execute(
            f"DELETE FROM usuarios WHERE usuario IN ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})",
            ("funcionario", "gestor", "e2e_user"),
        )
        cur.execute(
            f"INSERT INTO usuarios (usuario, senha, tipo, nome_completo, ativo) VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 1)",
            ("funcionario", senha_func, "funcionario", "Funcionario Padrao"),
        )
        cur.execute(
            f"INSERT INTO usuarios (usuario, senha, tipo, nome_completo, ativo) VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 1)",
            ("gestor", senha_gestor, "gestor", "Gestor Principal"),
        )

        cur.execute(
            f"INSERT INTO solicitacoes_horas_extras (usuario, data, hora_inicio, hora_fim, total_horas, justificativa, aprovador_solicitado, status) VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 'pendente')",
            ("funcionario", date.today().isoformat(), "18:00", "20:00", 2.0, "Demanda de fechamento", "gestor"),
        )
        cur.execute(
            f"INSERT INTO solicitacoes_horas_extras (usuario, data, hora_inicio, hora_fim, total_horas, justificativa, aprovador_solicitado, status, aprovado_por) VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 'aprovado', {SQL_PLACEHOLDER})",
            ("funcionario", date.today().isoformat(), "19:00", "21:00", 2.0, "Relatorio mensal", "gestor", "gestor"),
        )

        conn.commit()
    finally:
        return_connection(conn)


@pytest.fixture(scope="session")
def workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def runtime_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("e2e_runtime")
    (root / "database").mkdir(parents=True, exist_ok=True)
    (root / "uploads").mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture(scope="session")
def app_server(workspace_root: Path, runtime_dir: Path):
    _seed_runtime_database(workspace_root, runtime_dir)

    app_file = workspace_root / "ponto_esa_v5" / "app_v5_final.py"
    port = _find_free_port()
    base_url = f"http://127.0.0.1:{port}"

    env = os.environ.copy()
    if env.get("DATABASE_URL"):
        env["USE_POSTGRESQL"] = "true"
    env["PYTHONPATH"] = str(workspace_root)

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_file),
        "--server.headless=true",
        f"--server.port={port}",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]

    proc = subprocess.Popen(
        cmd,
        cwd=str(workspace_root / "ponto_esa_v5"),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _wait_http_ready(base_url)
        yield {"base_url": base_url, "process": proc}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="function")
def page(app_server):
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        pytest.skip("Playwright nao instalado. Instale requirements-e2e.txt e execute: python -m playwright install chromium")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        pg = context.new_page()
        pg.goto(app_server["base_url"], wait_until="domcontentloaded")
        yield pg
        context.close()
        browser.close()


def login(page, username: str, password: str) -> None:
    page.get_by_label(re.compile("Usuario|Usuário", re.I)).fill(username)
    page.get_by_label(re.compile("Senha", re.I)).fill(password)
    page.get_by_role("button", name=re.compile("Entrar|ENTRAR")).click()


def choose_sidebar_option(page, option_pattern: str) -> None:
    sidebar_select = page.locator('[data-testid="stSidebar"] [data-testid="stSelectbox"]').first
    sidebar_select.locator('div[role="combobox"]').click()
    page.locator('li[role="option"]').filter(has_text=re.compile(option_pattern, re.I)).first.click()
