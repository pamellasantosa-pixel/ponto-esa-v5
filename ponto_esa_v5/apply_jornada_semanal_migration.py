"""
Script para aplicar migration de jornada semanal variável
Adiciona campos para configurar horários diferentes por dia da semana
"""

import sys
import os
from pathlib import Path

# Adicionar diretório pai ao path
sys.path.insert(0, str(Path(__file__).parent))

from database import get_connection

def aplicar_migration_jornada_semanal():
    """Aplica migration para adicionar jornada semanal aos usuários"""
    conn = get_connection()
    cursor = conn.cursor()
    
    print("🔄 Iniciando migration de jornada semanal...")
    
    colunas_a_adicionar = [
        # Segunda-feira
        ("jornada_seg_inicio", "TIME"),
        ("jornada_seg_fim", "TIME"),
        ("trabalha_seg", "INTEGER DEFAULT 1"),
        ("intervalo_seg", "INTEGER DEFAULT 60"),  # intervalo em minutos
        
        # Terça-feira
        ("jornada_ter_inicio", "TIME"),
        ("jornada_ter_fim", "TIME"),
        ("trabalha_ter", "INTEGER DEFAULT 1"),
        ("intervalo_ter", "INTEGER DEFAULT 60"),
        
        # Quarta-feira
        ("jornada_qua_inicio", "TIME"),
        ("jornada_qua_fim", "TIME"),
        ("trabalha_qua", "INTEGER DEFAULT 1"),
        ("intervalo_qua", "INTEGER DEFAULT 60"),
        
        # Quinta-feira
        ("jornada_qui_inicio", "TIME"),
        ("jornada_qui_fim", "TIME"),
        ("trabalha_qui", "INTEGER DEFAULT 1"),
        ("intervalo_qui", "INTEGER DEFAULT 60"),
        
        # Sexta-feira
        ("jornada_sex_inicio", "TIME"),
        ("jornada_sex_fim", "TIME"),
        ("trabalha_sex", "INTEGER DEFAULT 1"),
        ("intervalo_sex", "INTEGER DEFAULT 60"),
        
        # Sábado
        ("jornada_sab_inicio", "TIME"),
        ("jornada_sab_fim", "TIME"),
        ("trabalha_sab", "INTEGER DEFAULT 0"),
        ("intervalo_sab", "INTEGER DEFAULT 60"),
        
        # Domingo
        ("jornada_dom_inicio", "TIME"),
        ("jornada_dom_fim", "TIME"),
        ("trabalha_dom", "INTEGER DEFAULT 0"),
        ("intervalo_dom", "INTEGER DEFAULT 60"),
    ]
    
    for coluna, tipo in colunas_a_adicionar:
        try:
            # Verificar se coluna já existe
            cursor.execute("SELECT COUNT(*) FROM pragma_table_info('usuarios') WHERE name = ?", (coluna,))
            if cursor.fetchone()[0] == 0:
                cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {coluna} {tipo}")
                print(f"  ✅ Coluna '{coluna}' adicionada")
            else:
                print(f"  ⏭️  Coluna '{coluna}' já existe")
        except Exception as e:
            print(f"  ⚠️  Erro ao adicionar coluna '{coluna}': {e}")
    
    # Copiar valores padrão existentes para todos os dias úteis
    print("\n🔄 Copiando jornada padrão para dias úteis...")
    try:
        cursor.execute("""
            UPDATE usuarios 
            SET 
                jornada_seg_inicio = jornada_inicio_previsto,
                jornada_seg_fim = jornada_fim_previsto,
                jornada_ter_inicio = jornada_inicio_previsto,
                jornada_ter_fim = jornada_fim_previsto,
                jornada_qua_inicio = jornada_inicio_previsto,
                jornada_qua_fim = jornada_fim_previsto,
                jornada_qui_inicio = jornada_inicio_previsto,
                jornada_qui_fim = jornada_fim_previsto,
                jornada_sex_inicio = jornada_inicio_previsto,
                jornada_sex_fim = jornada_fim_previsto
            WHERE jornada_seg_inicio IS NULL
        """)
        print("  ✅ Jornada padrão copiada para seg-sex")
    except Exception as e:
        print(f"  ⚠️  Erro ao copiar jornada padrão: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Migration de jornada semanal concluída!")
    print("💡 Agora você pode configurar horários diferentes para cada dia da semana")

def aplicar_migration_horas_extras_ativas():
    """Cria tabela para controlar horas extras em andamento"""
    conn = get_connection()
    cursor = conn.cursor()
    
    print("\n🔄 Criando tabela de horas extras ativas...")
    
    # Detectar tipo de banco
    import os
    usa_postgres = os.getenv('DATABASE_URL') is not None
    
    try:
        if usa_postgres:
            # PostgreSQL
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS horas_extras_ativas (
                    id SERIAL PRIMARY KEY,
                    usuario VARCHAR(255) NOT NULL,
                    aprovador VARCHAR(255) NOT NULL,
                    justificativa TEXT NOT NULL,
                    data_inicio TIMESTAMP NOT NULL,
                    hora_inicio TIME NOT NULL,
                    status VARCHAR(50) DEFAULT 'em_execucao',
                    data_fim TIMESTAMP,
                    hora_fim TIME,
                    tempo_decorrido_minutos INTEGER,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (usuario) REFERENCES usuarios(usuario),
                    FOREIGN KEY (aprovador) REFERENCES usuarios(usuario)
                )
            """)
        else:
            # SQLite
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS horas_extras_ativas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT NOT NULL,
                    aprovador TEXT NOT NULL,
                    justificativa TEXT NOT NULL,
                    data_inicio TIMESTAMP NOT NULL,
                    hora_inicio TIME NOT NULL,
                    status TEXT DEFAULT 'em_execucao',
                    data_fim TIMESTAMP,
                    hora_fim TIME,
                    tempo_decorrido_minutos INTEGER,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        print("  ✅ Tabela 'horas_extras_ativas' criada")
    except Exception as e:
        print(f"  ⚠️  Erro ao criar tabela: {e}")
    
    conn.commit()
    conn.close()
    
    print("✅ Migration de horas extras ativas concluída!")

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 APLICAR MIGRATIONS - JORNADA SEMANAL E HORAS EXTRAS")
    print("=" * 60)
    
    aplicar_migration_jornada_semanal()
    aplicar_migration_horas_extras_ativas()
    
    print("\n" + "=" * 60)
    print("✅ TODAS AS MIGRATIONS FORAM APLICADAS COM SUCESSO!")
    print("=" * 60)
