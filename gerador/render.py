"""Gera as artes da EscleroVida no visual padrão (azul-marinho/teal, logo branco).

Uso:
    python3 gerador/render.py pauta.json saida.jpg [--legenda legenda.txt]

O JSON descreve a arte:
    {
      "formato": "feed" | "story",              # feed = 1080x1350, story = 1080x1920
      "layout": "lista" | "passos" | "cidades" | "texto" | "mito_verdade",
      "kicker": "FIQUE ATENTO",                  # selo pequeno no topo (opcional)
      "titulo": ["Linha 1", "Linha 2", "*Linha em destaque*"],   # * = cor de destaque
      "subtitulo": "Frase curta abaixo do título",               # opcional
      "itens": ["...", "..."],                   # lista / passos / cidades
      "lead": "Frase em negrito",                # texto (opcional)
      "texto": "Parágrafo curto",                # texto
      "mito": "...", "verdade": "...",           # mito_verdade
      "destaque": "Frase de efeito",             # opcional
      "cta": "Procure o posto de saúde da sua cidade",          # opcional
      "nota": "O agendamento é feito pela Secretaria Municipal de Saúde."  # opcional
    }

O rodapé com o Responsável Técnico (Resolução CFM 2.336/2023) é sempre incluído.
O script recusa textos com termos proibidos (ver REGRAS.md) e textos que não cabem.
"""
import json
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
FONTES = os.path.join(AQUI, "fontes")
S = 2  # renderiza em 2x e reduz, para bordas suaves

WHITE = (255, 255, 255)
AQUA = (126, 214, 226)
CORAL = (255, 160, 146)
DEEP = (6, 44, 84)
SOFT = (214, 236, 242)
FOOT = (196, 222, 232)
BG_TOP = np.array([7, 36, 70], dtype=np.float32)
BG_BOT = np.array([4, 96, 116], dtype=np.float32)

RT = ["Responsável Técnico: Dr. Vinicius Guerra",
      "Cirurgião Vascular · CRM-BA 29908 · RQE 23546"]
RT_LEGENDA = "CRM-BA 29908"

FORMATOS = {
    "feed": dict(w=1080, h=1350, base=0.80, logo_w=270, logo_y=64, fim=1300),
    "story": dict(w=1080, h=1920, base=1.00, logo_w=330, logo_y=210, fim=1695),
}

# Termos que nunca podem aparecer (REGRAS.md). "não estético" é permitido.
PROIBIDOS = [
    (r"vasinh", "vasinhos"),
    (r"telangiect", "telangiectasias"),
    (r"(?<!não )(?<!nao )est[eé]tic", "estético/estética (use só 'não estético')"),
    (r"antes e depois", "antes e depois"),
    (r"garant", "garantia/garantido"),
    (r"\bcura\b|\bcurar|\bcurad", "cura"),
    (r"sem dor|indolor", "sem dor/indolor"),
    (r"100 ?%", "100%"),
    (r"milagr", "milagre"),
    (r"definitiv", "definitivo"),
    (r"R\$", "preço"),
]


def checar_texto(texto, origem):
    erros = []
    for padrao, nome in PROIBIDOS:
        if re.search(padrao, texto, flags=re.IGNORECASE):
            erros.append(f"{origem}: termo proibido -> {nome}")
    return erros


def textos_da_pauta(p):
    out = []
    for k in ("kicker", "subtitulo", "lead", "texto", "mito", "verdade", "destaque", "cta", "nota"):
        if p.get(k):
            out.append(p[k])
    out += [t.strip("*") for t in p.get("titulo", [])]
    out += p.get("itens", [])
    return " \n ".join(out)


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTES, name), max(8, round(size)))


def wrap(d, text, f, max_w):
    lines = []
    for par in str(text).split("\n"):
        cur = ""
        for w in par.split():
            test = (cur + " " + w).strip()
            if d.textlength(test, font=f) <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


# ---------- fundo, logo e elementos ----------

HANDLE = "@esclero_vida"


