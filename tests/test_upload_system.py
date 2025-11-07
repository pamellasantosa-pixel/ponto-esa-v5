import os
import shutil
import sqlite3
from ponto_esa_v5.upload_system import UploadSystem
from ponto_esa_v5.database import init_db


def setup_module(module):
    # preparar DB limpo
    db_path = 'database/ponto_esa.db'
    if os.path.exists(db_path):
        os.remove(db_path)
    os.makedirs('database', exist_ok=True)
    init_db()

    # limpar uploads (ignorar erros de permissão no Windows)
    if os.path.exists('uploads'):
        def on_rm_error(func, path, exc_info):
            try:
                os.chmod(path, 0o666)
                func(path)
            except Exception:
                pass

        try:
            shutil.rmtree('uploads', onerror=on_rm_error)
        except Exception:
            pass


def test_save_and_find_and_delete_file():
    us = UploadSystem(db_path='database/ponto_esa.db', upload_dir='uploads')

    content = b"Hello Test"
    resp = us.save_file(content, 'funcionario',
                        'test_file.txt', categoria='documento')
    assert resp['success'] is True
    upload_id = resp['upload_id']

    # Encontrar por hash
    file_hash = us.calculate_file_hash(content)
    found = us.find_file_by_hash(file_hash, 'funcionario')
    assert found is not None

    # Baixar conteúdo
    content2, info = us.get_file_content(upload_id, 'funcionario')
    assert content2 == content

    # Deletar
    del_res = us.delete_file(upload_id, 'funcionario')
    assert del_res['success'] is True

    # cleanup uploads (ignorar erros de permissão)
    if os.path.exists('uploads'):
        def on_rm_error(func, path, exc_info):
            # Tenta forçar remoção de arquivos read-only no Windows
            try:
                os.chmod(path, 0o666)
                func(path)
            except Exception:
                pass

        try:
            shutil.rmtree('uploads', onerror=on_rm_error)
        except Exception:
            # último recurso: ignorar falhas de limpeza em ambiente CI local
            pass
