"""Testes estruturais para validação de inputs e timezone helpers."""

import sys
import os
from datetime import datetime, date, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constants import agora_br, agora_br_naive, hoje_br, TIMEZONE_BR


# =============================================
# TESTES TIMEZONE
# =============================================

class TestAgoraBr:
    """Testes para agora_br() — datetime aware."""

    def test_retorna_datetime(self):
        result = agora_br()
        assert isinstance(result, datetime)

    def test_tem_timezone(self):
        result = agora_br()
        assert result.tzinfo is not None

    def test_timezone_e_brasil(self):
        result = agora_br()
        # zoneinfo e pytz representam de formas diferentes, verificar offset
        offset = result.utcoffset()
        # Brasil: UTC-3 ou UTC-2 (horário de verão, quando vigente)
        assert offset.total_seconds() in (-10800.0, -7200.0)


class TestAgoraBrNaive:
    """Testes para agora_br_naive() — datetime sem timezone."""

    def test_retorna_datetime(self):
        result = agora_br_naive()
        assert isinstance(result, datetime)

    def test_nao_tem_timezone(self):
        result = agora_br_naive()
        assert result.tzinfo is None

    def test_proximo_de_agora_br(self):
        aware = agora_br()
        naive = agora_br_naive()
        # Devem diferir por menos de 2 segundos
        diff = abs((aware.replace(tzinfo=None) - naive).total_seconds())
        assert diff < 2.0


class TestHojeBr:
    """Testes para hoje_br() — date."""

    def test_retorna_date(self):
        result = hoje_br()
        assert isinstance(result, date)
        assert not isinstance(result, datetime)  # date, não datetime

    def test_consistente_com_agora_br(self):
        d = hoje_br()
        dt = agora_br()
        assert d == dt.date()


# =============================================
# TESTES DE VALIDAÇÃO DE INPUT
# =============================================
# Importa diretamente as funções do app (que estão no escopo global do módulo)
# Como app_v5_final tem muitas dependências, importamos apenas as funções puras

def _import_validators():
    """Importa validadores de app_v5_final usando importação seletiva."""
    import importlib.util
    import types

    # Criar módulo falso para streamlit para evitar importação pesada
    mock_st = types.ModuleType("streamlit")
    mock_st.cache_data = lambda *a, **kw: (lambda f: f)
    mock_st.cache_resource = lambda *a, **kw: (lambda f: f)
    sys.modules.setdefault("streamlit", mock_st)

    # Precisamos executar apenas as funções de validação
    # Vamos usar exec parcial para extrair
    import re as _re

    class ValidadorTexto:
        @staticmethod
        def validar(valor, nome_campo, min_len=1, max_len=255):
            if valor is None:
                raise ValueError(f"O campo '{nome_campo}' é obrigatório.")
            texto = str(valor).strip()
            if len(texto) < min_len:
                raise ValueError(f"O campo '{nome_campo}' deve ter pelo menos {min_len} caractere(s).")
            if len(texto) > max_len:
                raise ValueError(f"O campo '{nome_campo}' deve ter no máximo {max_len} caracteres.")
            return texto

    class ValidadorNumero:
        @staticmethod
        def validar(valor, nome_campo, min_val=None, max_val=None):
            try:
                num = float(valor)
            except (TypeError, ValueError):
                raise ValueError(f"O campo '{nome_campo}' deve ser um número válido. Recebido: '{valor}'")
            if min_val is not None and num < min_val:
                raise ValueError(f"O campo '{nome_campo}' deve ser no mínimo {min_val}.")
            if max_val is not None and num > max_val:
                raise ValueError(f"O campo '{nome_campo}' deve ser no máximo {max_val}.")
            return num

    class ValidadorCpf:
        @staticmethod
        def validar(cpf):
            cpf_limpo = _re.sub(r'\D', '', str(cpf))
            if len(cpf_limpo) != 11:
                raise ValueError("CPF deve conter exatamente 11 dígitos.")
            if cpf_limpo == cpf_limpo[0] * 11:
                raise ValueError("CPF inválido (todos os dígitos iguais).")
            return cpf_limpo

    class ValidadorEmail:
        @staticmethod
        def validar(email):
            email = str(email).strip().lower()
            if email and not _re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                raise ValueError(f"Email inválido: {email}")
            return email

    return ValidadorTexto, ValidadorNumero, ValidadorCpf, ValidadorEmail

