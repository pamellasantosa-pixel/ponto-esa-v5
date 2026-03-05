import sqlite3
import os

# Ir para o diretório correto
script_dir = os.path.dirname(__file__)
db_path = os.path.join(script_dir, 'database', 'ponto_esa.db')

print(f"Conectando ao banco: {db_path}")
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Verificar se a tabela existe
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='atestados_horas'")
result = c.fetchone()
if result:
    print(f"✓ Tabela 'atestados_horas' encontrada!")
else:
    print("✗ Tabela não encontrada!")
    exit(1)

# Limpar atestados pendentes existentes (se houver)
c.execute("DELETE FROM atestados_horas WHERE status='pendente'")
print(f"Atestados pendentes removidos: {c.rowcount}")

# Criar atestados de demonstração
atestados = [
    ('demo_user', '2025-01-15', 6.5, 'Consulta médica - saída antecipada às 15:00h', None, 'pendente'),
    ('demo_user', '2025-01-18', 8.0, 'Atestado médico - ausência dia completo por gripe', None, 'pendente'),
]

for atestado in atestados:
    c.execute('''
        INSERT INTO atestados_horas 
        (usuario, data, horas_trabalhadas, justificativa, arquivo_id, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', atestado)

conn.commit()
print(f"✓ {len(atestados)} atestados de demonstração criados com sucesso!")

# Verificar dados criados
c.execute("SELECT id, usuario, data, horas_trabalhadas, status FROM atestados_horas WHERE status='pendente'")
rows = c.fetchall()
print(f"\nAtestados pendentes no banco:")
for row in rows:
    print(f"  ID {row[0]}: {row[1]} - {row[2]} - {row[3]}h - {row[4]}")

conn.close()
print("\n✓ Processo concluído!")