def logo_rgba():
    im = np.asarray(Image.open(os.path.join(AQUI, "logo.jpeg")).convert("RGB")).astype(np.float32)
    bg = np.array([234.0, 233.0, 231.0])
    a = np.max((bg - im) / bg, axis=2)
    a = np.clip((a - 0.12) / 0.80, 0, 1)
    return Image.fromarray((a * 255).astype(np.uint8), "L")


def fundo(W, H, alpha_logo):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    t = (yy / H * 0.8 + xx / W * 0.2)[..., None]
    img = BG_TOP * (1 - t) + BG_BOT * t
    ar = H / W
    for cx, cy, sig, amp in [(1.0, 0.05, 0.42, 42), (0.0, 0.95, 0.5, 34)]:
        d2 = (xx / W - cx) ** 2 + ((yy / H - cy) * ar) ** 2
        img = img + np.exp(-d2 / (2 * sig ** 2))[..., None] * np.array([40, 120, 130]) * (amp / 100)
    img = img + np.random.default_rng(7).normal(0, 1.6, (H, W, 1))
    base = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

    # linhas de fluxo (circulação) no canto superior direito
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    for k in range(5):
        pts = []
        for s in range(0, 101):
            u = s / 100
            x = W * (0.42 + 0.62 * u)
            y = H * (0.02 + 0.035 * k) + np.sin(u * 3.2 + k * 0.55) * H * 0.028 + u * H * 0.05
            pts.append((x, y))
        ld.line(pts, fill=AQUA + (26 - 3 * k,), width=max(2, W // 540), joint="curve")
    base.alpha_composite(lay)

    # coração da marca como marca d'água, sangrando no canto inferior direito
    heart = alpha_logo.crop((0, 0, 338, alpha_logo.height))
    hh = int(H * 0.58)
    heart = heart.resize((round(heart.width * hh / heart.height), hh), Image.LANCZOS)
    mark = Image.new("RGBA", heart.size, WHITE + (0,))
    mark.putalpha(heart.point(lambda v: v * 0.06))
    base.alpha_composite(mark, (W - round(heart.width * 0.62), H - round(hh * 0.86)))
    return base


def camada(img):
    return Image.new("RGBA", img.size, (0, 0, 0, 0))


def vidro(img, box, radius, tom=WHITE, fill_a=22, line_a=44, sombra=True):
    if sombra:
        sh = camada(img)
        x0, y0, x1, y1 = box
        o = radius * 0.25
        ImageDraw.Draw(sh).rounded_rectangle([x0, y0 + o, x1, y1 + o], radius=radius, fill=(0, 18, 38, 60))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(radius * 0.45)))
    lay = camada(img)
    ImageDraw.Draw(lay).rounded_rectangle(box, radius=radius, fill=tom + (fill_a,),
                                          outline=WHITE + (line_a,), width=2 * S)
    return Image.alpha_composite(img, lay)


class Ctx:
    def __init__(self, fmt, sc):
        self.W, self.H = fmt["w"] * S, fmt["h"] * S
        self.sc = sc * S
        self.M = 84 * S
        self.CW = self.W - 2 * self.M

    def z(self, v):
        return v * self.sc


# Cada bloco: bloco(ctx, img, d, y, desenhar) -> (img, y_final)

def b_chip(c, img, d, y, texto, desenhar, cor=AQUA, x=None, ponto=True):
    f = font("Inter-SemiBold.otf", c.z(26))
    sp = c.z(4.5)
    tw = sum(d.textlength(ch, font=f) + sp for ch in texto) - sp
    h = c.z(54)
    padl = c.z(48) if ponto else c.z(26)
    x = c.M if x is None else x
    if desenhar:
        lay = camada(img)
        ld = ImageDraw.Draw(lay)
        ld.rounded_rectangle([x, y, x + padl + tw + c.z(26), y + h], radius=h / 2,
                             fill=cor + (30,), outline=cor + (110,), width=2 * S)
        img = Image.alpha_composite(img, lay)
        d = ImageDraw.Draw(img)
        if ponto:
            r = c.z(6)
            cx0 = x + c.z(26)
            d.ellipse([cx0 - r, y + h / 2 - r, cx0 + r, y + h / 2 + r], fill=cor)
        cx = x + padl
        for ch in texto:
            d.text((cx, y + h / 2), ch, font=f, fill=cor, anchor="lm")
            cx += d.textlength(ch, font=f) + sp
    return img, y + h


