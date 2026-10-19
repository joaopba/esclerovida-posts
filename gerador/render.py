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
    "feed": dict(w=1080, h=1350, base=0.80, logo_w=330, logo_y=60, fim=1300),
    "story": dict(w=1080, h=1920, base=1.00, logo_w=430, logo_y=200, fim=1695),
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
    for cx, cy, sig, amp in [(0.95, 0.12, 0.45, 38), (0.0, 0.92, 0.5, 30)]:
        d2 = (xx / W - cx) ** 2 + ((yy / H - cy) * ar) ** 2
        img = img + np.exp(-d2 / (2 * sig ** 2))[..., None] * np.array([40, 120, 130]) * (amp / 100)
    img = img + np.random.default_rng(7).normal(0, 2.0, (H, W, 1))
    base = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    # coração da marca como marca d'água
    heart = alpha_logo.crop((0, 0, 338, alpha_logo.height))
    hh = int(H * 0.65)
    heart = heart.resize((round(heart.width * hh / heart.height), hh), Image.LANCZOS)
    mark = Image.new("RGBA", heart.size, WHITE + (0,))
    mark.putalpha(heart.point(lambda v: v * 0.075))
    base.alpha_composite(mark, (W - round(heart.width * 0.72), H - hh - int(H * 0.04)))
    return base


def camada(img):
    return Image.new("RGBA", img.size, (0, 0, 0, 0))


def vidro(img, box, radius):
    lay = camada(img)
    ImageDraw.Draw(lay).rounded_rectangle(box, radius=radius, fill=WHITE + (24,),
                                          outline=WHITE + (52,), width=2 * S)
    return Image.alpha_composite(img, lay)


class Ctx:
    def __init__(self, fmt, sc):
        self.W, self.H = fmt["w"] * S, fmt["h"] * S
        self.sc = sc * S
        self.M = 90 * S
        self.CW = self.W - 2 * self.M

    def z(self, v):
        return v * self.sc


# Cada bloco: bloco(ctx, img, d, y, desenhar) -> (img, y_final)

def b_chip(c, img, d, y, texto, desenhar, cor=AQUA, x=None):
    f = font("Inter-SemiBold.otf", c.z(28))
    sp = c.z(5)
    tw = sum(d.textlength(ch, font=f) + sp for ch in texto) - sp
    h = c.z(58)
    x = c.M if x is None else x
    if desenhar:
        lay = camada(img)
        ImageDraw.Draw(lay).rounded_rectangle([x, y, x + tw + 2 * c.z(28), y + h], radius=h / 2,
                                              fill=cor + (34,), outline=cor + (120,), width=2 * S)
        img = Image.alpha_composite(img, lay)
        d = ImageDraw.Draw(img)
        cx = x + c.z(28)
        for ch in texto:
            d.text((cx, y + h / 2), ch, font=f, fill=cor, anchor="lm")
            cx += d.textlength(ch, font=f) + sp
    return img, y + h


def b_titulo(c, img, d, y, linhas, desenhar):
    size = c.z(100)
    limpas = [l.strip("*") for l in linhas]
    while True:
        f = font("InterDisplay-Bold.otf", size)
        if max(d.textlength(l, font=f) for l in limpas) <= c.CW or size <= c.z(56):
            break
        size -= c.z(2)
    lh = size * 1.08
    for l in linhas:
        if desenhar:
            d.text((c.M, y), l.strip("*"), font=f, fill=AQUA if l.startswith("*") else WHITE)
        y += lh
    return img, y


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


def icone_check(d, cx, cy, r, c):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=AQUA)
    k = r / 21
    d.line([(cx - 9 * k, cy + 1 * k), (cx - 3 * k, cy + 7 * k), (cx + 9 * k, cy - 7 * k)],
           fill=DEEP, width=max(2, round(5 * k)), joint="curve")


def icone_pin(d, cx, cy, r, c):
    k = 2.1
    py, px = r / k, r * (1 - (1 / k) ** 2) ** 0.5
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=AQUA)
    d.polygon([(cx - px, cy + py), (cx + px, cy + py), (cx, cy + k * r)], fill=AQUA)
    ri = r * 0.42
    d.ellipse([cx - ri, cy - ri, cx + ri, cy + ri], fill=DEEP)


