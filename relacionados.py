"""Interlinking central: monta, para cada página, um bloco "Veja também" com entidades ligadas por geografia e tema,
e gera hubs por estado (/estados/<uf>/). Tudo derivado dos dados do site (ANP, IBGE, ANTT, ANTAQ/MPor, glossário)."""
import json, re, unicodedata, yaml
from paginas import UFN, norm, crumbs_html, crumbs_ld, brl, dbr, faq_block, faq_ld

GL_TOOLS = {  # verbete -> ferramentas/páginas de dados relacionadas
    "frete-minimo": [("/frete-minimo/", "Tabela de frete mínimo ANTT"), ("/guias/como-calcular-frete-minimo-antt/", "Guia: como calcular o frete mínimo")],
    "frete": [("/frete-minimo/", "Frete mínimo ANTT"), ("/calculadoras/custo-diesel-viagem/", "Custo de diesel por viagem")],
    "carga-lotacao": [("/frete-minimo/", "Frete mínimo ANTT")],
    "ct-e": [("/guias/como-emitir-cte/", "Guia: como emitir CT-e")], "mdf-e": [("/guias/como-emitir-mdfe/", "Guia: como emitir MDF-e")],
    "danfe": [("/guias/como-emitir-cte/", "Guia: como emitir CT-e")], "rntrc": [("/guias/como-emitir-cte/", "Guia: como emitir CT-e"), ("/frete-minimo/", "Frete mínimo ANTT")],
    "peso-cubado": [("/calculadoras/cubagem/", "Calculadora de cubagem")], "cubagem": [("/calculadoras/cubagem/", "Calculadora de cubagem")],
    "vale-pedagio": [("/rodovias/", "Rodovias federais e pedágios")], "modal-rodoviario": [("/rodovias/", "Rodovias federais"), ("/diesel/", "Preço do diesel")],
    "incoterms": [("/guias/como-exportar/", "Guia: como exportar")], "fob": [("/guias/como-exportar/", "Guia: como exportar")], "cif": [("/guias/como-exportar/", "Guia: como exportar")],
    "exw": [("/guias/como-exportar/", "Guia: como exportar")], "fca": [("/guias/como-exportar/", "Guia: como exportar")], "du-e": [("/guias/como-exportar/", "Guia: como exportar")],
    "siscomex": [("/guias/como-exportar/", "Guia: como exportar")], "despacho-aduaneiro": [("/guias/como-exportar/", "Guia: como exportar"), ("/portos/", "Portos brasileiros")],
    "ncm": [("/guias/como-exportar/", "Guia: como exportar")],
    "teu": [("/portos/", "Portos brasileiros")], "cabotagem": [("/portos/", "Portos brasileiros")], "demurrage": [("/portos/", "Portos brasileiros")],
    "modal-aquaviario": [("/portos/", "Portos brasileiros")], "armador": [("/portos/", "Portos brasileiros")], "free-time": [("/portos/", "Portos brasileiros")],
    "custo-logistico": [("/diesel/", "Preço do diesel"), ("/frete-minimo/", "Frete mínimo ANTT")], "modal": [("/rodovias/", "Rodovias"), ("/portos/", "Portos")],
}

