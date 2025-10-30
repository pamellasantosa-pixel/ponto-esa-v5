#!/usr/bin/env python3
"""Converte arquivos de texto para UTF-8 a partir de latin-1.
Uso: python tools/convert_to_utf8.py caminho/para/arquivo
"""
import sys
from pathlib import Path


def convert(path: Path):
    data = path.read_bytes()
    try:
        # Se já for UTF-8, não faz nada
        data.decode('utf-8')
        print(f"Já está em UTF-8: {path}")
        return False
    except UnicodeDecodeError:
        # Tenta latin-1
        text = data.decode('latin-1')
        path.write_text(text, encoding='utf-8', newline='\n')
        print(f"Convertido para UTF-8: {path}")
        return True


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python tools/convert_to_utf8.py <arquivo1> [arquivo2 ...]")
        sys.exit(1)
    changed = 0
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.exists() and p.is_file():
            if convert(p):
                changed += 1
        else:
            print(f"Ignorado (não encontrado/arquivo): {p}")
    print(f"Arquivos convertidos: {changed}")
