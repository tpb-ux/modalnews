#!/usr/bin/env python3
"""Coleta notícias de feeds RSS (sem IA) e gera content/*.md com resumo curto e link para a fonte.
Uso: python fetch.py [--max N] [--dry-run]"""
import argparse, datetime as dt, html, re, socket, time, unicodedata, urllib.request
from pathlib import Path
import io
import feedparser, yaml
from PIL import Image

socket.setdefaulttimeout(20)
ROOT = Path(__file__).parent; CONTENT = ROOT / "content"
UA = "Mozilla/5.0 (compatible; ModalNewsBot/1.0; +https://modalnews.com.br)"
BRT = dt.timezone(dt.timedelta(hours=-3))
KW = {
    "comercio-exterior": ["porto", "portuári", "exporta", "importa", "comex", "comércio exterior", "aduan", "alfândeg", "navio", "contêiner", "container", "cabotagem", "marítim", "antaq", "balança comercial", "tarifa"],
    "armazenagem": ["armazé", "armazenag", "centro de distribuição", "galpão", "galpões", "condomínio logístico", "wms", "estoque", "intralogística", "empilhadeira", "picking", "fulfillment"],
    "tecnologia": ["tecnologia", "software", "inteligência artificial", "automação", "robô", "digital", "startup", "plataforma", "aplicativo", "rastreamento", "drone", "iot", "tms"],
    "supply-chain": ["supply chain", "cadeia de suprimentos", "suprimento", "procurement", "abastecimento", "fornecedor", "s&op"],
    "transporte": ["transporte", "frete", "caminh", "rodovi", "ferrovi", "aéreo", "aviação", "carga", "transportadora", "motorista", "diesel", "antt", "rodovia", "última milha", "entrega", "frota"],
}

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()

def slugify(s): return norm(s).replace(" ", "-")[:70].strip("-")

def classify(text):
    t = (text or "").lower(); best, score = "mercado", 0
    for ed, words in KW.items():
        sc = sum(t.count(w) for w in words)
        if sc > score: best, score = ed, sc
    return best

LOGI = sorted({w for ws in KW.values() for w in ws} | {"logístic", "logistic", "supply", "armazen", "operador logístico", "e-commerce", "distribuição", "expedição", "embarcador", "terminal", "ferrovia", "hidrovia", "aeroporto"})

def score(title, summ):
    t, s = (title or "").lower(), (summ or "").lower()
    return sum(3 for w in LOGI if w in t) + sum(1 for w in LOGI if w in s)

def blocked(cfg, src, link, title, summ, trusted=False):
    hay_src = f"{src} {link}".lower(); txt = f"{title} {summ}".lower()
    for b in cfg.get("bloqueio_fontes", []):
        if b.lower() in hay_src: return f"fonte bloqueada ({b})"
    for b in cfg.get("bloqueio_palavras", []):  # início de palavra: "lula" não casa com "celular"
        if re.search(r"(?<!\w)" + re.escape(b.lower()), txt): return f"palavra bloqueada ({b})"
    if trusted: return None
    sc = score(title, summ)
    if sc < cfg.get("nota_minima", 3): return f"nota {sc} < {cfg.get('nota_minima', 3)}"
    return None

def revisar(cfg, remove=False):
    """Reaplica os filtros nas matérias já publicadas pelo coletor."""
    n = 0; trusted = {fd["nome"] for fd in cfg["feeds"] if fd.get("confiavel")}
    for f in sorted(CONTENT.glob("*.md")):
        fm = yaml.safe_load(f.read_text(encoding="utf-8").split("---", 2)[1]) or {}
        if fm.get("gerado_por") != "fetch.py": continue
        why = blocked(cfg, fm.get("fonte", ""), fm.get("link", ""), fm.get("titulo", ""), fm.get("resumo", ""), fm.get("fonte") in trusted)
        if why:
            n += 1; print(f"- {f.name}: {why}")
            if remove:
                f.unlink()
                with REMOVED.open("a", encoding="utf-8") as r: r.write(fm.get("link", "") + "\n")
    print(f"{n} matéria(s) fora dos filtros{' removida(s)' if remove else ''}.")

def clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    s = re.sub(r"(The post|O post)\b.*$", "", s, flags=re.S)
    return re.sub(r"\s+", " ", s).strip()

def short(s, n=260):
    if len(s) <= n: return s
    return s[:n].rsplit(" ", 1)[0].rstrip(",;:.-–[ ") + "…"

def og_image(url):
    if "news.google.com" in url: return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        h = urllib.request.urlopen(req, timeout=10).read(300000).decode("utf-8", "ignore")
        m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', h) or \
            re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image', h)
        return html.unescape(m.group(1)) if m and m.group(1).startswith("http") else None
    except Exception: return None

def feed_image(e):
    for k in ("media_content", "media_thumbnail"):
        for m in e.get(k) or []:
            if m.get("url", "").startswith("http"): return m["url"]
    for l in e.get("links", []):
        if l.get("rel") == "enclosure" and l.get("type", "").startswith("image"): return l["href"]
    m = re.search(r'<img[^>]+src=["\'](https?://[^"\']+)', (e.get("content") or [{}])[0].get("value", "") + e.get("summary", ""))
    return m.group(1) if m else None

REMOVED = ROOT / "data" / "removidos.txt"   # links rejeitados/removidos: nunca reimportar

IMG = ROOT / "static" / "img"

def save_image(url, slug):
    """Baixa a imagem, converte para WebP (1200px e 480px). Retorna dict de front matter ou None."""
    if not url or not url.startswith("http"): return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": url})
        data = urllib.request.urlopen(req, timeout=20).read(15_000_000)
        im = Image.open(io.BytesIO(data)); im.load()
        if im.width < 300: return None
        im = im.convert("RGB"); IMG.mkdir(parents=True, exist_ok=True)
        big = im if im.width <= 1200 else im.resize((1200, round(im.height * 1200 / im.width)), Image.LANCZOS)
        big.save(IMG / f"{slug}.webp", "WEBP", quality=80, method=6)
        im.resize((480, round(im.height * 480 / im.width)), Image.LANCZOS).save(IMG / f"{slug}-480.webp", "WEBP", quality=78, method=6)
        return {"imagem": f"/static/img/{slug}.webp", "imagem_w": big.width, "imagem_h": big.height, "imagem_origem": url}
    except Exception as ex:
        print(f"  ! imagem falhou ({url[:60]}): {ex}"); return None

def editoria_image(ed):
    return {"imagem": f"/static/img/editoria/{ed}.webp", "imagem_w": 1200, "imagem_h": 630}

def img_fm(info, src_name):
    out = [f"imagem: {q(info['imagem'])}", f"imagem_w: {info['imagem_w']}", f"imagem_h: {info['imagem_h']}"]
    if info.get("imagem_origem"): out += [f"imagem_credito: {q(src_name)}", f"imagem_origem: {q(info['imagem_origem'])}"]
    return "\n".join(out)

def migrar():
    """Converte matérias antigas (imagem remota/vazia) para WebP local ou imagem da editoria."""
    for f in sorted(CONTENT.glob("*.md")):
        raw = f.read_text(encoding="utf-8"); _, fm_txt, body = raw.split("---", 2)
        fm = yaml.safe_load(fm_txt) or {}
        if str(fm.get("imagem", "")).startswith("/static/img/"): continue
        info = save_image(fm.get("imagem", ""), f.stem) or editoria_image(fm["editoria"])
        lines = [l for l in fm_txt.strip("\n").split("\n") if not l.startswith("imagem")]
        lines.insert(4, img_fm(info, fm.get("fonte", "")))
        f.write_text("---\n" + "\n".join(lines) + "\n---" + body, encoding="utf-8")
        print(f"~ {f.name}: {info['imagem']}")

def existing():
    links, titles = set(), set()
    if REMOVED.exists(): links |= {l.strip() for l in REMOVED.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}
    for f in CONTENT.glob("*.md"):
        fm = yaml.safe_load(f.read_text(encoding="utf-8").split("---", 2)[1]) or {}
        if fm.get("link"): links.add(fm["link"])
        titles.add(norm(fm.get("titulo", "")))
    return links, titles

