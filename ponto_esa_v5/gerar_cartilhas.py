"""
Gerador de Cartilhas PDF - Ponto ExSA
=====================================
Gera cartilhas didaticas para funcionarios e gestores
"""

from fpdf import FPDF

class CartilhaPDF(FPDF):
    def __init__(self, titulo_cartilha):
        super().__init__()
        self.titulo_cartilha = titulo_cartilha
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(15, 15, 15)
        
    def header(self):
        self.set_font('Helvetica', 'B', 10)
        self.set_fill_color(46, 125, 50)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, 'PONTO ExSA - Sistema de Ponto Eletronico', new_x="LMARGIN", new_y="NEXT", align='C', fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(3)
        
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()}', align='C')
        
    def titulo_secao(self, titulo):
        self.set_font('Helvetica', 'B', 12)
        self.set_fill_color(33, 150, 243)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, f'  {titulo}', new_x="LMARGIN", new_y="NEXT", fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(3)
        
    def subtitulo(self, texto):
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(33, 150, 243)
        self.cell(0, 7, texto, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        
    def paragrafo(self, texto):
        self.set_font('Helvetica', '', 9)
        self.multi_cell(0, 5, texto)
        self.ln(1)
        
    def item(self, texto):
        self.set_font('Helvetica', '', 9)
        self.multi_cell(0, 5, f'  * {texto}')
        
    def dica(self, texto):
        self.set_font('Helvetica', 'I', 8)
        self.set_fill_color(255, 243, 224)
        self.set_text_color(200, 100, 0)
        self.multi_cell(0, 5, f'DICA: {texto}', fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(1)
        
    def aviso(self, texto):
        self.set_font('Helvetica', 'B', 8)
        self.set_fill_color(255, 235, 238)
        self.set_text_color(180, 40, 40)
        self.multi_cell(0, 5, f'IMPORTANTE: {texto}', fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(1)
        
    def passo(self, numero, texto):
        self.set_font('Helvetica', '', 9)
        self.set_fill_color(232, 245, 233)
        self.set_x(15)  # Resetar para margem esquerda
        self.multi_cell(0, 5, f'{numero}. {texto}', fill=True)


def gerar_cartilha_funcionario():
    """Gera a cartilha do funcionario"""
    pdf = CartilhaPDF("Cartilha do Funcionario")
    
    # Capa
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 24)
    pdf.ln(40)
    pdf.cell(0, 15, 'CARTILHA DO FUNCIONARIO', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_font('Helvetica', '', 14)
    pdf.cell(0, 10, 'Sistema de Ponto Eletronico - Ponto ExSA', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(15)
    pdf.set_font('Helvetica', 'I', 11)
    pdf.cell(0, 10, 'Guia completo de uso do sistema', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(30)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(0, 10, 'Versao: Janeiro/2026', new_x="LMARGIN", new_y="NEXT", align='C')
    
    # Sumario
    pdf.add_page()
    pdf.titulo_secao("SUMARIO")
    pdf.paragrafo("1. Introducao e Acesso ao Sistema")
    pdf.paragrafo("2. Registrar Ponto (Entrada/Saida)")
    pdf.paragrafo("3. Consultar Meus Registros")
    pdf.paragrafo("4. Solicitar Correcao de Registro")
    pdf.paragrafo("5. Registrar Ausencias")
    pdf.paragrafo("6. Atestado de Horas")
    pdf.paragrafo("7. Solicitar Horas Extras")
    pdf.paragrafo("8. Consultar Banco de Horas")
    pdf.paragrafo("9. Ver Horas por Projeto")
    pdf.paragrafo("10. Mensagens e Notificacoes")
    pdf.paragrafo("11. Configurar Lembretes no Celular")
    pdf.paragrafo("12. Duvidas Frequentes")
    
    # 1. Introducao
    pdf.add_page()
    pdf.titulo_secao("1. INTRODUCAO E ACESSO AO SISTEMA")
    
    pdf.subtitulo("O que e o Ponto ExSA?")
    pdf.paragrafo("O Ponto ExSA e o sistema de registro de ponto eletronico da empresa. Atraves dele voce pode registrar sua entrada e saida, solicitar horas extras, enviar atestados e muito mais - tudo pelo celular ou computador!")
    pdf.ln(2)
    
    pdf.subtitulo("Como acessar?")
    pdf.passo(1, "Abra o navegador (Chrome, Safari, etc.)")
    pdf.passo(2, "Digite: ponto-esa-v5.onrender.com")
    pdf.passo(3, "Digite seu usuario e senha")
    pdf.passo(4, "Clique em Entrar")
    pdf.ln(2)
    
    pdf.dica("Adicione o site aos favoritos para acesso rapido!")
    pdf.aviso("Nunca compartilhe sua senha com outras pessoas.")
    
    # 2. Registrar Ponto
    pdf.add_page()
    pdf.titulo_secao("2. REGISTRAR PONTO (ENTRADA/SAIDA)")
    
    pdf.subtitulo("Quando registrar?")
    pdf.item("Ao CHEGAR no trabalho (entrada)")
    pdf.item("Ao SAIR para o almoco")
    pdf.item("Ao VOLTAR do almoco")
    pdf.item("Ao SAIR no fim do expediente")
    pdf.ln(2)
    
    pdf.subtitulo("Como registrar?")
    pdf.passo(1, "No menu lateral, clique em Registrar Ponto")
    pdf.passo(2, "Selecione o tipo: Entrada, Saida Almoco, Retorno Almoco ou Saida")
    pdf.passo(3, "Selecione o projeto em que esta trabalhando")
    pdf.passo(4, "Clique no botao REGISTRAR PONTO")
    pdf.passo(5, "Aguarde a confirmacao na tela")
    pdf.ln(2)
    
    pdf.subtitulo("Registro Retroativo (ultimos 3 dias)")
    pdf.paragrafo("Esqueceu de registrar? Voce pode registrar pontos dos ultimos 3 dias:")
    pdf.passo(1, "Na tela de registro, marque Registro retroativo")
    pdf.passo(2, "Selecione a data e horario corretos")
    pdf.passo(3, "Escreva uma justificativa")
    pdf.passo(4, "Clique em registrar")
    pdf.ln(2)
    
    pdf.aviso("O registro retroativo precisa de justificativa e sera analisado pelo gestor.")
    
    # 3. Consultar Registros
    pdf.add_page()
    pdf.titulo_secao("3. CONSULTAR MEUS REGISTROS")
    
    pdf.subtitulo("Para que serve?")
    pdf.paragrafo("Aqui voce pode ver todos os seus registros de ponto, verificar se esta tudo correto e acompanhar suas horas trabalhadas.")
    pdf.ln(2)
    
    pdf.subtitulo("Como consultar?")
    pdf.passo(1, "No menu lateral, clique em Meus Registros")
    pdf.passo(2, "Use os filtros para escolher o periodo")
    pdf.passo(3, "Veja a lista com todos os seus registros")
    pdf.ln(2)
    
    pdf.subtitulo("Informacoes disponiveis:")
    pdf.item("Data e hora de cada registro")
    pdf.item("Tipo (entrada, saida, almoco)")
    pdf.item("Projeto associado")
    pdf.item("Total de horas trabalhadas no dia")
    pdf.item("Saldo do banco de horas")
    pdf.ln(2)
    
    pdf.dica("Consulte seus registros semanalmente para identificar erros rapidamente!")
    
    # 4. Solicitar Correcao
    pdf.add_page()
    pdf.titulo_secao("4. SOLICITAR CORRECAO DE REGISTRO")
    
    pdf.subtitulo("Quando solicitar?")
    pdf.paragrafo("Se voce perceber que um registro esta errado (horario incorreto, esqueceu de bater o ponto), voce pode solicitar uma correcao.")
    pdf.ln(2)
    
    pdf.subtitulo("Como solicitar?")
    pdf.passo(1, "No menu lateral, clique em Solicitar Correcao")
    pdf.passo(2, "Selecione o registro que precisa ser corrigido")
    pdf.passo(3, "Informe o horario correto")
    pdf.passo(4, "Escreva uma justificativa explicando o motivo")
    pdf.passo(5, "Clique em Enviar Solicitacao")
    pdf.ln(2)
    
    pdf.paragrafo("Apos enviar, o gestor ira analisar sua solicitacao. Voce recebera uma notificacao quando ela for aprovada ou rejeitada.")
    pdf.ln(2)
    
    pdf.dica("Seja claro na justificativa para facilitar a aprovacao!")
    
    # 5. Registrar Ausencias
    pdf.add_page()
    pdf.titulo_secao("5. REGISTRAR AUSENCIAS")
    
    pdf.subtitulo("Tipos de ausencia:")
    pdf.item("Atestado medico")
    pdf.item("Ferias")
    pdf.item("Licenca maternidade/paternidade")
    pdf.item("Falta justificada")
    pdf.item("Outros motivos")
    pdf.ln(2)
    
    pdf.subtitulo("Como registrar?")
    pdf.passo(1, "No menu lateral, clique em Registrar Ausencia")
    pdf.passo(2, "Selecione o tipo de ausencia")
    pdf.passo(3, "Informe a data ou periodo")
    pdf.passo(4, "Anexe o documento (se necessario)")
    pdf.passo(5, "Clique em Registrar")
    pdf.ln(2)
    
    pdf.aviso("Sempre anexe documentos quando necessario (atestado medico, etc.)")
    
    # 6. Atestado de Horas
    pdf.add_page()
    pdf.titulo_secao("6. ATESTADO DE HORAS")
    
    pdf.subtitulo("O que e?")
    pdf.paragrafo("O atestado de horas serve para justificar horas nao trabalhadas por motivo de saude ou outros. Diferente da ausencia completa, voce trabalhou parte do dia.")
    pdf.ln(2)
    
    pdf.subtitulo("Quando usar?")
    pdf.item("Saiu mais cedo para consulta medica")
    pdf.item("Chegou atrasado por motivo justificado")
    pdf.item("Precisou se ausentar algumas horas")
    pdf.ln(2)
    
    pdf.subtitulo("Como enviar?")
    pdf.passo(1, "No menu lateral, clique em Atestado de Horas")
    pdf.passo(2, "Informe a data")
    pdf.passo(3, "Informe quantas horas o atestado cobre")
    pdf.passo(4, "Escreva o motivo")
    pdf.passo(5, "Anexe o documento (opcional)")
    pdf.passo(6, "Clique em Enviar para Aprovacao")
    
    # 7. Horas Extras
    pdf.add_page()
    pdf.titulo_secao("7. SOLICITAR HORAS EXTRAS")
    
    pdf.subtitulo("ANTES de fazer hora extra:")
    pdf.aviso("Voce DEVE solicitar autorizacao ANTES de fazer hora extra!")
    pdf.ln(2)
    
    pdf.subtitulo("Como solicitar?")
    pdf.passo(1, "No menu lateral, clique em Horas Extras")
    pdf.passo(2, "Clique em Solicitar Hora Extra")
    pdf.passo(3, "Selecione o gestor que vai aprovar")
    pdf.passo(4, "Escreva a justificativa (por que precisa fazer HE)")
    pdf.passo(5, "Clique em Enviar Solicitacao")
    pdf.passo(6, "Aguarde a aprovacao do gestor")
    pdf.ln(2)
    
    pdf.subtitulo("Apos aprovacao:")
    pdf.paragrafo("Quando o gestor aprovar, voce pode comecar a hora extra. Ao terminar, clique em Finalizar Hora Extra para registrar.")
    pdf.ln(2)
    
    pdf.dica("Sempre tenha a aprovacao ANTES de comecar a hora extra!")
    
    # 8. Banco de Horas
    pdf.add_page()
    pdf.titulo_secao("8. CONSULTAR BANCO DE HORAS")
    
    pdf.subtitulo("O que e o banco de horas?")
    pdf.paragrafo("O banco de horas e o saldo de horas que voce trabalhou a mais (positivo) ou a menos (negativo) em relacao a sua jornada normal.")
    pdf.ln(2)
    
    pdf.subtitulo("Como consultar?")
    pdf.passo(1, "No menu lateral, clique em Meu Banco de Horas")
    pdf.passo(2, "Veja o saldo total no topo da tela")
    pdf.passo(3, "Consulte o historico de movimentacoes")
    pdf.ln(2)
    
    pdf.subtitulo("Entendendo o saldo:")
    pdf.item("Saldo POSITIVO: voce trabalhou mais que o esperado")
    pdf.item("Saldo NEGATIVO: voce trabalhou menos que o esperado")
    pdf.item("Saldo ZERADO: voce cumpriu a jornada certinho")
    pdf.ln(2)
    
    pdf.dica("Mantenha seu banco de horas equilibrado!")
    
    # 9. Horas por Projeto
    pdf.add_page()
    pdf.titulo_secao("9. VER HORAS POR PROJETO")
    
    pdf.subtitulo("Para que serve?")
    pdf.paragrafo("Aqui voce pode ver quantas horas trabalhou em cada projeto. Util para acompanhar sua dedicacao em diferentes atividades.")
    pdf.ln(2)
    
    pdf.subtitulo("Como consultar?")
    pdf.passo(1, "No menu lateral, clique em Minhas Horas por Projeto")
    pdf.passo(2, "Selecione o periodo desejado")
    pdf.passo(3, "Veja o grafico e a tabela com as horas por projeto")
    
    # 10. Mensagens e Notificacoes
    pdf.add_page()
    pdf.titulo_secao("10. MENSAGENS E NOTIFICACOES")
    
    pdf.subtitulo("Mensagens")
    pdf.paragrafo("O gestor pode enviar mensagens diretamente para voce. Para ver:")
    pdf.passo(1, "No menu lateral, clique em Mensagens")
    pdf.passo(2, "Veja as mensagens nao lidas (marcadas em vermelho)")
    pdf.passo(3, "Clique em cada mensagem para ler")
    pdf.passo(4, "Marque como lida apos visualizar")
    pdf.ln(2)
    
    pdf.subtitulo("Notificacoes")
    pdf.paragrafo("As notificacoes mostram eventos importantes:")
    pdf.item("Aprovacao/rejeicao de horas extras")
    pdf.item("Aprovacao/rejeicao de atestados")
    pdf.item("Respostas de solicitacoes de correcao")
    pdf.item("Avisos gerais do gestor")
    pdf.ln(2)
    
    pdf.passo(1, "No menu lateral, clique em Notificacoes")
    pdf.passo(2, "Veja o numero de notificacoes pendentes")
    
    # 11. Configurar Lembretes no Celular - PARTE MAIS IMPORTANTE
    pdf.add_page()
    pdf.titulo_secao("11. CONFIGURAR LEMBRETES NO CELULAR")
    
    pdf.subtitulo("Receba lembretes mesmo com o app fechado!")
    pdf.paragrafo("O sistema pode enviar lembretes para seu celular nos horarios de registrar o ponto. Voce recebe notificacoes mesmo sem estar usando o app!")
    pdf.ln(2)
    
    pdf.subtitulo("PASSO A PASSO PARA CONFIGURAR:")
    pdf.ln(2)
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 6, "PARTE 1: Instalar o app ntfy no celular", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 9)
    pdf.passo(1, "Abra a loja de aplicativos (Play Store ou App Store)")
    pdf.passo(2, "Pesquise por ntfy")
    pdf.passo(3, "Instale o app ntfy (icone com sino)")
    pdf.passo(4, "Abra o app ntfy")
    pdf.ln(2)
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 6, "PARTE 2: Ativar lembretes no Ponto ExSA", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 9)
    pdf.passo(1, "Acesse o Ponto ExSA pelo navegador")
    pdf.passo(2, "Faca login com seu usuario")
    pdf.passo(3, "No menu lateral, procure Lembretes de Ponto")
    pdf.passo(4, "Clique em Ativar Lembretes")
    pdf.passo(5, "Anote o TOPICO que aparecera (ex: ponto-esa-abc123)")
    pdf.ln(2)
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 6, "PARTE 3: Inscrever-se no topico", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 9)
    pdf.passo(1, "Abra o app ntfy no celular")
    pdf.passo(2, "Toque no botao + (adicionar)")
    pdf.passo(3, "Digite o topico que voce anotou")
    pdf.passo(4, "Toque em Inscrever-se")
    pdf.passo(5, "Pronto! Voce recebera as notificacoes!")
    pdf.ln(2)
    
    pdf.subtitulo("Horarios dos lembretes:")
    pdf.item("07:50 - Lembrete para registrar entrada")
    pdf.item("12:00 - Lembrete para registrar saida almoco")
    pdf.item("13:00 - Lembrete para registrar retorno almoco")
    pdf.item("16:50 - Lembrete para registrar saida")
    
    pdf.add_page()
    pdf.subtitulo("Personalizar horarios dos lembretes:")
    pdf.paragrafo("Voce pode configurar horarios personalizados:")
    pdf.passo(1, "No menu lateral, clique em Configurar Horarios")
    pdf.passo(2, "Altere os horarios conforme sua jornada")
    pdf.passo(3, "Clique em Salvar Horarios")
    pdf.ln(2)
    
    pdf.dica("Configure os horarios 10 minutos antes do seu registro real!")
    
    # 12. Duvidas Frequentes
    pdf.add_page()
    pdf.titulo_secao("12. DUVIDAS FREQUENTES")
    
    pdf.subtitulo("Esqueci de registrar o ponto. O que faco?")
    pdf.paragrafo("Use o Registro Retroativo (ultimos 3 dias) ou solicite uma Correcao de Registro ao gestor.")
    pdf.ln(2)
    
    pdf.subtitulo("Registrei o ponto errado. Como corrigir?")
    pdf.paragrafo("Va em Solicitar Correcao de Registro e envie a solicitacao com a justificativa.")
    pdf.ln(2)
    
    pdf.subtitulo("Nao recebi a notificacao no celular. Por que?")
    pdf.paragrafo("Verifique: 1) Se o app ntfy esta instalado; 2) Se voce se inscreveu no topico correto; 3) Se as notificacoes estao permitidas nas configuracoes do celular.")
    pdf.ln(2)
    
    pdf.subtitulo("Minha hora extra foi rejeitada. E agora?")
    pdf.paragrafo("Verifique o motivo da rejeicao nas notificacoes. Se necessario, faca uma nova solicitacao com justificativa mais detalhada.")
    pdf.ln(2)
    
    pdf.subtitulo("Preciso de ajuda. Quem procurar?")
    pdf.paragrafo("Entre em contato com seu gestor ou com o setor de RH da empresa.")
    
    # Pagina final
    pdf.add_page()
    pdf.ln(30)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, 'Obrigado por usar o Ponto ExSA!', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(5)
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 10, 'Em caso de duvidas, procure seu gestor.', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(15)
    pdf.set_font('Helvetica', 'I', 9)
    pdf.cell(0, 10, 'Expressao Socioambiental', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.cell(0, 10, 'Janeiro/2026', new_x="LMARGIN", new_y="NEXT", align='C')
    
    # Salvar
    pdf.output('Cartilha_Funcionario_PontoExSA.pdf')
    print("Cartilha do Funcionario gerada: Cartilha_Funcionario_PontoExSA.pdf")


def gerar_cartilha_gestor():
    """Gera a cartilha do gestor"""
    pdf = CartilhaPDF("Cartilha do Gestor")
    
    # Capa
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 24)
    pdf.ln(40)
    pdf.cell(0, 15, 'CARTILHA DO GESTOR', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_font('Helvetica', '', 14)
    pdf.cell(0, 10, 'Sistema de Ponto Eletronico - Ponto ExSA', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(15)
    pdf.set_font('Helvetica', 'I', 11)
    pdf.cell(0, 10, 'Guia completo de administracao', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(30)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(0, 10, 'Versao: Janeiro/2026', new_x="LMARGIN", new_y="NEXT", align='C')
    
    # Sumario
    pdf.add_page()
    pdf.titulo_secao("SUMARIO")
    pdf.paragrafo("1. Introducao e Acesso ao Sistema")
    pdf.paragrafo("2. Dashboard - Visao Geral")
    pdf.paragrafo("3. Todos os Registros")
    pdf.paragrafo("4. Aprovar Atestados")
    pdf.paragrafo("5. Aprovar Horas Extras")
    pdf.paragrafo("6. Corrigir Registros")
    pdf.paragrafo("7. Relatorios")
    pdf.paragrafo("8. Banco de Horas Geral")
    pdf.paragrafo("9. Gerenciar Usuarios")
    pdf.paragrafo("10. Gerenciar Projetos")
    pdf.paragrafo("11. Comunicacao (Avisos e Mensagens)")
    pdf.paragrafo("12. Gerenciar Ferias")
    pdf.paragrafo("13. Notificacoes e Lembretes")
    pdf.paragrafo("14. Configuracoes do Sistema")
    
    # 1. Introducao
    pdf.add_page()
    pdf.titulo_secao("1. INTRODUCAO E ACESSO AO SISTEMA")
    
    pdf.subtitulo("Funcao do Gestor")
    pdf.paragrafo("Como gestor, voce tem acesso a funcionalidades administrativas que permitem gerenciar a equipe, aprovar solicitacoes, gerar relatorios e configurar o sistema.")
    pdf.ln(2)
    
    pdf.subtitulo("Como acessar?")
    pdf.passo(1, "Abra o navegador (Chrome, Safari, etc.)")
    pdf.passo(2, "Digite: ponto-esa-v5.onrender.com")
    pdf.passo(3, "Digite seu usuario e senha de GESTOR")
    pdf.passo(4, "Clique em Entrar")
    pdf.ln(2)
    
    pdf.aviso("Mantenha sua senha segura. O acesso de gestor tem privilegios elevados.")
    
    # 2. Dashboard
    pdf.add_page()
    pdf.titulo_secao("2. DASHBOARD - VISAO GERAL")
    
    pdf.subtitulo("O que mostra?")
    pdf.paragrafo("O Dashboard e a tela inicial do gestor, mostrando um resumo de toda a equipe:")
    pdf.item("Total de funcionarios ativos")
    pdf.item("Funcionarios presentes/ausentes hoje")
    pdf.item("Solicitacoes pendentes (HE, atestados, correcoes)")
    pdf.item("Graficos de presenca da semana")
    pdf.item("Alertas importantes")
    pdf.ln(2)
    
    pdf.dica("Acesse o Dashboard diariamente para ter uma visao geral da equipe!")
    
    # 3. Todos os Registros
    pdf.add_page()
    pdf.titulo_secao("3. TODOS OS REGISTROS")
    
    pdf.subtitulo("Para que serve?")
    pdf.paragrafo("Permite visualizar os registros de ponto de TODOS os funcionarios. Util para auditoria e acompanhamento.")
    pdf.ln(2)
    
    pdf.subtitulo("Como usar?")
    pdf.passo(1, "No menu lateral, clique em Todos os Registros")
    pdf.passo(2, "Selecione o funcionario (ou todos)")
    pdf.passo(3, "Selecione o periodo desejado")
    pdf.passo(4, "Visualize os registros na tabela")
    pdf.passo(5, "Exporte para Excel se necessario")
    pdf.ln(2)
    
    pdf.dica("Use os filtros para encontrar rapidamente o que precisa!")
    
    # 4. Aprovar Atestados
    pdf.add_page()
    pdf.titulo_secao("4. APROVAR ATESTADOS")
    
    pdf.subtitulo("Sua responsabilidade:")
    pdf.paragrafo("Analisar e aprovar/rejeitar atestados de horas enviados pelos funcionarios. O atestado justifica horas nao trabalhadas.")
    pdf.ln(2)
    
    pdf.subtitulo("Como aprovar?")
    pdf.passo(1, "No menu lateral, clique em Aprovar Atestados")
    pdf.passo(2, "Veja a lista de atestados pendentes")
    pdf.passo(3, "Clique em um atestado para ver detalhes")
    pdf.passo(4, "Verifique o documento anexado (se houver)")
    pdf.passo(5, "Clique em Aprovar ou Rejeitar")
    pdf.passo(6, "Se rejeitar, informe o motivo")
    pdf.ln(2)
    
    pdf.aviso("O funcionario recebera uma notificacao automatica com sua decisao.")
    
    # 5. Aprovar Horas Extras
    pdf.add_page()
    pdf.titulo_secao("5. APROVAR HORAS EXTRAS")
    
    pdf.subtitulo("Fluxo de aprovacao:")
    pdf.paragrafo("Funcionarios devem solicitar hora extra ANTES de realiza-la. Voce recebe a solicitacao e decide se aprova ou nao.")
    pdf.ln(2)
    
    pdf.subtitulo("Como aprovar?")
    pdf.passo(1, "No menu lateral, clique em Aprovar Horas Extras")
    pdf.passo(2, "Veja as solicitacoes pendentes")
    pdf.passo(3, "Analise a justificativa do funcionario")
    pdf.passo(4, "Clique em Aprovar ou Rejeitar")
    pdf.passo(5, "Se rejeitar, informe o motivo")
    pdf.ln(2)
    
    pdf.subtitulo("Apos aprovacao:")
    pdf.paragrafo("O funcionario recebe uma notificacao e pode comecar a hora extra. As horas serao contabilizadas no banco de horas.")
    pdf.ln(2)
    
    pdf.dica("Voce recebe uma notificacao no celular quando alguem solicita HE!")
    
    # 6. Corrigir Registros
    pdf.add_page()
    pdf.titulo_secao("6. CORRIGIR REGISTROS")
    
    pdf.subtitulo("Quando usar?")
    pdf.paragrafo("Funcionarios solicitam correcoes quando registraram o ponto errado ou esqueceram de registrar.")
    pdf.ln(2)
    
    pdf.subtitulo("Como aprovar correcoes?")
    pdf.passo(1, "No menu lateral, clique em Corrigir Registros")
    pdf.passo(2, "Veja as solicitacoes pendentes")
    pdf.passo(3, "Analise o horario original vs. o solicitado")
    pdf.passo(4, "Leia a justificativa do funcionario")
    pdf.passo(5, "Clique em Aprovar ou Rejeitar")
    pdf.ln(2)
    
    pdf.aviso("Verifique se a justificativa e coerente antes de aprovar!")
    
    # 7. Relatorios
    pdf.add_page()
    pdf.titulo_secao("7. RELATORIOS")
    
    pdf.subtitulo("Relatorios disponiveis:")
    pdf.item("Relatorio de presenca (diario, semanal, mensal)")
    pdf.item("Relatorio de horas extras")
    pdf.item("Relatorio de banco de horas")
    pdf.item("Relatorio de horas por projeto")
    pdf.item("Relatorio de ausencias")
    pdf.ln(2)
    
    pdf.subtitulo("Como gerar?")
    pdf.passo(1, "No menu lateral, clique em Relatorios")
    pdf.passo(2, "Selecione o tipo de relatorio")
    pdf.passo(3, "Defina o periodo e filtros")
    pdf.passo(4, "Clique em Gerar Relatorio")
    pdf.passo(5, "Exporte para Excel ou PDF")
    pdf.ln(2)
    
    pdf.dica("Gere relatorios mensais para acompanhamento da equipe!")
    
    # 8. Banco de Horas Geral
    pdf.add_page()
    pdf.titulo_secao("8. BANCO DE HORAS GERAL")
    
    pdf.subtitulo("Visao consolidada:")
    pdf.paragrafo("Veja o saldo de banco de horas de todos os funcionarios em uma unica tela.")
    pdf.ln(2)
    
    pdf.subtitulo("Como acessar?")
    pdf.passo(1, "No menu lateral, clique em Banco de Horas Geral")
    pdf.passo(2, "Veja a tabela com todos os funcionarios")
    pdf.passo(3, "Identifique quem tem saldo positivo ou negativo")
    pdf.passo(4, "Clique em um funcionario para ver detalhes")
    pdf.ln(2)
    
    pdf.aviso("Acompanhe funcionarios com saldo muito negativo!")
    
    # 9. Gerenciar Usuarios
    pdf.add_page()
    pdf.titulo_secao("9. GERENCIAR USUARIOS")
    
    pdf.subtitulo("Funcoes disponiveis:")
    pdf.item("Cadastrar novos funcionarios")
    pdf.item("Editar dados de funcionarios")
    pdf.item("Ativar/desativar funcionarios")
    pdf.item("Redefinir senhas")
    pdf.item("Definir jornada de trabalho")
    pdf.ln(2)
    
    pdf.subtitulo("Cadastrar novo funcionario:")
    pdf.passo(1, "Clique em Gerenciar Usuarios")
    pdf.passo(2, "Clique em Adicionar Usuario")
    pdf.passo(3, "Preencha: nome, usuario, senha, CPF, data nascimento")
    pdf.passo(4, "Defina o tipo (funcionario ou gestor)")
    pdf.passo(5, "Configure a jornada de trabalho")
    pdf.passo(6, "Clique em Salvar")
    
    # 10. Gerenciar Projetos
    pdf.add_page()
    pdf.titulo_secao("10. GERENCIAR PROJETOS")
    
    pdf.subtitulo("Para que serve?")
    pdf.paragrafo("Cadastre os projetos da empresa para que os funcionarios possam associar seus registros de ponto.")
    pdf.ln(2)
    
    pdf.subtitulo("Como cadastrar projeto?")
    pdf.passo(1, "Clique em Gerenciar Projetos")
    pdf.passo(2, "Clique em Adicionar Projeto")
    pdf.passo(3, "Informe o nome do projeto")
    pdf.passo(4, "Adicione descricao (opcional)")
    pdf.passo(5, "Clique em Salvar")
    pdf.ln(2)
    
    pdf.dica("Mantenha os projetos organizados para relatorios precisos!")
    
    # 11. Comunicacao
    pdf.add_page()
    pdf.titulo_secao("11. COMUNICACAO (AVISOS E MENSAGENS)")
    
    pdf.subtitulo("Enviar aviso para todos:")
    pdf.paragrafo("Use para comunicados gerais que todos devem ver.")
    pdf.passo(1, "Clique em Comunicacao")
    pdf.passo(2, "Clique na aba Enviar Aviso")
    pdf.passo(3, "Digite o titulo e a mensagem")
    pdf.passo(4, "Selecione Todos os funcionarios ou escolha especificos")
    pdf.passo(5, "Clique em Enviar Aviso")
    pdf.ln(2)
    
    pdf.subtitulo("Mensagem direta:")
    pdf.paragrafo("Use para comunicar algo a um funcionario especifico.")
    pdf.passo(1, "Clique em Comunicacao")
    pdf.passo(2, "Clique na aba Mensagem Direta")
    pdf.passo(3, "Selecione o destinatario")
    pdf.passo(4, "Digite a mensagem")
    pdf.passo(5, "Clique em Enviar Mensagem")
    pdf.ln(2)
    
    pdf.aviso("O funcionario recebe a mensagem como notificacao no celular!")
    
    # 12. Gerenciar Ferias
    pdf.add_page()
    pdf.titulo_secao("12. GERENCIAR FERIAS")
    
    pdf.subtitulo("Cadastrar ferias de funcionario:")
    pdf.passo(1, "Clique em Ferias")
    pdf.passo(2, "Clique na aba Cadastrar Ferias")
    pdf.passo(3, "Selecione o funcionario")
    pdf.passo(4, "Informe data de inicio e fim")
    pdf.passo(5, "Defina quantos dias antes notificar")
    pdf.passo(6, "Clique em Cadastrar Ferias")
    pdf.ln(2)
    
    pdf.paragrafo("O sistema enviara automaticamente um lembrete para o funcionario X dias antes das ferias.")
    pdf.ln(2)
    
    pdf.subtitulo("Visualizar ferias cadastradas:")
    pdf.paragrafo("Na aba Ferias Cadastradas voce ve todas as ferias programadas e pode excluir se necessario.")
    
    # 13. Notificacoes
    pdf.add_page()
    pdf.titulo_secao("13. NOTIFICACOES E LEMBRETES")
    
    pdf.subtitulo("Notificacoes automaticas para o gestor:")
    pdf.item("Novas solicitacoes de hora extra")
    pdf.item("Novos atestados enviados")
    pdf.item("Novas solicitacoes de correcao")
    pdf.item("Resumo diario de pendencias (8h da manha)")
    pdf.ln(2)
    
    pdf.subtitulo("Configurar lembretes no celular:")
    pdf.paragrafo("O gestor tambem pode receber lembretes no celular. Siga o mesmo processo do funcionario:")
    pdf.passo(1, "Instale o app ntfy no celular")
    pdf.passo(2, "Ative os lembretes no menu lateral do Ponto ExSA")
    pdf.passo(3, "Anote o topico gerado")
    pdf.passo(4, "Inscreva-se no topico pelo app ntfy")
    pdf.ln(2)
    
    pdf.subtitulo("O que voce recebe no celular:")
    pdf.item("Lembretes de ponto (se configurado)")
    pdf.item("Novas solicitacoes de funcionarios")
    pdf.item("Resumo de pendencias pela manha")
    pdf.item("Aniversarios de funcionarios")
    
    # 14. Configuracoes
    pdf.add_page()
    pdf.titulo_secao("14. CONFIGURACOES DO SISTEMA")
    
    pdf.subtitulo("Configurar Jornada:")
    pdf.paragrafo("Defina os horarios padrao de entrada e saida para a empresa.")
    pdf.passo(1, "Clique em Configurar Jornada")
    pdf.passo(2, "Defina horario de entrada e saida")
    pdf.passo(3, "Defina tolerancia (minutos)")
    pdf.passo(4, "Salve as configuracoes")
    pdf.ln(2)
    
    pdf.subtitulo("Sistema:")
    pdf.paragrafo("Em Sistema voce encontra:")
    pdf.item("Informacoes sobre o banco de dados")
    pdf.item("Logs do sistema")
    pdf.item("Backup de dados")
    pdf.item("Configuracoes avancadas")
    pdf.ln(2)
    
    pdf.aviso("Cuidado com configuracoes avancadas - podem afetar todo o sistema!")
    
    # Resumo de pendencias
    pdf.add_page()
    pdf.titulo_secao("RESUMO: TAREFAS DIARIAS DO GESTOR")
    
    pdf.subtitulo("Todo dia:")
    pdf.item("Verificar o Dashboard")
    pdf.item("Aprovar/rejeitar solicitacoes pendentes")
    pdf.item("Verificar notificacoes")
    pdf.ln(2)
    
    pdf.subtitulo("Toda semana:")
    pdf.item("Gerar relatorio semanal de presenca")
    pdf.item("Verificar banco de horas da equipe")
    pdf.item("Enviar avisos importantes (se houver)")
    pdf.ln(2)
    
    pdf.subtitulo("Todo mes:")
    pdf.item("Gerar relatorio mensal")
    pdf.item("Verificar ferias programadas")
    pdf.item("Revisar usuarios ativos/inativos")
    
    # Pagina final
    pdf.add_page()
    pdf.ln(30)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, 'Obrigado por usar o Ponto ExSA!', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(5)
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 10, 'Em caso de duvidas tecnicas, contate o suporte.', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(15)
    pdf.set_font('Helvetica', 'I', 9)
    pdf.cell(0, 10, 'Expressao Socioambiental', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.cell(0, 10, 'Janeiro/2026', new_x="LMARGIN", new_y="NEXT", align='C')
    
    # Salvar
    pdf.output('Cartilha_Gestor_PontoExSA.pdf')
    print("Cartilha do Gestor gerada: Cartilha_Gestor_PontoExSA.pdf")


if __name__ == "__main__":
    print("="*50)
    print("GERANDO CARTILHAS PDF - PONTO ExSA")
    print("="*50)
    print()
    
    print("Gerando Cartilha do Funcionario...")
    gerar_cartilha_funcionario()
    
    print()
    print("Gerando Cartilha do Gestor...")
    gerar_cartilha_gestor()
    
    print()
    print("="*50)
    print("CARTILHAS GERADAS COM SUCESSO!")
    print("="*50)
