"""
Utilitário de hash de senhas com bcrypt + migração transparente de SHA256 legado.

Estratégia de migração:
1. Novos usuários → bcrypt diretamente.
2. Login de usuário existente → verifica hash:
   a) Se começa com "$2b$" → bcrypt, verifica normalmente.
   b) Senão → assume SHA256 legado, verifica via sha256, e se válido,
      re-hash para bcrypt in-place (upgrade transparente).
3. Nenhum usuário fica sem acesso durante a migração.
"""

import hashlib
import logging

import bcrypt

from database import get_connection, return_connection, SQL_PLACEHOLDER

logger = logging.getLogger(__name__)


def hash_password(plain: str) -> str:
    """Gera hash bcrypt com salt automático para uma senha em texto plano."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _is_bcrypt(hashed: str) -> bool:
    """Verifica se o hash já é bcrypt (prefixo $2b$ ou $2a$)."""
    if not hashed or not isinstance(hashed, str):
        return False
    return hashed.startswith(("$2b$", "$2a$", "$2y$"))


def _verify_sha256_legacy(plain: str, hashed: str) -> bool:
    """Verifica senha contra hash SHA256 legado (sem salt)."""
    if not hashed or not isinstance(hashed, str):
        return False
    return hashlib.sha256(plain.encode()).hexdigest() == hashed


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica senha contra hash (bcrypt ou SHA256 legado)."""
    if not hashed:
        return False
    if _is_bcrypt(hashed):
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    return _verify_sha256_legacy(plain, hashed)


def verify_and_upgrade(plain: str, hashed: str, usuario: str) -> bool:
    """Verifica senha e, se for SHA256 legado válido, faz upgrade para bcrypt.
    
    Args:
        plain: Senha em texto plano digitada pelo usuário.
        hashed: Hash armazenado no banco.
        usuario: Login do usuário (para UPDATE).
    
    Returns:
        True se a senha é válida, False caso contrário.
    """
    if not hashed:
        return False
    if _is_bcrypt(hashed):
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    
    # Verificar SHA256 legado
    if not _verify_sha256_legacy(plain, hashed):
        return False
    
    # Senha SHA256 válida → upgrade para bcrypt
    try:
        new_hash = hash_password(plain)
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE usuarios SET senha = {SQL_PLACEHOLDER} WHERE usuario = {SQL_PLACEHOLDER}",
                (new_hash, usuario),
            )
            conn.commit()
            logger.info("Hash de senha migrado para bcrypt: %s", usuario)
        finally:
            return_connection(conn)
    except Exception as exc:
        # Falha no upgrade não impede o login
        logger.warning("Falha ao migrar hash para bcrypt para %s: %s", usuario, exc)
    
    return True