def b_titulo(c, img, d, y, linhas, desenhar):
    size = c.z(104)
    limpas = [l.strip("*") for l in linhas]
    while True:
        f = font("InterDisplay-Bold.otf", size)
        if max(d.textlength(l, font=f) for l in limpas) <= c.CW or size <= c.z(56):
            break
        size -= c.z(2)
    lh = size * 1.06
    for l in linhas:
        if desenhar:
            d.text((c.M - size * 0.04, y), l.strip("*"), font=f, fill=AQUA if l.startswith("*") else WHITE)
        y += lh
    # barra de destaque abaixo do título (abaixo das descendentes)
    y += size * 0.20
    if desenhar:
        d.rounded_rectangle([c.M, y, c.M + c.z(92), y + c.z(8)], radius=c.z(4), fill=AQUA)
        d.rounded_rectangle([c.M + c.z(104), y, c.M + c.z(124), y + c.z(8)], radius=c.z(4), fill=CORAL)
    return img, y + c.z(8)


def b_paragrafo(c, img, d, y, texto, desenhar, fname="Inter-Medium.otf", size=38, cor=SOFT,
                lh=1.36, centro=False, largura=None, x=None):
    f = font(fname, c.z(size))
    largura = largura or c.CW
    x = c.M if x is None else x
    for l in wrap(d, texto, f, largura):
        if desenhar:
            if centro:
                d.text((c.W / 2, y), l, font=f, fill=cor, anchor="mt")
            else:
                d.text((x, y), l, font=f, fill=cor)
        y += c.z(size) * lh
    return img, y


def icone_check(d, cx, cy, r, cor=AQUA, traco=DEEP):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=cor)
    k = r / 21
    d.line([(cx - 9 * k, cy + 1 * k), (cx - 3 * k, cy + 7 * k), (cx + 9 * k, cy - 7 * k)],
           fill=traco, width=max(2, round(5 * k)), joint="curve")


def icone_x(d, cx, cy, r, cor=CORAL, traco=DEEP):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=cor)
    k = r / 21
    w = max(2, round(5 * k))
    d.line([(cx - 7 * k, cy - 7 * k), (cx + 7 * k, cy + 7 * k)], fill=traco, width=w)
    d.line([(cx - 7 * k, cy + 7 * k), (cx + 7 * k, cy - 7 * k)], fill=traco, width=w)


def icone_pin(d, cx, cy, r):
    k = 2.1
    py, px = r / k, r * (1 - (1 / k) ** 2) ** 0.5
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=AQUA)
    d.polygon([(cx - px, cy + py), (cx + px, cy + py), (cx, cy + k * r)], fill=AQUA)
    ri = r * 0.42
    d.ellipse([cx - ri, cy - ri, cx + ri, cy + ri], fill=DEEP)


def icone_num(d, cx, cy, r, n):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=AQUA)
    d.text((cx, cy), str(n), font=font("Inter-Bold.otf", r * 1.1), fill=DEEP, anchor="mm")


def b_lista(c, img, d, y, itens, tipo, desenhar):
    gap = c.z(14)
    ix = c.M + c.z(58)          # centro do ícone
    tx = c.M + c.z(112)         # início do texto
    tw = c.W - c.M - c.z(36) - tx
    cid = tipo == "cidades"
    f = font("Inter-SemiBold.otf" if cid else "Inter-Medium.otf", c.z(41 if cid else 38))
    lh = c.z(50)
    rows = []
    for it in itens:
        ls = wrap(d, it, f, tw)
        rows.append((ls, max(c.z(92), len(ls) * lh + c.z(38))))
    total = sum(h for _, h in rows) + gap * (len(rows) - 1)
    if desenhar:
        ry = y
        boxes = []
        for ls, h in rows:
            img = vidro(img, [c.M, ry, c.W - c.M, ry + h], c.z(30), fill_a=20, line_a=38)
            boxes.append((ry, h, ls))
            ry += h + gap
        d = ImageDraw.Draw(img)
        if tipo == "passos" and len(boxes) > 1:
            lay = camada(img)
            ld = ImageDraw.Draw(lay)
            for (y0, h0, _), (y1, h1, _) in zip(boxes, boxes[1:]):
                a, b = y0 + h0 / 2 + c.z(26), y1 + h1 / 2 - c.z(26)
                ld.line([(ix, a), (ix, b)], fill=AQUA + (150,), width=round(c.z(4)))
            img = Image.alpha_composite(img, lay)
            d = ImageDraw.Draw(img)
        for i, (ry, h, ls) in enumerate(boxes):
            top_text = ry + (h - len(ls) * lh) / 2
            first_mid = top_text + lh / 2
            if cid:
                icone_pin(d, ix, first_mid - c.z(9), c.z(16))
            elif tipo == "passos":
                icone_num(d, ix, first_mid, c.z(24), i + 1)
            else:
                icone_check(d, ix, first_mid, c.z(22))
            for j, l in enumerate(ls):
                d.text((tx, top_text + lh * j + lh / 2), l, font=f, fill=WHITE, anchor="lm")
    return img, y + total


