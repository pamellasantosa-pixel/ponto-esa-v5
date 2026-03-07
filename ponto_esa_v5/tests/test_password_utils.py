"""Testes estruturais para password_utils — bcrypt + migração SHA256."""

import hashlib
import sys
import os

import pytest

# Garantir que o módulo ponto_esa_v5 esteja acessível
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from password_utils import (
    hash_password,
    verify_password,
    _is_bcrypt,
    _verify_sha256_legacy,
)


class TestHashPassword:
    """Testes para hash_password (bcrypt)."""

    def test_retorna_string(self):
        result = hash_password("minha_senha")
        assert isinstance(result, str)

    def test_hash_comeca_com_prefixo_bcrypt(self):
        result = hash_password("test123")
        assert result.startswith("$2b$")

    def test_hashes_diferentes_para_mesma_senha(self):
        """Bcrypt usa salt aleatório — hashes devem diferir."""
        h1 = hash_password("mesma_senha")
        h2 = hash_password("mesma_senha")
        assert h1 != h2

    def test_hash_nao_contem_senha_original(self):
        result = hash_password("senha_secreta_123")
        assert "senha_secreta_123" not in result


class TestIsBcrypt:
    """Testes para _is_bcrypt."""

    def test_detecta_prefixo_2b(self):
        assert _is_bcrypt("$2b$12$abcdef")

    def test_detecta_prefixo_2a(self):
        assert _is_bcrypt("$2a$12$abcdef")

    def test_detecta_prefixo_2y(self):
        assert _is_bcrypt("$2y$12$abcdef")

    def test_rejeita_sha256(self):
        sha = hashlib.sha256(b"test").hexdigest()
        assert not _is_bcrypt(sha)

    def test_rejeita_string_vazia(self):
        assert not _is_bcrypt("")


class TestVerifySha256Legacy:
    """Testes para verificação SHA256 legada."""

    def test_sha256_valido(self):
        senha = "minha_senha"
        sha = hashlib.sha256(senha.encode()).hexdigest()
        assert _verify_sha256_legacy(senha, sha) is True

    def test_sha256_invalido(self):
        assert _verify_sha256_legacy("errada", "abc123") is False


class TestVerifyPassword:
    """Testes para verify_password (suporta bcrypt e SHA256)."""

    def test_verifica_bcrypt_correto(self):
        h = hash_password("bcrypt_test")
        assert verify_password("bcrypt_test", h) is True

    def test_rejeita_bcrypt_incorreto(self):
        h = hash_password("bcrypt_test")
        assert verify_password("senha_errada", h) is False

    def test_verifica_sha256_legado(self):
        senha = "legado_test"
        sha = hashlib.sha256(senha.encode()).hexdigest()
        assert verify_password(senha, sha) is True

    def test_rejeita_sha256_incorreto(self):
        sha = hashlib.sha256(b"correta").hexdigest()
        assert verify_password("errada", sha) is False

    def test_senha_vazia_bcrypt(self):
        h = hash_password("")
        assert verify_password("", h) is True
        assert verify_password("nao_vazia", h) is False
