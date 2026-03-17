import json, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ponto_esa_v5.database import get_connection, return_connection, USE_POSTGRESQL

expected = [
    'idx_registros_usuario','idx_registros_data_hora','idx_registros_usuario_data',
    'idx_usuarios_tipo_ativo','idx_usuarios_usuario','idx_ausencias_usuario',
    'idx_ausencias_status','idx_ausencias_data','idx_he_usuario_status','idx_he_aprovador',
    'idx_notif_usuario_lida','idx_banco_horas_usuario','idx_jornada_usuario_data',
    'idx_auditoria_registro_id','idx_auditoria_usuario_data','idx_auditoria_data_alteracao',
    'idx_pendencias_ign_data','idx_corr_usuario_status_data','idx_pendencia_ignorada_unica',
    'idx_push_subscriptions_usuario'
]

if not USE_POSTGRESQL:
    print('ERRO: ambiente nao esta em PostgreSQL (USE_POSTGRESQL=False).')
    sys.exit(2)

conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT indexname, tablename, indexdef FROM pg_indexes WHERE schemaname='public' ORDER BY indexname")
rows = cur.fetchall()
return_connection(conn)

existing = {r[0]: {'table': r[1], 'def': r[2]} for r in rows}
missing = [n for n in expected if n not in existing]
found = [n for n in expected if n in existing]
pct = round((len(found) * 100.0) / len(expected), 2)

print(json.dumps({
    'postgres_ok': True,
    'expected_total': len(expected),
    'found_total': len(found),
    'missing_total': len(missing),
    'coverage_percent': pct,
    'missing': missing,
    'found': found,
}, ensure_ascii=False, indent=2))
