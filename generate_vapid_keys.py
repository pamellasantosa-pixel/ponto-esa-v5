#!/usr/bin/env python3
"""
Script para gerar chaves VAPID para Web Push Notifications.
Execute este script UMA VEZ para gerar as chaves e adicione-as ao .env

Uso:
    python generate_vapid_keys.py

As chaves geradas devem ser adicionadas ao arquivo .env:
    VAPID_PUBLIC_KEY=<chave_publica>
    VAPID_PRIVATE_KEY=<chave_privada>
    VAPID_CLAIM_EMAIL=mailto:seu@email.com
"""

import base64
import os

try:
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
except ImportError:
    print("❌ Erro: biblioteca 'cryptography' não instalada.")
    print("Execute: pip install cryptography")
    exit(1)


def generate_vapid_keys():
    """
    Gera um par de chaves VAPID (ECDSA P-256) para Web Push.
    
    Retorna:
        dict: Contendo 'public_key' e 'private_key' em formato base64url
    """
    # Gerar chave privada ECDSA usando curva P-256 (SECP256R1)
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    
    # Extrair chave pública
    public_key = private_key.public_key()
    
    # Serializar chave privada em formato DER (raw)
    private_numbers = private_key.private_numbers()
    private_bytes = private_numbers.private_value.to_bytes(32, byteorder='big')
    
    # Serializar chave pública em formato não comprimido (65 bytes: 0x04 + x + y)
    public_numbers = public_key.public_numbers()
    public_bytes = b'\x04' + \
        public_numbers.x.to_bytes(32, byteorder='big') + \
        public_numbers.y.to_bytes(32, byteorder='big')
    
    # Converter para base64url (sem padding)
    private_key_b64 = base64.urlsafe_b64encode(private_bytes).rstrip(b'=').decode('ascii')
    public_key_b64 = base64.urlsafe_b64encode(public_bytes).rstrip(b'=').decode('ascii')
    
    return {
        'public_key': public_key_b64,
        'private_key': private_key_b64
    }


def main():
    print("=" * 60)
    print("🔐 Gerador de Chaves VAPID para Web Push Notifications")
    print("=" * 60)
    print()
    
    keys = generate_vapid_keys()
    
    print("✅ Chaves VAPID geradas com sucesso!")
    print()
    print("-" * 60)
    print("📋 Adicione as seguintes linhas ao seu arquivo .env:")
    print("-" * 60)
    print()
    print(f"VAPID_PUBLIC_KEY={keys['public_key']}")
    print(f"VAPID_PRIVATE_KEY={keys['private_key']}")
    print("VAPID_CLAIM_EMAIL=mailto:contato@expressaosa.com.br")
    print()
    print("-" * 60)
    print("📋 Chave pública para usar no JavaScript do frontend:")
    print("-" * 60)
    print()
    print(f"const VAPID_PUBLIC_KEY = '{keys['public_key']}';")
    print()
    print("=" * 60)
    print("⚠️  IMPORTANTE: Guarde a chave PRIVADA em local seguro!")
    print("    Nunca compartilhe ou exponha a chave privada.")
    print("=" * 60)
    
    # Perguntar se deseja salvar no .env automaticamente
    print()
    resposta = input("Deseja adicionar automaticamente ao arquivo .env? (s/N): ").strip().lower()
    
    if resposta == 's':
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        
        # Ler conteúdo existente
        existing_content = ""
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                existing_content = f.read()
        
        # Verificar se já existem chaves VAPID
        if 'VAPID_PUBLIC_KEY' in existing_content or 'VAPID_PRIVATE_KEY' in existing_content:
            print("⚠️  Já existem chaves VAPID no arquivo .env")
            overwrite = input("Deseja substituir? (s/N): ").strip().lower()
            if overwrite != 's':
                print("❌ Operação cancelada.")
                return
            
            # Remover linhas existentes
            lines = existing_content.split('\n')
            lines = [l for l in lines if not l.startswith('VAPID_')]
            existing_content = '\n'.join(lines)
        
        # Adicionar novas chaves
        with open(env_path, 'w') as f:
            f.write(existing_content.rstrip())
            if existing_content and not existing_content.endswith('\n'):
                f.write('\n')
            f.write(f"\n# Chaves VAPID para Web Push Notifications\n")
            f.write(f"VAPID_PUBLIC_KEY={keys['public_key']}\n")
            f.write(f"VAPID_PRIVATE_KEY={keys['private_key']}\n")
            f.write("VAPID_CLAIM_EMAIL=mailto:contato@expressaosa.com.br\n")
        
        print(f"✅ Chaves adicionadas ao arquivo: {env_path}")
        print("⚠️  Lembre-se de adicionar estas variáveis também no Render Dashboard!")


if __name__ == '__main__':
    main()
