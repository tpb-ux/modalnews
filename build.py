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

THIN_MIN = 300  # páginas pSEO com menos palavras que isso saem do índice (noindex,follow) e do sitemap
THIN_FAMILIAS = ("/diesel/", "/rotas/", "/logistica/", "/aeroportos/", "/portos/", "/pedagios/", "/rodovias/", "/estados/", "/frete-minimo/", "/veiculos/", "/tipos-de-carga/", "/comparativos/", "/glossario/")
THIN = set()
ED_IMG = {"veiculos": BASE + "/static/img/editoria/transporte.webp", "resumo-semanal": BASE + "/static/img/editoria/mercado.webp"}
HUB_FAQ = {}  # path -> [(pergunta, resposta)]: FAQ injetado em páginas de índice/hub que não têm FAQ próprio

def _inject_faq(path, body, jsonld):
    fq = HUB_FAQ.get(path)
    if not fq or (jsonld and '"FAQPage"' in json.dumps(jsonld)): return body, jsonld
    from paginas import faq_block, faq_ld
    blk = f'<section class="faq-hub"><h2>Perguntas frequentes</h2>{faq_block(E, fq)}</section>'
    i = body.rfind("</article>")
    body = body[:i] + blk + body[i:] if i >= 0 else body + f'<div class="post">{blk}</div>'
    if not jsonld: jsonld = {"@context": "https://schema.org", "@graph": [faq_ld(fq)]}
    elif "@graph" in jsonld: jsonld = {**jsonld, "@graph": jsonld["@graph"] + [faq_ld(fq)]}
    else:
        j = {k: v for k, v in jsonld.items() if k != "@context"}; jsonld = {"@context": "https://schema.org", "@graph": [j, faq_ld(fq)]}
    return body, jsonld

def fit_title(t, n=65):
    """Encurta títulos longos sem cortar palavras: tira o sufixo da marca, depois o trecho após ':'."""
    for f in (lambda x: x.replace(f" | {CFG['site_name']}", ""), lambda x: x.replace(" hoje:", ":"), lambda x: x.split(":")[0].strip()):
        if len(t) <= n: break
        t = f(t)
    return t if len(t) <= n else t[:n - 1].rsplit(" ", 1)[0] + "…"

