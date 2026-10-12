#!/usr/bin/env python3
"""Gerador estático do Modal News. Uso: python build.py"""
import sys, datetime as dt, html, json, re, shutil
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
        if not str(m.get("imagem", "")).startswith("/static/img/"):
            m.update(imagem=f"/static/img/editoria/{m['editoria']}.webp", imagem_w=1200, imagem_h=630); m.pop("imagem_credito", None)
        posts.append(dict(m, data=d, slug=slug, url=f"/{m['editoria']}/{slug}/",
                          html=markdown.markdown(body, extensions=["extra"])))
    return sorted(posts, key=lambda p: p["data"], reverse=True)

def fmt(d): return d.strftime("%d/%m/%Y %H:%M")

import hashlib
CSSV = hashlib.md5((ROOT / "static" / "style.css").read_bytes()).hexdigest()[:10]

def page(title, desc, path, body, og_img=None, og_type="website", jsonld=None, robots=None):
    canon = BASE + path
    img = og_img or BASE + "/static/og-default.png"
    nav = "".join(f'<a href="/{s}/">{E(n)}</a>' for s, n in EDS.items())
    nav_ed = "".join(f'<a class="{"on" if path.startswith(f"/{s}/") else ""}" href="/{s}/">{E(n)}</a>' for s, n in EDS.items())
    ref_links = "".join(f'<a href="{u}">{n}</a>' for u, n in [("/diesel/", "Preço do diesel"), ("/frete-minimo/", "Frete mínimo"), ("/portos/", "Portos"), ("/rodovias/", "Rodovias"),
                        ("/guias/", "Guias"), ("/estados/", "Logística por estado"), ("/logistica/", "Logística por cidade"), ("/calculadoras/cubagem/", "Calculadora de cubagem"), ("/calculadoras/custo-diesel-viagem/", "Custo de diesel"), ("/siglas/", "Siglas")])
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
    ld += f'<script type="application/ld+json">{json.dumps(SITE_LD, ensure_ascii=False)}</script>'
    rb = f'<meta name="robots" content="{robots}">' if robots else ""
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title>{rb}<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{canon}"><link rel="stylesheet" href="/static/style.css?v={CSSV}">
<link rel="alternate" type="application/rss+xml" title="{E(CFG['site_name'])}" href="/rss.xml">
<meta property="og:site_name" content="{E(CFG['site_name'])}"><meta property="og:locale" content="pt_BR">
<meta property="og:type" content="{og_type}"><meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{canon}">
<meta property="og:image" content="{E(img)}"><meta name="twitter:card" content="summary_large_image">{ld}
</head><body><header class="top"><div class="wrap hrow"><a class="logo" href="/"><img src="/static/logo.svg" alt="{E(CFG['site_name'])}" width="220" height="44"></a>
<div class="tag">{E(CFG['tagline'])}</div><button class="burger" id="mn-btn" aria-label="Abrir menu" aria-expanded="false" aria-controls="mn-drawer"><span></span><span></span><span></span></button></div></header>
<nav class="ed" aria-label="Editorias"><div class="wrap"><a class="{'pill' if path == '/' else ''}" href="/">Início</a>{nav_ed}<a class="{'on' if path.startswith('/glossario/') else ''}" href="/glossario/">Glossário</a>
<details class="dd"><summary>Referência</summary><div class="ddm">{ref_links}</div></details></div></nav>
<div class="drawer" id="mn-drawer" hidden><div class="dpanel" role="dialog" aria-modal="true" aria-label="Menu"><button class="dclose" id="mn-close" aria-label="Fechar menu">×</button>
<p class="fh">Editorias</p><a href="/">Início</a>{nav}<p class="fh">Referência</p><a href="/glossario/">Glossário</a>{ref_links}</div></div>
<script>(function(){{var b=document.getElementById('mn-btn'),d=document.getElementById('mn-drawer'),c=document.getElementById('mn-close');
function o(x){{d.hidden=!x;b.setAttribute('aria-expanded',x);document.body.style.overflow=x?'hidden':'';if(x)c.focus();else b.focus()}}
b.onclick=function(){{o(d.hidden)}};c.onclick=function(){{o(false)}};d.onclick=function(e){{if(e.target===d)o(false)}};
document.addEventListener('keydown',function(e){{if(e.key==='Escape'&&!d.hidden)o(false)}});
var a=document.querySelector('nav.ed a.on,nav.ed a.pill');if(a&&a.scrollIntoView&&innerWidth<860)a.scrollIntoView({{inline:'center',block:'nearest'}});
document.addEventListener('click',function(e){{var x=document.querySelector('details.dd[open]');if(x&&!x.contains(e.target))x.open=false}})}})();</script>
<main class="wrap">{body}</main><footer><div class="wrap fgrid"><div><img src="/static/logo.svg" alt="" width="180" height="36" class="flogo"><p>{E(CFG['tagline'])}</p></div>
<div><p class="fh">Editorias</p>{nav}</div><div><p class="fh">Referência</p><a href="/glossario/">Glossário de Logística</a><a href="/siglas/">Siglas</a><a href="/diesel/">Preço do diesel</a><a href="/frete-minimo/">Frete mínimo ANTT</a><a href="/portos/">Portos</a><a href="/rodovias/">Rodovias</a><a href="/estados/">Logística por estado</a><a href="/logistica/">Logística por cidade</a><a href="/guias/">Guias práticos</a><a href="/calculadoras/cubagem/">Calculadora de cubagem</a><a href="/calculadoras/custo-diesel-viagem/">Custo de diesel</a><a href="/links-uteis/">Links úteis</a></div>
<div><p class="fh">Institucional</p><a href="/sobre/">Sobre</a><a href="/politica-editorial/">Política editorial</a><a href="/metodologia/">Metodologia</a><a href="/correcoes/">Correções</a><a href="/privacidade/">Privacidade</a><a href="/rss.xml">Feed RSS</a></div></div>
<div class="wrap fbot">© {dt.date.today().year} {E(CFG['site_name'])} · Todos os direitos reservados</div></footer></body></html>"""

SITE_LD = {"@context": "https://schema.org", "@graph": [
    {"@type": "NewsMediaOrganization", "@id": BASE + "/#org", "name": CFG["site_name"], "url": BASE + "/", "logo": {"@type": "ImageObject", "url": BASE + CFG["publisher_logo"]},
     "publishingPrinciples": BASE + "/politica-editorial/", "correctionsPolicy": BASE + "/correcoes/", "actionableFeedbackPolicy": BASE + "/correcoes/",
     **({"sameAs": CFG["redes"]} if CFG.get("redes") else {}), **({"taxID": CFG["cnpj"]} if CFG.get("cnpj") else {})},
    {"@type": "WebSite", "@id": BASE + "/#site", "name": CFG["site_name"], "url": BASE + "/", "inLanguage": "pt-BR", "publisher": {"@id": BASE + "/#org"}}]}

def itemlist(ps):
    return {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": BASE + p["url"], "name": p["titulo"]} for i, p in enumerate(ps[:20])]}

def img(p, cls="", sizes="(max-width: 760px) 100vw, 300px", priority=False):
    src = p["imagem"]; w, h = p.get("imagem_w", 1200), p.get("imagem_h", 630)
    thumb = src[:-5] + "-480.webp"
    load = 'fetchpriority="high" decoding="async"' if priority else 'loading="lazy" decoding="async"'
    return (f'<img{f" class={chr(34)}{cls}{chr(34)}" if cls else ""} src="{src}" srcset="{PREFIX}{thumb} 480w, {PREFIX}{src} {w}w" '
            f'sizes="{sizes}" width="{w}" height="{h}" alt="{E(p["titulo"])}" {load}>')

def card(p, cls="", h="h3"):
    return f"""<div class="card {cls}"><a href="{p['url']}"><div class="thumb">{img(p)}<span class="badge">{E(EDS[p['editoria']])}</span></div>