def b_texto(c, img, d, y, lead, texto, desenhar):
    pad = c.z(48)
    bar = c.z(8)
    xin = c.M + pad + c.z(30)
    inner = c.W - c.M - pad - xin
    _, h1 = b_paragrafo(c, img, d, 0, lead, False, "Inter-Bold.otf", 42, WHITE, 1.28, largura=inner) if lead else (None, 0)
    _, h2 = b_paragrafo(c, img, d, 0, texto, False, "Inter-Regular.otf", 37, SOFT, 1.45, largura=inner)
    gap = c.z(20) if lead else 0
    total = pad * 2 + h1 + gap + h2
    if desenhar:
        img = vidro(img, [c.M, y, c.W - c.M, y + total], c.z(36))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([c.M + pad - bar / 2, y + pad, c.M + pad + bar / 2, y + total - pad],
                            radius=bar / 2, fill=AQUA)
        yy = y + pad - c.z(4)
        if lead:
            _, yy = b_paragrafo(c, img, d, yy, lead, True, "Inter-Bold.otf", 42, WHITE, 1.28, largura=inner, x=xin)
            yy += gap
        b_paragrafo(c, img, d, yy, texto, True, "Inter-Regular.otf", 37, SOFT, 1.45, largura=inner, x=xin)
    return img, y + total


def b_mito_verdade(c, img, d, y, mito, verdade, desenhar):
    pad = c.z(40)
    inner = c.CW - 2 * pad
    gapc = c.z(20)
    for rotulo, cor, texto, fname, icone in (("MITO", CORAL, mito, "Inter-Medium.otf", icone_x),
                                             ("VERDADE", AQUA, verdade, "Inter-SemiBold.otf", icone_check)):
        _, ht = b_paragrafo(c, img, d, 0, texto, False, fname, 38, WHITE, 1.38, largura=inner)
        hl = c.z(52)
        total = pad * 2 + hl + c.z(20) + ht
        if desenhar:
            img = vidro(img, [c.M, y, c.W - c.M, y + total], c.z(34), tom=cor, fill_a=26, line_a=40)
            lay = camada(img)
            ImageDraw.Draw(lay).rounded_rectangle([c.M, y + c.z(28), c.M + c.z(8), y + total - c.z(28)],
                                                  radius=c.z(4), fill=cor + (255,))
            img = Image.alpha_composite(img, lay)
            d = ImageDraw.Draw(img)
            r = c.z(22)
            icone(d, c.M + pad + r, y + pad + hl / 2, r, cor, DEEP)
            fl = font("Inter-Bold.otf", c.z(30))
            cx = c.M + pad + 2 * r + c.z(18)
            for ch in rotulo:
                d.text((cx, y + pad + hl / 2), ch, font=fl, fill=cor, anchor="lm")
                cx += d.textlength(ch, font=fl) + c.z(4)
            b_paragrafo(c, img, d, y + pad + hl + c.z(20), texto, True, fname, 38, WHITE, 1.38,
                        largura=inner, x=c.M + pad)
        y += total + gapc
    return img, y - gapc


