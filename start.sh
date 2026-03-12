#!/bin/bash
set -euo pipefail

export PYTHONPATH="$(pwd)"

# Worker opcional para notificações em processo separado do web app.
if [ "${ENABLE_NOTIFICATION_WORKER:-true}" = "true" ]; then
	export USE_EMBEDDED_SCHEDULER=false
	python ponto_esa_v5/notification_worker.py --mode scheduler &
fi

exec streamlit run ponto_esa_v5/app_v5_final.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.headless=true
