"""Fase 3 — comparativos X × Y (/comparativos/<slug>/) e glossário inglês × português (/glossario/ingles-portugues/).
Texto próprio em data/comparativos.yaml e data/glossario_en.yaml; definições curtas vêm do glossário do site."""
import re, yaml
from paginas import crumbs_html, crumbs_ld, faq_block, faq_ld

def build(B):
    E, BASE, ROOT = B.E, B.BASE, B.ROOT
    G = yaml.safe_load((ROOT / "data/glossario.yaml").read_text(encoding="utf-8")); G = G if isinstance(G, list) else G["termos"]
    gl = {B.slugify(t["t"]): t for t in G}
    first = lambda s: ((gl[s]["d"][0] if isinstance(gl[s]["d"], list) else gl[s]["d"].strip().split("\n\n")[0]) if s in gl else "")
    C = yaml.safe_load((ROOT / "data/comparativos.yaml").read_text(encoding="utf-8"))
    urls = []; lm = None
    by_term = {}
    for c in C: by_term.setdefault(c["a"], []).append(c); by_term.setdefault(c["b"], []).append(c)
    for c in C:
        u = f"/comparativos/{c['slug']}/"; na, nb = c["na"], c["nb"]
        fq = [tuple(x) for x in c["faq"]] + [(f"Qual a diferença entre {na} e {nb}?", c["intro"])]
        if c.get("quando_a"): fq.append((f"Quando usar {na}?", c["quando_a"]))
        if c.get("quando_b"): fq.append((f"Quando usar {nb}?", c["quando_b"]))
        if len(fq) < 5 and first(c["a"]): fq.append((f"O que é {na}?", first(c["a"])))
        if len(fq) < 5 and first(c["b"]): fq.append((f"O que é {nb}?", first(c["b"])))
        tb = "".join(f"<tr><th scope='row'>{E(r[0])}</th><td>{E(r[1])}</td><td>{E(r[2])}</td></tr>" for r in c["tabela"])
        defs = f"<h2>O que é {E(na)}</h2><p>{E(first(c['a']))} <a href='/glossario/{c['a']}/'>Definição completa de {E(na)}</a>.</p><h2>O que é {E(nb)}</h2><p>{E(first(c['b']))} <a href='/glossario/{c['b']}/'>Definição completa de {E(nb)}</a>.</p>"
        fontes = ("<h2>Fontes</h2><ul>" + "".join(f'<li><a href="{E(l)}" rel="noopener" target="_blank">{E(n)}</a></li>' for n, l in c["fontes"]) + "</ul>") if c.get("fontes") else ""
        outros = [x for x in C if x is not c and ({x["a"], x["b"]} & {c["a"], c["b"]} or True)][:0]
        cr = [("Início", "/"), ("Comparativos", "/comparativos/"), (f"{na} × {nb}", u)]
        body = f"""<article class="post data">{crumbs_html(E, cr)}<h1>{E(na)} × {E(nb)}: qual a diferença?</h1><p class="snippet">{E(c['intro'])}</p>
<h2>Tabela comparativa</h2><div class="tblw"><table class="tbl"><thead><tr><th>Critério</th><th>{E(na)}</th><th>{E(nb)}</th></tr></thead><tbody>{tb}</tbody></table></div>
<h2>Exemplo prático</h2><p>{E(c['exemplo'])}</p><h2>Quando usar {E(na)}</h2><p>{E(c['quando_a'])}</p><h2>Quando usar {E(nb)}</h2><p>{E(c['quando_b'])}</p>{defs}
<h2>Perguntas frequentes</h2>{faq_block(E, fq)}{fontes}</article>"""
        words = len(re.findall(r"\w+", " ".join([c["intro"], c["exemplo"], c["quando_a"], c["quando_b"], first(c["a"]), first(c["b"])] + [a for _, a in fq])))
        idx = words >= 300 and len(c["tabela"]) >= 4 and len(fq) >= 4
        ld = {"@context": "https://schema.org", "@graph": [
            {"@type": "Article", "headline": f"{na} × {nb}: qual a diferença?", "url": BASE + u, "inLanguage": "pt-BR", "author": {"@type": "Organization", "name": "Modal News"}, "publisher": {"@type": "Organization", "name": "Modal News"},
             "about": [{"@type": "DefinedTerm", "name": na, "url": f"{BASE}/glossario/{c['a']}/"}, {"@type": "DefinedTerm", "name": nb, "url": f"{BASE}/glossario/{c['b']}/"}]},
            faq_ld(fq), crumbs_ld(BASE, cr)]}
        desc = f"Diferença entre {na} e {nb}: tabela comparativa, quando usar cada um, exemplos e perguntas frequentes."
        B.write(u, B.page(f"{na} × {nb}: diferença e tabela comparativa"[:65], desc, u, body, jsonld=ld, robots=None if idx else "noindex,follow"))
        B.REL[u] = [(f"/glossario/{c['a']}/", f"O que é {na}"), (f"/glossario/{c['b']}/", f"O que é {nb}")] + [(f"/comparativos/{x['slug']}/", f"{x['na']} × {x['nb']}") for x in C if x is not c][:6] + [("/glossario/ingles-portugues/", "Glossário inglês × português")]
        if idx: urls.append(u)
    for s, cs in by_term.items():
        B.REL.setdefault(f"/glossario/{s}/", [])[0:0] = [(f"/comparativos/{x['slug']}/", f"Comparativo: {x['na']} × {x['nb']}") for x in cs]
    u = "/comparativos/"
    body = f'<article class="post">{crumbs_html(E, [("Início", "/"), ("Comparativos", u)])}<h1>Comparativos de logística</h1><p class="snippet">Diferenças entre termos, documentos, Incoterms e modelos de operação logística, com tabela comparativa, quando usar cada um e perguntas frequentes.</p><ul class="rel-news">' + \
           "".join(f'<li><a href="/comparativos/{c["slug"]}/">{E(c["na"])} × {E(c["nb"])}</a></li>' for c in C) + "</ul></article>"
    B.write(u, B.page("Comparativos de logística: diferenças entre termos e modelos", "Comparativos de logística: FOB × CIF, WMS × TMS, CT-e × MDF-e, FIFO × FEFO, 3PL × 4PL e mais, com tabelas e FAQs.", u, body,
                      jsonld={"@context": "https://schema.org", "@graph": [{"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{BASE}/comparativos/{c['slug']}/"} for i, c in enumerate(C)]}, crumbs_ld(BASE, [("Início", "/"), ("Comparativos", u)])]}))
    urls.insert(0, u)
    # ---------- inglês × português
    L = sorted(yaml.safe_load((ROOT / "data/glossario_en.yaml").read_text(encoding="utf-8")), key=lambda x: x[0].lower())
    u = "/glossario/ingles-portugues/"
    rows = "".join(f"<tr id='{B.slugify(en)}'><td lang='en'><strong>{E(en)}</strong></td><td>" + (f"<a href='/glossario/{s}/'>{E(pt)}</a>" if s else E(pt)) + f"</td><td>{E(n)}</td></tr>" for en, pt, s, n in L)
    fq = [("Por que a logística usa tantos termos em inglês?", "Porque boa parte dos conceitos, sistemas e normas de comércio exterior nasceu em empresas e entidades internacionais, como os Incoterms da Câmara de Comércio Internacional. Muitos termos, como picking, cross docking e lead time, são usados em inglês no dia a dia das operações no Brasil."),
          ("Os Incoterms têm tradução oficial?", "As siglas dos Incoterms (EXW, FCA, FOB, CIF, DDP e outras) são usadas no original em contratos no mundo todo. As traduções servem para entender o significado, mas no contrato deve constar a sigla e a versão, por exemplo FOB Incoterms 2020."),
          ("Qual a diferença entre supply chain e logística?", "Supply chain (cadeia de suprimentos) abrange fornecedores, produção, distribuição e clientes. Logística é a parte que planeja e executa o fluxo e a armazenagem de materiais e informações dentro dessa cadeia, incluindo transporte, estoques, armazéns e distribuição até o cliente final."),
          ("Como se diz carga lotação e carga fracionada em inglês?", "Carga lotação corresponde a full truckload (FTL), e carga fracionada a less than truckload (LTL), termos comuns em fretes rodoviários nos Estados Unidos. No FTL o veículo é dedicado a um embarcador; no LTL várias remessas dividem o caminhão e passam por terminais."),
          ("Como se diz conhecimento de embarque em inglês?", "No transporte marítimo é bill of lading (B/L); no aéreo, air waybill (AWB). No Brasil, o transporte rodoviário de cargas usa o CT-e, que não tem equivalente direto em inglês e costuma ser explicado como electronic bill of lading ou consignment note.")]
    cr = [("Início", "/"), ("Glossário", "/glossario/"), ("Inglês × português", u)]
    body = f"""<article class="post data">{crumbs_html(E, cr)}<h1>Glossário de logística inglês × português</h1><p class="snippet">{len(L)} termos de logística, transporte e comércio exterior em inglês com a tradução usada no Brasil e link para a definição completa no glossário do Modal News.</p>
<div class="tblw"><table class="tbl"><thead><tr><th>Inglês</th><th>Português</th><th>Observação</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>Perguntas frequentes</h2>{faq_block(E, fq)}<p>Veja também o <a href="/glossario/">glossário completo</a>, as <a href="/siglas/">siglas</a> e os <a href="/comparativos/">comparativos</a>.</p></article>"""
    ld = {"@context": "https://schema.org", "@graph": [{"@type": "DefinedTermSet", "name": "Glossário de logística inglês × português", "url": BASE + u, "inLanguage": ["en", "pt-BR"],
           "hasDefinedTerm": [{"@type": "DefinedTerm", "name": en, "inLanguage": "en", "description": pt, **({"url": f"{BASE}/glossario/{s}/"} if s else {})} for en, pt, s, n in L]}, faq_ld(fq), crumbs_ld(BASE, cr)]}
    B.write(u, B.page("Glossário de logística inglês × português", f"{len(L)} termos de logística em inglês com tradução e significado: picking, lead time, safety stock, bill of lading, freight forwarder e mais.", u, body, jsonld=ld))
    for en, pt, s, n in L:
        if s: B.REL.setdefault(f"/glossario/{s}/", []).append((f"{u}#{B.slugify(en)}", f"Em inglês: {en}"))
    urls.append(u)
    print(f"Comparativos: {len(C)} ({len(urls) - 2} indexáveis); inglês×português: {len(L)} termos")
    return urls