def b_destaque(c, img, d, y, texto, desenhar):
    xin = c.M + c.z(30)
    _, h = b_paragrafo(c, img, d, 0, texto, False, "Inter-Bold.otf", 40, WHITE, 1.3, largura=c.CW - c.z(30))
    if desenhar:
        d.rounded_rectangle([c.M, y + c.z(4), c.M + c.z(8), y + h - c.z(8)], radius=c.z(4), fill=CORAL)
        b_paragrafo(c, img, d, y, texto, True, "Inter-Bold.otf", 40, WHITE, 1.3, largura=c.CW - c.z(30), x=xin)
    return img, y + h - c.z(10)


def b_cta(c, img, d, y, texto, nota, desenhar):
    if texto:
        bh = c.z(112)
        r = c.z(38)
        size = c.z(38)
        while True:
            f = font("Inter-Bold.otf", size)
            tw = d.textlength(texto, font=f)
            wbox = c.z(52) + tw + c.z(24) + 2 * r + c.z(14)
            if wbox <= c.CW or size <= c.z(26):
                break
            size -= c.z(1)
        if desenhar:
            x0 = (c.W - wbox) / 2
            sh = camada(img)
            ImageDraw.Draw(sh).rounded_rectangle([x0, y + c.z(14), x0 + wbox, y + bh + c.z(14)], radius=bh / 2,
                                                 fill=(0, 20, 40, 110))
            img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(c.z(18))))
            d = ImageDraw.Draw(img)
            d.rounded_rectangle([x0, y, x0 + wbox, y + bh], radius=bh / 2, fill=WHITE)
            d.text((x0 + c.z(52), y + bh / 2), texto, font=f, fill=DEEP, anchor="lm")
            cx, cy = x0 + wbox - c.z(14) - r, y + bh / 2
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BG_BOT_RGB)
            k = r / 38
            w = max(2, round(5 * k))
            d.line([(cx - 13 * k, cy), (cx + 12 * k, cy)], fill=WHITE, width=w)
            d.line([(cx + 2 * k, cy - 11 * k), (cx + 13 * k, cy), (cx + 2 * k, cy + 11 * k)],
                   fill=WHITE, width=w, joint="curve")
        y += bh + c.z(24)
    if nota:
        d = ImageDraw.Draw(img) if desenhar else d
        img, y = b_paragrafo(c, img, d, y, nota, desenhar, "Inter-Medium.otf", 28, SOFT, 1.38, centro=True)
    return img, y


def b_rodape(c, img, d, y, desenhar):
    if desenhar:
        lay = camada(img)
        ImageDraw.Draw(lay).line([(c.W / 2 - c.z(70), y), (c.W / 2 + c.z(70), y)],
                                 fill=WHITE + (70,), width=2 * S)
        img = Image.alpha_composite(img, lay)
        d = ImageDraw.Draw(img)
    y += c.z(22)
    for l, fname in zip(RT, ("Inter-SemiBold.otf", "Inter-Regular.otf")):
        if desenhar:
            d.text((c.W / 2, y), l, font=font(fname, c.z(25)), fill=FOOT, anchor="mt")
        y += c.z(35)
    return img, y


BG_BOT_RGB = tuple(int(v) for v in BG_BOT)


# ---------- composição ----------

def blocos_conteudo(p):
    bl = []
    if p.get("kicker"):
        bl.append(("chip", p["kicker"].upper(), 30))
    bl.append(("titulo", p["titulo"], 24 if p.get("subtitulo") else 40))
    if p.get("subtitulo"):
        bl.append(("sub", p["subtitulo"], 38))
    lay = p["layout"]
    if lay in ("lista", "passos", "cidades"):
        bl.append(("lista", (p["itens"], lay), 40))
    elif lay == "texto":
        bl.append(("texto", (p.get("lead"), p["texto"]), 40))
    elif lay == "mito_verdade":
        bl.append(("mv", (p["mito"], p["verdade"]), 40))
    else:
        raise SystemExit(f"layout desconhecido: {lay}")
    if p.get("destaque"):
        bl.append(("destaque", p["destaque"], 0))
    return bl


