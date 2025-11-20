#!/usr/bin/env python3
"""
Script para testar a interface de horas extras diretamente
"""

import sys
import os

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Simular session_state do Streamlit
    class MockSessionState:
        def __init__(self):
            self.usuario = "test_user"
            self.nome_completo = "Usuário Teste"

    # Mock do streamlit
    class MockStreamlit:
        def markdown(self, text, **kwargs):
            print(f"Markdown: {text[:100]}...")

        def button(self, label, **kwargs):
            print(f"Button: {label}")
            return False

        def tabs(self, tabs_list):
            print(f"Tabs: {tabs_list}")
            return [MockTab() for _ in tabs_list]

        def subheader(self, text):
            print(f"Subheader: {text}")

        def form(self, key):
            print(f"Form: {key}")
            return MockForm()

        def expander(self, text):
            print(f"Expander: {text}")
            return MockExpander()

        def info(self, text):
            print(f"Info: {text}")

        def error(self, text):
            print(f"Error: {text}")

        def success(self, text):
            print(f"Success: {text}")

        def warning(self, text):
            print(f"Warning: {text}")

        def columns(self, n):
            return [MockColumn() for _ in range(n)]

        def selectbox(self, label, options, **kwargs):
            print(f"Selectbox: {label} - Options: {options[:3]}...")
            return options[0] if options else None

        def date_input(self, label, **kwargs):
            print(f"Date input: {label}")
            from datetime import date
            return date.today()

        def time_input(self, label, **kwargs):
            print(f"Time input: {label}")
            from datetime import time
            return time(8, 0)

        def text_area(self, label, **kwargs):
            print(f"Text area: {label}")
            return "Teste de justificativa"

        def dataframe(self, data, **kwargs):
            print(f"Dataframe: {len(data) if hasattr(data, '__len__') else 'N/A'} rows")

        def rerun(self):
            print("Rerun called")

    class MockTab:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    class MockForm:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    class MockExpander:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    class MockColumn:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

        def write(self, text):
            print(f"Column write: {text[:50]}...")

    # Substituir streamlit
    sys.modules['streamlit'] = MockStreamlit()

    # Importar e testar
    print("🔍 Testando interface de horas extras...")

    from horas_extras_system import HorasExtrasSystem
    from app_v5_final import horas_extras_interface

    # Criar sistema
    horas_extras_system = HorasExtrasSystem()

    # Simular session_state
    import streamlit as st
    st.session_state = MockSessionState()

    print("✅ Ambiente simulado criado")

    # Tentar executar a interface
    print("\n🎯 Executando horas_extras_interface...")
    try:
        horas_extras_interface(horas_extras_system)
        print("✅ Interface executada com sucesso!")
    except Exception as e:
        print(f"❌ Erro na interface: {e}")
        import traceback
        traceback.print_exc()

except Exception as e:
    print(f"❌ Erro geral: {e}")
    import traceback
    traceback.print_exc()