<div class="in"><{h}>{E(p['titulo'])}</{h}><p>{E(p.get('resumo',''))}</p><span class="more">Ler na íntegra</span></div></a></div>"""

def hero(p):
    return f"""<a class="hero-main" href="{p['url']}"><div class="htxt"><div class="kick">Destaque <span>• {p['data'].strftime('%d/%m/%Y')}</span></div>
<h2>{E(p['titulo'])}</h2><p>{E(p.get('resumo',''))}</p></div>{img(p, sizes="(max-width: 860px) 100vw, 660px", priority=True)}</a>"""

def mini(p):
    return f"""<a class="mini" href="{p['url']}">{img(p, sizes="96px")}<div><span class="kick">{E(EDS[p['editoria']])}</span><h3>{E(p['titulo'])}</h3></div></a>"""

def sec(title_small, title_big, link=None):
    t = f'<span>{E(title_small)}</span><strong>{E(title_big)}</strong>'
    return f'<h2 class="st">{f"<a href={chr(34)}{link}{chr(34)}>{t}</a>" if link else t}</h2>'

def write(path, txt):
    import relacionados
    txt = relacionados.inject(path, txt, E)
    f = OUT / path.lstrip("/"); f = f / "index.html" if path.endswith("/") else f
    txt = re.sub(r'(href|src)="/(?!/)', lambda m: f'{m.group(1)}="{PREFIX}/', txt)
    f.parent.mkdir(parents=True, exist_ok=True); f.write_text(txt, encoding="utf-8")

def main():
    posts = load()
    if OUT.exists(): shutil.rmtree(OUT)
    shutil.copytree(ROOT / "static", OUT / "static")
    shutil.copy(ROOT / "static" / "favicon.ico", OUT / "favicon.ico")
    if CFG.get("cname"): (OUT / "CNAME").write_text(CFG["cname"].strip() + "\n")
    own = lambda p: not p["imagem"].startswith("/static/img/editoria/")
    recent48 = lambda p: (dt.datetime.now(dt.timezone.utc) - p["data"]) < dt.timedelta(hours=48)
    import relacionados
    hub_urls = relacionados.build(sys.modules[__name__], posts)
    import paginas3
    hub_urls += paginas3.build(sys.modules[__name__])
    pri = CFG.get("destaque_prioritario")
    dest = ([p for p in posts if p.get("destaque")] or [p for p in posts if own(p) and pri and p.get("fonte") == pri and recent48(p)][:1]
            or [p for p in posts if own(p)][:1] or posts[:1])
    body = ""
    if dest:
        main_p = dest[0]; side = [p for p in posts if p is not main_p][:4]
        body = f'<div class="hero">{hero(main_p)}<div class="side">{"".join(mini(p) for p in side)}</div></div>'
    for s, n in EDS.items():
        ps = [p for p in posts if p["editoria"] == s][:4]
        if ps: body += f'<section class="blk">{sec("As últimas em", n, f"/{s}/")}<div class="grid">{"".join(card(p) for p in ps)}</div></section>'
    org = {"@type": "NewsMediaOrganization", "@id": BASE + "/#org", "name": CFG["site_name"], "url": BASE}
    body += '<section class="blk refbox"><h2 class="st"><span>Referência</span><strong>Ferramentas e dados</strong></h2><div class="chips"><a class="chip" href="/glossario/">Glossário de Logística</a><a class="chip" href="/siglas/">Siglas</a><a class="chip" href="/diesel/">Preço do diesel por cidade</a><a class="chip" href="/frete-minimo/">Frete mínimo ANTT</a><a class="chip" href="/portos/">Portos</a><a class="chip" href="/rodovias/">Rodovias</a><a class="chip" href="/guias/">Guias</a><a class="chip" href="/calculadoras/cubagem/">Calculadora de cubagem</a><a class="chip" href="/calculadoras/custo-diesel-viagem/">Custo de diesel por viagem</a></div></section>'
    write("/", page(f"{CFG['site_name']}: notícias de logística, transporte e supply chain", CFG["tagline"] + ". Glossário, preço do diesel por cidade (ANP) e calculadoras.", "/", body,
                    jsonld=itemlist(posts)))
    for s, n in EDS.items():
        ps = [p for p in posts if p["editoria"] == s]
        inner = "".join(card(p) for p in ps) or "<p>Nenhuma matéria ainda.</p>"
        write(f"/{s}/", page(f"{n} — {CFG['site_name']}", f"Notícias de {n} no {CFG['site_name']}", f"/{s}/",
                             f'<section class="blk">{sec("Editoria", n)}<div class="grid">{inner}</div></section>', jsonld=itemlist(ps)))
    import glossario
    gl_urls, interlink, gl_lastmod, terms = glossario.build(sys.modules["__main__"] if "__main__" in sys.modules and hasattr(sys.modules["__main__"], "page") else sys.modules[__name__], posts)
    for p in posts:
        if p.get("html"):  # links para o glossário no texto da matéria (fora do link da fonte)
            head, sep, tail = p["html"].partition("<p><strong>")
            p["html"] = interlink(head, budget=3) + sep + tail
        ld = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": p["titulo"][:110],
              "description": p.get("resumo", ""), "image": [{"@type": "ImageObject", "url": BASE + p["imagem"], "width": p.get("imagem_w", 1200), "height": p.get("imagem_h", 630)}],
              "datePublished": p["data"].isoformat(), "dateModified": p["data"].isoformat(),
              "articleSection": EDS[p["editoria"]], "mainEntityOfPage": BASE + p["url"],
              "author": {"@type": "Organization", "name": CFG["site_name"]},
              "publisher": {**org, "logo": {"@type": "ImageObject", "url": BASE + CFG["publisher_logo"]}}}
        b = f"""<article class="post"><div class="kick"><a href="/{p['editoria']}/">{E(EDS[p['editoria']])}</a></div>
