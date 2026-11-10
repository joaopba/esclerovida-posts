"""Arte com foto (notícias: início de atendimento, eventos) no visual da EscleroVida.

Uso:
    python3 -I gerador/foto.py arte.json foto.jpg saida.jpg [--logo2 logo_parceiro.png] [--legenda legenda.txt]

O JSON aceita os mesmos campos de render.py (formato, kicker, titulo, subtitulo, cta, nota)
e mais:
    "recorte": [x0, y0, x1, y1]   # área da foto a usar, em proporção (0 a 1); padrão: foto inteira
    "foto_altura": 0.52            # fração da altura da arte ocupada pela foto
A foto ocupa o topo e se funde ao fundo azul. O rodapé do RT sai sempre.
Use só fotos sem pacientes identificáveis (REGRAS.md).
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R  # noqa: E402

S = R.S


def compor_foto(img, foto, recorte, h_foto):
    W = img.width
    fw, fh = foto.size
    x0, y0, x1, y1 = recorte
    foto = foto.crop((round(x0 * fw), round(y0 * fh), round(x1 * fw), round(y1 * fh)))
    # preenche W x h_foto (cover)
    esc = max(W / foto.width, h_foto / foto.height)
    foto = foto.resize((round(foto.width * esc), round(foto.height * esc)), Image.LANCZOS)
    left = (foto.width - W) // 2
    foto = foto.crop((left, 0, left + W, h_foto)).convert("RGBA")
    # degradê: escurece o topo (logos) e funde a base no fundo
    yy = np.linspace(0, 1, h_foto, dtype=np.float32)
    a = np.ones(h_foto, dtype=np.float32)
    fade = 0.38
    base = yy > 1 - fade
    a[base] = np.clip((1 - yy[base]) / fade, 0, 1) ** 1.3
    mask = Image.fromarray((np.repeat(a[:, None], W, 1) * 255).astype(np.uint8), "L")
    foto.putalpha(mask)
    img.alpha_composite(foto)
    top = np.clip(1 - yy / 0.30, 0, 1) ** 1.5 * 150
    sombra = Image.new("RGBA", (W, h_foto), (4, 30, 60, 0))
    sombra.putalpha(Image.fromarray(np.repeat(top[:, None], W, 1).astype(np.uint8), "L"))
    img.alpha_composite(sombra)
    return img


def logo_parceiro(img, caminho, x_dir, y_centro, altura):
    lg = Image.open(caminho).convert("RGBA")
    esc = altura / lg.height
    lg = lg.resize((round(lg.width * esc), round(altura)), Image.LANCZOS)
    pad = round(altura * 0.16)
    box = Image.new("RGBA", (lg.width + 2 * pad, lg.height + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(box).rounded_rectangle([0, 0, box.width - 1, box.height - 1], radius=pad * 1.4,
                                          fill=(255, 255, 255, 240))
    box.alpha_composite(lg, (pad, pad))
    img.alpha_composite(box, (round(x_dir - box.width), round(y_centro - box.height / 2)))
    return img


def main():
    args = sys.argv[1:]
    if len(args) < 3:
        raise SystemExit(__doc__)
    p = json.load(open(args[0], encoding="utf-8"))
    erros = R.checar_texto(R.textos_da_pauta(p), "arte")
    if "--legenda" in args:
        leg = open(args[args.index("--legenda") + 1], encoding="utf-8").read()
        erros += R.checar_texto(leg, "legenda")
        if R.RT_LEGENDA not in leg:
            erros.append("legenda: falta a linha do Responsável Técnico (CRM-BA 29908)")
    if erros:
        raise SystemExit("ERRO:\n" + "\n".join(erros))
    logo2 = args[args.index("--logo2") + 1] if "--logo2" in args else None

    fmt = R.FORMATOS[p["formato"]]
    alpha = R.logo_rgba()
    medida = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    lw = fmt["logo_w"] * S
    lh = round(alpha.height * lw / alpha.width)
    H = fmt["h"] * S
    h_foto = round(H * p.get("foto_altura", 0.52))
    blocos = []
    if p.get("kicker"):
        blocos.append(("chip", p["kicker"].upper(), 26))
    blocos.append(("titulo", p["titulo"], 22 if p.get("subtitulo") else 30))
    if p.get("subtitulo"):
        blocos.append(("sub", p["subtitulo"], 0))

    sc = fmt["base"] * 1.05
    while True:
        c = R.Ctx(fmt, sc)
        _, h_cont = R.desenhar_conteudo(c, None, medida, 0, blocos, False)
        _, h_cta = R.b_cta(c, None, medida, 0, p.get("cta"), p.get("nota"), False)
        _, h_rod = R.b_rodape(c, None, medida, 0, False)
        fim = fmt["fim"] * S
        topo = h_foto - c.z(150)
        livre = fim - topo - (h_cont + c.z(40) + h_cta + c.z(30) + h_rod)
        if livre >= 0:
            break
        sc -= 0.02
        if sc < fmt["base"] * 0.72:
            raise SystemExit("ERRO: o texto não cabe na arte. Encurte o título ou o subtítulo.")

    img = R.fundo(c.W, c.H, alpha)
    foto = Image.open(args[1]).convert("RGB")
    img = compor_foto(img, foto, p.get("recorte", [0, 0, 1, 1]), h_foto)
    img = R.cabecalho(img, alpha, fmt, lw, lh) if not logo2 else img
    if logo2:
        logo = Image.new("RGBA", (alpha.width, alpha.height), R.WHITE + (0,))
        logo.putalpha(alpha)
        logo = logo.resize((lw, lh), Image.LANCZOS)
        img.alpha_composite(logo, (c.M, fmt["logo_y"] * S))
        img = logo_parceiro(img, logo2, c.W - c.M, fmt["logo_y"] * S + lh / 2, lh * 1.05)

    y_rod = fim - h_rod
    y_cta = y_rod - c.z(30) - h_cta
    y_cont = topo + max(0, (y_cta - c.z(40) - topo - h_cont) * 0.5)
    d = ImageDraw.Draw(img)
    img, _ = R.desenhar_conteudo(c, img, d, y_cont, blocos, True)
    d = ImageDraw.Draw(img)
    img, _ = R.b_cta(c, img, d, y_cta, p.get("cta"), p.get("nota"), True)
    d = ImageDraw.Draw(img)
    img, _ = R.b_rodape(c, img, d, y_rod, True)
    out = img.convert("RGB").resize((fmt["w"], fmt["h"]), Image.LANCZOS)
    out.save(args[2], "JPEG", quality=92, optimize=True)
    print(f"ok: {args[2]} (escala {sc:.2f})")


if __name__ == "__main__":
    main()
