#!/usr/bin/env python3
"""
Script de teste para verificar se a interface de horas extras está funcionando
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock do streamlit para testar sem interface gráfica
class MockStreamlit:
    def set_page_config(self, **kwargs):
        print(f"SET_PAGE_CONFIG: {kwargs}")

    def markdown(self, text, **kwargs):
        print(f"MARKDOWN: {text[:100]}...")

    def tabs(self, tabs_list):
        print(f"TABS: {tabs_list}")
        return [MockTab() for _ in tabs_list]

    def button(self, text, **kwargs):
        print(f"BUTTON: {text}")
        return False

    def form(self, key):
        print(f"FORM: {key}")
        return MockForm()

    def subheader(self, text):
        print(f"SUBHEADER: {text}")

    def write(self, text):
        print(f"WRITE: {text}")

    def columns(self, n):
        return [MockColumn() for _ in range(n)]

    def date_input(self, label, **kwargs):
        print(f"DATE_INPUT: {label}")
        from datetime import date
        return date.today()

    def time_input(self, label, **kwargs):
        print(f"TIME_INPUT: {label}")
        from datetime import time
        return time(8, 0)

    def text_area(self, label, **kwargs):
        print(f"TEXT_AREA: {label}")
        return ""

    def selectbox(self, label, options, **kwargs):
        print(f"SELECTBOX: {label} - options: {options[:3]}...")
        return options[0] if options else ""

    def expander(self, label):
        print(f"EXPANDER: {label}")
        return MockExpander()

    def info(self, text):
        print(f"INFO: {text}")

    def error(self, text):
        print(f"ERROR: {text}")

    def success(self, text):
        print(f"SUCCESS: {text}")

    def warning(self, text):
        print(f"WARNING: {text}")

    def rerun(self):
        print("RERUN called")

class MockColumn:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

class MockExpander:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

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

    def form_submit_button(self, text, **kwargs):
        print(f"FORM SUBMIT BUTTON: {text}")
        return False

# Substituir streamlit pelo mock
sys.modules['streamlit'] = MockStreamlit()

# Agora importar e testar a função
try:
    from app_v5_final import horas_extras_interface
    print("✅ Importação da função horas_extras_interface bem-sucedida")

    # Mock do sistema de horas extras
    class MockHorasExtrasSystem:
        pass

    # Testar a função
    print("🧪 Testando horas_extras_interface...")
    horas_extras_system = MockHorasExtrasSystem()
    horas_extras_interface(horas_extras_system)
    print("✅ Função horas_extras_interface executada sem erros")

except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()