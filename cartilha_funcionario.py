from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
import textwrap
import os
import re


def gerar_cartilha_funcionario(md_path="ESPECIFICACAO_FUNCIONARIO.md", out_pdf="cartilha_funcionario.pdf"):
    # Ler o markdown gerado pelo sistema e renderizar em PDF (simples, linha a linha)
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            md = f.read()
    except Exception:
        md = "Guia do Funcionário - conteúdo não encontrado. Coloque ESPECIFICACAO_FUNCIONARIO.md na raiz."

    c = canvas.Canvas(out_pdf, pagesize=A4)
    width, height = A4

    left_margin = 2 * cm
    right_margin = 2 * cm
    usable_width = width - left_margin - right_margin
    bottom_margin = 2 * cm

    # Configurações de fonte
    title_font = ("Helvetica-Bold", 16)
    normal_font = ("Helvetica", 10)

    y = height - 2 * cm

    # Título
    c.setFont(*title_font)
    c.drawString(left_margin, y, "Cartilha do Funcionário - Ponto ExSA")
    y -= 1 * cm

    # Converter markdown em parágrafos simples (ignorar formatação complexa)
    paragraphs = md.split('\n\n')

    c.setFont(*normal_font)
    img_pattern = re.compile(r"!\[.*?\]\((.*?)\)")

    md_dir = os.path.dirname(os.path.abspath(md_path)) or "."

    for p in paragraphs:
        # Se o parágrafo contém uma tag de imagem Markdown, renderize a imagem
        img_match = img_pattern.search(p)
        if img_match:
            img_path = img_match.group(1).strip()
            # Caminho relativo ao markdown
            if not os.path.isabs(img_path):
                img_path = os.path.join(md_dir, img_path)

            # Remover a linha da imagem do texto do parágrafo para evitar duplicação
            text_only = img_pattern.sub('', p).strip()

            # Renderizar texto antes da imagem, se houver
            if text_only:
                for raw_line in text_only.split('\n'):
                    wrapped = textwrap.wrap(raw_line, width=100)
                    if not wrapped:
                        lines = [""]
                    else:
                        lines = wrapped
                    for line in lines:
                        if y < bottom_margin + 3 * cm:
                            c.showPage()
                            c.setFont(*normal_font)
                            y = height - 2 * cm
                        c.drawString(left_margin, y, line)
                        y -= 0.6 * cm

            # Tentar incluir a imagem se existir
            if os.path.exists(img_path):
                try:
                    img = ImageReader(img_path)
                    iw, ih = img.getSize()
                    max_w = usable_width
                    max_h = y - bottom_margin
                    if max_h <= 0:
                        c.showPage()
                        y = height - 2 * cm
                        max_h = y - bottom_margin

                    scale = min(max_w / iw, max_h / ih, 1.0)
                    draw_w = iw * scale
                    draw_h = ih * scale
                    # Se não couber verticalmente na página atual, criar nova página
                    if draw_h + 1 * cm > (y - bottom_margin):
                        c.showPage()
                        c.setFont(*normal_font)
                        y = height - 2 * cm

                    c.drawImage(img, left_margin, y - draw_h, width=draw_w, height=draw_h)
                    y -= (draw_h + 0.4 * cm)
                except Exception:
                    # Falha ao desenhar a imagem — inserir aviso textual
                    if y < bottom_margin + 2 * cm:
                        c.showPage()
                        c.setFont(*normal_font)
                        y = height - 2 * cm
                    c.drawString(left_margin, y, f"[Imagem inválida: {os.path.basename(img_path)}]")
                    y -= 0.6 * cm
            else:
                if y < bottom_margin + 2 * cm:
                    c.showPage()
                    c.setFont(*normal_font)
                    y = height - 2 * cm
                c.drawString(left_margin, y, f"[Imagem não encontrada: {img_path}]")
                y -= 0.6 * cm

            continue

        # Caso sem imagem, renderizar como texto normal
        lines = []
        for raw_line in p.split('\n'):
            wrapped = textwrap.wrap(raw_line, width=100)
            if not wrapped:
                lines.append("")
            else:
                lines.extend(wrapped)

        for line in lines:
            if y < bottom_margin:
                c.showPage()
                c.setFont(*normal_font)
                y = height - 2 * cm
            c.drawString(left_margin, y, line)
            y -= 0.6 * cm

    c.save()


if __name__ == "__main__":
    gerar_cartilha_funcionario()
