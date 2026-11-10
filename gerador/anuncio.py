"""Arte de anúncio com foto (ex.: início dos atendimentos em um município).

Uso:
    python3 -I gerador/anuncio.py arte.json foto.jpg logo_parceiro.png saida.jpg [--legenda legenda.txt]

Visual: foto tratada no topo, "folha" azul de cantos arredondados subindo sobre a foto,
nome da cidade em destaque, logo do parceiro ao lado do título, linha de benefícios e
faixa com o caminho do SUS. O rodapé do Responsável Técnico sai sempre.

JSON:
    {
      "formato": "feed" | "story",
      "titulo_pre": "Começamos os\natendimentos em",   # 1 ou 2 linhas (separe com \n)
      "cidade": "Caculé",
      "subtitulo": "Tratamento de varizes pelo SUS",
      "itens": ["Sem custo", "Sem internação", "Sessões rápidas"],     # até 3, curtos
      "cta_titulo": "Procure o posto de saúde da sua cidade",
      "cta_texto": "O agendamento é feito pela Secretaria Municipal de Saúde.",
      "transicao": "degrade" | "folha",     # degrade (padrão): a foto se desfaz no azul; folha: painel arredondado
      "rotulo": "EM PARCERIA COM",          # texto acima da logo do parceiro
      "recorte": [x0, y0, x1, y1],          # área da foto a usar (0 a 1)
      "cor_destaque": [r, g, b],            # cor do nome da cidade (ex.: cor do município)
      "cor_acento": [r, g, b],              # cor do ícone da faixa
      "logo2_altura": 200
    }
Use só fotos sem pacientes identificáveis e logo do parceiro em PNG transparente.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R  # noqa: E402

S = R.S
WHITE = (255, 255, 255)
NAVY = np.array([5, 28, 58], dtype=np.float32)


def preparar_foto(caminho, recorte, W, hp, base=0.60):
    f = Image.open(caminho).convert("RGB")
    x0, y0, x1, y1 = recorte
    f = f.crop((round(x0 * f.width), round(y0 * f.height), round(x1 * f.width), round(y1 * f.height)))
    esc = max(W / f.width, hp / f.height)
    f = f.resize((round(f.width * esc), round(f.height * esc)), Image.LANCZOS)
    left = (f.width - W) // 2
    f = f.crop((left, 0, left + W, hp))
    f = ImageEnhance.Contrast(f).enhance(1.07)
    f = ImageEnhance.Color(f).enhance(1.06)
    a = np.asarray(f).astype(np.float32)
    a = a * 0.90 + NAVY * 0.10                       # leve tom azul, para unir à marca
    yy = np.linspace(0, 1, hp, dtype=np.float32)[:, None, None]
    topo = np.clip(1 - yy / 0.36, 0, 1) ** 1.4 * 0.66   # escurece o topo (logo legível)
    m = np.maximum(topo, np.clip((yy - 0.50) / 0.50, 0, 1) ** 1.3 * base)
    a = a * (1 - m) + NAVY * m
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


def gradiente(W, H, ys):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    t = np.clip((yy - ys) / max(1, H - ys), 0, 1)
    t = (t * 0.88 + xx / W * 0.12)[..., None]
    img = R.BG_TOP * (1 - t) + R.BG_BOT * t
    d2 = (xx / W - 1.0) ** 2 + ((yy - ys) / W - 0.05) ** 2
    img = img + np.exp(-d2 / (2 * 0.40 ** 2))[..., None] * np.array([40, 120, 130]) * 0.30
    img = img + np.random.default_rng(7).normal(0, 1.5, (H, W, 1))
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


def espacado(d, x, y, texto, f, fill, sp, centro=False):
    w = sum(d.textlength(ch, font=f) + sp for ch in texto) - sp
    if centro:
        x -= w / 2
    for ch in texto:
        d.text((x, y), ch, font=f, fill=fill, anchor="ls")
        x += d.textlength(ch, font=f) + sp
    return w


def pin(d, cx, cy, r, cor, furo):
    r1 = r * 0.40
    hy = cy - r * 0.16
    d.ellipse([cx - r1, hy - r1, cx + r1, hy + r1], fill=cor)
    k = 2.0
    py, px = r1 / k, r1 * (1 - (1 / k) ** 2) ** 0.5
    d.polygon([(cx - px, hy + py), (cx + px, hy + py), (cx, hy + k * r1)], fill=cor)
    ri = r1 * 0.40
    d.ellipse([cx - ri, hy - ri, cx + ri, hy + ri], fill=furo)


def render(p, foto, logo2, saida):
    fmt = R.FORMATOS[p["formato"]]
    W, H = fmt["w"] * S, fmt["h"] * S
    sc = 1.0 if p["formato"] == "feed" else 1.17
    c = R.Ctx(fmt, sc)
    z = c.z
    M, CW = c.M, c.CW
    creme = tuple(p.get("cor_destaque", (255, 219, 147)))
    acento = tuple(p.get("cor_acento", (233, 69, 34)))
    md = ImageDraw.Draw(Image.new("RGB", (10, 10)))

    # ---------- medidas ----------
    lg2 = Image.open(logo2).convert("RGBA")
    L = z(p.get("logo2_altura", 200))
    lw2 = L * lg2.width / lg2.height
    rot = p.get("rotulo", "EM PARCERIA COM")
    f_rot = R.font("Inter-SemiBold.otf", z(19))
    rot_w = sum(md.textlength(ch, font=f_rot) + z(4) for ch in rot) - z(4)
    bloco_w = max(lw2, rot_w)
    bloco_h = z(19) + z(22) + L

    f_pre = R.font("Inter-Medium.otf", z(54))
    disp = CW - bloco_w - z(76)
    size = z(196)
    while True:
        f_cid = R.font("InterDisplay-Bold.otf", size)
        if md.textlength(p["cidade"], font=f_cid) <= disp or size <= z(110):
            break
        size -= z(4)
    bb = f_cid.getbbox(p["cidade"], anchor="ls")
    asc, desc = -bb[1], max(0, bb[3])
    pre_linhas = p["titulo_pre"].split("\n")           # aceita 2 linhas com "\n"
    pre_tam = z(54 if len(pre_linhas) == 1 else 50)
    while max(md.textlength(l, font=R.font("Inter-Medium.otf", pre_tam)) for l in pre_linhas) > disp \
            and pre_tam > z(34):
        pre_tam -= z(1)
    f_pre = R.font("Inter-Medium.otf", pre_tam)
    pre_lh = pre_tam * 1.16
    pre_asc = pre_tam * 0.74 + (len(pre_linhas) - 1) * pre_lh
    tit_h = pre_asc + z(30) + asc + desc
    row_h = max(tit_h, bloco_h)

    f_sub = R.font("Inter-SemiBold.otf", z(36))
    f_it = R.font("Inter-Medium.otf", z(29))
    itens = p.get("itens", [])[:3]
    h_bar = z(120)
    _, h_rod = R.b_rodape(c, None, md, 0, False)

    blocos = [z(58), row_h, z(34), 2 * S, z(36), z(36), z(26), z(40), z(38), h_bar, z(30), h_rod]
    fim = fmt["fim"] * S
    ys = fim - sum(blocos)                     # topo da folha
    Rr = z(64)

    # ---------- foto + fundo ----------
    if p.get("transicao", "degrade") == "degrade":
        # a foto se desfaz em degradê no fundo azul
        hp = round(ys + z(96))
        img = gradiente(W, H, ys * 0.80).convert("RGBA")
        # coração da marca como marca d'água, sangrando no canto inferior direito
        al_logo = R.logo_rgba()
        heart = al_logo.crop((0, 0, 338, al_logo.height))
        hh = int(H * 0.58)
        heart = heart.resize((round(heart.width * hh / heart.height), hh), Image.LANCZOS)
        mark = Image.new("RGBA", heart.size, WHITE + (0,))
        mark.putalpha(heart.point(lambda v: v * p.get("marca_dagua", 0.07)))
        img.alpha_composite(mark, (W - round(heart.width * 0.62), H - round(hh * 0.86)))
        foto_im = preparar_foto(foto, p.get("recorte", [0, 0, 1, 1]), W, hp, base=0.0).convert("RGBA")
        yy = np.linspace(0, 1, hp, dtype=np.float32)
        fade = 0.42
        al = np.clip((1 - yy) / fade, 0, 1) ** 1.25
        foto_im.putalpha(Image.fromarray((np.repeat(al[:, None], W, 1) * 255).astype(np.uint8), "L"))
        img.alpha_composite(foto_im)
    else:
        # "folha": painel de cantos arredondados subindo sobre a foto
        hp = round(ys + Rr + z(30))
        img = Image.new("RGBA", (W, H), tuple(int(v) for v in NAVY) + (255,))
        img.paste(preparar_foto(foto, p.get("recorte", [0, 0, 1, 1]), W, hp), (0, 0))
        sh = R.camada(img)
        ImageDraw.Draw(sh).rounded_rectangle([-8, ys - z(6), W + 8, H + Rr], radius=Rr, fill=(0, 12, 30, 170))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(z(30))))
        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, ys, W, H + Rr], radius=Rr, fill=255)
        img.paste(gradiente(W, H, ys), (0, 0), mask)
        lay = R.camada(img)
        ImageDraw.Draw(lay).rounded_rectangle([-8, ys, W + 8, H + Rr], radius=Rr, outline=WHITE + (46,),
                                              width=2 * S)
        img = Image.alpha_composite(img, lay)

    # ---------- cabeçalho ----------
    alpha = R.logo_rgba()
    lw = fmt["logo_w"] * S
    lh = round(alpha.height * lw / alpha.width)
    img = R.cabecalho(img, alpha, fmt, lw, lh)
    d = ImageDraw.Draw(img)

    # ---------- título + logo do parceiro ----------
    y = ys + blocos[0]
    ty = y + (row_h - tit_h) / 2
    for i, l in enumerate(pre_linhas):
        d.text((M, ty + pre_asc - (len(pre_linhas) - 1 - i) * pre_lh), l, font=f_pre, fill=WHITE, anchor="ls")
    d.text((M - size * 0.045, ty + pre_asc + z(30) + asc), p["cidade"], font=f_cid, fill=creme, anchor="ls")

    by = y + (row_h - bloco_h) / 2
    cx = W - M - bloco_w / 2
    espacado(d, cx, by + z(19) * 0.78, rot, f_rot, R.SOFT, z(4), centro=True)
    lg = lg2.resize((round(lw2), round(L)), Image.LANCZOS)
    lx, ly = round(cx - lw2 / 2), round(by + z(19) + z(22))
    sh = R.camada(img)
    som = Image.new("RGBA", lg.size, (0, 14, 30, 0))
    som.putalpha(lg.getchannel("A").point(lambda v: v * 0.5))
    sh.alpha_composite(som, (lx, ly + round(L * 0.012)))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(L * 0.02)))
    img.alpha_composite(lg, (lx, ly))
    lay = R.camada(img)
    ld = ImageDraw.Draw(lay)
    xs = W - M - bloco_w - z(38)
    ld.line([(xs, y + row_h * 0.08), (xs, y + row_h * 0.92)], fill=WHITE + (56,), width=2 * S)
    y += row_h + blocos[2]
    ld.line([(M, y), (W - M, y)], fill=WHITE + (44,), width=2 * S)
    img = Image.alpha_composite(img, lay)
    d = ImageDraw.Draw(img)
    y += blocos[3] + blocos[4]

    # ---------- subtítulo + benefícios ----------
    d.text((M, y + z(36) * 0.76), p["subtitulo"], font=f_sub, fill=WHITE, anchor="ls")
    y += blocos[5] + blocos[6]
    r = z(16)
    tam = z(29)
    while True:                                # reduz a fonte até a linha caber
        f_it = R.font("Inter-Medium.otf", tam)
        larg = [2 * r + z(12) + d.textlength(t, font=f_it) for t in itens]
        folga = (CW - sum(larg)) / max(1, len(itens) - 1)
        if folga >= z(22) or tam <= z(20):
            break
        tam -= z(1)
    folga = min(folga, z(44))
    x = M
    cy = y + z(20)
    for t, w in zip(itens, larg):
        R.icone_check(d, x + r, cy, r, cor=creme, traco=R.DEEP)
        d.text((x + 2 * r + z(12), cy), t, font=f_it, fill=R.SOFT, anchor="lm")
        x += w + folga
    y += blocos[7] + blocos[8]

    # ---------- faixa: caminho do SUS ----------
    img = R.vidro(img, [M, y, W - M, y + h_bar], z(30), fill_a=24, line_a=48, sombra=True)
    d = ImageDraw.Draw(img)
    ri = z(33)
    icx, icy = M + z(26) + ri, y + h_bar / 2
    d.ellipse([icx - ri, icy - ri, icx + ri, icy + ri], fill=acento)
    pin(d, icx, icy, ri, WHITE, acento)
    tx = icx + ri + z(24)
    disp_tx = W - M - z(28) - tx
    for txt, fname, tam, dy, cor in ((p["cta_titulo"], "Inter-Bold.otf", z(31), -z(19), WHITE),
                                     (p["cta_texto"], "Inter-Regular.otf", z(24), z(22), R.SOFT)):
        while d.textlength(txt, font=R.font(fname, tam)) > disp_tx and tam > z(16):
            tam -= z(0.5)
        d.text((tx, icy + dy), txt, font=R.font(fname, tam), fill=cor, anchor="lm")
    y += h_bar + blocos[10]

    # ---------- rodapé ----------
    img, _ = R.b_rodape(c, img, d, y, True)

    out = img.convert("RGB").resize((fmt["w"], fmt["h"]), Image.LANCZOS)
    out.save(saida, "JPEG", quality=93, optimize=True)


def main():
    args = sys.argv[1:]
    if len(args) < 4:
        raise SystemExit(__doc__)
    p = json.load(open(args[0], encoding="utf-8"))
    texto = " \n ".join([p["titulo_pre"], p["cidade"], p["subtitulo"], p["cta_titulo"], p["cta_texto"],
                         p.get("rotulo", "")] + p.get("itens", []))
    erros = R.checar_texto(texto, "arte")
    if "--legenda" in args:
        leg = open(args[args.index("--legenda") + 1], encoding="utf-8").read()
        erros += R.checar_texto(leg, "legenda")
        if R.RT_LEGENDA not in leg:
            erros.append("legenda: falta a linha do Responsável Técnico (CRM-BA 29908)")
    if erros:
        raise SystemExit("ERRO:\n" + "\n".join(erros))
    render(p, args[1], args[2], args[3])
    print(f"ok: {args[3]}")


if __name__ == "__main__":
    main()