<h1>{E(p['titulo'])}</h1><p class="meta">Publicado em <time datetime="{p['data'].isoformat()}">{fmt(p['data'])}</time>
{(' · Fonte: ' + E(p['fonte'])) if p.get('fonte') else ''}</p>{'' if p.get('gerado_por') else '<p><strong>' + E(p.get('resumo','')) + '</strong></p>'}
<figure class="cover">{img(p, "cover", "(max-width: 800px) 100vw, 760px", True)}{f'<figcaption>Imagem: {E(p["imagem_credito"])}</figcaption>' if p.get("imagem_credito") else ''}</figure>{p['html']}</article>"""
        write(p["url"], page(f"{p['titulo']} — {CFG['site_name']}", p.get("resumo", ""), p["url"], b,
                             BASE + p["imagem"], "article", ld, robots="noindex,follow" if p.get("gerado_por") else None))
    rd = yaml.safe_load((ROOT / "data" / "redirects.yaml").read_text()) if (ROOT / "data" / "redirects.yaml").exists() else {}
    live = {p["url"] for p in posts}
    for old, new in rd.items():
        if old in live: continue
        write(old, f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="robots" content="noindex"><link rel="canonical" href="{BASE}{new}"><meta http-equiv="refresh" content="0; url={new}"><title>Página movida</title></head><body><p>Esta notícia foi removida. <a href="{new}">Ver a editoria</a>.</p></body></html>')
    import paginas, paginas2
    me = sys.modules[__name__]; me._posts = posts; me._interlink = interlink
    fm_urls, fm_lm = paginas2.frete_minimo(me); pt_urls, pt_lm = paginas2.portos(me)
    rd_urls, rd_lm = paginas2.rodovias(me); gu_urls, gu_lm = paginas2.guias(me)
    ds_urls, ds_lastmod = paginas.diesel(sys.modules[__name__])
    calc_urls = paginas.calculadoras(sys.modules[__name__])
    conf_urls = paginas.confianca(sys.modules[__name__], len(terms))
    sig_urls = paginas.siglas(sys.modules[__name__], terms)
    own = [p for p in posts if not p.get("gerado_por")]
    today = dt.date.today().isoformat()
    def smfile(name, urls, lastmod={}, images=None):
        rows = "".join(f"<url><loc>{BASE}{u}</loc>" + (f"<lastmod>{lastmod[u]}</lastmod>" if u in lastmod else "")
                       + (f"<image:image><image:loc>{BASE}{images[u]}</image:loc></image:image>" if images and u in images else "") + "</url>" for u in urls)
        (OUT / name).write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">' + rows + "</urlset>", encoding="utf-8")
        return name
    latest = max([p["data"] for p in posts], default=dt.datetime.now(dt.timezone.utc)).date().isoformat()
    files = [smfile("sitemap-paginas.xml", ["/"] + [f"/{s}/" for s in EDS] + conf_urls + calc_urls + sig_urls, {"/": latest, **{f"/{s}/": latest for s in EDS}}),
             smfile("sitemap-glossario.xml", gl_urls, gl_lastmod), smfile("sitemap-diesel.xml", ds_urls, ds_lastmod),
             smfile("sitemap-frete-minimo.xml", fm_urls, fm_lm), smfile("sitemap-entidades.xml", pt_urls + rd_urls, {**pt_lm, **rd_lm}), smfile("sitemap-guias.xml", gu_urls, gu_lm), smfile("sitemap-estados.xml", hub_urls)]
    if own: files.append(smfile("sitemap-artigos.xml", [p["url"] for p in own], {p["url"]: p["data"].date().isoformat() for p in own}, {p["url"]: p["imagem"] for p in own}))
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<sitemap><loc>{BASE}/{f}</loc></sitemap>" for f in files) + "</sitemapindex>", encoding="utf-8")
    items = "".join(f"<item><title>{E(p['titulo'])}</title><link>{BASE}{p['url']}</link><guid>{BASE}{p['url']}</guid><pubDate>{format_datetime(p['data'])}</pubDate><category>{E(EDS[p['editoria']])}</category><description>{E(p.get('resumo',''))}</description></item>" for p in posts[:30])
    (OUT / "rss.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>{E(CFG["site_name"])}</title><link>{BASE}/</link><description>{E(CFG["tagline"])}</description><language>pt-br</language>{items}</channel></rss>', encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /saude.json\nDisallow: /*?utm_\n\nSitemap: {BASE}/sitemap.xml\n")
    col = json.loads((ROOT / "data" / "saude_coleta.json").read_text()) if (ROOT / "data" / "saude_coleta.json").exists() else {}
    paginas.extras(sys.modules[__name__], {"build": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "ultima_coleta": col.get("hora"), "feeds_com_erro": col.get("erros", []),
        "materias": len(posts), "termos": len(terms), "paginas_indexaveis": sum(len(x) for x in (gl_urls, ds_urls, calc_urls, conf_urls, sig_urls, fm_urls, pt_urls, rd_urls, gu_urls)) + 1 + len(EDS),
        "diesel_semana": max(ds_lastmod.values(), default=None)})
    print(f"OK: {len(posts)} matérias -> {OUT}")

if __name__ == "__main__": main()
