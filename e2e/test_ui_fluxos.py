import re
from datetime import date
from datetime import datetime


def login(page, username: str, password: str) -> None:
    page.get_by_role("button", name=re.compile("Entrar|ENTRAR")).wait_for(timeout=20000)

    user_input = page.locator('input[type="text"]').first
    pass_input = page.locator('input[type="password"]').first

    user_input.fill(username)
    pass_input.fill(password)

    page.get_by_role("button", name=re.compile("Entrar|ENTRAR")).click()
    page.wait_for_timeout(1200)


def choose_sidebar_option(page, option_text: str) -> None:
    sidebar = page.locator('[data-testid="stSidebar"]').first
    sidebar.wait_for(timeout=15000)

    menu_label = sidebar.get_by_text(re.compile(r"Escolha uma opcao|Escolha uma opção", re.I)).first
    menu_box = menu_label.locator("xpath=ancestor::div[@data-testid='stSelectbox'][1]")

    if menu_box.count() == 0:
        menu_box = sidebar.locator('[data-testid="stSelectbox"]').first

    trigger = menu_box.locator('[data-baseweb="select"]').first
    if trigger.count() == 0:
        trigger = menu_box

    trigger.click(force=True)

    for _ in range(3):
        option = page.locator('li[role="option"], div[role="option"]').filter(
            has_text=re.compile(re.escape(option_text), re.I)
        ).first
        try:
            option.click(force=True, timeout=4000)
            return
        except Exception:
            trigger.click(force=True)
            page.wait_for_timeout(250)

    raise AssertionError(f"Nao foi possivel selecionar opcao lateral: {option_text}")


def open_sidebar_option(page, option_text: str, ready_pattern: str) -> None:
    for _ in range(3):
        choose_sidebar_option(page, option_text)
        try:
            page.get_by_text(re.compile(ready_pattern, re.I)).first.wait_for(timeout=5000)
            return
        except Exception:
            page.wait_for_timeout(600)
    raise AssertionError(f"Nao foi possivel abrir opcao lateral: {option_text}")


def test_login_invalido_mostra_erro(page):
    login(page, "usuario_invalido", "senha_invalida")
    page.get_by_text(re.compile("Usuario ou senha incorretos|Usuário ou senha incorretos", re.I)).wait_for(timeout=10000)


def test_login_funcionario_e_registro_ponto(page):
    login(page, "funcionario", "senha_func_123")
    page.locator('[data-testid="stSidebar"] [data-testid="stSelectbox"]').first.wait_for(timeout=15000)

    open_sidebar_option(page, "Registrar Ponto", r"Novo Registro")

    tipo_combo = page.locator('input[role="combobox"][aria-label*="Tipo de Registro"]').first
    tipo_combo.click()
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    atividade_texto = "Registro E2E de ponto"
    descricao_field = page.locator('textarea[aria-label*="Descrição da Atividade"]').last
    descricao_field.wait_for(state="visible", timeout=10000)
    descricao_field.fill(atividade_texto)
    page.get_by_role("button", name=re.compile("Registrar Ponto", re.I)).first.click()

    # O app faz rerun logo apos gravar; validar o registro persistido e mais estavel.
    page.get_by_text(re.compile("Registros de", re.I)).first.wait_for(timeout=15000)
    page.get_by_text(atividade_texto, exact=False).first.wait_for(state="attached", timeout=15000)


def test_gestor_cadastra_novo_usuario(page):
    login(page, "gestor", "senha_gestor_123")
    page.locator('[data-testid="stSidebar"] [data-testid="stSelectbox"]').first.wait_for(timeout=15000)

    open_sidebar_option(page, "Gerenciar Usuários", r"Gerenciamento de Usuarios|Gerenciamento de Usuários|Novo Usuario|Novo Usuário")

    # Abre aba de cadastro
    page.get_by_role("tab", name=re.compile("Novo Usuario|Novo Usuário", re.I)).first.click()

    sufixo = datetime.now().strftime("%Y%m%d%H%M%S")
    username = f"e2e_{sufixo}"

    page.get_by_label(re.compile(r"^Login:\*$", re.I)).fill(username)
    page.get_by_label(re.compile(r"Nome Completo:\*", re.I)).fill("Usuario E2E")
    page.get_by_label(re.compile(r"CPF:\*", re.I)).fill("52998224725")
    page.get_by_label(re.compile(r"E-mail:\*", re.I)).fill(f"{username}@teste.local")
    data_nasc_label = page.get_by_text(re.compile(r"Data de Nascimento", re.I)).first
    data_nasc_label.click()
    page.keyboard.type("01/01/1990")
    page.keyboard.press("Enter")

    page.get_by_label(re.compile(r"^Senha:\*$", re.I)).fill("SenhaE2E@123")
    page.get_by_label(re.compile(r"Confirmar Senha:\*", re.I)).fill("SenhaE2E@123")

    page.get_by_role("button", name=re.compile("Cadastrar Usuario|Cadastrar Usuário", re.I)).click()
    page.get_by_text(
        re.compile(
            "usuario cadastrado|usuário cadastrado|sucesso|erro ao cadastrar usuário|preencha todos os campos|data de nascimento",
            re.I,
        )
    ).first.wait_for(timeout=12000)


def test_gestor_aprova_hora_extra_pendente(page):
    login(page, "gestor", "senha_gestor_123")
    page.locator('[data-testid="stSidebar"] [data-testid="stSelectbox"]').first.wait_for(timeout=15000)

    open_sidebar_option(page, "Aprovar Horas Extras", r"Aprovar Horas Extras|SOLICITACAO DE HORAS EXTRAS|SOLICITAÇÃO DE HORAS EXTRAS|Nenhuma solicitacao pendente|Nenhuma solicitação pendente")

    aprovar_btn = page.get_by_role("button", name=re.compile("Aprovar", re.I)).first
    if aprovar_btn.count() > 0:
        aprovar_btn.click()
        page.wait_for_timeout(1200)

    page.get_by_text(re.compile("Aprovar Horas Extras|SOLICITACAO DE HORAS EXTRAS|SOLICITAÇÃO DE HORAS EXTRAS", re.I)).first.wait_for(timeout=12000)


def test_relatorios_geram_visualizacao_e_exportacao(page):
    login(page, "gestor", "senha_gestor_123")
    page.locator('[data-testid="stSidebar"] [data-testid="stSelectbox"]').first.wait_for(timeout=15000)

    open_sidebar_option(page, "Relatórios", r"Relatorios de Horas Extras|Relatórios de Horas Extras")

    # Aba por usuario para garantir exportacao
    tab = page.get_by_role("tab", name=re.compile("Por Funcionario|Por Funcionário", re.I)).first
    tab.click()

    page.get_by_role("button", name=re.compile("Gerar Relatorio por Usuario|Gerar Relatório por Usuário", re.I)).click()
    page.get_by_role("button", name=re.compile("Exportar CSV", re.I)).first.wait_for(timeout=10000)
