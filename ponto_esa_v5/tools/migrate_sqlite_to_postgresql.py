"""
Script de migração de SQLite para PostgreSQL
Migra todos os dados do banco SQLite para PostgreSQL
"""

import sqlite3
import psycopg2
import os
from datetime import datetime

# Configuração
SQLITE_DB = 'database/ponto_esa.db'
PG_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'ponto_esa'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres'),
    'port': os.getenv('DB_PORT', '5432')
}

def migrate():
    """Executa a migração do SQLite para PostgreSQL"""
    print("🚀 Iniciando migração SQLite → PostgreSQL")
    print(f"📂 Origem: {SQLITE_DB}")
    print(f"📊 Destino: {PG_CONFIG['host']}:{PG_CONFIG['port']}/{PG_CONFIG['database']}\n")
    
    # Verificar se o banco SQLite existe
    if not os.path.exists(SQLITE_DB):
        print(f"❌ Erro: Banco de dados SQLite não encontrado: {SQLITE_DB}")
        return False
    
    try:
        # Conectar nos dois bancos
        sqlite_conn = sqlite3.connect(SQLITE_DB)
        sqlite_conn.row_factory = sqlite3.Row
        pg_conn = psycopg2.connect(**PG_CONFIG)
        pg_conn.autocommit = False
        
        sqlite_cur = sqlite_conn.cursor()
        pg_cur = pg_conn.cursor()
        
        # Tabelas para migrar (em ordem de dependências)
        tabelas = [
            'usuarios',
            'projetos',
            'registros_ponto',
            'ausencias',
            'solicitacoes_horas_extras',
            'atestado_horas',
            'atestados_horas',
            'uploads',
            'banco_horas',
            'feriados',
            'auditoria_correcoes'
        ]
        
        total_registros = 0
        
        for tabela in tabelas:
            try:
                # Verificar se a tabela existe no SQLite
                sqlite_cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tabela}'")
                if not sqlite_cur.fetchone():
                    print(f"⏭️  Tabela '{tabela}' não existe no SQLite, pulando...")
                    continue
                
                # Buscar todos os dados da tabela
                sqlite_cur.execute(f"SELECT * FROM {tabela}")
                rows = sqlite_cur.fetchall()
                
                if not rows:
                    print(f"⚪ Tabela '{tabela}': 0 registros")
                    continue
                
                # Obter nomes das colunas
                column_names = [description[0] for description in sqlite_cur.description]
                
                # Limpar tabela no PostgreSQL (cuidado!)
                pg_cur.execute(f"DELETE FROM {tabela}")
                
                # Inserir dados no PostgreSQL
                migrados = 0
                for row in rows:
                    # Criar placeholders para PostgreSQL (%s)
                    placeholders = ', '.join(['%s'] * len(row))
                    columns = ', '.join(column_names)
                    
                    try:
                        pg_cur.execute(
                            f"INSERT INTO {tabela} ({columns}) VALUES ({placeholders})",
                            tuple(row)
                        )
                        migrados += 1
                    except Exception as e:
                        print(f"      ⚠️  Erro ao inserir registro: {e}")
                        continue
                
                # Resetar sequência do ID no PostgreSQL
                try:
                    pg_cur.execute(f"SELECT setval(pg_get_serial_sequence('{tabela}', 'id'), COALESCE(MAX(id), 1)) FROM {tabela}")
                except:
                    pass  # Tabela pode não ter coluna id
                
                print(f"✅ Tabela '{tabela}': {migrados} registros migrados")
                total_registros += migrados
                
            except Exception as e:
                print(f"❌ Erro na tabela '{tabela}': {e}")
                continue
        
        # Commit final
        pg_conn.commit()
        
        print(f"\n🎉 Migração concluída com sucesso!")
        print(f"📊 Total de registros migrados: {total_registros}")
        
        # Fechar conexões
        sqlite_conn.close()
        pg_conn.close()
        
        return True
        
    except psycopg2.Error as e:
        print(f"\n❌ Erro no PostgreSQL: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Erro geral: {e}")
        return False


def verify_migration():
    """Verifica se a migração foi bem-sucedida"""
    print("\n🔍 Verificando migração...")
    
    try:
        sqlite_conn = sqlite3.connect(SQLITE_DB)
        pg_conn = psycopg2.connect(**PG_CONFIG)
        
        sqlite_cur = sqlite_conn.cursor()
        pg_cur = pg_conn.cursor()
        
        tabelas = ['usuarios', 'projetos', 'registros_ponto', 'ausencias']
        
        print("\nComparação de registros:\n")
        print(f"{'Tabela':<25} {'SQLite':<10} {'PostgreSQL':<10} {'Status':<10}")
        print("-" * 60)
        
        tudo_ok = True
        for tabela in tabelas:
            try:
                sqlite_cur.execute(f"SELECT COUNT(*) FROM {tabela}")
                count_sqlite = sqlite_cur.fetchone()[0]
                
                pg_cur.execute(f"SELECT COUNT(*) FROM {tabela}")
                count_pg = pg_cur.fetchone()[0]
                
                status = "✅ OK" if count_sqlite == count_pg else "❌ ERRO"
                if count_sqlite != count_pg:
                    tudo_ok = False
                
                print(f"{tabela:<25} {count_sqlite:<10} {count_pg:<10} {status:<10}")
            except:
                print(f"{tabela:<25} {'N/A':<10} {'N/A':<10} {'⚠️ SKIP':<10}")
        
        sqlite_conn.close()
        pg_conn.close()
        
        return tudo_ok
        
    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
        return False


if __name__ == '__main__':
    print("=" * 60)
    print(" Migração SQLite → PostgreSQL - Ponto ExSA v5.0")
    print("=" * 60)
    print()
    
    resposta = input("⚠️  ATENÇÃO: Esta operação irá substituir os dados no PostgreSQL.\nDeseja continuar? (sim/não): ")
    
    if resposta.lower() in ['sim', 's', 'yes', 'y']:
        sucesso = migrate()
        
        if sucesso:
            verify_migration()
            print("\n✅ Migração completa! Você pode agora usar o PostgreSQL.")
            print("💡 Configure USE_POSTGRESQL=true no arquivo .env")
        else:
            print("\n❌ Migração falhou. Verifique os erros acima.")
    else:
        print("\n❌ Migração cancelada.")
