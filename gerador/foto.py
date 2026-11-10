"""Arte com foto (notícias: início de atendimento, eventos) no visual da EscleroVida.

Uso:
    python3 -I gerador/foto.py arte.json foto.jpg saida.jpg [--logo2 logo_parceiro.png] [--legenda legenda.txt]

O JSON aceita os mesmos campos de render.py (formato, kicker, titulo, subtitulo, cta, nota)
e mais:
    "recorte": [x0, y0, x1, y1]   # área da foto a usar, em proporção (0 a 1); padrão: foto inteira
    "foto_altura": 0.52            # fração da altura da arte ocupada pela foto
    "cor_destaque": [r, g, b]      # opcional: cor do selo, da linha de destaque do título
    "cor_botao": [r, g, b]         # opcional: cor do círculo da seta no botão (ex.: cores do município)
    "logo2_altura": 170            # altura do selo do parceiro (px), com --logo2
    "titulo_destaque_escala": 1.5  # opcional: aumenta a linha do título com * (ex.: nome da cidade)
    "logo2_moldura": false         # opcional: PNG transparente direto na arte, sem quadrado
    "logo2_rotulo": "EM PARCERIA COM"  # opcional: texto pequeno acima da logo do parceiro
    "logo2_pos": "topo" | "baixo"  # "baixo": logo grande no canto inferior direito, ao lado do botão
A foto ocupa o topo e se funde ao fundo azul. O rodapé do RT sai sempre.
Use só fotos sem pacientes identificáveis (REGRAS.md).
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

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


def logo_parceiro(img, caminho, x_dir, y_topo, altura, moldura=True):
    """Logo do parceiro. moldura=True: selo de cantos arredondados (cores originais).
    moldura=False: PNG transparente aplicado direto na arte, com sombra suave."""
    lg = Image.open(caminho).convert("RGBA")
    esc = altura / lg.height
    lg = lg.resize((round(lg.width * esc), round(altura)), Image.LANCZOS)
    if not moldura:
        x0, y0 = round(x_dir - lg.width), round(y_topo)
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sombra = Image.new("RGBA", lg.size, (0, 14, 30, 0))
        sombra.putalpha(lg.getchannel("A").point(lambda v: v * 0.55))
        sh.alpha_composite(sombra, (x0, y0 + round(altura * 0.012)))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(altura * 0.02)))
        img.alpha_composite(lg, (x0, y0))
        return img
    r = round(altura * 0.06)
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    x0, y0 = round(x_dir - lg.width), round(y_topo)
    ImageDraw.Draw(sh).rounded_rectangle([x0, y0 + r * 0.3, x0 + lg.width, y0 + lg.height + r * 0.3],
                                         radius=r, fill=(0, 18, 38, 110))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(r * 0.6)))
    m = Image.new("L", lg.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, lg.width - 1, lg.height - 1], radius=r, fill=255)
    lg.putalpha(m)
    img.alpha_composite(lg, (x0, y0))
    return img


def titulo_destaque(escala):
    """Substitui o título padrão: a linha com * sai maior (ex.: o nome da cidade)."""
    def b_titulo(c, img, d, y, linhas, desenhar):
        size = c.z(104)
        limpas = [l.strip("*") for l in linhas]
        while True:
            f = R.font("InterDisplay-Bold.otf", size)
            fd = R.font("InterDisplay-Bold.otf", size * escala)
            larg = max(d.textlength(l.strip("*"), font=fd if l.startswith("*") else f) for l in linhas)
            if larg <= c.CW or size <= c.z(56):
                break
            size -= c.z(2)
        for l in linhas:
            dest = l.startswith("*")
            fl, sz = (fd, size * escala) if dest else (f, size)
            if desenhar:
                d.text((c.M - sz * 0.04, y), l.strip("*"), font=fl, fill=R.AQUA if dest else R.WHITE)
            y += sz * 1.06
        y += size * 0.20
        if desenhar:
            d.rounded_rectangle([c.M, y, c.M + c.z(92), y + c.z(8)], radius=c.z(4), fill=R.AQUA)
            d.rounded_rectangle([c.M + c.z(104), y, c.M + c.z(124), y + c.z(8)], radius=c.z(4), fill=R.CORAL)
        return img, y + c.z(8)
    return b_titulo


def cta_esquerda(c, img, y, largura, texto, nota, desenhar):
    """Botão + nota alinhados à esquerda, dentro de `largura`. Retorna (img, altura)."""
    d = ImageDraw.Draw(img) if desenhar else ImageDraw.Draw(Image.new("RGB", (10, 10)))
    bh = c.z(104)
    r = c.z(35)
    size = c.z(36)
    while True:
        f = R.font("Inter-Bold.otf", size)
        tw = d.textlength(texto, font=f)
        wbox = c.z(44) + tw + c.z(22) + 2 * r + c.z(14)
        if wbox <= largura or size <= c.z(24):
            break
        size -= c.z(1)
    x0 = c.M
    if desenhar:
        sh = R.camada(img)
        ImageDraw.Draw(sh).rounded_rectangle([x0, y + c.z(12), x0 + wbox, y + bh + c.z(12)], radius=bh / 2,
                                             fill=(0, 20, 40, 110))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(c.z(16))))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([x0, y, x0 + wbox, y + bh], radius=bh / 2, fill=R.WHITE)
        d.text((x0 + c.z(44), y + bh / 2), texto, font=f, fill=R.DEEP, anchor="lm")
        cx, cy = x0 + wbox - c.z(14) - r, y + bh / 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=R.BG_BOT_RGB)
        k = r / 38
        w = max(2, round(5 * k))
        d.line([(cx - 13 * k, cy), (cx + 12 * k, cy)], fill=R.WHITE, width=w)
        d.line([(cx + 2 * k, cy - 11 * k), (cx + 13 * k, cy), (cx + 2 * k, cy + 11 * k)],
               fill=R.WHITE, width=w, joint="curve")
    h = bh
    if nota:
        h += c.z(22)
        img, yy = R.b_paragrafo(c, img, d, y + h, nota, desenhar, "Inter-Medium.otf", 28, R.SOFT, 1.38,
                                largura=largura)
        h = yy - y
    return img, h


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
    if p.get("cor_destaque"):
        R.AQUA = tuple(p["cor_destaque"])
        R.b_chip.__defaults__ = (R.AQUA, None, True)
    if p.get("titulo_destaque_escala"):
        R.b_titulo = titulo_destaque(p["titulo_destaque_escala"])
    if p.get("cor_botao"):
        R.BG_BOT_RGB = tuple(p["cor_botao"])
        R.CORAL = tuple(p["cor_botao"])

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
        baixo = logo2 and p.get("logo2_pos") == "baixo"
        L = p.get("logo2_altura", 170) * S
        if baixo:
            _lg = Image.open(logo2)
            larg_cta = c.CW - L * _lg.width / _lg.height - c.z(80 if not p.get("logo2_moldura", True) else 40)
            _, h_esq = cta_esquerda(c, Image.new("RGBA", (10, 10)), 0, larg_cta, p.get("cta"), p.get("nota"), False)
            h_cta = max(L, h_esq)
        else:
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
    img = R.cabecalho(img, alpha, fmt, lw, lh) if (not logo2 or baixo) else img
    if logo2 and not baixo:
        logo = Image.new("RGBA", (alpha.width, alpha.height), R.WHITE + (0,))
        logo.putalpha(alpha)
        logo = logo.resize((lw, lh), Image.LANCZOS)
        img.alpha_composite(logo, (c.M, fmt["logo_y"] * S))
        alt = p.get("logo2_altura", 170) * S
        img = logo_parceiro(img, logo2, c.W - c.M, fmt["logo_y"] * S + lh / 2 - alt / 2, alt)

    y_rod = fim - h_rod
    y_cta = y_rod - c.z(30) - h_cta
    y_cont = topo + max(0, (y_cta - c.z(40) - topo - h_cont) * 0.5)
    d = ImageDraw.Draw(img)
    img, _ = R.desenhar_conteudo(c, img, d, y_cont, blocos, True)
    d = ImageDraw.Draw(img)
    if baixo:
        img, _ = cta_esquerda(c, img, y_cta + (h_cta - h_esq) / 2, larg_cta, p.get("cta"), p.get("nota"), True)
        moldura = p.get("logo2_moldura", True)
        if not moldura:
            # filete vertical separando o botão da logo
            lay = R.camada(img)
            xs = c.W - c.M - L * Image.open(logo2).width / Image.open(logo2).height - c.z(34)
            ImageDraw.Draw(lay).line([(xs, y_cta + L * 0.12), (xs, y_cta + L * 0.88)],
                                     fill=R.WHITE + (60,), width=2 * S)
            img = Image.alpha_composite(img, lay)
        y_logo, L_logo = y_cta + (h_cta - L) / 2, L
        rot = p.get("logo2_rotulo")
        if rot:
            # rótulo pequeno, espaçado, centralizado acima da logo (ex.: "EM PARCERIA COM")
            fr = R.font("Inter-SemiBold.otf", c.z(22))
            sp = c.z(4)
            dr = ImageDraw.Draw(img)
            tw = sum(dr.textlength(ch, font=fr) + sp for ch in rot) - sp
            h_rot = c.z(22) * 1.2 + c.z(18)
            L_logo = L - h_rot
            _lg = Image.open(logo2)
            lw2 = L_logo * _lg.width / _lg.height
            cx = c.W - c.M - lw2 / 2
            x = cx - tw / 2
            for ch in rot:
                dr.text((x, y_logo), ch, font=fr, fill=R.SOFT)
                x += dr.textlength(ch, font=fr) + sp
            y_logo += h_rot
        img = logo_parceiro(img, logo2, c.W - c.M, y_logo, L_logo, moldura)
    else:
        img, _ = R.b_cta(c, img, d, y_cta, p.get("cta"), p.get("nota"), True)
    d = ImageDraw.Draw(img)
    img, _ = R.b_rodape(c, img, d, y_rod, True)
    out = img.convert("RGB").resize((fmt["w"], fmt["h"]), Image.LANCZOS)
    out.save(args[2], "JPEG", quality=92, optimize=True)
    print(f"ok: {args[2]} (escala {sc:.2f})")


if __name__ == "__main__":
    main()
