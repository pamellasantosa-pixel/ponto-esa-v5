"""
Módulo de Validação - Ponto ExSA
================================
Funções de validação de dados (CPF, E-mail, etc.)

Implementa algoritmos oficiais de validação.

@author: Pâmella SAR - Expressão Socioambiental
@version: 1.0.0
"""

import re
from typing import Tuple, Optional


def validar_cpf(cpf: str) -> Tuple[Optional[str], bool, Optional[str]]:
    """
    Valida CPF usando o algoritmo oficial dos dígitos verificadores.
    
    O algoritmo da Receita Federal utiliza dois dígitos verificadores
    calculados através de multiplicações e somas dos dígitos anteriores.
    
    Args:
        cpf: String do CPF (com ou sem formatação)
        
    Returns:
        Tuple contendo:
        - cpf_limpo: CPF apenas com números (ou None se inválido)
        - is_valid: True se válido, False caso contrário
        - mensagem_erro: Mensagem de erro (ou None se válido)
        
    Exemplos:
        >>> validar_cpf("123.456.789-09")
        ('12345678909', True, None)
        >>> validar_cpf("111.111.111-11")
        (None, False, "CPF inválido (todos os dígitos iguais)")
    """
    if not cpf:
        return None, False, "CPF é obrigatório"
    
    # Remove caracteres não numéricos (pontos, traços, espaços)
    cpf_limpo = ''.join(filter(str.isdigit, str(cpf)))
    
    # Verifica se tem 11 dígitos
    if len(cpf_limpo) != 11:
        return None, False, "CPF deve ter 11 dígitos"
    
    # Verifica se todos os dígitos são iguais (CPFs inválidos conhecidos)
    # Ex: 000.000.000-00, 111.111.111-11, etc.
    if cpf_limpo == cpf_limpo[0] * 11:
        return None, False, "CPF inválido (sequência repetida)"
    
    # ============================================
    # CÁLCULO DO PRIMEIRO DÍGITO VERIFICADOR
    # ============================================
    # Multiplica os 9 primeiros dígitos por pesos de 10 a 2
    # Soma os resultados
    # Divide por 11 e obtém o resto
    # Se resto < 2, dígito = 0; senão, dígito = 11 - resto
    
    soma = 0
    for i in range(9):
        soma += int(cpf_limpo[i]) * (10 - i)
    
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    # Verifica primeiro dígito verificador
    if int(cpf_limpo[9]) != digito1:
        return None, False, "CPF inválido (dígito verificador incorreto)"
    
    # ============================================
    # CÁLCULO DO SEGUNDO DÍGITO VERIFICADOR
    # ============================================
    # Multiplica os 10 primeiros dígitos por pesos de 11 a 2
    # Soma os resultados
    # Divide por 11 e obtém o resto
    # Se resto < 2, dígito = 0; senão, dígito = 11 - resto
    
    soma = 0
    for i in range(10):
        soma += int(cpf_limpo[i]) * (11 - i)
    
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    # Verifica segundo dígito verificador
    if int(cpf_limpo[10]) != digito2:
        return None, False, "CPF inválido (dígito verificador incorreto)"
    
    # CPF válido!
    return cpf_limpo, True, None


def formatar_cpf(cpf: str) -> str:
    """
    Formata CPF para exibição (XXX.XXX.XXX-XX).
    
    Args:
        cpf: CPF apenas com números
        
    Returns:
        CPF formatado ou string original se inválido
    """
    cpf_limpo = ''.join(filter(str.isdigit, str(cpf)))
    
    if len(cpf_limpo) != 11:
        return cpf
    
    return f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"


def validar_email(email: str) -> Tuple[Optional[str], bool, Optional[str]]:
    """
    Valida formato de e-mail.
    
    Args:
        email: String do e-mail
        
    Returns:
        Tuple contendo:
        - email_limpo: E-mail normalizado (lowercase, sem espaços)
        - is_valid: True se válido, False caso contrário
        - mensagem_erro: Mensagem de erro (ou None se válido)
        
    Exemplos:
        >>> validar_email("Usuario@Empresa.com")
        ('usuario@empresa.com', True, None)
        >>> validar_email("email_invalido")
        (None, False, "Formato de e-mail inválido")
    """
    if not email or not str(email).strip():
        return None, False, "E-mail é obrigatório"
    
    email_limpo = str(email).strip().lower()
    
    # Regex para validação de e-mail (RFC 5322 simplificado)
    # Aceita: letras, números, pontos, underscores, hífens, percentual, mais
    # Seguido de @ e domínio válido
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email_limpo):
        return None, False, "Formato de e-mail inválido"
    
    # Verificações adicionais
    if '..' in email_limpo:
        return None, False, "E-mail não pode conter pontos consecutivos"
    
    local_part, domain = email_limpo.split('@')
    
    if len(local_part) > 64:
        return None, False, "Parte local do e-mail muito longa"
    
    if len(domain) > 255:
        return None, False, "Domínio do e-mail muito longo"
    
    return email_limpo, True, None


def validar_senha(senha: str, confirmar_senha: str = None) -> Tuple[bool, Optional[str]]:
    """
    Valida força da senha.
    
    Args:
        senha: Senha a validar
        confirmar_senha: Confirmação da senha (opcional)
        
    Returns:
        Tuple contendo:
        - is_valid: True se válida, False caso contrário
        - mensagem_erro: Mensagem de erro (ou None se válida)
    """
    if not senha:
        return False, "Senha é obrigatória"
    
    if len(senha) < 6:
        return False, "Senha deve ter pelo menos 6 caracteres"
    
    if confirmar_senha is not None and senha != confirmar_senha:
        return False, "As senhas não conferem"
    
    return True, None


def validar_data_nascimento(data_nascimento, idade_minima: int = 16) -> Tuple[bool, Optional[str]]:
    """
    Valida data de nascimento.
    
    Args:
        data_nascimento: Data de nascimento
        idade_minima: Idade mínima permitida (default: 16)
        
    Returns:
        Tuple contendo:
        - is_valid: True se válida, False caso contrário
        - mensagem_erro: Mensagem de erro (ou None se válida)
    """
    from datetime import date, timedelta
    
    if data_nascimento is None:
        return False, "Data de nascimento é obrigatória"
    
    hoje = date.today()
    idade = hoje.year - data_nascimento.year
    
    # Ajustar se ainda não fez aniversário este ano
    if (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day):
        idade -= 1
    
    if idade < idade_minima:
        return False, f"Idade mínima é {idade_minima} anos"
    
    if idade > 120:
        return False, "Data de nascimento inválida"
    
    return True, None


# CPFs conhecidos como inválidos (para testes)
CPFS_INVALIDOS = [
    '00000000000',
    '11111111111',
    '22222222222',
    '33333333333',
    '44444444444',
    '55555555555',
    '66666666666',
    '77777777777',
    '88888888888',
    '99999999999',
]


__all__ = [
    'validar_cpf',
    'formatar_cpf',
    'validar_email',
    'validar_senha',
    'validar_data_nascimento',
    'CPFS_INVALIDOS'
]
