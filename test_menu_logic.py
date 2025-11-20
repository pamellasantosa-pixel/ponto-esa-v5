#!/usr/bin/env python3
"""
Script para testar a lógica do menu lateral
"""

# Simular os valores que seriam calculados
he_aprovar = 0  # Simular que não há solicitações para aprovar
correcoes_pendentes = 0
atestados_pendentes = 0
total_notif = he_aprovar + correcoes_pendentes + atestados_pendentes

# Construir as opções do menu como no código
opcoes_menu = [
    "🕐 Registrar Ponto",
    "📋 Meus Registros",
    f"🔧 Solicitar Correção de Registro{f' 🔴{correcoes_pendentes}' if correcoes_pendentes > 0 else ''}",
    "🏥 Registrar Ausência",
    f"⏰ Atestado de Horas{f' 🔴{atestados_pendentes}' if atestados_pendentes > 0 else ''}",
    f"🕐 Horas Extras{f' 🔴{he_aprovar}' if he_aprovar > 0 else ''}",
    "📊 Relatórios de Horas Extras",
    "🏦 Meu Banco de Horas",
    "📁 Meus Arquivos",
    f"🔔 Notificações{f' 🔴{total_notif}' if total_notif > 0 else ''}"
]

print("Opções do menu construídas:")
for i, opcao in enumerate(opcoes_menu):
    print(f"{i+1}. '{opcao}'")

print("\nVerificando se '🕐 Horas Extras' está presente:")
horas_extras_opcao = None
for opcao in opcoes_menu:
    if opcao.startswith("🕐 Horas Extras"):
        horas_extras_opcao = opcao
        break

if horas_extras_opcao:
    print(f"✅ Encontrada: '{horas_extras_opcao}'")
    print(f"   - Começa com '🕐 Horas Extras': {horas_extras_opcao.startswith('🕐 Horas Extras')}")
else:
    print("❌ Opção '🕐 Horas Extras' não encontrada!")

print("\nTestando condições de seleção:")
opcao_teste = horas_extras_opcao
print(f"Opção selecionada: '{opcao_teste}'")
print(f"opcao == '🕐 Registrar Ponto': {opcao_teste == '🕐 Registrar Ponto'}")
print(f"opcao.startswith('🔧 Solicitar Correção'): {opcao_teste.startswith('🔧 Solicitar Correção')}")
print(f"opcao == '🏥 Registrar Ausência': {opcao_teste == '🏥 Registrar Ausência'}")
print(f"opcao.startswith('⏰ Atestado de Horas'): {opcao_teste.startswith('⏰ Atestado de Horas')}")
print(f"opcao.startswith('🕐 Horas Extras'): {opcao_teste.startswith('🕐 Horas Extras')}")
print(f"opcao == '📊 Relatórios de Horas Extras': {opcao_teste == '📊 Relatórios de Horas Extras'}")
print(f"opcao == '🏦 Meu Banco de Horas': {opcao_teste == '🏦 Meu Banco de Horas'}")
print(f"opcao == '📁 Meus Arquivos': {opcao_teste == '📁 Meus Arquivos'}")
print(f"opcao.startswith('🔔 Notificações'): {opcao_teste.startswith('🔔 Notificações')}")

if opcao_teste.startswith("🕐 Horas Extras"):
    print("✅ A condição para horas_extras_interface seria atendida!")
else:
    print("❌ A condição para horas_extras_interface NÃO seria atendida!")