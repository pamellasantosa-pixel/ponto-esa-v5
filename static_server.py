"""
Servidor de arquivos estáticos simples para Service Worker
Pode ser usado para testes locais ou futuras implementações de Push Notifications
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

class StaticHandler(SimpleHTTPRequestHandler):
    """Handler com MIME types corretos para Service Worker"""
    
    extensions_map = {
        '.js': 'application/javascript',
        '.json': 'application/json',
        '.html': 'text/html',
        '.css': 'text/css',
        '': 'application/octet-stream',
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory='static', **kwargs)
    
    def end_headers(self):
        self.send_header('Service-Worker-Allowed', '/')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

def run_server(port=8502):
    server = HTTPServer(('0.0.0.0', port), StaticHandler)
    print(f'[Static] Servindo em http://0.0.0.0:{port}')
    server.serve_forever()

if __name__ == '__main__':
    run_server()