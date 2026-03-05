import os
from PIL import Image, ImageDraw, ImageFont


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def create_placeholder(path, text, size=(900, 540), bgcolor=(240, 240, 240)):
    img = Image.new('RGB', size, color=bgcolor)
    draw = ImageDraw.Draw(img)

    # borda
    draw.rectangle([5, 5, size[0]-6, size[1]-6], outline=(180, 180, 180), width=3)

    # Fonte padrão
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except Exception:
        font = ImageFont.load_default()

    # Medir texto de forma compatível com várias versões do Pillow
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
    except Exception:
        w, h = font.getsize(text)

    draw.text(((size[0]-w)/2, (size[1]-h)/2), text, fill=(40, 40, 40), font=font)

    img.save(path)


def main():
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'screenshots')
    ensure_dir(base)

    items = [
        ("registrar_ponto.png", "Registrar Ponto"),
        ("meus_registros.png", "Meus Registros"),
        ("notificacoes.png", "Notificações"),
    ]

    # Placeholders do gestor
    gestor_items = [
        ("painel_gestor.png", "Painel do Gestor"),
        ("aprovar_correcoes.png", "Aprovar Correções"),
        ("aprovar_atestados.png", "Aprovar Atestados"),
    ]

    for name, label in gestor_items:
        path = os.path.join(base, name)
        create_placeholder(path, label)
        print('Gerado:', path)

    for name, label in items:
        path = os.path.join(base, name)
        create_placeholder(path, label)
        print('Gerado:', path)


if __name__ == '__main__':
    main()
