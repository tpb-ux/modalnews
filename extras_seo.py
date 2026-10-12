"""SEO/GEO: datasets abertos (/dados/ + CSV), autores (Person, campos vazios ficam ocultos), seção de análises
(conteúdo próprio, só publica com revisão), sitemap de notícias e llms.txt enxuto. Sem IA."""
import csv, datetime as dt, io, json, re
from pathlib import Path
import yaml

LICENCA = ("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/deed.pt-br")

# ------------------------------------------------------------------ autores
def autores(B):
    f = B.ROOT / "data" / "autores.yaml"
    lst = (yaml.safe_load(f.read_text(encoding="utf-8")) or {}).get("autores", []) if f.exists() else []
    return {a["slug"]: a for a in lst if a.get("slug") and (a.get("nome") or "").strip()}  # sem nome = oculto

def person(B, a):
    p = {"@type": "Person", "@id": f"{B.BASE}/autores/{a['slug']}/#pessoa", "name": a["nome"], "url": f"{B.BASE}/autores/{a['slug']}/"}
    if a.get("cargo"): p["jobTitle"] = a["cargo"]
    if a.get("foto"): p["image"] = B.BASE + a["foto"]
    sa = [x for x in a.get("sameAs") or [] if x]
    if sa: p["sameAs"] = sa
    p["worksFor"] = {"@id": B.BASE + "/#org"}
    return p

def paginas_autores(B):
    au = autores(B); urls = []
    if not au: return urls  # estrutura pronta; nada é publicado enquanto os campos estiverem vazios
    E = B.E
    for a in au.values():
        u = f"/autores/{a['slug']}/"
        b = (f'<article class="post"><h1>{E(a["nome"])}</h1>' + (f'<p class="meta">{E(a["cargo"])}</p>' if a.get("cargo") else "")
             + (f'<p>{E(a["bio"])}</p>' if a.get("bio") else "") + "".join(f'<p><a href="{E(x)}" rel="me noopener" target="_blank">{E(x)}</a></p>' for x in a.get("sameAs") or [] if x) + "</article>")
        B.write(u, B.page(f"{a['nome']} | {B.CFG['site_name']}", (a.get("bio") or f"{a['nome']}, {a.get('cargo', 'autor')} do {B.CFG['site_name']}.")[:155], u, b,
                          jsonld={"@context": "https://schema.org", "@type": "ProfilePage", "mainEntity": person(B, a)})); urls.append(u)
    b = '<article class="post"><h1>Autores e editores</h1><ul>' + "".join(f'<li><a href="/autores/{a["slug"]}/">{E(a["nome"])}</a>{(" · " + E(a["cargo"])) if a.get("cargo") else ""}</li>' for a in au.values()) + "</ul></article>"
    B.write("/autores/", B.page(f"Autores | {B.CFG['site_name']}", f"Quem escreve e revisa o conteúdo próprio do {B.CFG['site_name']}: jornalistas, editores e revisores.", "/autores/", b)); urls.append("/autores/")
    return urls

# ------------------------------------------------------------------ análises (conteúdo próprio com revisão)
def publicavel(p, au):
    """Análise só vai ao ar com status aprovado, autor e revisor cadastrados (fluxo: drafts/ -> revisão -> content/)."""
    if p.get("tipo") != "analise": return True
    ok = p.get("status") == "aprovado" and p.get("autor") in au and p.get("revisado_por") in au and "[[REVIS" not in p.get("html", "")
    if not ok: print(f"Análise retida (sem aprovação/autor/revisor cadastrados): {p.get('titulo', '')[:70]}")
    return ok