def fit_desc(d, n=160):
    return d if len(d) <= n else d[:n - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"

FAQ_PSEO = ("/diesel/", "/logistica/", "/rotas/", "/aeroportos/", "/portos/", "/pedagios/", "/rodovias/", "/estados/")
FAQ_HUBS = ("/estados/", "/diesel/estado/")  # hubs por estado mantêm o FAQ completo
FAQ_MAX_PSEO = 3  # regra de FAQ: nas pSEO só ficam até 3 perguntas cuja resposta traz dado da página (número); hubs e glossário mantêm ≥5
FAQ_STATS = {"pseo_paginas": 0, "pseo_faqs": 0, "pseo_removidas": 0}
_DET = re.compile(r'<details class="faq"[^>]*><summary><h3>(.*?)</h3></summary>.*?</details>', re.S)

def _faq_pseo(path, body, jsonld):
    if not (path.startswith(FAQ_PSEO) and path.count("/") >= 3) or path.startswith(FAQ_HUBS) or not jsonld: return body, jsonld
    graph = jsonld.get("@graph") if "@graph" in jsonld else [jsonld]
    fq = next((g for g in graph if isinstance(g, dict) and g.get("@type") == "FAQPage"), None)
    if not fq: return body, jsonld
    qs = fq["mainEntity"]; keep = [q for q in qs if re.search(r"\d", q["acceptedAnswer"]["text"])][:FAQ_MAX_PSEO]
    names = {E(q["name"]) for q in keep} | {q["name"] for q in keep}
    FAQ_STATS["pseo_paginas"] += 1; FAQ_STATS["pseo_faqs"] += len(keep); FAQ_STATS["pseo_removidas"] += len(qs) - len(keep)
    body = _DET.sub(lambda m: m.group(0) if m.group(1) in names else "", body)
    if keep: fq["mainEntity"] = keep
    else:
        body = re.sub(r'<h2[^>]*>Perguntas frequentes[^<]*</h2>', "", body)
        if "@graph" in jsonld: jsonld = {**jsonld, "@graph": [g for g in graph if g is not fq]}
        else: jsonld = None
    return body, jsonld

def page(title, desc, path, body, og_img=None, og_type="website", jsonld=None, robots=None):
    body, jsonld = _inject_faq(path, body, jsonld)
    body, jsonld = _faq_pseo(path, body, jsonld)
    title, desc = fit_title(title), fit_desc(desc)
    if jsonld:  # Article/NewsArticle sem imagem: usa a imagem social da página (rich results exigem image)
        for it in (jsonld.get("@graph") or [jsonld]):
            if isinstance(it, dict) and it.get("@type") in ("Article", "NewsArticle") and not it.get("image"):
                it["image"] = og_img or ED_IMG.get(path.split("/")[1]) or BASE + "/static/og-default.png"
    if not robots and path.startswith(THIN_FAMILIAS) and path.count("/") >= 3:
        nw = len(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>", " ", body, flags=re.S)).split())
        if nw < THIN_MIN: robots = "noindex,follow"; THIN.add(path)
    canon = BASE + path
    img = og_img or BASE + "/static/og-default.png"
    nav = "".join(f'<a href="/{s}/">{E(n)}</a>' for s, n in EDS.items())
    nav_ed = "".join(f'<a class="{"on" if path.startswith(f"/{s}/") else ""}" href="/{s}/">{E(n)}</a>' for s, n in EDS.items())
    ref_links = "".join(f'<a href="{u}">{n}</a>' for u, n in [("/diesel/", "Preço do diesel"), ("/frete-minimo/", "Frete mínimo"), ("/portos/", "Portos"), ("/rodovias/", "Rodovias"),
                        ("/guias/", "Guias"), ("/estados/", "Logística por estado"), ("/logistica/", "Logística por cidade"), ("/resumo-semanal/", "Resumo semanal"), ("/comparativos/", "Comparativos"), ("/veiculos/", "Veículos de carga"), ("/tipos-de-carga/", "Tipos de carga"), ("/glossario/ingles-portugues/", "Inglês × português"), ("/calculadoras/cubagem/", "Calculadora de cubagem"), ("/calculadoras/custo-diesel-viagem/", "Custo de diesel"), ("/siglas/", "Siglas"), ("/aeroportos/", "Aeroportos de carga"), ("/pedagios/", "Pedágios"), ("/rotas/", "Rotas de frete"), ("/utilidades/", "Utilidades"), ("/busca/", "Buscar")])
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
    ld += f'<script type="application/ld+json">{json.dumps(SITE_LD, ensure_ascii=False)}</script>'
    import qualidade
    rb = f'<meta name="robots" content="{robots or qualidade.INDEX_ROBOTS}">'
    vf = CFG.get("verificacao") or {}
    if True:
        rb += (f'<meta name="google-site-verification" content="{E(vf["google"])}">' if vf.get("google") else "") + (f'<meta name="msvalidate.01" content="{E(vf["bing"])}">' if vf.get("bing") else "")
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
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
<div><p class="fh">Editorias</p>{nav}</div><div><p class="fh">Referência</p><a href="/glossario/">Glossário de Logística</a><a href="/siglas/">Siglas</a><a href="/diesel/">Preço do diesel</a><a href="/frete-minimo/">Frete mínimo ANTT</a><a href="/portos/">Portos</a><a href="/rodovias/">Rodovias</a><a href="/estados/">Logística por estado</a><a href="/logistica/">Logística por cidade</a><a href="/resumo-semanal/">Resumo semanal</a><a href="/comparativos/">Comparativos</a><a href="/veiculos/">Veículos de carga</a><a href="/tipos-de-carga/">Tipos de carga</a><a href="/glossario/ingles-portugues/">Glossário inglês × português</a><a href="/guias/">Guias práticos</a><a href="/calculadoras/cubagem/">Calculadora de cubagem</a><a href="/calculadoras/custo-diesel-viagem/">Custo de diesel</a><a href="/links-uteis/">Links úteis</a></div>
<div><p class="fh">Institucional</p><a href="/sobre/">Sobre</a><a href="/expediente/">Expediente</a><a href="/contato/">Contato</a><a href="/termos/">Termos de uso</a><a href="/busca/">Buscar</a><a href="/politica-editorial/">Política editorial</a><a href="/metodologia/">Metodologia</a><a href="/correcoes/">Correções</a><a href="/privacidade/">Privacidade</a><a href="/rss.xml">Feed RSS</a></div></div>
<div class="wrap fbot">© {dt.date.today().year} {E(CFG['site_name'])} · Todos os direitos reservados</div></footer></body></html>"""

SITE_LD = {"@context": "https://schema.org", "@graph": [
    {"@type": "NewsMediaOrganization", "@id": BASE + "/#org", "name": CFG["site_name"], "url": BASE + "/", "logo": {"@type": "ImageObject", "url": BASE + CFG["publisher_logo"]},
     "publishingPrinciples": BASE + "/politica-editorial/", "correctionsPolicy": BASE + "/correcoes/", "actionableFeedbackPolicy": BASE + "/correcoes/",
     **({"sameAs": [r for r in CFG.get("empresa", {}).get("redes", []) if r]} if any(CFG.get("empresa", {}).get("redes", [])) else {}),
     **({"legalName": CFG["empresa"]["razao_social"], "taxID": CFG["empresa"]["cnpj"], "identifier": {"@type": "PropertyValue", "propertyID": "CNPJ", "value": CFG["empresa"]["cnpj"]},
         "address": {"@type": "PostalAddress", "streetAddress": CFG["empresa"]["endereco"]["logradouro"], "addressLocality": CFG["empresa"]["endereco"]["cidade"], "addressRegion": CFG["empresa"]["endereco"]["uf"],
                     "postalCode": CFG["empresa"]["endereco"]["cep"], "addressCountry": "BR"}} if CFG.get("empresa") else {}),
     **({"email": CFG["empresa"]["email"]} if CFG.get("empresa", {}).get("email") else {})},
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

def sec(title_small, title_big, link=None, tag="h2"):
    t = f'<span>{E(title_small)}</span><strong>{E(title_big)}</strong>'
    return f'<{tag} class="st">{f"<a href={chr(34)}{link}{chr(34)}>{t}</a>" if link else t}</{tag}>'

def write(path, txt):
    import relacionados
    txt = relacionados.inject(path, txt, E)
    f = OUT / path.lstrip("/"); f = f / "index.html" if path.endswith("/") else f
    txt = re.sub(r'(href|src)="/(?!/)', lambda m: f'{m.group(1)}="{PREFIX}/', txt)
    f.parent.mkdir(parents=True, exist_ok=True); f.write_text(txt, encoding="utf-8")

def main():
    import fetch, extras_seo, qualidade as Q
    nmig = fetch.migrar_cards()
    AUT = extras_seo.autores(sys.modules[__name__])
    posts = [p for p in load() if extras_seo.publicavel(p, AUT)]
    for p in posts:
        if p.get("tipo") == "analise": p["url"] = f"/analises/{p['slug']}/"
    if OUT.exists(): shutil.rmtree(OUT)
    shutil.copytree(ROOT / "static", OUT / "static")
    shutil.copy(ROOT / "static" / "favicon.ico", OUT / "favicon.ico")
    if CFG.get("cname"): (OUT / "CNAME").write_text(CFG["cname"].strip() + "\n")
    own = lambda p: not p["imagem"].startswith("/static/img/editoria/")
    recent48 = lambda p: (dt.datetime.now(dt.timezone.utc) - p["data"]) < dt.timedelta(hours=48)
    import faq_hubs; faq_hubs.build(sys.modules[__name__], posts)
    import relacionados
    hub_urls = relacionados.build(sys.modules[__name__], posts)
    import paginas3
    hub_urls += paginas3.build(sys.modules[__name__])
    import paginas7, paginas8
    me_ = sys.modules[__name__]
    v1_urls = paginas7.portos(me_) + paginas7.aeroportos(me_) + paginas7.pedagios(me_) + paginas7.diesel_antt(me_) + paginas7.utilidades(me_) + paginas8.rotas(me_) + paginas8.expediente(me_)
    paginas8.busca_page(me_)
    import paginas4
    cmp_urls = paginas4.build(sys.modules[__name__])
    import paginas5
    vei_urls = paginas5.build(sys.modules[__name__])
    import paginas6
    res_urls = paginas6.build(sys.modules[__name__], posts)
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
    body = f'<h1 class="sr-only">{E(CFG["site_name"])}: notícias de logística, transporte e supply chain</h1>' + body
    write("/", page(f"{CFG['site_name']}: notícias de logística, transporte e supply chain", CFG["tagline"] + ". Glossário, preço do diesel por cidade (ANP) e calculadoras.", "/", body,
                    jsonld=itemlist(posts)))
    for s, n in EDS.items():
        ps = [p for p in posts if p["editoria"] == s]
        inner = "".join(card(p, h="h2") for p in ps) or "<p>Nenhuma matéria ainda.</p>"
        fts = sorted({p.get("fonte", "") for p in ps if p.get("fonte")})
        dsc = f"Notícias de {n.lower()} na logística: resumos de {', '.join(fts[:3]) if fts else 'portais do setor'} com link para a fonte, atualizados a cada 30 minutos."
        write(f"/{s}/", page(f"Notícias de {n} na logística | {CFG['site_name']}", dsc[:160], f"/{s}/",
                             f'<section class="blk">{sec("Editoria", n, tag="h1")}<div class="grid">{inner}</div></section>', jsonld=itemlist(ps)))
    import glossario
    gl_urls, interlink, gl_lastmod, terms = glossario.build(sys.modules["__main__"] if "__main__" in sys.modules and hasattr(sys.modules["__main__"], "page") else sys.modules[__name__], posts)
    me0 = sys.modules[__name__]
    for p in posts:
        if p.get("html"):  # links para o glossário no texto da matéria (fora do link da fonte)
            head, sep, tail = p["html"].partition("<p><strong>")
            p["html"] = interlink(head, budget=3) + sep + tail
        ld = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": p["titulo"][:110],
              "description": p.get("resumo", ""), "image": [{"@type": "ImageObject", "url": BASE + p["imagem"], "width": p.get("imagem_w", 1200), "height": p.get("imagem_h", 630)}],
              "datePublished": p["data"].isoformat(), "dateModified": (p.get("atualizado") or p["data"]).isoformat() if hasattr(p.get("atualizado") or p["data"], "isoformat") else str(p.get("atualizado")),
              "articleSection": EDS[p["editoria"]], "mainEntityOfPage": BASE + p["url"],
              "author": extras_seo.person(me0, AUT[p["autor"]]) if p.get("autor") in AUT else {"@type": "Organization", "name": CFG["site_name"], "url": BASE + "/"},
              **({"editor": extras_seo.person(me0, AUT[p["revisado_por"]])} if p.get("revisado_por") in AUT else {}),
              "publisher": {**org, "logo": {"@type": "ImageObject", "url": BASE + CFG["publisher_logo"]}}}
        b = f"""<article class="post"><div class="kick"><a href="/{p['editoria']}/">{E(EDS[p['editoria']])}</a></div>
<h1>{E(p['titulo'])}</h1><p class="meta">{('Por <a href="/autores/' + p['autor'] + '/">' + E(AUT[p['autor']]['nome']) + '</a> · ') if p.get('autor') in AUT else ''}Publicado em <time datetime="{p['data'].isoformat()}">{fmt(p['data'])}</time>{(' · Atualizado em ' + fmt(p['atualizado'])) if isinstance(p.get('atualizado'), dt.datetime) else ''}
{(' · Fonte: ' + E(p['fonte'])) if p.get('fonte') else ''}</p>{'' if p.get('gerado_por') else '<p><strong>' + E(p.get('resumo','')) + '</strong></p>'}
<figure class="cover">{img(p, "cover", "(max-width: 800px) 100vw, 760px", True)}{(f'<figcaption>Imagem: <a href="{E(p["link"])}" rel="nofollow noopener" target="_blank">{E(p["imagem_credito"])}</a></figcaption>' if p.get("link") else f'<figcaption>Imagem: {E(p["imagem_credito"])}</figcaption>') if p.get("imagem_credito") else ''}</figure>{p['html']}</article>"""
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
    paginas7.portos_index(me)
    ds_urls, ds_lastmod = paginas.diesel(sys.modules[__name__])
    calc_urls = paginas.calculadoras(sys.modules[__name__])
    conf_urls = paginas.confianca(sys.modules[__name__], len(terms))
    sig_urls = paginas.siglas(sys.modules[__name__], terms)
    me_x = sys.modules[__name__]
    dados_urls, dados_lm = extras_seo.dados(me_x); aut_urls = extras_seo.paginas_autores(me_x)
    an = [p for p in posts if p.get("tipo") == "analise"]
    if an:
        write("/analises/", page(f"Análises | {CFG['site_name']}", "Análises próprias do Modal News com dados oficiais de diesel, frete, rotas e infraestrutura, assinadas e revisadas.", "/analises/",
                                 f'<section class="blk">{sec("Conteúdo próprio", "Análises", tag="h1")}<div class="grid">{"".join(card(x, h="h2") for x in an)}</div></section>', jsonld=itemlist(an)))
    conf_urls = conf_urls + dados_urls + aut_urls + (["/analises/"] if an else [])
    own = [p for p in posts if not p.get("gerado_por")]
    today = dt.date.today().isoformat()
    def smfile(name, urls, lastmod={}, images=None):
        urls = [u for u in urls if u not in THIN]
        rows = "".join(f"<url><loc>{BASE}{u}</loc>" + (f"<lastmod>{lastmod[u]}</lastmod>" if u in lastmod else "")
                       + (f"<image:image><image:loc>{BASE}{images[u]}</image:loc></image:image>" if images and u in images else "") + "</url>" for u in urls)
        (OUT / name).write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">' + rows + "</urlset>", encoding="utf-8")
        return name
    latest = max([p["data"] for p in posts], default=dt.datetime.now(dt.timezone.utc)).date().isoformat()
    files = [smfile("sitemap-paginas.xml", ["/"] + [f"/{s}/" for s in EDS] + conf_urls + calc_urls + sig_urls, {"/": latest, **{f"/{s}/": latest for s in EDS}}),
             smfile("sitemap-glossario.xml", gl_urls, gl_lastmod), smfile("sitemap-diesel.xml", ds_urls, ds_lastmod),
             smfile("sitemap-frete-minimo.xml", fm_urls, fm_lm), smfile("sitemap-entidades.xml", pt_urls + rd_urls, {**pt_lm, **rd_lm}), smfile("sitemap-guias.xml", gu_urls, gu_lm), smfile("sitemap-estados.xml", hub_urls), smfile("sitemap-comparativos.xml", cmp_urls), smfile("sitemap-veiculos-cargas.xml", vei_urls), smfile("sitemap-resumo-semanal.xml", res_urls), smfile("sitemap-infraestrutura.xml", v1_urls)]
    if own: files.append(smfile("sitemap-artigos.xml", [p["url"] for p in own], {p["url"]: p["data"].date().isoformat() for p in own}, {p["url"]: p["imagem"] for p in own}))
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<sitemap><loc>{BASE}/{f}</loc></sitemap>" for f in files) + "</sitemapindex>", encoding="utf-8")
    items = "".join(f"<item><title>{E(p['titulo'])}</title><link>{BASE}{p['url']}</link><guid>{BASE}{p['url']}</guid><pubDate>{format_datetime(p['data'])}</pubDate><category>{E(EDS[p['editoria']])}</category><description>{E(p.get('resumo',''))}</description></item>" for p in posts[:30])
    (OUT / "rss.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>{E(CFG["site_name"])}</title><link>{BASE}/</link><description>{E(CFG["tagline"])}</description><language>pt-br</language>{items}</channel></rss>', encoding="utf-8")
    (OUT / "robots.txt").write_text(Q.robots_txt(BASE, disallow=("/saude.json", "/*?utm_")))
    nnews = extras_seo.sitemap_noticias(me_x, posts)
    if nnews: files.append("sitemap-noticias.xml")
    # ---- unicidade: páginas pSEO com pouco texto próprio saem do índice e do sitemap
    qc = CFG.get("qualidade") or {}
    fams = {}; cand = set()
    for f in OUT.rglob("index.html"):
        u = "/" + f.parent.relative_to(OUT).as_posix() + "/"
        if not (u.startswith(THIN_FAMILIAS) and u.count("/") >= 3): continue
        h = f.read_text(encoding="utf-8")
        if 'content="noindex' not in h: cand.add(u)
        fams.setdefault(u.split("/")[1], {})[u] = h
    qstats, abaixo = Q.unicidade(fams, corte=qc.get("corte_unicidade", 0.15), cortes=qc.get("cortes_unicidade"), avaliar=cand)
    for u in abaixo:
        f = OUT / u.strip("/") / "index.html"; f.write_text(Q.set_robots(f.read_text(encoding="utf-8"), "noindex,follow"), encoding="utf-8"); THIN.add(u)
    for sm in OUT.glob("sitemap-*.xml"):
        t = sm.read_text(encoding="utf-8"); t2 = re.sub(r"<url><loc>" + re.escape(BASE) + r"(/[^<]*)</loc>.*?</url>", lambda m: "" if m.group(1) in abaixo else m.group(0), t)
        if t2 != t: sm.write_text(t2, encoding="utf-8")
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<sitemap><loc>{BASE}/{f}</loc></sitemap>" for f in files) + "</sitemapindex>", encoding="utf-8")
    fams_all = {k: v for k, v in fams.items()}
    sim = Q.similaridade({k: {u: h for u, h in v.items() if u in cand and u not in abaixo} for k, v in fams_all.items()})
    erros_rede, pct_rede = Q.anti_rede(OUT, CFG.get("rede_dominios") or [])
    if erros_rede:
        for e in erros_rede: print("ERRO:", e)
        sys.exit("ERRO: regra anti-rede violada")
    me_x._qualidade = {"unicidade": qstats, "noindex_por_unicidade": len(abaixo), "similaridade_jaccard5": sim, "faq_pseo": dict(FAQ_STATS), "rede_links_pct": pct_rede, "sitemap_noticias": nnews}
    print(f"Unicidade: {len(abaixo)} página(s) abaixo do corte em noindex · similaridade média por família: " + ", ".join(f"{k}={v}" for k, v in sorted(sim.items())))
    col = json.loads((ROOT / "data" / "saude_coleta.json").read_text()) if (ROOT / "data" / "saude_coleta.json").exists() else {}
    paginas.extras(sys.modules[__name__], {"build": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "ultima_coleta": col.get("hora"), "feeds_com_erro": col.get("erros", []),
        "materias": len(posts), "termos": len(terms), "paginas_indexaveis": sum(len(x) for x in (gl_urls, ds_urls, calc_urls, conf_urls, sig_urls, fm_urls, pt_urls, rd_urls, gu_urls)) + 1 + len(EDS),
        "diesel_semana": max(ds_lastmod.values(), default=None)})
    gen_llms(); extras_seo.llms(me_x, ["/diesel/", "/logistica/", "/rotas/", "/frete-minimo/", "/portos/", "/aeroportos/", "/rodovias/", "/pedagios/", "/estados/", "/glossario/", "/siglas/", "/comparativos/", "/veiculos/", "/tipos-de-carga/", "/guias/", "/calculadoras/cubagem/", "/calculadoras/custo-diesel-viagem/", "/resumo-semanal/", "/utilidades/"])
    nb = paginas8.busca_index(me)
    if CFG.get("indexnow_key"): (OUT / f"{CFG['indexnow_key']}.txt").write_text(CFG["indexnow_key"])
    import indexnow; indexnow.diff(me)
    print(f"Busca: {nb} páginas no índice")
    if THIN: print(f"Qualidade: {len(THIN)} página(s) pSEO com menos de {THIN_MIN} palavras em noindex: " + ", ".join(sorted(THIN)[:10]))
    broken = linkcheck()
    if broken:
        for u, (n, src) in sorted(broken.items(), key=lambda x: -x[1][0])[:30]: print(f"LINK QUEBRADO {u} ({n}x, ex.: {src})")
        sys.exit(f"ERRO: {len(broken)} destinos internos quebrados")
    import saude; saude.build(sys.modules[__name__], posts)  # só roda com 0 links quebrados
    print(f"OK: {len(posts)} matérias -> {OUT}")

def _meta(u):
    f = OUT / u.strip("/") / "index.html"
    if not f.exists(): return "", ""
    h = f.read_text(encoding="utf-8")
    t = re.search(r"<title>(.*?)</title>", h, re.S); d = re.search(r'<meta name="description" content="(.*?)"', h)
    return html.unescape(t.group(1).strip()) if t else "", html.unescape(d.group(1)) if d else ""

def gen_llms():
    """llms.txt e llms-full.txt gerados a partir dos sitemaps: todas as seções indexáveis, sem lista fixa."""
    urls = []
    for f in sorted(OUT.glob("sitemap-*.xml")): urls += re.findall(r"<loc>(.*?)</loc>", f.read_text(encoding="utf-8"))
    urls = [u[len(BASE):] or "/" for u in urls]
    sec = {}
    for u in urls: sec.setdefault("/" + u.strip("/").split("/")[0] + "/" if u != "/" else "/", []).append(u)
    t0, d0 = _meta("/")
    out = [f"# {CFG['site_name']}", "", f"> {d0 or CFG['tagline']}", "",
           f"Site estático em português (pt-BR), {len(urls)} páginas indexáveis. Dados de fontes oficiais citadas em cada página; notícias de terceiros são resumos com link para a fonte e não são indexadas.", "",
           "## Seções", ""]
    full = list(out[:5]) + ["## Todas as páginas indexáveis", ""]
    inst = []
    for hub, us in sorted(sec.items(), key=lambda x: -len(x[1])):
        if hub == "/": continue
        t, d = _meta(hub)
        if len(us) == 1 and us[0] == hub: inst.append(f"- [{t or hub}]({BASE}{hub}): {d}"); continue
        out.append(f"- [{t or hub}]({BASE}{hub}): {d} ({len(us)} páginas)")
        for u in [x for x in us if x != hub][:3]:
            tt, _ = _meta(u); out.append(f"  - [{tt or u}]({BASE}{u})")
    out += ["", "## Páginas institucionais e ferramentas", ""] + inst + ["", f"Lista completa: {BASE}/llms-full.txt · Sitemap: {BASE}/sitemap.xml", ""]
    for u in urls:
        tt, dd = _meta(u); full.append(f"- [{tt or u}]({BASE}{u}): {dd}")
    (OUT / "llms.txt").write_text("\n".join(out), encoding="utf-8")
    (OUT / "llms-full.txt").write_text("\n".join(full) + "\n", encoding="utf-8")

HREF = re.compile(r"""href=["']([^"'#?]+)""")
def linkcheck():
    """Falha o build se algum link interno apontar para página/arquivo inexistente."""
    bad = {}
    for f in OUT.rglob("*.html"):
        src = "/" + f.relative_to(OUT).as_posix().replace("index.html", "")
        for h in HREF.findall(f.read_text(encoding="utf-8")):
            if h.startswith(BASE): h = h[len(BASE):] or "/"
            if not h.startswith("/") or h.startswith("//"): continue
            t = OUT / h.lstrip("/")
            if (t / "index.html").exists() or t.is_file(): continue
            n, s0 = bad.get(h, (0, src)); bad[h] = (n + 1, s0)
    return bad

if __name__ == "__main__": main()