def icone_num(d, cx, cy, r, c, n):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=AQUA)
    d.text((cx, cy), str(n), font=font("Inter-Bold.otf", r * 1.15), fill=DEEP, anchor="mm")


def b_lista(c, img, d, y, itens, tipo, desenhar):
    pv = c.z(20)
    tx = c.M + c.z(104)
    tw = c.W - c.M - c.z(40) - tx
    f = font("Inter-SemiBold.otf" if tipo == "cidades" else "Inter-Medium.otf", c.z(42 if tipo == "cidades" else 38))
    lh = c.z(48 if tipo != "cidades" else 52)
    rows = []
    for it in itens:
        ls = wrap(d, it, f, tw)
        rows.append((ls, max(c.z(74), len(ls) * lh + c.z(26))))
    total = pv * 2 + sum(h for _, h in rows)
    if desenhar:
        img = vidro(img, [c.M, y, c.W - c.M, y + total], c.z(44))
        if tipo == "cidades":
            lay = camada(img)
            ld = ImageDraw.Draw(lay)
            ry = y + pv
            for _, h in rows[:-1]:
                ry += h
                ld.line([(tx, ry), (c.W - c.M - c.z(44), ry)], fill=(255, 255, 255, 46), width=2 * S)
            img = Image.alpha_composite(img, lay)
        d = ImageDraw.Draw(img)
        ry = y + pv
        for i, (ls, h) in enumerate(rows):
            top_text = ry + (h - len(ls) * lh) / 2
            first_mid = top_text + lh / 2
            cx = c.M + c.z(60)
            if tipo == "cidades":
                icone_pin(d, cx, first_mid - c.z(8), c.z(16), c)
            elif tipo == "passos":
                icone_num(d, cx, first_mid, c.z(22), c, i + 1)
            else:
                icone_check(d, cx, first_mid, c.z(21), c)
            for j, l in enumerate(ls):
                d.text((tx, top_text + lh * j + lh / 2), l, font=f, fill=WHITE, anchor="lm")
            ry += h
    return img, y + total


def b_texto(c, img, d, y, lead, texto, desenhar):
    pad = c.z(46)
    inner = c.CW - 2 * pad
    _, h1 = b_paragrafo(c, img, d, 0, lead, False, "Inter-Bold.otf", 40, WHITE, 1.3, largura=inner) if lead else (None, 0)
    _, h2 = b_paragrafo(c, img, d, 0, texto, False, "Inter-Regular.otf", 36, SOFT, 1.42, largura=inner)
    gap = c.z(16) if lead else 0
    total = pad * 2 + h1 + gap + h2
    if desenhar:
        img = vidro(img, [c.M, y, c.W - c.M, y + total], c.z(44))
        d = ImageDraw.Draw(img)
        yy = y + pad - c.z(4)
        if lead:
            _, yy = b_paragrafo(c, img, d, yy, lead, True, "Inter-Bold.otf", 40, WHITE, 1.3, largura=inner, x=c.M + pad)
            yy += gap
        b_paragrafo(c, img, d, yy, texto, True, "Inter-Regular.otf", 36, SOFT, 1.42, largura=inner, x=c.M + pad)
    return img, y + total


def b_mito_verdade(c, img, d, y, mito, verdade, desenhar):
    pad = c.z(40)
    inner = c.CW - 2 * pad
    for rotulo, cor, texto, fname in (("MITO", CORAL, mito, "Inter-Medium.otf"),
                                      ("VERDADE", AQUA, verdade, "Inter-SemiBold.otf")):
        _, ht = b_paragrafo(c, img, d, 0, texto, False, fname, 38, WHITE, 1.36, largura=inner)
        total = pad * 2 + c.z(58) + c.z(22) + ht
        if desenhar:
            img = vidro(img, [c.M, y, c.W - c.M, y + total], c.z(40))
            d = ImageDraw.Draw(img)
            img, yy = b_chip(c, img, d, y + pad, rotulo, True, cor=cor, x=c.M + pad)
            d = ImageDraw.Draw(img)
            b_paragrafo(c, img, d, yy + c.z(22), texto, True, fname, 38, WHITE, 1.36, largura=inner, x=c.M + pad)
        y += total + c.z(24)
    return img, y - c.z(24)


