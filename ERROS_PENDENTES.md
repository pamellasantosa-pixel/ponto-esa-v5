# Erros Pendentes de SQL - PostgreSQL vs SQLite

## Status
✅ Login funcionando
✅ Conexão PostgreSQL OK
✅ Tabelas principais criadas

## Erros Encontrados (29/10/2025 01:15)

### 1. Coluna `horas_trabalhadas` não existe
- **Arquivo**: `app_v5_final.py` linha ~1724
- **Erro**: `psycopg2.errors.UndefinedColumn: column a.horas_trabalhadas does not exist`
- **Causa**: Query procurando coluna que não existe na tabela
- **Solução**: Verificar schema da tabela e ajustar query

### 2. Sintaxe SQL `INSERT OR IGNORE`
- **Arquivo**: Não localizado ainda (erro na linha 2 de algum arquivo)
- **Erro**: `psycopg2.errors.SyntaxError: syntax error near "OR"`
- **Causa**: `INSERT OR IGNORE` é SQLite, PostgreSQL usa `INSERT ... ON CONFLICT DO NOTHING`
- **Solução**: Substituir em todos os arquivos

### 3. strptime com datetime.time
- **Arquivo**: `app_v5_final.py` linha ~3190
- **Erro**: `TypeError: strptime() argument 1 must be str, not datetime.time`
- **Causa**: Tentando fazer parse de um objeto que já é time
- **Solução**: Verificar se já é time antes de fazer strptime

### 4. Erro de sintaxe no final da entrada
- **Arquivo**: `app_v5_final.py` linha ~2241
- **Erro**: `psycopg2.errors.SyntaxError: syntax error at end of input`
- **Causa**: Query SQL incompleta ou placeholder errado
- **Solução**: Revisar query na função aprovar_atestados_interface

### 5. IndexError em banco_horas_system
- **Arquivo**: `banco_horas_system.py` linha ~240
- **Erro**: `IndexError: tuple index out of range`
- **Causa**: Tentando acessar índice que não existe no resultado da query
- **Solução**: Verificar se resultado existe antes de acessar

## Próximos Passos
1. Criar script para encontrar e corrigir todos os `INSERT OR IGNORE`
2. Revisar schema das tabelas vs queries
3. Corrigir conversões de tipo (str vs time)
4. Adicionar verificações de resultado antes de acessar índices

## Nota
Muitos destes erros só aparecem quando usuário navega por funcionalidades específicas.
O sistema está funcional na parte de login e registro básico.