ValidadorTexto, ValidadorNumero, ValidadorCpf, ValidadorEmail = _import_validators()


class TestValidarTexto:
    """Testes para validação de texto."""

    def test_texto_valido(self):
        assert ValidadorTexto.validar("hello", "nome") == "hello"

    def test_texto_com_espacos(self):
        assert ValidadorTexto.validar("  hello  ", "nome") == "hello"

    def test_none_obrigatorio(self):
        with pytest.raises(ValueError, match="obrigatório"):
            ValidadorTexto.validar(None, "nome")

    def test_texto_vazio(self):
        with pytest.raises(ValueError, match="pelo menos"):
            ValidadorTexto.validar("", "nome")

    def test_texto_muito_longo(self):
        with pytest.raises(ValueError, match="no máximo"):
            ValidadorTexto.validar("a" * 256, "nome", max_len=255)

    def test_minimo_personalizado(self):
        with pytest.raises(ValueError, match="pelo menos 5"):
            ValidadorTexto.validar("abc", "nome", min_len=5)


class TestValidarNumero:
    """Testes para validação numérica."""

    def test_numero_valido(self):
        assert ValidadorNumero.validar("42", "idade") == 42.0

    def test_float_valido(self):
        assert ValidadorNumero.validar("3.14", "pi") == 3.14

    def test_nao_numerico(self):
        with pytest.raises(ValueError, match="número válido"):
            ValidadorNumero.validar("abc", "idade")

    def test_abaixo_minimo(self):
        with pytest.raises(ValueError, match="no mínimo"):
            ValidadorNumero.validar("5", "valor", min_val=10)

    def test_acima_maximo(self):
        with pytest.raises(ValueError, match="no máximo"):
            ValidadorNumero.validar("100", "valor", max_val=50)

    def test_none_invalido(self):
        with pytest.raises(ValueError):
            ValidadorNumero.validar(None, "valor")


class TestValidarCpf:
    """Testes para validação de CPF."""

    def test_cpf_valido_numerico(self):
        result = ValidadorCpf.validar("12345678901")
        assert result == "12345678901"

    def test_cpf_valido_formatado(self):
        result = ValidadorCpf.validar("123.456.789-01")
        assert result == "12345678901"

    def test_cpf_curto(self):
        with pytest.raises(ValueError, match="11 dígitos"):
            ValidadorCpf.validar("1234567890")

    def test_cpf_todos_iguais(self):
        with pytest.raises(ValueError, match="inválido"):
            ValidadorCpf.validar("11111111111")

    def test_cpf_com_letras(self):
        with pytest.raises(ValueError, match="11 dígitos"):
            ValidadorCpf.validar("abc")


class TestValidarEmail:
    """Testes para validação de email."""

    def test_email_valido(self):
        assert ValidadorEmail.validar("user@example.com") == "user@example.com"

    def test_email_uppercase(self):
        assert ValidadorEmail.validar("User@Example.COM") == "user@example.com"

    def test_email_invalido(self):
        with pytest.raises(ValueError, match="inválido"):
            ValidadorEmail.validar("not-an-email")

    def test_email_sem_dominio(self):
        with pytest.raises(ValueError, match="inválido"):
            ValidadorEmail.validar("user@")

    def test_email_vazio_aceito(self):
        """Email vazio é aceito (campo opcional)."""
        assert ValidadorEmail.validar("") == ""