# ------------------------------------------------------------------ dados abertos
def _csv(path, head, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(head); w.writerows(rows)
    return len(rows)

def dados(B):
    D = B.ROOT / "data"; out = B.OUT / "dados"; E = B.E; BASE = B.BASE; sets = []
    db = json.loads((D / "diesel.json").read_text(encoding="utf-8")); w = sorted(db["semanas"])[-1]; c = db["semanas"][w]
    rows = []; ibge = json.loads((D / "ibge_municipios.json").read_text(encoding="utf-8"))
    for k, v in sorted(c["municipios"].items()):
        mun, uf = k.split("|"); s10, s500 = v.get("s10") or {}, v.get("s500") or {}; ib = ibge.get(k) or {}
        rows.append([c["ini"], c["fim"], uf, ib.get("ibge", ""), ib.get("nome") or mun.title(), s10.get("media"), s10.get("min"), s10.get("max"), s10.get("postos"), s500.get("media"), s500.get("min"), s500.get("max"), s500.get("postos")])
    n = _csv(out / "diesel-municipios.csv", ["semana_ini", "semana_fim", "uf", "codigo_ibge", "municipio", "s10_media", "s10_min", "s10_max", "s10_postos", "s500_media", "s500_min", "s500_max", "s500_postos"], rows)
    sets.append(("diesel-municipios", "Preço do diesel S10 e S500 por município (semana mais recente)", f"Média, mínimo, máximo e número de postos por município na semana de {"/".join(reversed(c["ini"].split("-")))} a {"/".join(reversed(c["fim"].split("-")))}.", n,
                 "ANP, Levantamento de Preços de Combustíveis (dados abertos, semanal)", "https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/levantamento-de-precos-de-combustiveis-ultimas-semanas-pesquisadas",
                 "Agregamos o arquivo semanal oficial por município (nome normalizado + UF). S500 corresponde ao produto 'óleo diesel' (B S500). Municípios sem posto pesquisado na semana ficam fora.", c["fim"]))
    R = json.loads((D / "rotas.json").read_text(encoding="utf-8"))
    rows = [[r["a"]["nome"], r["a"]["uf"], r["b"].get("porto_nome") or r["b"]["nome"], r["b"]["uf"], r["km"], r["min"], r.get("linha_reta"), len(r["pracas"]), "; ".join(f"{p['br']} {p['nome']}" for p in r["pracas"])] for r in R["rotas"]]
    n = _csv(out / "rotas-frete.csv", ["origem", "uf_origem", "destino", "uf_destino", "km_estrada", "minutos_estimados", "km_linha_reta", "pracas_federais", "pracas"], rows)
    sets.append(("rotas-frete", "Rotas rodoviárias: distância, tempo e pedágios federais", "Distância por estrada (OSRM), tempo estimado sem paradas, linha reta e praças de pedágio federais no traçado.", n,
                 "OSRM sobre OpenStreetMap (© colaboradores do OpenStreetMap, ODbL); praças: ANTT dados abertos", "https://www.openstreetmap.org/copyright",
                 "Rota calculada entre os centroides IBGE dos municípios. Praça entra quando está a até 250 m do traçado. Pedágios estaduais não estão incluídos. Derivado de dados ODbL: a redistribuição mantém a atribuição ao OpenStreetMap.", None))
    fm = json.loads((D / "frete_minimo.json").read_text(encoding="utf-8")); rows = []
    for tab, t in fm["tabelas"].items():
        for carga, cv in (t.get("cargas") or {}).items():
            for eixo in sorted(cv.get("ccd", {}), key=lambda x: int(x)):
                rows.append([fm["ato"].get("nome"), tab, carga, eixo, cv["ccd"][eixo], cv.get("cc", {}).get(eixo)])
    n = _csv(out / "frete-minimo-coeficientes.csv", ["ato", "tabela", "tipo_de_carga", "eixos", "ccd_r_por_km", "cc_r_carga_descarga"], rows)
    sets.append(("frete-minimo-coeficientes", "Coeficientes do piso mínimo de frete da ANTT", "CCD (R$/km) e CC (R$) por tabela, tipo de carga e número de eixos, do ato vigente.", n,
                 fm["ato"].get("nome", "ANTT"), fm["ato"].get("url", "https://www.gov.br/antt"), "Transcrição direta das tabelas do ato vigente. Piso = km × CCD + CC, sem pedágio.", None))
    hoje = dt.date.today().isoformat(); E_ = E
    cards_h = ""; graph = []
    for slug, nome, desc, n, fonte, furl, metodo, mod in sets:
        cards_h += (f'<section class="blk" id="{slug}"><h2>{E_(nome)}</h2><p>{E_(desc)}</p><dl class="deflist"><dt>Arquivo</dt><dd><a href="/dados/{slug}.csv">{slug}.csv</a> ({n} linhas, UTF-8)</dd>'
                    f'<dt>Fonte original</dt><dd><a href="{E_(furl)}" target="_blank" rel="noopener">{E_(fonte)}</a></dd><dt>Método</dt><dd>{E_(metodo)}</dd>'
                    f'<dt>Licença</dt><dd><a href="{LICENCA[1]}" target="_blank" rel="noopener">{LICENCA[0]}</a> para a nossa compilação; cite "Modal News" e a fonte original.</dd><dt>Atualizado em</dt><dd>{mod or hoje}</dd></dl></section>')
        graph.append({"@type": "Dataset", "name": nome, "description": desc + " " + metodo, "url": f"{BASE}/dados/#{slug}", "license": LICENCA[1], "isAccessibleForFree": True,
                      "creator": {"@id": BASE + "/#org"}, "isBasedOn": furl, "dateModified": mod or hoje, "inLanguage": "pt-BR",
                      "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{BASE}/dados/{slug}.csv"}]})
    fq = [("Posso usar os dados do Modal News?", f"Sim. A compilação está sob licença {LICENCA[0]}: cite o Modal News e a fonte original indicada em cada arquivo."),
          ("Com que frequência os arquivos são atualizados?", "O de diesel acompanha a pesquisa semanal da ANP; rotas e pedágios, as atualizações da ANTT; o de frete mínimo muda quando sai nova portaria."),
          ("Os arquivos são oficiais?", "Não. São compilações do Modal News feitas a partir de dados oficiais. Para uso legal ou contratual, consulte sempre a fonte original."),
          ("Em que formato estão os dados?", "CSV com separador vírgula, codificação UTF-8 e cabeçalho na primeira linha. Decimais usam ponto."),
          ("Como reportar um erro nos dados?", "Pela página de correções do site. Erros confirmados são corrigidos e registrados.")]
    from paginas import faq_block, faq_ld
    body = (f'<article class="post data"><h1>Dados abertos do Modal News</h1><p class="snippet">Arquivos CSV com os dados que alimentam as páginas de diesel, rotas e frete mínimo, com fonte, método e licença. '
            f'Use à vontade citando a origem.</p>{cards_h}<h2>Perguntas frequentes</h2>{faq_block(E, fq)}<p class="src">Ver também a <a href="/metodologia/">metodologia</a>.</p></article>')
    B.write("/dados/", B.page(f"Dados abertos de logística em CSV | {B.CFG['site_name']}", "Baixe em CSV os preços do diesel por município (ANP), rotas com pedágios federais e coeficientes do frete mínimo ANTT, com método e licença.",
                              "/dados/", body, jsonld={"@context": "https://schema.org", "@graph": graph + [faq_ld(fq)]}))
    return ["/dados/"], {"/dados/": hoje}