def q(s): return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--max", type=int); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--migrar-imagens", action="store_true")
    ap.add_argument("--revisar", action="store_true", help="lista matérias publicadas que violam os filtros")
    ap.add_argument("--remover", action="store_true", help="com --revisar, apaga essas matérias")
    a = ap.parse_args()
    cfg = yaml.safe_load((ROOT / "feeds.yaml").read_text(encoding="utf-8"))
    if a.migrar_imagens: return migrar()
    if a.revisar: return revisar(cfg, a.remover)
    limit = a.max or cfg.get("max_por_execucao", 12); per = cfg.get("max_por_feed", 3)
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=cfg.get("max_idade_dias", 3))
    CONTENT.mkdir(exist_ok=True); links, titles = existing(); new = 0; erros = []
    for fd in cfg["feeds"]:
        if new >= limit: break
        try:
            raw = urllib.request.urlopen(urllib.request.Request(fd["url"], headers={"User-Agent": UA}), timeout=20).read()
            d = feedparser.parse(raw)
        except Exception as ex:
            print(f"! {fd['nome']}: erro {ex}"); erros.append({"feed": fd["nome"], "url": fd["url"], "erro": str(ex)[:120]}); continue
        if not d.entries: print(f"! {fd['nome']}: sem itens"); erros.append({"feed": fd["nome"], "url": fd["url"], "erro": "sem itens"}); continue
        got = 0
        for e in d.entries:
            if got >= fd.get("max", per) or new >= limit: break
            link, title = e.get("link", "").strip(), clean(e.get("title", ""))
            src_name = fd["nome"]; gn = "news.google.com" in fd["url"]
            if gn:
                st = (e.get("source") or {}).get("title")
                if st:
                    src_name = st
                    title = re.sub(r"\s+-\s+" + re.escape(st) + r"\s*$", "", title)
            if len(title) < 25 or title.endswith("|"): continue
            if not link or not title or link in links or norm(title) in titles: continue
            tp = e.get("published_parsed") or e.get("updated_parsed")
            when = dt.datetime(*tp[:6], tzinfo=dt.timezone.utc) if tp else dt.datetime.now(dt.timezone.utc)
            if when < cutoff: continue
            summ = "" if gn else clean(e.get("summary", ""))
            if len(summ) < 40 or norm(summ).startswith(norm(title)[:40]):
                summ = f"{title}. Notícia publicada por {src_name}."
            why = blocked(cfg, src_name, link, title, "" if summ.startswith(title) else summ, fd.get("confiavel", False))
            if why: print(f"  x {title[:70]} ({src_name}): {why}"); continue
            resumo = short(summ)
            ed = fd.get("editoria") or classify(title + " " + summ)
            when = when.astimezone(BRT).replace(microsecond=0)
            fn = CONTENT / f"{when:%Y-%m-%d}-{slugify(title)}.md"
            if fn.exists(): continue
            info = None if a.dry_run else save_image(feed_image(e) or og_image(link), fn.stem)
            info = info or editoria_image(ed)
            body = (f"---\ntitulo: {q(title)}\ndata: {when.isoformat()}\neditoria: {ed}\nresumo: {q(resumo)}\n"
                    f"{img_fm(info, src_name)}\nfonte: {q(src_name)}\nlink: {q(link)}\ngerado_por: fetch.py\n---\n"
                    f"{resumo}\n\n**[Leia na íntegra em {src_name} →]({link})**\n\n"
                    f"<small>Resumo automático a partir do feed público de {src_name}. Os direitos do conteúdo original pertencem à fonte.</small>\n")
            print(f"+ [{ed}] {title[:80]} ({src_name})")
            if not a.dry_run: fn.write_text(body, encoding="utf-8")
            links.add(link); titles.add(norm(title)); got += 1; new += 1
    print(f"{new} matéria(s) nova(s).")
    if not a.dry_run:
        import json
        (ROOT / "data" / "saude_coleta.json").write_text(json.dumps({"hora": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "novas": new, "erros": erros}, ensure_ascii=False, indent=1), encoding="utf-8")

if __name__ == "__main__": main()
