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

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=5).getcode()==200 else 1)"

# Comando padrão para rodar
CMD ["streamlit", "run", "ponto_esa_v5/app_v5_final.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
