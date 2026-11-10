"""Arte "Onde estamos": mapa dos municípios atendidos, no visual da EscleroVida.

Uso:
    python3 -I gerador/mapa.py arte.json saida.jpg [--legenda legenda.txt]

Desenha a região da Bahia onde ficam os municípios parceiros (contornos do IBGE, em
gerador/dados/ba-municipios.json), destaca cada município e põe o nome ao lado.
Um mapa pequeno da Bahia mostra onde fica a região. O rodapé do RT sai sempre.

JSON:
    {
      "formato": "feed" | "story",
      "titulo": ["Onde", "*estamos*"],            # * = cor de destaque
      "subtitulo": "Tratamento de varizes pelo SUS, sem custo e sem internação.",
      "cidades": {                                 # nome exato do IBGE -> posição do rótulo
        "Caculé": {"dx": 0, "dy": -70},            # deslocamento do rótulo em px (arte final)
        ...
      },
      "cta_titulo": "Procure o posto de saúde da sua cidade",
      "cta_texto": "O agendamento é feito pela Secretaria Municipal de Saúde.",
      "mapa_altura": 560,                          # altura da área do mapa (px)
      "mapa_largura": 0.70,                        # fração da largura ocupada pelas cidades
      "mapa_dy": 0,                                # desloca o mapa na vertical (px)
      "bahia": {"x": 84, "y": -150, "h": 150}      # mapa pequeno da Bahia (y relativo ao fim do mapa)
    }
Atualize "cidades" sempre que a lista de municípios parceiros mudar (REGRAS.md).
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R  # noqa: E402
import anuncio as A  # noqa: E402

S = R.S
WHITE = (255, 255, 255)
DADOS = os.path.join(R.AQUI, "dados", "ba-municipios.json")


def centro(aneis):
    """Centróide (por área) do maior anel."""
    anel = max(aneis, key=len)
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(anel, anel[1:] + anel[:1]):
        f = x0 * y1 - x1 * y0
        a += f
        cx += (x0 + x1) * f
        cy += (y0 + y1) * f
    return (cx / (3 * a), cy / (3 * a)) if a else anel[0]


def render(p, saida):
    fmt = R.FORMATOS[p["formato"]]
    W, H = fmt["w"] * S, fmt["h"] * S
    sc = 1.0 if p["formato"] == "feed" else 1.15
    c = R.Ctx(fmt, sc)
    z, M = c.z, c.M
    md = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    muns = json.load(open(DADOS, encoding="utf-8"))["municipios"]
    alvo = p["cidades"]
    faltam = [n for n in alvo if n not in {m["nome"] for m in muns}]
    if faltam:
        raise SystemExit("ERRO: município não encontrado nos dados do IBGE: " + ", ".join(faltam))

    # ---------- fundo + cabeçalho ----------
    alpha = R.logo_rgba()
    img = R.fundo(W, H, alpha)
    lw = fmt["logo_w"] * S
    lh = round(alpha.height * lw / alpha.width)
    img = R.cabecalho(img, alpha, fmt, lw, lh)
    d = ImageDraw.Draw(img)

    # ---------- título ----------
    y = fmt["logo_y"] * S + lh + z(54)
    linhas = p["titulo"]
    size = z(112)
    f = R.font("InterDisplay-Bold.otf", size)
    x = M - size * 0.04
    if p.get("titulo_em_linha", True):          # título em uma linha só, 2 cores
        for l in linhas:
            t = l.strip("*") + " "
            d.text((x, y + size * 0.80), t, font=f, fill=R.AQUA if l.startswith("*") else WHITE, anchor="ls")
            x += d.textlength(t, font=f)
        y += size * 1.02
    else:
        for l in linhas:
            d.text((x, y + size * 0.80), l.strip("*"), font=f, fill=R.AQUA if l.startswith("*") else WHITE,
                   anchor="ls")
            y += size * 1.04
    y += z(14)
    img, y = R.b_paragrafo(c, img, d, y, p["subtitulo"], True, "Inter-Medium.otf", 34, R.SOFT, 1.34)
    y_mapa = y + z(10)

    # ---------- rodapé e faixa (de baixo para cima) ----------
    _, h_rod = R.b_rodape(c, None, md, 0, False)
    fim = fmt["fim"] * S
    y_rod = fim - h_rod
    h_bar = z(120)
    y_bar = y_rod - z(30) - h_bar
    h_mapa = p.get("mapa_altura")
    h_mapa = h_mapa * S if h_mapa else y_bar - z(24) - y_mapa

    # ---------- projeção ----------
    pts = [pt for m in muns if m["nome"] in alvo for a in m["aneis"] for pt in a]
    lon0, lon1 = min(q[0] for q in pts), max(q[0] for q in pts)
    lat0, lat1 = min(q[1] for q in pts), max(q[1] for q in pts)
    latm = math.radians((lat0 + lat1) / 2)
    k = W * p.get("mapa_largura", 0.70) / ((lon1 - lon0) * math.cos(latm))     # px por grau
    cx0 = W / 2 + p.get("mapa_dx", 0) * S
    cy0 = y_mapa + h_mapa / 2 + p.get("mapa_dy", 0) * S

    def xy(lon, lat):
        return (cx0 + (lon - (lon0 + lon1) / 2) * math.cos(latm) * k, cy0 - (lat - (lat0 + lat1) / 2) * k)

    # ---------- mapa da região ----------
    mapa = R.camada(img)
    dm = ImageDraw.Draw(mapa)
    for m in muns:
        for a in m["aneis"]:
            pol = [xy(*q) for q in a]
            if max(q[0] for q in pol) < -50 or min(q[0] for q in pol) > W + 50:
                continue
            dm.polygon(pol, fill=WHITE + (13,))
            dm.line(pol + [pol[0]], fill=WHITE + (52,), width=S, joint="curve")
    # some suavemente nas bordas da área do mapa
    yy = np.arange(H, dtype=np.float32)
    borda = h_mapa * 0.16
    mv = np.clip(np.minimum(yy - (y_mapa - borda * 0.4), (y_mapa + h_mapa + borda * 0.4) - yy) / borda, 0, 1)
    xx = np.arange(W, dtype=np.float32)
    mh = np.clip(np.minimum(xx, W - xx) / (W * 0.07), 0, 1)
    masc = (mv[:, None] * mh[None, :]) ** 1.2
    al = np.asarray(mapa.getchannel("A")).astype(np.float32) * masc
    mapa.putalpha(Image.fromarray(al.astype(np.uint8), "L"))
    img = Image.alpha_composite(img, mapa)

    # municípios em destaque (com brilho)
    dest = R.camada(img)
    dd = ImageDraw.Draw(dest)
    centros = {}
    for m in muns:
        if m["nome"] in alvo:
            for a in m["aneis"]:
                dd.polygon([xy(*q) for q in a], fill=R.AQUA + (255,))
            centros[m["nome"]] = xy(*centro(m["aneis"]))
    brilho = dest.filter(ImageFilter.GaussianBlur(z(16)))
    brilho.putalpha(brilho.getchannel("A").point(lambda v: v * 0.55))
    img = Image.alpha_composite(img, brilho)
    img = Image.alpha_composite(img, dest)
    d = ImageDraw.Draw(img)
    for m in muns:
        if m["nome"] in alvo:
            for a in m["aneis"]:
                pol = [xy(*q) for q in a]
                d.line(pol + [pol[0]], fill=WHITE, width=round(1.5 * S), joint="curve")

    # ---------- rótulos ----------
    fl = R.font("Inter-Bold.otf", z(28))
    for nome, pos in alvo.items():
        px, py = centros[nome]
        lx, ly = px + pos.get("dx", 0) * S, py + pos.get("dy", -60) * S
        tw = d.textlength(nome, font=fl)
        bw, bh = tw + z(40), z(52)
        box = [lx - bw / 2, ly - bh / 2, lx + bw / 2, ly + bh / 2]
        # linha do município até a borda do rótulo
        ex = min(max(px, box[0] + z(18)), box[2] - z(18))
        ey = box[3] if py > ly else box[1]
        lay = R.camada(img)
        ld = ImageDraw.Draw(lay)
        ld.line([(px, py), (ex, ey)], fill=WHITE + (235,), width=round(1.5 * S))
        r = z(6)
        ld.ellipse([px - r, py - r, px + r, py + r], fill=R.DEEP + (255,), outline=WHITE + (255,), width=S)
        sh = R.camada(img)
        ImageDraw.Draw(sh).rounded_rectangle([box[0], box[1] + z(5), box[2], box[3] + z(5)], radius=bh / 2,
                                             fill=(0, 16, 36, 130))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(z(8))))
        ld.rounded_rectangle(box, radius=bh / 2, fill=WHITE + (255,))
        img = Image.alpha_composite(img, lay)
        d = ImageDraw.Draw(img)
        d.text((lx, ly), nome, font=fl, fill=R.DEEP, anchor="mm")

    # ---------- mapa pequeno da Bahia ----------
    b = p.get("bahia")
    if b is not False:
        b = b or {}
        bh_ = b.get("h", 150) * S
        allp = [q for m in muns for a in m["aneis"] for q in a]
        bl0, bl1 = min(q[0] for q in allp), max(q[0] for q in allp)
        bt0, bt1 = min(q[1] for q in allp), max(q[1] for q in allp)
        kb = bh_ / (bt1 - bt0)
        cl = math.cos(math.radians((bt0 + bt1) / 2))
        bx = b.get("x", 84) * S
        by = y_mapa + h_mapa + b.get("y", -150) * S

        def bxy(lon, lat):
            return (bx + (lon - bl0) * cl * kb, by + (bt1 - lat) * kb)

        lay = R.camada(img)
        ld = ImageDraw.Draw(lay)
        for m in muns:
            for a in m["aneis"]:
                ld.polygon([bxy(*q) for q in a], fill=WHITE + (255,))
        sil = lay.getchannel("A").filter(ImageFilter.MaxFilter(3))
        lay = Image.new("RGBA", img.size, WHITE + (0,))
        lay.putalpha(sil.point(lambda v: v * 0.26))
        img = Image.alpha_composite(img, lay)
        d = ImageDraw.Draw(img)
        for m in muns:
            if m["nome"] in alvo:
                qx, qy = bxy(*centro(m["aneis"]))
                r = z(4.5)
                d.ellipse([qx - r, qy - r, qx + r, qy + r], fill=R.AQUA)
        A.espacado(d, bx + (bl1 - bl0) * cl * kb / 2, by + bh_ + z(26), "BAHIA",
                   R.font("Inter-SemiBold.otf", z(17)), R.SOFT, z(5), centro=True)

    # ---------- faixa: caminho do SUS ----------
    img = R.vidro(img, [M, y_bar, W - M, y_bar + h_bar], z(30), fill_a=24, line_a=48, sombra=True)
    d = ImageDraw.Draw(img)
    ri = z(33)
    icx, icy = M + z(26) + ri, y_bar + h_bar / 2
    d.ellipse([icx - ri, icy - ri, icx + ri, icy + ri], fill=R.AQUA)
    A.pin(d, icx, icy, ri, R.DEEP, R.AQUA)
    tx = icx + ri + z(24)
    disp = W - M - z(28) - tx
    for txt, fname, tam, dy, cor in ((p["cta_titulo"], "Inter-Bold.otf", z(31), -z(19), WHITE),
                                     (p["cta_texto"], "Inter-Regular.otf", z(24), z(22), R.SOFT)):
        while d.textlength(txt, font=R.font(fname, tam)) > disp and tam > z(16):
            tam -= z(0.5)
        d.text((tx, icy + dy), txt, font=R.font(fname, tam), fill=cor, anchor="lm")

    img, _ = R.b_rodape(c, img, d, y_rod, True)
    out = img.convert("RGB").resize((fmt["w"], fmt["h"]), Image.LANCZOS)
    out.save(saida, "JPEG", quality=93, optimize=True)


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        raise SystemExit(__doc__)
    p = json.load(open(args[0], encoding="utf-8"))
    texto = " \n ".join([t.strip("*") for t in p["titulo"]] + [p["subtitulo"], p["cta_titulo"], p["cta_texto"]]
                        + list(p["cidades"]))
    erros = R.checar_texto(texto, "arte")
    if "--legenda" in args:
        leg = open(args[args.index("--legenda") + 1], encoding="utf-8").read()
        erros += R.checar_texto(leg, "legenda")
        if R.RT_LEGENDA not in leg:
            erros.append("legenda: falta a linha do Responsável Técnico (CRM-BA 29908)")
    if erros:
        raise SystemExit("ERRO:\n" + "\n".join(erros))
    render(p, args[1])
    print(f"ok: {args[1]}")


if __name__ == "__main__":
    main()