def build(B, posts):
    E, BASE = B.E, B.BASE; ROOT = B.ROOT; REL = {}
    def add(path, items):
        seen = set(); out = []
        for u, t in items:
            if u and u != path and u not in seen: seen.add(u); out.append((u, t))
        if out: REL[path] = REL.get(path, []) + out
    # ---------- dados
    db = json.loads((ROOT / "data" / "diesel.json").read_text(encoding="utf-8")); ibge = json.loads((ROOT / "data" / "ibge_municipios.json").read_text(encoding="utf-8"))
    cur = db["semanas"][max(db["semanas"])]
    cities = {}
    for k, v in cur["municipios"].items():
        nome, uf = k.split("|"); m = ibge.get(f"{norm(nome)}|{uf}"); disp = m["nome"] if m else nome.title()
        cities[f"{norm(disp)}|{uf}"] = {"nome": disp, "uf": uf, "url": f"/diesel/{B.slugify(disp)}-{uf.lower()}/", "s10": (v.get("s10") or {}).get("media"), "postos": (v.get("s10") or v.get("s500"))["postos"]}
    rod = json.loads((ROOT / "data" / "rodovias.json").read_text(encoding="utf-8"))["rodovias"]
    portos = yaml.safe_load((ROOT / "data" / "portos.yaml").read_text(encoding="utf-8"))["portos"]
    pidx = {p["slug"]: p for p in portos}
    ROD_UF = {}; ROD_CITY = {}
    for br, r in rod.items():
        for uf in r["ufs"]: ROD_UF.setdefault(uf, []).append(br)
        for p in r["pracas"]: ROD_CITY.setdefault(f"{norm(p['municipio'])}|{p['uf']}", set()).add(br)
    P_UF = {}
    for p in portos: P_UF.setdefault(p["uf"], []).append(p)
    hub = lambda uf: (f"/estados/{uf.lower()}/", f"Logística em {UFN[uf]}")
    rlink = lambda br: (f"/rodovias/{br.lower()}/", br)
    plink = lambda p: (f"/portos/{p['slug']}/", p["nome"])
    by_uf = {}
    for c in cities.values(): by_uf.setdefault(c["uf"], []).append(c)
    # ---------- diesel cidade
    for key, c in cities.items():
        uf = c["uf"]; it = [hub(uf), (f"/diesel/estado/{uf.lower()}/", f"Diesel em {UFN[uf]}")]
        it += [rlink(b) for b in sorted(ROD_CITY.get(key, []))] + [plink(p) for p in P_UF.get(uf, []) if norm(p["cidade"]) == key.split("|")[0]]
        it += [rlink(b) for b in sorted(ROD_UF.get(uf, []))[:4]] + [plink(p) for p in P_UF.get(uf, [])[:3]]
        it += [("/frete-minimo/", "Frete mínimo ANTT"), ("/calculadoras/custo-diesel-viagem/", "Custo de diesel por viagem")]
        add(c["url"], it)
    # ---------- diesel estado
    for uf in cur["estados"]:
        add(f"/diesel/estado/{uf.lower()}/", [hub(uf)] + [rlink(b) for b in sorted(ROD_UF.get(uf, []))] + [plink(p) for p in P_UF.get(uf, [])] + [("/frete-minimo/", "Frete mínimo ANTT")])
    # ---------- rodovias
    for br, r in rod.items():
        cs = []
        for p in r["pracas"]:
            c = cities.get(f"{norm(p['municipio'])}|{p['uf']}")
            if c and c not in cs: cs.append(c)
        it = [hub(uf) for uf in r["ufs"]] + [(c["url"], f"Diesel em {c['nome']} ({c['uf']})") for c in cs[:8]]
        it += [(f"/diesel/estado/{uf.lower()}/", f"Diesel em {UFN[uf]}") for uf in r["ufs"]] + [plink(p) for uf in r["ufs"] for p in P_UF.get(uf, [])[:2]]
        it += [("/frete-minimo/", "Frete mínimo ANTT"), ("/glossario/vale-pedagio/", "O que é vale-pedágio")]
        add(f"/rodovias/{br.lower()}/", it)
    # ---------- portos
    for p in portos:
        uf = p["uf"]; c = cities.get(f"{norm(p['cidade'])}|{uf}")
        it = [hub(uf)] + ([(c["url"], f"Diesel em {c['nome']}")] if c else []) + [plink(x) for x in P_UF.get(uf, []) if x is not p]
        it += [rlink(b) for b in sorted(ROD_UF.get(uf, []))[:4]] + [("/guias/como-exportar/", "Guia: como exportar"), ("/glossario/teu/", "O que é TEU"), ("/glossario/cabotagem/", "O que é cabotagem")]
        add(f"/portos/{p['slug']}/", it)
    # ---------- frete mínimo, guias, calculadoras
    fm_common = [("/guias/como-calcular-frete-minimo-antt/", "Guia: como calcular o frete mínimo"), ("/diesel/", "Preço do diesel hoje"), ("/rodovias/", "Rodovias e pedágios"),
                 ("/calculadoras/custo-diesel-viagem/", "Custo de diesel por viagem"), ("/glossario/frete-minimo/", "O que é frete mínimo"), ("/glossario/carga-lotacao/", "O que é carga lotação")]
    fmj = json.loads((ROOT / "data" / "frete_minimo.json").read_text(encoding="utf-8"))
    for carga in fmj["tabelas"]["A"]["cargas"]: add(f"/frete-minimo/{B.slugify(carga)}/", [("/frete-minimo/", "Calculadora de frete mínimo")] + fm_common)
    add("/frete-minimo/", fm_common)
    G = yaml.safe_load((ROOT / "data" / "guias.yaml").read_text(encoding="utf-8"))
    gl = {"como-emitir-cte": ["ct-e", "danfe", "rntrc", "mdf-e"], "como-emitir-mdfe": ["mdf-e", "ct-e", "vale-pedagio"], "como-calcular-frete-minimo-antt": ["frete-minimo", "carga-lotacao", "vale-pedagio"],
          "como-exportar": ["incoterms", "fob", "du-e", "siscomex", "despacho-aduaneiro", "ncm"]}
    tools = {"como-emitir-cte": [("/guias/como-emitir-mdfe/", "Guia: como emitir MDF-e")], "como-emitir-mdfe": [("/guias/como-emitir-cte/", "Guia: como emitir CT-e"), ("/rodovias/", "Rodovias")],
             "como-calcular-frete-minimo-antt": [("/frete-minimo/", "Calculadora de frete mínimo"), ("/diesel/", "Preço do diesel")], "como-exportar": [("/portos/", "Portos brasileiros"), ("/glossario/incoterms/", "Incoterms")]}
    for g in G: add(f"/guias/{g['slug']}/", tools.get(g["slug"], []) + [(f"/glossario/{s}/", f"Glossário: {s.upper() if len(s) <= 5 else s.replace('-', ' ')}") for s in gl.get(g["slug"], [])])
    add("/calculadoras/cubagem/", [("/glossario/peso-cubado/", "O que é peso cubado"), ("/glossario/carga-fracionada/", "Carga fracionada"), ("/frete-minimo/", "Frete mínimo ANTT")])
    add("/calculadoras/custo-diesel-viagem/", [("/diesel/", "Preço do diesel por cidade"), ("/frete-minimo/", "Frete mínimo ANTT"), ("/rodovias/", "Rodovias e pedágios")])
    # ---------- glossário
    for s, L in GL_TOOLS.items(): add(f"/glossario/{s}/", L)
    # ---------- notícias: geografia e tema citados no título/resumo
    names = {uf: [UFN[uf]] for uf in UFN}
    big = sorted([c for c in cities.values() if c["postos"] >= 12 and len(c["nome"]) >= 5], key=lambda c: -len(c["nome"]))
    for p in posts:
        txt = f"{p['titulo']} {p.get('resumo', '')}"; it = []
        for br in rod:
            if re.search(rf"\bBR[- ]?{br[3:]}\b", txt): it.append(rlink(br))
        for x in portos:
            sh = re.sub(r"^Porto (de|do|da) ", "", x["nome"])
            if re.search(rf"\b(porto|portos) (de|do|da) {re.escape(sh)}\b", txt, re.I): it.append(plink(x))
        for uf, ns in names.items():
            if any(re.search(rf"\b{re.escape(n)}\b", txt) for n in ns) or re.search(rf"\({uf}\)", txt): it.append(hub(uf))
        for c in big:
            if re.search(rf"\b{re.escape(c['nome'])}\b", txt): it.append((c["url"], f"Diesel em {c['nome']}")); break
        low = txt.lower()
        if "diesel" in low or "combustív" in low: it.append(("/diesel/", "Preço do diesel hoje"))
        if "frete" in low: it.append(("/frete-minimo/", "Frete mínimo ANTT"))
        if any(w in low for w in ("export", "import", "comércio exterior")): it.append(("/guias/como-exportar/", "Guia: como exportar"))
        if "porto" in low: it.append(("/portos/", "Portos brasileiros"))
        add(p["url"], it[:8])
    # ---------- hubs por estado
    hub_urls = []
    for uf in sorted(UFN):
        u = f"/estados/{uf.lower()}/"; cs = sorted(by_uf.get(uf, []), key=lambda c: -c["postos"]); st = cur["estados"].get(uf, {})
        rds = sorted(ROD_UF.get(uf, [])); pts = P_UF.get(uf, [])
        npr = sum(1 for br in rds for x in rod[br]["pracas"] if x["uf"] == uf)
        news = [p for p in posts if UFN[uf] in p["titulo"] + p.get("resumo", "") or f"({uf})" in p["titulo"] + p.get("resumo", "")][:5]
        s10 = (st.get("s10") or {}).get("media")
        lead = f"Painel de logística de {UFN[uf]} com dados oficiais: preço do diesel em {len(cs)} cidades pesquisadas pela ANP" + (f" (S10 a {brl(s10)}/l em média na semana de {dbr(cur['ini'])} a {dbr(cur['fim'])})" if s10 else "") + \
               (f", {len(rds)} rodovia(s) federal(is) concedida(s) com {npr} praças de pedágio" if rds else "") + (f" e {len(pts)} porto(s) público(s)" if pts else "") + "."
        fq = []
        if s10: fq.append((f"Qual o preço do diesel em {UFN[uf]}?", f"Na semana de {dbr(cur['ini'])} a {dbr(cur['fim'])}, o diesel S10 custou em média {brl(s10)} por litro em {UFN[uf]}, segundo a ANP. Veja os preços por cidade na página de diesel do estado."))
        if rds: fq.append((f"Quais rodovias federais têm pedágio em {UFN[uf]}?", f"Segundo o cadastro de praças de pedágio da ANTT, as rodovias federais concedidas com praças em {UFN[uf]} são: {', '.join(rds)}, com {npr} praças ativas no estado."))
        if pts: fq.append((f"Quais são os portos públicos de {UFN[uf]}?", f"O Modal News acompanha em {UFN[uf]}: {', '.join(p['nome'] for p in pts)}, com dados oficiais da ANTAQ e do Ministério de Portos e Aeroportos."))
        blocks = f"<h2>Diesel em {UFN[uf]}</h2><p><a href='/diesel/estado/{uf.lower()}/'>Preços do diesel em {UFN[uf]} por cidade</a>.</p><div class='chips small'>" + "".join(f'<a class="chip" href="{c["url"]}">{E(c["nome"])}</a>' for c in cs) + "</div>"
        if rds: blocks += f"<h2>Rodovias federais concedidas</h2><div class='chips'>" + "".join(f'<a class="chip" href="/rodovias/{b.lower()}/">{b}</a>' for b in rds) + "</div>"
        if pts: blocks += f"<h2>Portos</h2><div class='chips'>" + "".join(f'<a class="chip" href="/portos/{p["slug"]}/">{E(p["nome"])}</a>' for p in pts) + "</div>"
        if news: blocks += "<h2>Notícias</h2><ul class='rel-news'>" + "".join(f'<li><a href="{p["url"]}">{E(p["titulo"])}</a></li>' for p in news) + "</ul>"
        blocks += "<h2>Ferramentas</h2><div class='chips'><a class='chip' href='/frete-minimo/'>Frete mínimo ANTT</a><a class='chip' href='/calculadoras/custo-diesel-viagem/'>Custo de diesel por viagem</a><a class='chip' href='/calculadoras/cubagem/'>Cubagem</a></div>"
        body = f"""<article class="post data">{crumbs_html(E, [("Início", "/"), ("Estados", "/estados/"), (UFN[uf], u)])}<h1>Logística em {UFN[uf]} ({uf})</h1><p class="snippet">{E(lead)}</p>{blocks}
{('<h2>Perguntas frequentes</h2>' + faq_block(E, fq)) if fq else ''}</article>"""
        pts_n = (1 if s10 else 0) + len(cs) // 3 + len(rds) + len(pts)
        idx = pts_n >= 3
        ld = {"@context": "https://schema.org", "@graph": [{"@type": "CollectionPage", "name": f"Logística em {UFN[uf]}", "url": BASE + u, "about": {"@type": "State", "name": UFN[uf]}}] + ([faq_ld(fq)] if fq else []) + [crumbs_ld(BASE, [("Início", "/"), ("Estados", "/estados/"), (UFN[uf], u)])]}
        B.write(u, B.page(f"Logística em {UFN[uf]}: diesel, rodovias e portos", lead[:152].rsplit(" ", 1)[0] + "…" if len(lead) > 155 else lead, u, body, jsonld=ld, robots=None if idx else "noindex,follow"))
        if idx: hub_urls.append(u)
    u = "/estados/"
    body = f'<article class="post">{crumbs_html(E, [("Início", "/"), ("Estados", u)])}<h1>Logística por estado</h1><p class="snippet">Escolha um estado para ver preço do diesel por cidade, rodovias federais com pedágio, portos públicos e notícias, com dados oficiais da ANP, ANTT e ANTAQ.</p><div class="chips">' + "".join(f'<a class="chip" href="/estados/{x.lower()}/">{UFN[x]}</a>' for x in sorted(UFN, key=lambda x: UFN[x])) + "</div></article>"
    B.write(u, B.page("Logística por estado: diesel, rodovias e portos", "Painéis de logística dos 27 estados brasileiros com diesel por cidade (ANP), rodovias com pedágio (ANTT) e portos (ANTAQ).", u, body, jsonld={"@context": "https://schema.org", "@graph": [crumbs_ld(BASE, [("Início", "/"), ("Estados", u)])]}))
    B.REL = REL
    print(f"Interlinking: {len(REL)} páginas com 'Veja também', {len(hub_urls)} hubs de estado indexáveis")
    return [u] + hub_urls

def inject(path, html, E):
    """Chamado pelo write(): insere o bloco Veja também antes de </article>."""
    import sys
    B = sys.modules.get("build") or sys.modules.get("__main__")
    items = getattr(B, "REL", {}).get(path)
    if not items or "</article>" not in html or 'class="relbox"' in html: return html
    box = '<aside class="relbox" aria-label="Veja também"><h2>Veja também</h2><ul>' + "".join(f'<li><a href="{u}">{E(t)}</a></li>' for u, t in items[:12]) + "</ul></aside>"
    i = html.rfind("</article>"); return html[:i] + box + html[i:]
