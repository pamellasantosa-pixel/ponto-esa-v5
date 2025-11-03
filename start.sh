#!/bin/bash

# Executar migração do banco de dados
echo "🔄 Executando migração do banco de dados..."
cd ponto_esa_v5
python database_postgresql.py
cd ..

# Iniciar aplicação Streamlit
echo "🚀 Iniciando aplicação..."
streamlit run ponto_esa_v5/app_v5_final.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.headless=true
