from cartilha_funcionario import gerar_cartilha_funcionario


if __name__ == '__main__':
    gerar_cartilha_funcionario(md_path="ESPECIFICACAO_GESTOR.md", out_pdf="cartilha_gestor.pdf")
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

def gerar_cartilha_gestor():
    c = canvas.Canvas("cartilha_gestor.pdf", pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 18)
    c.drawString(2*cm, height-2*cm, "Cartilha do Gestor - App Ponto ESA")

    c.setFont("Helvetica", 12)
    y = height-3*cm
    c.drawString(2*cm, y, "1. Instalação do App")
    y -= 1*cm
    c.drawString(2.5*cm, y, "- Baixe o app na Play Store ou App Store.")
    y -= 0.7*cm
    c.drawString(2.5*cm, y, "- Permita notificações para receber avisos importantes.")
    y -= 0.7*cm
    c.drawString(2.5*cm, y, "- Faça login com seu usuário e senha fornecidos pela empresa.")

    y -= 1.2*cm
    c.drawString(2*cm, y, "2. Acompanhando a Equipe")
    y -= 0.7*cm
    c.drawString(2.5*cm, y, "- Veja o status de ponto dos colaboradores em tempo real.")
    y -= 0.7*cm
    c.drawString(2.5*cm, y, "- Receba alertas de atrasos e ausências.")

    y -= 1.2*cm
    c.drawString(2*cm, y, "3. Aprovação de Justificativas")
    y -= 0.7*cm
    c.drawString(2.5*cm, y, "- Analise e aprove/reprove justificativas enviadas pela equipe.")
    y -= 0.7*cm
    c.drawString(2.5*cm, y, "- Consulte documentos anexados.")

    y -= 1.2*cm
    c.drawString(2*cm, y, "4. Relatórios Gerenciais")
    y -= 0.7*cm
    c.drawString(2.5*cm, y, "- Gere relatórios de frequência e exporte para Excel ou PDF.")
    y -= 0.7*cm
    c.drawString(2.5*cm, y, "- Analise indicadores de presença e pontualidade.")

    y -= 1.2*cm
    c.drawString(2*cm, y, "5. Notificações")
    y -= 0.7*cm
    c.drawString(2.5*cm, y, "- Ative as notificações do app nas configurações do seu celular.")
    y -= 0.7*cm
    c.drawString(2.5*cm, y, "- Receba avisos sobre solicitações e pendências da equipe.")

    y -= 1.2*cm
    c.drawString(2*cm, y, "6. Dicas de Gestão")
    y -= 0.7*cm
    c.drawString(2.5*cm, y, "- Oriente a equipe sobre a importância do registro correto do ponto.")
    y -= 0.7*cm
    c.drawString(2.5*cm, y, "- Utilize os relatórios para melhorar a gestão do time.")

    c.save()

if __name__ == "__main__":
    gerar_cartilha_gestor()
