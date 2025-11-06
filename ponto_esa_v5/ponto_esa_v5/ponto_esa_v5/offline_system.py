"""
Sistema Offline para Ponto ExSA
Permite funcionamento offline com sincronização automática
"""

import sqlite3
import json
import datetime
import os
from pathlib import Path

class OfflineSystem:
    """Sistema de gerenciamento offline"""
    
    def __init__(self):
        self.offline_db_path = "database/offline_ponto_esa.db"
        self.sync_queue_path = "database/sync_queue.json"
        self.init_offline_db()
    
    def init_offline_db(self):
        """Inicializa banco de dados offline"""
        os.makedirs("database", exist_ok=True)
        
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        # Tabela de registros offline
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registros_offline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                data DATE NOT NULL,
                tipo TEXT NOT NULL,
                horario_informado TIME,
                horario_real TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modalidade TEXT,
                projeto TEXT,
                atividade TEXT,
                localizacao TEXT,
                ip_address TEXT,
                synced INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de ausências offline
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ausencias_offline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                data_inicio DATE NOT NULL,
                data_fim DATE,
                tipo TEXT NOT NULL,
                motivo TEXT,
                comprovante TEXT,
                synced INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de cache de dados
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache_dados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chave TEXT UNIQUE NOT NULL,
                valor TEXT,
                expires_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def is_online(self):
        """Verifica se há conexão com internet"""
        try:
            import urllib.request
            urllib.request.urlopen('http://www.google.com', timeout=3)
            return True
        except:
            return False
    
    def save_offline_registro(self, user_id, data, tipo, horario_informado, modalidade, projeto, atividade, localizacao=""):
        """Salva registro offline"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO registros_offline 
            (user_id, data, tipo, horario_informado, modalidade, projeto, atividade, localizacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, data, tipo, horario_informado, modalidade, projeto, atividade, localizacao))
        
        conn.commit()
        conn.close()
        
        # Adicionar à fila de sincronização
        self.add_to_sync_queue('registro', cursor.lastrowid)
        return True
    
    def save_offline_ausencia(self, user_id, data_inicio, data_fim, tipo, motivo):
        """Salva ausência offline"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ausencias_offline 
            (user_id, data_inicio, data_fim, tipo, motivo)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, data_inicio, data_fim, tipo, motivo))
        
        conn.commit()
        conn.close()
        
        # Adicionar à fila de sincronização
        self.add_to_sync_queue('ausencia', cursor.lastrowid)
        return True
    
    def add_to_sync_queue(self, tipo, item_id):
        """Adiciona item à fila de sincronização"""
        queue_item = {
            'tipo': tipo,
            'item_id': item_id,
            'timestamp': datetime.datetime.now().isoformat(),
            'attempts': 0
        }
        
        # Carregar fila existente
        sync_queue = self.load_sync_queue()
        sync_queue.append(queue_item)
        
        # Salvar fila atualizada
        with open(self.sync_queue_path, 'w') as f:
            json.dump(sync_queue, f, indent=2)
    
    def load_sync_queue(self):
        """Carrega fila de sincronização"""
        if os.path.exists(self.sync_queue_path):
            try:
                with open(self.sync_queue_path, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def sync_to_online(self):
        """Sincroniza dados offline com banco online"""
        if not self.is_online():
            return False, "Sem conexão com internet"
        
        sync_queue = self.load_sync_queue()
        synced_items = []
        errors = []
        
        for item in sync_queue:
            try:
                if item['tipo'] == 'registro':
                    success = self.sync_registro(item['item_id'])
                elif item['tipo'] == 'ausencia':
                    success = self.sync_ausencia(item['item_id'])
                else:
                    success = False
                
                if success:
                    synced_items.append(item)
                else:
                    item['attempts'] += 1
                    if item['attempts'] >= 3:
                        errors.append(f"Falha ao sincronizar {item['tipo']} ID {item['item_id']}")
                        synced_items.append(item)  # Remove da fila após 3 tentativas
            
            except Exception as e:
                errors.append(f"Erro ao sincronizar {item['tipo']} ID {item['item_id']}: {str(e)}")
                item['attempts'] += 1
        
        # Remover itens sincronizados da fila
        remaining_queue = [item for item in sync_queue if item not in synced_items]
        
        with open(self.sync_queue_path, 'w') as f:
            json.dump(remaining_queue, f, indent=2)
        
        return len(synced_items) > 0, f"Sincronizados: {len(synced_items)}, Erros: {len(errors)}"
    
    def sync_registro(self, offline_id):
        """Sincroniza registro específico"""
        try:
            # Buscar registro offline
            conn_offline = sqlite3.connect(self.offline_db_path)
            cursor_offline = conn_offline.cursor()
            
            cursor_offline.execute('''
                SELECT * FROM registros_offline WHERE id = ? AND synced = 0
            ''', (offline_id,))
            
            registro = cursor_offline.fetchone()
            conn_offline.close()
            
            if not registro:
                return True  # Já foi sincronizado
            
            # Inserir no banco online
            conn_online = sqlite3.connect('database/ponto_esa.db')
            cursor_online = conn_online.cursor()
            
            cursor_online.execute('''
                INSERT INTO registros 
                (user_id, data, tipo, horario_informado, modalidade, projeto, atividade, localizacao, horario_real)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (registro[1], registro[2], registro[3], registro[4], registro[6], registro[7], registro[8], registro[9], registro[5]))
            
            conn_online.commit()
            conn_online.close()
            
            # Marcar como sincronizado
            conn_offline = sqlite3.connect(self.offline_db_path)
            cursor_offline = conn_offline.cursor()
            cursor_offline.execute('UPDATE registros_offline SET synced = 1 WHERE id = ?', (offline_id,))
            conn_offline.commit()
            conn_offline.close()
            
            return True
            
        except Exception as e:
            print(f"Erro ao sincronizar registro {offline_id}: {str(e)}")
            return False
    
    def sync_ausencia(self, offline_id):
        """Sincroniza ausência específica"""
        try:
            # Buscar ausência offline
            conn_offline = sqlite3.connect(self.offline_db_path)
            cursor_offline = conn_offline.cursor()
            
            cursor_offline.execute('''
                SELECT * FROM ausencias_offline WHERE id = ? AND synced = 0
            ''', (offline_id,))
            
            ausencia = cursor_offline.fetchone()
            conn_offline.close()
            
            if not ausencia:
                return True  # Já foi sincronizado
            
            # Inserir no banco online
            conn_online = sqlite3.connect('database/ponto_esa.db')
            cursor_online = conn_online.cursor()
            
            cursor_online.execute('''
                INSERT INTO ausencias 
                (user_id, data_inicio, data_fim, tipo, motivo)
                VALUES (?, ?, ?, ?, ?)
            ''', (ausencia[1], ausencia[2], ausencia[3], ausencia[4], ausencia[5]))
            
            conn_online.commit()
            conn_online.close()
            
            # Marcar como sincronizado
            conn_offline = sqlite3.connect(self.offline_db_path)
            cursor_offline = conn_offline.cursor()
            cursor_offline.execute('UPDATE ausencias_offline SET synced = 1 WHERE id = ?', (offline_id,))
            conn_offline.commit()
            conn_offline.close()
            
            return True
            
        except Exception as e:
            print(f"Erro ao sincronizar ausência {offline_id}: {str(e)}")
            return False
    
    def get_offline_registros(self, user_id, data=None):
        """Obtém registros offline do usuário"""
        conn = sqlite3.connect(self.offline_db_path)
        
        if data:
            query = '''
                SELECT * FROM registros_offline 
                WHERE user_id = ? AND data = ? 
                ORDER BY horario_real
            '''
            cursor = conn.cursor()
            cursor.execute(query, (user_id, data))
        else:
            query = '''
                SELECT * FROM registros_offline 
                WHERE user_id = ? 
                ORDER BY data DESC, horario_real DESC
            '''
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))
        
        registros = cursor.fetchall()
        conn.close()
        
        return registros
    
    def cache_data(self, chave, valor, expires_minutes=60):
        """Armazena dados no cache"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        expires_at = datetime.datetime.now() + datetime.timedelta(minutes=expires_minutes)
        
        cursor.execute('''
            INSERT OR REPLACE INTO cache_dados (chave, valor, expires_at)
            VALUES (?, ?, ?)
        ''', (chave, json.dumps(valor), expires_at))
        
        conn.commit()
        conn.close()
    
    def get_cached_data(self, chave):
        """Recupera dados do cache"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT valor FROM cache_dados 
            WHERE chave = ? AND expires_at > CURRENT_TIMESTAMP
        ''', (chave,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result[0])
        return None
    
    def cleanup_old_cache(self):
        """Remove dados expirados do cache"""
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM cache_dados WHERE expires_at <= CURRENT_TIMESTAMP")
        
        conn.commit()
        conn.close()
    
    def get_sync_status(self):
        """Retorna status da sincronização"""
        sync_queue = self.load_sync_queue()
        
        # Contar registros não sincronizados
        conn = sqlite3.connect(self.offline_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM registros_offline WHERE synced = 0")
        registros_pendentes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ausencias_offline WHERE synced = 0")
        ausencias_pendentes = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'online': self.is_online(),
            'queue_size': len(sync_queue),
            'registros_pendentes': registros_pendentes,
            'ausencias_pendentes': ausencias_pendentes,
            'total_pendentes': registros_pendentes + ausencias_pendentes
        }

# Funções auxiliares para integração com Streamlit
def init_offline_system():
    """Inicializa sistema offline"""
    return OfflineSystem()

def auto_sync():
    """Executa sincronização automática em background"""
    import threading
    import time
    
    def sync_worker():
        offline_system = OfflineSystem()
        while True:
            try:
                if offline_system.is_online():
                    offline_system.sync_to_online()
                    offline_system.cleanup_old_cache()
                time.sleep(60)  # Tentar sincronizar a cada minuto
            except Exception as e:
                print(f"Erro na sincronização automática: {str(e)}")
                time.sleep(300)  # Aguardar 5 minutos em caso de erro
    
    sync_thread = threading.Thread(target=sync_worker, daemon=True)
    sync_thread.start()

# Integração com JavaScript para PWA offline
OFFLINE_JS = """
// Service Worker para funcionalidade offline
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/offline-sw.js')
        .then(function(registration) {
            console.log('Offline SW registered:', registration);
        })
        .catch(function(error) {
            console.log('Offline SW registration failed:', error);
        });
}

// Detectar mudanças no status de conexão
window.addEventListener('online', function() {
    console.log('Conexão restaurada - iniciando sincronização');
    // Trigger sync
    fetch('/sync', {method: 'POST'});
});

window.addEventListener('offline', function() {
    console.log('Conexão perdida - modo offline ativado');
});

// Armazenamento local para dados offline
class OfflineStorage {
    static save(key, data) {
        localStorage.setItem(`ponto_esa_${key}`, JSON.stringify({
            data: data,
            timestamp: Date.now()
        }));
    }
    
    static load(key) {
        const item = localStorage.getItem(`ponto_esa_${key}`);
        if (item) {
            const parsed = JSON.parse(item);
            // Verificar se não expirou (24 horas)
            if (Date.now() - parsed.timestamp < 24 * 60 * 60 * 1000) {
                return parsed.data;
            }
        }
        return null;
    }
    
    static clear(key) {
        localStorage.removeItem(`ponto_esa_${key}`);
    }
}
"""

# Service Worker para PWA offline
OFFLINE_SERVICE_WORKER = """
const CACHE_NAME = 'ponto-exsa-offline-v1';
const urlsToCache = [
    '/',
    '/static/manifest.json',
    '/static/Exsafundo.jpg',
    '/static/icon-192.png',
    '/static/icon-512.png'
];

// Instalar service worker
self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(function(cache) {
                return cache.addAll(urlsToCache);
            })
    );
});

// Interceptar requisições
self.addEventListener('fetch', function(event) {
    event.respondWith(
        caches.match(event.request)
            .then(function(response) {
                // Retornar do cache se disponível
                if (response) {
                    return response;
                }
                
                // Tentar buscar online
                return fetch(event.request).catch(function() {
                    // Se offline, retornar página offline
                    if (event.request.destination === 'document') {
                        return caches.match('/offline.html');
                    }
                });
            })
    );
});

// Sincronização em background
self.addEventListener('sync', function(event) {
    if (event.tag === 'background-sync') {
        event.waitUntil(doBackgroundSync());
    }
});

function doBackgroundSync() {
    return fetch('/api/sync', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            action: 'sync_offline_data'
        })
    });
}
"""

def create_offline_files():
    """Cria arquivos necessários para funcionamento offline"""
    
    # Criar service worker offline
    os.makedirs("static", exist_ok=True)
    
    with open("static/offline-sw.js", "w", encoding="utf-8") as f:
        f.write(OFFLINE_SERVICE_WORKER)
    
    # Criar página offline
    offline_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Ponto ExSA - Offline</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background: linear-gradient(135deg, #87CEEB 0%, #4682B4 100%);
                min-height: 100vh;
                margin: 0;
            }
            .offline-container {
                background: white;
                border-radius: 20px;
                padding: 40px;
                max-width: 500px;
                margin: 0 auto;
                box-shadow: 0 15px 35px rgba(0,0,0,0.1);
            }
            .logo {
                width: 80px;
                height: 80px;
                background: linear-gradient(45deg, #3498DB, #2980B9);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 20px;
                color: white;
                font-size: 24px;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="offline-container">
            <div class="logo">ESA</div>
            <h1>Modo Offline</h1>
            <p>Você está sem conexão com a internet.</p>
            <p>O sistema continuará funcionando offline e sincronizará automaticamente quando a conexão for restaurada.</p>
            <button onclick="location.reload()">Tentar Novamente</button>
        </div>
    </body>
    </html>
    """
    
    with open("static/offline.html", "w", encoding="utf-8") as f:
        f.write(offline_html)

if __name__ == "__main__":
    # Teste do sistema offline
    offline_system = OfflineSystem()
    status = offline_system.get_sync_status()
    print(f"Status do sistema offline: {status}")
    
    # Criar arquivos offline
    create_offline_files()
    print("Arquivos offline criados com sucesso!")

