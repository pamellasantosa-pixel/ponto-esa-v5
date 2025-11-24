# Dockerfile para rodar o Ponto ExSA com Streamlit
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

# Copiar código
COPY . /app

# Instalar dependências
RUN pip install --no-cache-dir --upgrade pip \
    && if [ -f ponto_esa_v5/requirements-pinned.txt ]; then pip install --no-cache-dir -r ponto_esa_v5/requirements-pinned.txt; fi

# Expor porta padrão do Streamlit
EXPOSE 8501

# Comando padrão para rodar
CMD ["streamlit", "run", "ponto_esa_v5/app_v5_final.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
