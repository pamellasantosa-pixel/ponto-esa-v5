#!/bin/bash
streamlit run ponto_esa_v5/app_v5_final.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.headless=true
