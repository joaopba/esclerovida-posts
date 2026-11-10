"""Slide de foto para carrossel (acompanha uma arte de anúncio), no visual da EscleroVida.

Uso:
    python3 -I gerador/slide_foto.py slide.json foto.jpg logo_parceiro.png saida.jpg

A foto entra na largura toda e se desfaz em degradê no fundo azul; embaixo vão o nome da
cidade, uma linha de apoio, a logo do parceiro e o rodapé do Responsável Técnico.

JSON:
    {
      "formato": "feed",
      "cidade": "Caculé",
      "subtitulo": "Tratamento de varizes pelo SUS",
      "rotulo": "EM PARCERIA COM",
      "recorte": [x0, y0, x1, y1],      # área da foto a usar (0 a 1)
      "foto_y": 0,                       # onde a foto começa (px); > 0 deixa o topo azul
      "foto_altura": 1040,               # altura ocupada pela foto (px)
      "cor_destaque": [r, g, b]
    }
Use só fotos sem pacientes identificáveis (REGRAS.md).
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R  # noqa: E402
import anuncio as A  # noqa: E402

S = R.S
WHITE = (255, 255, 255)


def render(p, foto, logo2, saida):
    fmt = R.FORMATOS[p["formato"]]
    W, H = fmt["w"] * S, fmt["h"] * S
    c = R.Ctx(fmt, 1.0 if p["formato"] == "feed" else 1.17)
    z, M = c.z, c.M
    creme = tuple(p.get("cor_destaque", (255, 219, 147)))
    md = ImageDraw.Draw(Image.new("RGB", (10, 10)))

    y0 = p.get("foto_y", 0) * S
    hp = p["foto_altura"] * S
    img = A.gradiente(W, H, (y0 + hp) * 0.80).convert("RGBA")
    al_logo = R.logo_rgba()
    heart = al_logo.crop((0, 0, 338, al_logo.height))
    hh = int(H * 0.58)
    heart = heart.resize((round(heart.width * hh / heart.height), hh), Image.LANCZOS)
    mark = Image.new("RGBA", heart.size, WHITE + (0,))
    mark.putalpha(heart.point(lambda v: v * 0.07))
    img.alpha_composite(mark, (W - round(heart.width * 0.62), H - round(hh * 0.86)))

    f = A.preparar_foto(foto, p.get("recorte", [0, 0, 1, 1]), W, hp, base=0.0).convert("RGBA")
    yy = np.linspace(0, 1, hp, dtype=np.float32)
    al = np.clip((1 - yy) / p.get("fade_base", 0.34), 0, 1) ** 1.25
    if y0 > 0:
        al = al * np.clip(yy / 0.12, 0, 1)
    f.putalpha(Image.fromarray((np.repeat(al[:, None], W, 1) * 255).astype(np.uint8), "L"))
    img.alpha_composite(f, (0, y0))

    lw = fmt["logo_w"] * S
    lh = round(al_logo.height * lw / al_logo.width)
    img = R.cabecalho(img, al_logo, fmt, lw, lh)
    d = ImageDraw.Draw(img)

    # ---------- rodapé e faixa de texto ----------
    _, h_rod = R.b_rodape(c, None, md, 0, False)
    fim = fmt["fim"] * S
    y_rod = fim - h_rod
    lg2 = Image.open(logo2).convert("RGBA")
    L = z(p.get("logo2_altura", 150))
    lw2 = L * lg2.width / lg2.height
    rot = p.get("rotulo", "EM PARCERIA COM")
    f_rot = R.font("Inter-SemiBold.otf", z(17))
    rot_w = sum(md.textlength(ch, font=f_rot) + z(4) for ch in rot) - z(4)
    bloco_w, bloco_h = max(lw2, rot_w), z(17) + z(18) + L
    y_bl = y_rod - z(34) - bloco_h

    f_cid = R.font("InterDisplay-Bold.otf", z(118))
    bb = f_cid.getbbox(p["cidade"], anchor="ls")
    asc = -bb[1]
    f_sub = R.font("Inter-Medium.otf", z(32))
    tit_h = asc + z(26) + z(32)
    ty = y_bl + (bloco_h - tit_h) / 2
    d.text((M - z(118) * 0.045, ty + asc), p["cidade"], font=f_cid, fill=creme, anchor="ls")
    d.text((M, ty + asc + z(26) + z(32) * 0.78), p["subtitulo"], font=f_sub, fill=R.SOFT, anchor="ls")

    cx = W - M - bloco_w / 2
    A.espacado(d, cx, y_bl + z(17) * 0.78, rot, f_rot, R.SOFT, z(4), centro=True)
    lg = lg2.resize((round(lw2), round(L)), Image.LANCZOS)
    lx, ly = round(cx - lw2 / 2), round(y_bl + z(17) + z(18))
    sh = R.camada(img)
    som = Image.new("RGBA", lg.size, (0, 14, 30, 0))
    som.putalpha(lg.getchannel("A").point(lambda v: v * 0.5))
    sh.alpha_composite(som, (lx, ly + round(L * 0.012)))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(L * 0.02)))
    img.alpha_composite(lg, (lx, ly))
    lay = R.camada(img)
    xs = W - M - bloco_w - z(38)
    ImageDraw.Draw(lay).line([(xs, y_bl + bloco_h * 0.08), (xs, y_bl + bloco_h * 0.92)], fill=WHITE + (56,),
                             width=2 * S)
    img = Image.alpha_composite(img, lay)
    d = ImageDraw.Draw(img)
    img, _ = R.b_rodape(c, img, d, y_rod, True)
    img.convert("RGB").resize((fmt["w"], fmt["h"]), Image.LANCZOS).save(saida, "JPEG", quality=93, optimize=True)


def main():
    args = sys.argv[1:]
    if len(args) < 4:
        raise SystemExit(__doc__)
    p = json.load(open(args[0], encoding="utf-8"))
    erros = R.checar_texto(" \n ".join([p["cidade"], p["subtitulo"], p.get("rotulo", "")]), "arte")
    if erros:
        raise SystemExit("ERRO:\n" + "\n".join(erros))
    render(p, args[1], args[2], args[3])
    print(f"ok: {args[3]}")


if __name__ == "__main__":
    main()
