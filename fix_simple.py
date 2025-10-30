#!/usr/bin/env python3
"""Script simples para substituir TODOS os ? por %s"""

# Ler o arquivo (tenta UTF-8, cai para latin-1 se necessário)
try:
    with open('ponto_esa_v5/app_v5_final.py', 'r', encoding='utf-8') as f:
        content = f.read()
except UnicodeDecodeError:
    with open('ponto_esa_v5/app_v5_final.py', 'r', encoding='latin-1') as f:
        content = f.read()

# Contar antes
count_before = content.count(' ?')
print(f"Placeholders ' ?' encontrados: {count_before}")

# Substituir todos os " ?" por " %s"
content = content.replace(' ?', ' %s')

# Contar depois
count_after = content.count(' ?')
print(f"Placeholders ' ?' restantes: {count_after}")
print(f"Substituições feitas: {count_before - count_after}")

# Salvar sempre em UTF-8 para padronizar
with open('ponto_esa_v5/app_v5_final.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print("✅ Concluído!")
