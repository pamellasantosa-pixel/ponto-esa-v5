#!/usr/bin/env python3
"""Substituir padrões específicos de ?"""

import re

with open('ponto_esa_v5/app_v5_final.py', 'r', encoding='latin-1') as f:
    content = f.read()

original = content

# Padrões para substituir
patterns = [
    (r'>=\s*\?', '>= %s'),
    (r'LIKE\s*\?', 'LIKE %s'),
    (r'BETWEEN\s*\?\s*AND\s*\?', 'BETWEEN %s AND %s'),
    (r'=\s*\?\s+AND', '= %s AND'),
]

for pattern, replacement in patterns:
    content = re.sub(pattern, replacement, content)

# Contar mudanças
changes = len([i for i, (c1, c2) in enumerate(
    zip(original, content)) if c1 != c2])
print(f"Caracteres modificados: {changes}")

with open('ponto_esa_v5/app_v5_final.py', 'w', encoding='latin-1') as f:
    f.write(content)

print("✅ Substituições específicas concluídas!")
