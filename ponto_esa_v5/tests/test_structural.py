"""Testes estruturais para thread-safety e SQL injection prevention."""

import sys
import os
import threading
import hashlib
import re

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestThreadSafetyStructural:
    """Verifica que locks existem nos módulos corretos."""

    def test_database_tem_pool_lock(self):
        """database.py deve ter _pool_conn_lock para proteger _pool_connections."""
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database.py")
        content = open(path, encoding="utf-8").read()
        assert "_pool_conn_lock" in content, "database.py deve conter _pool_conn_lock"
        assert "threading.Lock()" in content, "database.py deve usar threading.Lock()"
        # Verificar que get_connection e return_connection usam o lock
        assert "with _pool_conn_lock:" in content, "database.py deve usar 'with _pool_conn_lock:'"

    def test_notifications_tem_lock(self):
        """notifications.py deve ter self._lock para proteger active_notifications."""
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "notifications.py")
        content = open(path, encoding="utf-8").read()
        assert "self._lock" in content, "notifications.py deve conter self._lock"
        assert "threading.Lock()" in content, "notifications.py deve usar threading.Lock()"

    def test_geocoding_tem_cache_lock(self):
        """geocoding.py deve ter _endereco_cache_lock."""
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "geocoding.py")
        content = open(path, encoding="utf-8").read()
        assert "_endereco_cache_lock" in content, "geocoding.py deve conter _endereco_cache_lock"
        assert "threading.Lock()" in content, "geocoding.py deve usar threading.Lock()"


class TestSQLInjectionPrevention:
    """Verifica que nenhuma query SQL usa interpolação direta de variáveis de usuário."""

    def _get_python_files(self):
        """Retorna todos os .py no diretório do projeto."""
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return [
            os.path.join(project_dir, f)
            for f in os.listdir(project_dir)
            if f.endswith(".py") and not f.startswith("test_")
        ]

    def test_nenhum_execute_com_concatenacao(self):
        """Nenhum cursor.execute() deve usar concatenação (+) para construir SQL."""
        pattern = re.compile(r'\.execute\([^)]*["\'][^)]*\+[^)]*\)')
        violations = []
        for fpath in self._get_python_files():
            with open(fpath, encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    if pattern.search(line) and "SQL_PLACEHOLDER" not in line:
                        violations.append(f"{os.path.basename(fpath)}:{i}: {line.strip()}")
        assert not violations, f"SQL concatenation found:\n" + "\n".join(violations)

    def test_nenhum_execute_com_format(self):
        """Nenhum cursor.execute() deve usar .format() para construir SQL."""
        pattern = re.compile(r'\.execute\(.*\.format\(')
        violations = []
        for fpath in self._get_python_files():
            with open(fpath, encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    if pattern.search(line):
                        violations.append(f"{os.path.basename(fpath)}:{i}: {line.strip()}")
        assert not violations, f"SQL .format() found:\n" + "\n".join(violations)


class TestBareExceptElimination:
    """Verifica que não existem bare excepts (except:) no projeto."""

    def test_nenhum_bare_except(self):
        """Nenhum arquivo .py deve ter 'except:' sem tipo de exceção."""
        pattern = re.compile(r'^\s*except\s*:\s*$')
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        violations = []
        for f in os.listdir(project_dir):
            if not f.endswith(".py"):
                continue
            fpath = os.path.join(project_dir, f)
            with open(fpath, encoding="utf-8") as fp:
                for i, line in enumerate(fp, 1):
                    if pattern.match(line):
                        violations.append(f"{f}:{i}: {line.strip()}")
        assert not violations, f"Bare excepts found:\n" + "\n".join(violations)


class TestDatetimeNowElimination:
    """Verifica que datetime.now() sem timezone foi eliminado do projeto."""

    def test_nenhum_datetime_now_sem_tz(self):
        """Nenhum arquivo principal deve usar datetime.now() sem timezone em código executável."""
        pattern = re.compile(r'datetime\.now\(\s*\)')
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        violations = []
        for f in os.listdir(project_dir):
            if not f.endswith(".py") or f.startswith("test_"):
                continue
            fpath = os.path.join(project_dir, f)
            with open(fpath, encoding="utf-8") as fp:
                in_docstring = False
                for i, line in enumerate(fp, 1):
                    stripped = line.strip()
                    # Rastrear blocos de docstring
                    if '"""' in stripped or "'''" in stripped:
                        count = stripped.count('"""') + stripped.count("'''")
                        if count == 1:
                            in_docstring = not in_docstring
                        # Linha com abertura e fechamento de docstring na mesma linha: ignorar
                        continue
                    if in_docstring:
                        continue
                    # Ignorar comentários
                    if stripped.startswith("#"):
                        continue
                    if pattern.search(line):
                        violations.append(f"{f}:{i}: {stripped}")
        assert not violations, f"datetime.now() without tz found:\n" + "\n".join(violations)


class TestBcryptMigration:
    """Verifica que SHA256 não é mais usado para hash de novas senhas."""

    def test_nenhum_sha256_para_senha_em_app(self):
        """app_v5_final.py não deve usar hashlib.sha256 para senhas."""
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        fpath = os.path.join(project_dir, "app_v5_final.py")
        with open(fpath, encoding="utf-8") as f:
            content = f.read()
        # Buscar padrão hashlib.sha256(...).hexdigest() usado para senhas
        matches = re.findall(r'hashlib\.sha256\(.*?\.encode\(\)\)\.hexdigest\(\)', content)
        assert len(matches) == 0, f"SHA256 password hash still in app: {matches}"

    def test_password_utils_usa_bcrypt(self):
        """password_utils.py deve importar e usar bcrypt."""
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        fpath = os.path.join(project_dir, "password_utils.py")
        with open(fpath, encoding="utf-8") as f:
            content = f.read()
        assert "import bcrypt" in content
        assert "bcrypt.hashpw" in content
        assert "bcrypt.checkpw" in content


class TestAtomicTransactions:
    """Verifica que as funções de atomicidade aceitam conn_external."""

    def test_jornada_semanal_aceita_conn_external(self):
        """salvar_jornada_semanal deve ter parâmetro conn_external."""
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        fpath = os.path.join(project_dir, "jornada_semanal_system.py")
        with open(fpath, encoding="utf-8") as f:
            content = f.read()
        assert "conn_external=None" in content, "salvar_jornada_semanal must accept conn_external"

    def test_registrar_ponto_aceita_conn_external(self):
        """registrar_ponto em app_v5_final.py deve ter parâmetro conn_external."""
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        fpath = os.path.join(project_dir, "app_v5_final.py")
        with open(fpath, encoding="utf-8") as f:
            content = f.read()
        assert "def registrar_ponto(" in content
        # Encontrar a assinatura da função
        match = re.search(r'def registrar_ponto\([^)]+\)', content)
        assert match, "registrar_ponto must exist"
        assert "conn_external" in match.group(0), "registrar_ponto must accept conn_external"
