#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para aplicar TODAS as correções no app_v5_final.py
Corrige: timezone em todas as funções, SQL placeholders, expander aninhado
"""

import re

# Ler arquivo
with open('ponto_esa_v5/app_v5_final.py', 'r', encoding='utf-8') as f:
    content = f.read()

print(f"Tamanho original: {len(content)} bytes")
print(f"Linhas originais: {content.count(chr(10)) + 1}")

changes_made = []

# 1. Substituir datetime.now() por get_datetime_br() em todo o código
# Exceto em definições e comparações que já usam timezone
old_datetime_now = re.compile(r'datetime\.now\(\)(?!\s*\(TIMEZONE_BR\))')
matches = old_datetime_now.findall(content)
if matches:
    content = old_datetime_now.sub('get_datetime_br()', content)
    changes_made.append(f"datetime.now() -> get_datetime_br(): {len(matches)} ocorrências")

# 2. Atualizar registrar_ponto() para usar SQL_PLACEHOLDER
old_registrar = '''        cursor.execute(\'\'\'
            INSERT INTO registros_ponto 
            (usuario, tipo, data_hora, latitude, longitude, precisao, observacao, foto_path, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        \'\'\', (
            st.session_state.usuario,
            tipo,
            agora.strftime('%Y-%m-%d %H:%M:%S'),
            latitude,
            longitude,
            precisao,
            observacao,
            foto_path if foto_path else None,
            'pendente'
        ))'''

new_registrar = '''        placeholders = ', '.join([SQL_PLACEHOLDER] * 9)
        cursor.execute(f\'\'\'
            INSERT INTO registros_ponto 
            (usuario, tipo, data_hora, latitude, longitude, precisao, observacao, foto_path, status)
            VALUES ({placeholders})
        \'\'\', (
            st.session_state.usuario,
            tipo,
            agora.strftime('%Y-%m-%d %H:%M:%S'),
            latitude,
            longitude,
            precisao,
            observacao,
            foto_path if foto_path else None,
            'pendente'
        ))'''

if old_registrar in content:
    content = content.replace(old_registrar, new_registrar)
    changes_made.append("registrar_ponto() atualizada com SQL_PLACEHOLDER")

# 3. Atualizar obter_registros_usuario() para usar SQL_PLACEHOLDER
old_obter_registros = '''    cursor.execute(\'\'\'
        SELECT * FROM registros_ponto 
        WHERE usuario = ?
        ORDER BY data_hora DESC
    \'\'\', (usuario,))'''

new_obter_registros = f'''    cursor.execute(f\'\'\'
        SELECT * FROM registros_ponto 
        WHERE usuario = {{SQL_PLACEHOLDER}}
        ORDER BY data_hora DESC
    \'\'\', (usuario,))'''

if old_obter_registros in content:
    content = content.replace(old_obter_registros, new_obter_registros)
    changes_made.append("obter_registros_usuario() atualizada com SQL_PLACEHOLDER")

# 4. Corrigir expander aninhado (linha ~3190)
old_expander = '''                with st.expander("🔑 Alterar Senha"):'''
new_expander = '''                st.markdown("**🔑 Alterar Senha:**")
                if True:  # Removido expander aninhado'''

if old_expander in content:
    content = content.replace(old_expander, new_expander)
    changes_made.append("Expander aninhado corrigido")

# 5. Atualizar corrigir_registro_ponto() para usar SQL_PLACEHOLDER
old_corrigir = '''        cursor.execute(\'\'\'
            UPDATE registros_ponto
            SET data_hora = ?, tipo = ?, observacao = ?
            WHERE id = ? AND usuario = ?
        \'\'\', (
            novo_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            novo_tipo,
            nova_obs,
            registro_id,
            usuario
        ))'''

new_corrigir = '''        placeholders_update = [SQL_PLACEHOLDER] * 5
        cursor.execute(f\'\'\'
            UPDATE registros_ponto
            SET data_hora = {SQL_PLACEHOLDER}, tipo = {SQL_PLACEHOLDER}, observacao = {SQL_PLACEHOLDER}
            WHERE id = {SQL_PLACEHOLDER} AND usuario = {SQL_PLACEHOLDER}
        \'\'\', (
            novo_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            novo_tipo,
            nova_obs,
            registro_id,
            usuario
        ))'''

if old_corrigir in content:
    content = content.replace(old_corrigir, new_corrigir)
    changes_made.append("corrigir_registro_ponto() atualizada com SQL_PLACEHOLDER")

# 6. Atualizar docstring no topo
old_docstring = '''"""
Ponto ExSA v5.0 - Sistema de Controle de Ponto
Versão com Horas Extras, Banco de Horas, GPS Real e Melhorias
Desenvolvido por Pâmella SAR para Expressão Socioambiental Pesquisa e Projetos
Última atualização: 24/10/2025 11:30 - Correção de timezone (Brasília) e expanders
"""'''

new_docstring = '''"""
Ponto ExSA v5.0 - Sistema de Controle de Ponto
Versão com Horas Extras, Banco de Horas, GPS Real e Melhorias
Desenvolvido por Pâmella SAR para Expressão Socioambiental Pesquisa e Projetos
Última atualização: 24/10/2025 14:00 - Timezone BR, PostgreSQL, Expanders corrigidos
"""'''

if old_docstring in content:
    content = content.replace(old_docstring, new_docstring)
    changes_made.append("Docstring atualizada")

print(f"\n{'='*60}")
print("MUDANÇAS APLICADAS:")
print(f"{'='*60}")
for i, change in enumerate(changes_made, 1):
    print(f"{i}. {change}")

print(f"\nTamanho após mudanças: {len(content)} bytes")
print(f"Linhas após mudanças: {content.count(chr(10)) + 1}")

# Salvar com LF (Unix line endings)
with open('ponto_esa_v5/app_v5_final.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print("\n✅ Arquivo salvo com line endings LF!")

# Verificação final
with open('ponto_esa_v5/app_v5_final.py', 'r', encoding='utf-8') as f:
    verification = f.read()
    
print(f"\n{'='*60}")
print("VERIFICAÇÃO FINAL:")
print(f"{'='*60}")
print(f"✓ SQL_PLACEHOLDER presente: {verification.count('SQL_PLACEHOLDER')} ocorrências")
print(f"✓ get_datetime_br presente: {verification.count('get_datetime_br')} ocorrências")
print(f"✓ datetime.now() restantes: {verification.count('datetime.now()')}")
print(f"✓ import pytz presente: {'import pytz' in verification}")
print(f"✓ Expander aninhado removido: {'with st.expander' in verification.split('Alterar Senha')[1].split('\n')[0] if 'Alterar Senha' in verification else 'N/A'}")
