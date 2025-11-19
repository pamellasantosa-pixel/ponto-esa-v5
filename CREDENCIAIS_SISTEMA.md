# 🔐 CREDENCIAIS DO SISTEMA - REFERÊNCIA RÁPIDA

## Usuários Padrão

| Usuário | Senha | Tipo | Acesso |
|---------|-------|------|--------|
| `funcionario` | `senha_func_123` | Funcionário | Registrar ponto, solicitar HE, atestados |
| `gestor` | `senha_gestor_123` | Gestor | Aprovações, dashboard, gerenciamento |
| `admin` | `admin123` | Admin | Acesso total ao sistema |

## Como Usar

### Ambiente Local (Desenvolvimento)
```bash
cd ponto_esa_v5
python manage_users.py reset
```
Isso cria/atualiza os usuários padrão no banco de dados.

### Ambiente Render (Produção)
Use as credenciais acima diretamente na interface de login.

## Hashes SHA256 das Senhas

Se precisar inserir manualmente no banco:

```sql
-- Funcionário
INSERT INTO usuarios (usuario, senha, tipo, nome_completo, ativo) 
VALUES ('funcionario', '86ea8f7d99993a76cdfa8bf07f88a046ab54e47512c866335f268e0df02655b0', 'funcionario', 'Funcionário Demo', 1);

-- Gestor
INSERT INTO usuarios (usuario, senha, tipo, nome_completo, ativo) 
VALUES ('gestor', '389e0b4ec373638b9e93354dbfce0dd55f0007dadecb2ee62d4d1a799dd52375', 'gestor', 'Gestor Demo', 1);

-- Admin
INSERT INTO usuarios (usuario, senha, tipo, nome_completo, ativo) 
VALUES ('admin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'admin', 'Administrador', 1);
```

## Troubleshooting

### ❌ "Login Inválido"
1. Verifique se a tabela `usuarios` existe
2. Confirme que o usuário foi criado
3. Reinicie a aplicação

### ❌ "Conexão Recusada"
1. Verifique se o banco PostgreSQL está rodando
2. Confirme credenciais do banco em `.env`
3. Para SQLite local, ignore este erro

### ✅ Redefinir Senha
```bash
python manage_users.py reset
```

## Gerenciador de Usuários

O arquivo `manage_users.py` oferece:

```bash
# Ver credenciais padrão
python manage_users.py

# Resetar usuários (local)
python manage_users.py reset
```

---

**Última atualização:** 19 de novembro de 2025
