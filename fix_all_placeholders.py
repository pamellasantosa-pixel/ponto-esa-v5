#!/usr/bin/env python3
"""Script para substituir todos os placeholders ? por %s no app_v5_final.py"""

import re

# Ler o arquivo (tenta UTF-8, fallback para latin-1)
try:
    with open('ponto_esa_v5/app_v5_final.py', 'r', encoding='utf-8') as f:
        content = f.read()
except UnicodeDecodeError:
    with open('ponto_esa_v5/app_v5_final.py', 'r', encoding='latin-1') as f:
        content = f.read()

# Contar placeholders antes
count_before = content.count('?')
print(f"Placeholders '?' encontrados: {count_before}")

# Substituir todos os ? que não estejam dentro de strings
# Padrão: ? seguido de vírgula, parêntese fechado, ou espaço
content = re.sub(r'\?(?=\s*[,\)])', '%s', content)

# Contar depois
count_after = content.count('?')
print(f"Placeholders '?' restantes: {count_after}")
print(f"Substituições feitas: {count_before - count_after}")

# Salvar o arquivo sempre como UTF-8
with open('ponto_esa_v5/app_v5_final.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print("✅ Arquivo atualizado com sucesso!")
