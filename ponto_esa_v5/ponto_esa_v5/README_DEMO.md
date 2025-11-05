# Demo setup

Para criar um banco de demonstração e rodar a aplicação localmente:

1. Criar o DB demo:

```powershell
python tools/demo_setup.py
```

2. Copiar o DB demo para o DB principal (ou ajustar o caminho no código):

```powershell
copy database\ponto_esa_demo.db database\ponto_esa.db
```

3. Rodar a aplicação (Streamlit):

```powershell
streamlit run app_v5_final.py
```

Usuário demo: `demo_user` / senha: `senha_func_123`
