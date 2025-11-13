import sys
import os
import datetime
import uuid

# Adiciona o diretório raiz e o diretório ponto_esa_v5 ao sys.path para garantir que os módulos sejam encontrados
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'ponto_esa_v5')))

from ponto_esa_v5.upload_system import UploadSystem

def test_upload_download():
    """Testa o fluxo de upload e download de arquivos."""
    # Configurações iniciais
    usuario = "teste_usuario"
    categoria = "testes"
    # Conteúdo do arquivo dinâmico para evitar conflitos
    conteudo_arquivo = f"Conteudo de teste unico: {uuid.uuid4()}".encode("utf-8")
    # Nome do arquivo dinâmico para evitar conflitos
    nome_arquivo = f"arquivo_teste_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    # Instanciar o sistema de upload
    upload_system = UploadSystem()

    # Testar upload
    print("Iniciando upload...")
    upload_result = upload_system.save_file(
        file_content=conteudo_arquivo,
        usuario=usuario,
        original_filename=nome_arquivo,
        categoria=categoria
    )

    if not upload_result["success"]:
        print(f"Erro no upload: {upload_result['message']}")
        return

    caminho_arquivo = upload_result.get("path")
    print(f"Upload concluído. Caminho do arquivo: {caminho_arquivo}")

    # Testar download
    print("Iniciando download...")
    download_result = upload_system.get_file_content(caminho_arquivo)

    if not download_result[0]:  # Verifica o primeiro elemento da tupla (sucesso)
        print(f"Erro no download: {download_result[1]}")  # Mensagem de erro no segundo elemento
        return

    conteudo_baixado = download_result[1]  # Conteúdo do arquivo no segundo elemento
    if conteudo_baixado == conteudo_arquivo:
        print("Download bem-sucedido. O conteúdo do arquivo está correto.")
    else:
        print("Erro: O conteúdo baixado não corresponde ao conteúdo original.")

if __name__ == "__main__":
    test_upload_download()