def b_cta(c, img, d, y, texto, nota, desenhar):
    if texto:
        size = c.z(40)
        while True:
            f = font("Inter-Bold.otf", size)
            tw = d.textlength(texto, font=f)
            if tw + 2 * c.z(56) <= c.CW or size <= c.z(28):
                break
            size -= c.z(1)
        bh = c.z(112)
        if desenhar:
            x0 = (c.W - tw) / 2 - c.z(56)
            sh = camada(img)
            ImageDraw.Draw(sh).rounded_rectangle([x0, y + c.z(12), c.W - x0, y + bh + c.z(12)], radius=bh / 2,
                                                 fill=(0, 20, 40, 90))
            img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(c.z(16))))
            d = ImageDraw.Draw(img)
            d.rounded_rectangle([x0, y, c.W - x0, y + bh], radius=bh / 2, fill=WHITE)
            d.text((c.W / 2, y + bh / 2), texto, font=f, fill=DEEP, anchor="mm")
        y += bh + c.z(22)
    if nota:
        d = ImageDraw.Draw(img) if desenhar else d
        img, y = b_paragrafo(c, img, d, y, nota, desenhar, "Inter-Regular.otf", 29, SOFT, 1.38, centro=True)
    return img, y


def b_rodape(c, img, d, y, desenhar):
    for l, fname in zip(RT, ("Inter-SemiBold.otf", "Inter-Regular.otf")):
        if desenhar:
            d.text((c.W / 2, y), l, font=font(fname, c.z(26)), fill=FOOT, anchor="mt")
        y += c.z(36)
    return img, y


# ---------- composição ----------

def blocos_conteudo(p):
    bl = []
    if p.get("kicker"):
        bl.append(("chip", p["kicker"].upper(), 30))
    bl.append(("titulo", p["titulo"], 22 if p.get("subtitulo") else 36))
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
            img, y = b_paragrafo(c, img, d, y, val, desenhar, "Inter-Bold.otf", 42, WHITE, 1.3, centro=True)
        if desenhar:
            d = ImageDraw.Draw(img)
        y += c.z(gap)
    return img, y


def render(p, saida):
    fmt = FORMATOS[p["formato"]]
    blocos = blocos_conteudo(p)
    alpha = logo_rgba()
    medida = ImageDraw.Draw(Image.new("RGB", (10, 10)))

    sc = fmt["base"]
    while True:
        c = Ctx(fmt, sc)
        lw = fmt["logo_w"] * S
        lh = round(alpha.height * lw / alpha.width)
        topo = fmt["logo_y"] * S + lh + c.z(52)
        _, h_cont = desenhar_conteudo(c, None, medida, 0, blocos, False)
        _, h_cta = b_cta(c, None, medida, 0, p.get("cta"), p.get("nota"), False)
        _, h_rod = b_rodape(c, None, medida, 0, False)
        fim = fmt["fim"] * S
        livre = fim - topo - (h_cont + c.z(40) + h_cta + c.z(26) + h_rod)
        if livre >= 0:
            break
        sc -= 0.03
        if sc < fmt["base"] * 0.78:
            raise SystemExit("ERRO: o texto não cabe na arte. Encurte o título, os itens ou o parágrafo.")

    img = fundo(c.W, c.H, alpha)
    logo = Image.new("RGBA", (alpha.width, alpha.height), WHITE + (0,))
    logo.putalpha(alpha)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    img.alpha_composite(logo, ((c.W - lw) // 2, fmt["logo_y"] * S))

    y_rod = fim - h_rod
    y_cta = y_rod - c.z(26) - h_cta
    y_cont = topo + max(0, (y_cta - c.z(40) - topo - h_cont) / 2)
    d = ImageDraw.Draw(img)
    img, _ = desenhar_conteudo(c, img, d, y_cont, blocos, True)
    d = ImageDraw.Draw(img)
    img, _ = b_cta(c, img, d, y_cta, p.get("cta"), p.get("nota"), True)
    d = ImageDraw.Draw(img)
    b_rodape(c, img, d, y_rod, True)

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
