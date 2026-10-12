#!/usr/bin/env python3
"""Gera as imagens padrão por editoria (sem fotos de terceiros): static/img/editoria/<slug>.webp (+ -480.webp)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
OUT = Path(__file__).parent / "static" / "img" / "editoria"; OUT.mkdir(parents=True, exist_ok=True)
FONT = "/usr/share/fonts/truetype/sand-box/google/Open Sans/OpenSans-VariableFont_wdth,wght.ttf"
D, A, A2, L = (46, 51, 61), (240, 78, 35), (201, 61, 23), (232, 234, 236)

def font(size, w="Bold"):
    try:
        f = ImageFont.truetype(FONT, size); f.set_variation_by_name(w); return f
    except Exception: return ImageFont.load_default(size)

def icon(d, slug, x, y, s):
    lw = max(6, s // 18)
    if slug == "transporte":  # caminhão
        d.rounded_rectangle([x, y + s*.2, x + s*.62, y + s*.7], 10, outline=A, width=lw)
        d.polygon([(x + s*.62, y + s*.35), (x + s*.85, y + s*.35), (x + s, y + s*.52), (x + s, y + s*.7), (x + s*.62, y + s*.7)], outline=A, width=lw)
        for cx in (x + s*.2, x + s*.8): d.ellipse([cx - s*.1, y + s*.62, cx + s*.1, y + s*.82], fill=D, outline=L, width=lw)
    elif slug == "supply-chain":  # rede de nós
        pts = [(x + s*.1, y + s*.5), (x + s*.45, y + s*.15), (x + s*.45, y + s*.85), (x + s*.9, y + s*.5)]
        for a, b in [(0, 1), (0, 2), (1, 3), (2, 3), (1, 2)]: d.line([pts[a], pts[b]], fill=L, width=lw // 2)
        for i, (px, py) in enumerate(pts): d.ellipse([px - s*.09, py - s*.09, px + s*.09, py + s*.09], fill=A if i % 3 == 0 else D, outline=A, width=lw)
    elif slug == "armazenagem":  # estante com caixas
        for i in range(3):
            yy = y + s*.3 + i * s*.25; d.line([x, yy, x + s, yy], fill=L, width=lw)
            for j in range(3 - (i % 2)): d.rectangle([x + s*.08 + j * s*.3, yy - s*.18, x + s*.3 + j * s*.3, yy - lw], fill=A if (i + j) % 2 == 0 else A2)
        d.line([x, y + s*.05, x, y + s*.8], fill=L, width=lw); d.line([x + s, y + s*.05, x + s, y + s*.8], fill=L, width=lw)
    elif slug == "comercio-exterior":  # navio com contêineres
        for j in range(4): d.rectangle([x + s*.15 + j * s*.18, y + s*.3, x + s*.3 + j * s*.18, y + s*.5], fill=A if j % 2 else A2)
        d.polygon([(x, y + s*.52), (x + s, y + s*.52), (x + s*.85, y + s*.75), (x + s*.12, y + s*.75)], fill=L)
        for k in range(3): d.arc([x + k * s*.33, y + s*.8, x + (k + 1) * s*.33, y + s*.95], 200, 340, fill=A, width=lw // 2)
    elif slug == "tecnologia":  # chip
        d.rounded_rectangle([x + s*.2, y + s*.2, x + s*.8, y + s*.8], 14, outline=A, width=lw)
        d.rectangle([x + s*.38, y + s*.38, x + s*.62, y + s*.62], fill=A)
        for k in range(4):
            o = s*.28 + k * s*.15
            for seg in ([x + o, y, x + o, y + s*.2], [x + o, y + s*.8, x + o, y + s], [x, y + o, x + s*.2, y + o], [x + s*.8, y + o, x + s, y + o]): d.line(seg, fill=L, width=lw // 2)
    else:  # mercado: gráfico
        d.line([x, y + s, x + s, y + s], fill=L, width=lw); d.line([x, y, x, y + s], fill=L, width=lw)
        for i, h in enumerate([.3, .5, .42, .7, .9]): d.rectangle([x + s*.08 + i * s*.18, y + s*(1 - h), x + s*.2 + i * s*.18, y + s - lw], fill=A if i == 4 else A2)

def make(slug, nome):
    W, H = 1200, 630; im = Image.new("RGB", (W, H), D); d = ImageDraw.Draw(im)
    for i in range(-H, W, 60): d.line([(i, H), (i + H, 0)], fill=(52, 58, 69), width=18)  # textura diagonal
    d.rectangle([0, H - 16, W, H], fill=A); d.rectangle([70, 90, 82, 250], fill=A)
    d.text((105, 90), "MODAL NEWS", font=font(30, "Bold"), fill=A)
    d.text((105, 135), nome, font=font(78, "ExtraBold"), fill=(255, 255, 255))
    d.text((105, 250), "Notícias de logística", font=font(32, "Regular"), fill=L)
    icon(d, slug, 760, 170, 330)
    big = OUT / f"{slug}.webp"; im.save(big, "WEBP", quality=80)
    im.resize((480, 252), Image.LANCZOS).save(OUT / f"{slug}-480.webp", "WEBP", quality=78)
    print(big)

if __name__ == "__main__":
    import yaml
    for e in yaml.safe_load((Path(__file__).parent / "config.yaml").read_text(encoding="utf-8"))["editorias"]: make(e["slug"], e["nome"])