# ------------------------------------------------------------------ sitemap de notícias
def sitemap_noticias(B, posts):
    """Google News sitemap: só conteúdo próprio indexável publicado nas últimas 48 h. Fica vazio enquanto não houver."""
    agora = dt.datetime.now(dt.timezone.utc); E = B.E
    own = [p for p in posts if not p.get("gerado_por") and agora - p["data"] <= dt.timedelta(hours=48)]
    rows = "".join(f"<url><loc>{B.BASE}{p['url']}</loc><news:news><news:publication><news:name>{E(B.CFG['site_name'])}</news:name><news:language>pt</news:language></news:publication>"
                   f"<news:publication_date>{p['data'].isoformat()}</news:publication_date><news:title>{E(p['titulo'])}</news:title></news:news></url>" for p in own)
    (B.OUT / "sitemap-noticias.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">' + rows + "</urlset>", encoding="utf-8")
    return len(own)

# ------------------------------------------------------------------ llms.txt enxuto
def llms(B, hubs):
    """Só hubs, datasets e páginas de método/confiança. A lista completa fica no sitemap."""
    BASE = B.BASE; out = [f"# {B.CFG['site_name']}", "", f"> {B.CFG['tagline']}. Dados oficiais (ANP, ANTT, IBGE, ANAC, ANTAQ) organizados por cidade, rota e rodovia, glossário técnico e calculadoras.", "",
           "Conteúdo próprio indexável: páginas de dados e glossário. Notícias de terceiros são resumos com link para a fonte e ficam fora do índice.", "", "## Dados e ferramentas", ""]
    for u in hubs:
        t, d = B._meta(u)
        if t: out.append(f"- [{t}]({BASE}{u}): {d}")
    out += ["", "## Dados abertos (CSV, CC BY 4.0)", ""]
    for f in sorted((B.OUT / "dados").glob("*.csv")): out.append(f"- {BASE}/dados/{f.name}")
    out += ["", "## Confiança", ""]
    for u in ("/sobre/", "/expediente/", "/politica-editorial/", "/metodologia/", "/correcoes/", "/dados/"):
        t, d = B._meta(u)
        if t: out.append(f"- [{t}]({BASE}{u}): {d}")
    out += ["", f"Sitemap: {BASE}/sitemap.xml", ""]
    (B.OUT / "llms.txt").write_text("\n".join(out), encoding="utf-8")
