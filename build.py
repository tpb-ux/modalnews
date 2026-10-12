#!/usr/bin/env python3
"""Gerador estático do Modal News. Uso: python build.py"""
import datetime as dt, html, json, re, shutil
from pathlib import Path
from email.utils import format_datetime
import markdown, yaml

ROOT = Path(__file__).parent
CFG = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
OUT, BASE = ROOT / "public", CFG["base_url"].rstrip("/")
from urllib.parse import urlparse
PREFIX = urlparse(BASE).path.rstrip("/")
EDS = {e["slug"]: e["nome"] for e in CFG["editorias"]}
E = html.escape

def slugify(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

def load():
    posts = []
    for f in sorted((ROOT / "content").glob("*.md")):
        raw = f.read_text(encoding="utf-8")
        _, fm, body = raw.split("---", 2)
        m = yaml.safe_load(fm)
        d = m["data"]
        if isinstance(d, str): d = dt.datetime.fromisoformat(d)
        if not isinstance(d, dt.datetime): d = dt.datetime.combine(d, dt.time(8))
        if d.tzinfo is None: d = d.replace(tzinfo=dt.timezone(dt.timedelta(hours=-3)))
        if m["editoria"] not in EDS: raise SystemExit(f"{f.name}: editoria inválida {m['editoria']}")
        slug = m.get("slug") or slugify(f.stem)
        posts.append(dict(m, data=d, slug=slug, url=f"/{m['editoria']}/{slug}/",
                          html=markdown.markdown(body, extensions=["extra"])))
    return sorted(posts, key=lambda p: p["data"], reverse=True)

def fmt(d): return d.strftime("%d/%m/%Y %H:%M")

def page(title, desc, path, body, og_img=None, og_type="website", jsonld=None):
    canon = BASE + path
    img = og_img or BASE + "/static/og-default.png"
    nav = "".join(f'<a href="/{s}/">{E(n)}</a>' for s, n in EDS.items())
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}">
<link rel="canonical" href="{canon}"><link rel="stylesheet" href="/static/style.css">
<link rel="alternate" type="application/rss+xml" title="{E(CFG['site_name'])}" href="/rss.xml">
<meta property="og:site_name" content="{E(CFG['site_name'])}"><meta property="og:locale" content="pt_BR">
<meta property="og:type" content="{og_type}"><meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{canon}">
<meta property="og:image" content="{E(img)}"><meta name="twitter:card" content="summary_large_image">{ld}
</head><body><header class="top"><div class="wrap"><a class="logo" href="/">Modal<span>News</span></a>
<div class="tag">{E(CFG['tagline'])}</div></div></header><nav class="ed"><div class="wrap"><a href="/">Início</a>{nav}</div></nav>
<main class="wrap">{body}</main><footer><div class="wrap">© {dt.date.today().year} {E(CFG['site_name'])} · modalnews.com.br · <a href="/rss.xml">RSS</a></div></footer></body></html>"""

def card(p, cls="", h="h3"):
    return f"""<div class="card {cls}"><a href="{p['url']}"><img src="{E(p.get('imagem',''))}" alt="" loading="lazy">
