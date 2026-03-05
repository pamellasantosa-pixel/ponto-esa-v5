#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script para substituir placeholders SQLite (?) por PostgreSQL (%s)"""

import re

with open('app_v5_final.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Contar ? antes
count_before = content.count('?')

# Substituir ? por %s em queries SQL (dentro de strings)
# Isso substitui ? que aparecem em contextos SQL
content = re.sub(r'\?', '%s', content)

# Contar %s depois
count_after = content.count('%s')

with open('app_v5_final.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'✅ Substituição concluída!')
print(f'   ? encontrados: {count_before}')
print(f'   %s no arquivo: {count_after}')
print('✅ Arquivo atualizado para compatibilidade com PostgreSQL')