def desenhar_conteudo(c, img, d, y, blocos, desenhar):
    for kind, val, gap in blocos:
        if kind == "chip":
            img, y = b_chip(c, img, d, y, val, desenhar)
        elif kind == "titulo":
            img, y = b_titulo(c, img, d, y, val, desenhar)
        elif kind == "sub":
            img, y = b_paragrafo(c, img, d, y, val, desenhar, "Inter-Medium.otf", 38, SOFT, 1.32)
        elif kind == "lista":
            img, y = b_lista(c, img, d, y, val[0], val[1], desenhar)
        elif kind == "texto":
            img, y = b_texto(c, img, d, y, val[0], val[1], desenhar)
        elif kind == "mv":
            img, y = b_mito_verdade(c, img, d, y, val[0], val[1], desenhar)
        elif kind == "destaque":
            img, y = b_destaque(c, img, d, y, val, desenhar)
        if desenhar:
            d = ImageDraw.Draw(img)
        y += c.z(gap)
    return img, y


def cabecalho(img, alpha, fmt, lw, lh):
    S_ = S
    W = fmt["w"] * S_
    M = 84 * S_
    logo = Image.new("RGBA", (alpha.width, alpha.height), WHITE + (0,))
    logo.putalpha(alpha)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    y0 = fmt["logo_y"] * S_
    img.alpha_composite(logo, (M, y0))
    d = ImageDraw.Draw(img)
    f = font("Inter-SemiBold.otf", lh * 0.30)
    d.text((W - M, y0 + lh / 2), HANDLE, font=f, fill=SOFT, anchor="rm")
    return img


def render(p, saida):
    fmt = FORMATOS[p["formato"]]
    blocos = blocos_conteudo(p)
    alpha = logo_rgba()
    medida = ImageDraw.Draw(Image.new("RGB", (10, 10)))

    lw = fmt["logo_w"] * S
    lh = round(alpha.height * lw / alpha.width)
    sc = fmt["base"] * 1.12   # tenta aproveitar o espaço; reduz até caber
    while True:
        c = Ctx(fmt, sc)
        topo = fmt["logo_y"] * S + lh + c.z(70)
        _, h_cont = desenhar_conteudo(c, None, medida, 0, blocos, False)
        _, h_cta = b_cta(c, None, medida, 0, p.get("cta"), p.get("nota"), False)
        _, h_rod = b_rodape(c, None, medida, 0, False)
        fim = fmt["fim"] * S
        livre = fim - topo - (h_cont + c.z(56) + h_cta + c.z(34) + h_rod)
        if livre >= 0:
            break
        sc -= 0.02
        if sc < fmt["base"] * 0.76:
            raise SystemExit("ERRO: o texto não cabe na arte. Encurte o título, os itens ou o parágrafo.")

    img = fundo(c.W, c.H, alpha)
    img = cabecalho(img, alpha, fmt, lw, lh)

    y_rod = fim - h_rod
    y_cta = y_rod - c.z(34) - h_cta
    y_cont = topo + max(0, (y_cta - c.z(56) - topo - h_cont) * 0.45)
    d = ImageDraw.Draw(img)
    img, _ = desenhar_conteudo(c, img, d, y_cont, blocos, True)
    d = ImageDraw.Draw(img)
    img, _ = b_cta(c, img, d, y_cta, p.get("cta"), p.get("nota"), True)
    d = ImageDraw.Draw(img)
    img, _ = b_rodape(c, img, d, y_rod, True)

    out = img.convert("RGB").resize((fmt["w"], fmt["h"]), Image.LANCZOS)
    out.save(saida, "JPEG", quality=92, optimize=True)
    return sc


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        raise SystemExit(__doc__)
    pauta = json.load(open(args[0], encoding="utf-8"))
    erros = checar_texto(textos_da_pauta(pauta), "arte")
    if "--legenda" in args:
        leg = open(args[args.index("--legenda") + 1], encoding="utf-8").read()
        erros += checar_texto(leg, "legenda")
        if RT_LEGENDA not in leg:
            erros.append("legenda: falta a linha do Responsável Técnico (CRM-BA 29908)")
    if erros:
        raise SystemExit("ERRO:\n" + "\n".join(erros))
    sc = render(pauta, args[1])
    print(f"ok: {args[1]} (escala {sc:.2f})")


if __name__ == "__main__":
    main()
