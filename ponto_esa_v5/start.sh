#!/bin/bash

# Executar migração do banco de dados
echo "🔄 Executando migração do banco de dados..."
python database_postgresql.py

# No Render, usar apenas Streamlit (Push Notifications vão usar notificações locais)
echo "🚀 Iniciando Streamlit..."
streamlit run app_v5_final.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.headless=true