<div class="in"><div class="kick">{E(EDS[p['editoria']])}</div><{h}>{E(p['titulo'])}</{h}><p>{E(p.get('resumo',''))}</p></div></a></div>"""

def write(path, txt):
    f = OUT / path.lstrip("/"); f = f / "index.html" if path.endswith("/") else f
    txt = re.sub(r'(href|src)="/(?!/)', lambda m: f'{m.group(1)}="{PREFIX}/', txt)
    f.parent.mkdir(parents=True, exist_ok=True); f.write_text(txt, encoding="utf-8")

def main():
    posts = load()
    if OUT.exists(): shutil.rmtree(OUT)
    shutil.copytree(ROOT / "static", OUT / "static")
    if CFG.get("cname"): (OUT / "CNAME").write_text(CFG["cname"].strip() + "\n")
    dest = [p for p in posts if p.get("destaque")] or posts[:1]
    main_p = dest[0]; side = [p for p in posts if p is not main_p][:2]
    body = f'<div class="hero">{card(main_p,"main","h2")}<div class="side">{"".join(card(p) for p in side)}</div></div>'
    for s, n in EDS.items():
        ps = [p for p in posts if p["editoria"] == s][:4]
        if ps: body += f'<section class="blk"><h2 class="st"><a href="/{s}/">{E(n)}</a></h2><div class="grid">{"".join(card(p) for p in ps)}</div></section>'
    org = {"@type": "NewsMediaOrganization", "name": CFG["site_name"], "url": BASE}
    write("/", page(f"{CFG['site_name']} — {CFG['tagline']}", CFG["tagline"], "/", body,
                    jsonld={"@context": "https://schema.org", **org}))
    for s, n in EDS.items():
        ps = [p for p in posts if p["editoria"] == s]
        inner = "".join(card(p) for p in ps) or "<p>Nenhuma matéria ainda.</p>"
        write(f"/{s}/", page(f"{n} — {CFG['site_name']}", f"Notícias de {n} no {CFG['site_name']}", f"/{s}/",
                             f'<section class="blk"><h2 class="st">{E(n)}</h2><div class="grid">{inner}</div></section>'))
    for p in posts:
        ld = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": p["titulo"][:110],
              "description": p.get("resumo", ""), "image": [p.get("imagem")] if p.get("imagem") else [],
              "datePublished": p["data"].isoformat(), "dateModified": p["data"].isoformat(),
              "articleSection": EDS[p["editoria"]], "mainEntityOfPage": BASE + p["url"],
              "author": {"@type": "Organization", "name": CFG["site_name"]},
              "publisher": {**org, "logo": {"@type": "ImageObject", "url": BASE + CFG["publisher_logo"]}}}
        b = f"""<article class="post"><div class="kick"><a href="/{p['editoria']}/">{E(EDS[p['editoria']])}</a></div>
<h1>{E(p['titulo'])}</h1><p class="meta">Publicado em <time datetime="{p['data'].isoformat()}">{fmt(p['data'])}</time>
{(' · Fonte: ' + E(p['fonte'])) if p.get('fonte') else ''}</p><p><strong>{E(p.get('resumo',''))}</strong></p>
{f'<img class="cover" src="{E(p["imagem"])}" alt="">' if p.get('imagem') else ''}{p['html']}</article>"""
        write(p["url"], page(f"{p['titulo']} — {CFG['site_name']}", p.get("resumo", ""), p["url"], b,
                             p.get("imagem"), "article", ld))
    now = dt.datetime.now(dt.timezone.utc)
    urls = ["/"] + [f"/{s}/" for s in EDS] + [p["url"] for p in posts]
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<url><loc>{BASE}{u}</loc></url>" for u in urls) + "</urlset>", encoding="utf-8")
    recent = [p for p in posts if now - p["data"] < dt.timedelta(days=2)] or posts[:1]
    (OUT / "news-sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">'
        + "".join(f"<url><loc>{BASE}{p['url']}</loc><news:news><news:publication><news:name>{E(CFG['site_name'])}</news:name><news:language>pt</news:language></news:publication><news:publication_date>{p['data'].isoformat()}</news:publication_date><news:title>{E(p['titulo'])}</news:title></news:news></url>" for p in recent)
        + "</urlset>", encoding="utf-8")
    items = "".join(f"<item><title>{E(p['titulo'])}</title><link>{BASE}{p['url']}</link><guid>{BASE}{p['url']}</guid><pubDate>{format_datetime(p['data'])}</pubDate><category>{E(EDS[p['editoria']])}</category><description>{E(p.get('resumo',''))}</description></item>" for p in posts[:30])
    (OUT / "rss.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>{E(CFG["site_name"])}</title><link>{BASE}/</link><description>{E(CFG["tagline"])}</description><language>pt-br</language>{items}</channel></rss>', encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\nSitemap: {BASE}/news-sitemap.xml\n")
    print(f"OK: {len(posts)} matérias -> {OUT}")

if __name__ == "__main__": main()
