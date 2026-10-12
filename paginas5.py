"""Fase 4 — tipos de veículo (/veiculos/<slug>/) e tipos de carga (/tipos-de-carga/<slug>/).
Limites legais: Resolução CONTRAN 882/2021. Coeficientes: tabela de frete mínimo ANTT vigente (data/frete_minimo.json)."""
import json, re, yaml
from paginas import brl, crumbs_html, crumbs_ld, faq_block, faq_ld
CONTRAN = "https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-contran/resolucoes/Resolucao8822021.pdf"
dec = lambda v: (f"{v:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")).replace(",0", "")

def build(B):
    E, BASE, ROOT = B.E, B.BASE, B.ROOT
    V = yaml.safe_load((ROOT / "data/veiculos.yaml").read_text(encoding="utf-8")); T = yaml.safe_load((ROOT / "data/tipos_carga.yaml").read_text(encoding="utf-8"))
    fm = json.loads((ROOT / "data/frete_minimo.json").read_text(encoding="utf-8")); ato = fm["ato"]; TA = fm["tabelas"]["A"]["cargas"]; vig = "/".join(reversed(ato["vigencia"].split("-")))
    IC = json.loads((ROOT / "data/ibge_cidades.json").read_text())["municipios"]; ib = json.loads((ROOT / "data/ibge_municipios.json").read_text())
    rev = {str(v["ibge"]): (v["nome"], k.split("|")[1]) for k, v in ib.items()}
    cities = [rev[c] for c, d in sorted(IC.items(), key=lambda x: -x[1].get("pop", 0)) if c in rev][:8]
    cities = [(n, uf) for n, uf in cities if (B.OUT / "logistica" / f"{B.slugify(n)}-{uf.lower()}" / "index.html").exists() or True][:6]
    vs = {v["slug"]: v for v in V}; cs = lambda c: B.slugify(c)
    fonte = f'<p class="src">Fontes: <a href="{CONTRAN}" target="_blank" rel="noopener">Resolução CONTRAN nº 882/2021</a> (pesos e dimensões) e <a href="{E(ato["url"])}" target="_blank" rel="noopener">{E(ato["nome"])}</a> (frete mínimo, Tabela A, vigente desde {vig}).</p>'
    urls = []
    for v in V:
        u = f"/veiculos/{v['slug']}/"; n, cur = v["nome"], v["curto"]; ex = str(v["eixos"])
        pbt = sum(x[1] for x in v["conjuntos"])
        lim = "".join(f"<tr><td>{E(a)}</td><td>{dec(b)} t</td></tr>" for a, b in v["conjuntos"])
        tl = (f"<div class='tblw'><table class='tbl'><thead><tr><th>Eixo ou conjunto</th><th>Limite legal</th></tr></thead><tbody>{lim}<tr><th>Soma dos limites (PBT/PBTC)</th><th>{dec(pbt)} t</th></tr></tbody></table></div>"
              "<p class='src'>A soma dos limites por eixo é o teto legal; o peso efetivo também não pode passar do PBT/PBTC homologado pelo fabricante, que consta no CRLV.</p>") if v["conjuntos"] else ""
        ficha = [("Número de eixos", ex if v["eixos"] else "Varia conforme a configuração"), ("Enquadramento", v["rntrc_tipo"]), ("Comprimento máximo legal", v["comp"]), ("Exige AET", "Sim" if v["aet"] else "Não, dentro dos limites gerais")]
        if v["conjuntos"]: ficha.insert(1, ("Peso bruto máximo legal (soma dos eixos)", f"{dec(pbt)} t"))
        fhtml = "<dl class='deflist'>" + "".join(f"<dt>{E(a)}</dt><dd>{E(b)}</dd>" for a, b in ficha) + "</dl>"
        eixs = [ex] if v["eixos"] else ["5", "6", "7"]
        if ex == "2" or not v["eixos"]: pass
        rows = "".join(f"<tr><td><a href='/frete-minimo/{cs(c)}/'>{E(c)}</a></td>" + "".join(f"<td>{brl(TA[c]['ccd'][e])}/km + {brl(TA[c]['cc'][e])}</td>" if TA[c]["ccd"].get(e) else "<td>—</td>" for e in eixs) + "</tr>" for c in TA)
        ftab = f"<div class='tblw'><table class='tbl'><thead><tr><th>Tipo de carga</th>" + "".join(f"<th>{e} eixos</th>" for e in eixs) + f"</tr></thead><tbody>{rows}</tbody></table></div>"
        e0 = eixs[0]; cg = TA["Carga Geral"]; exv = 500 * cg["ccd"][e0] + cg["cc"][e0]
        fq = [tuple(x) for x in v["faq"]]
        fq.append((f"Qual o frete mínimo da ANTT para {cur}?", f"Na tabela da ANTT em vigor desde {vig}, para carga geral com {e0} eixos o piso é {brl(cg['ccd'][e0])} por km mais {brl(cg['cc'][e0])} de carga e descarga. Numa viagem de 500 km o mínimo é {brl(exv)}, sem pedágio. Outros tipos de carga têm coeficientes próprios."))
        if v["conjuntos"]: fq.append((f"Qual o peso máximo permitido para {cur}?", f"Pela Resolução CONTRAN 882/2021, a soma dos limites por eixo de {cur.lower() if cur[0].isupper() and cur not in ('VUC',) else cur} é {dec(pbt)} t: " + ", ".join(f"{a.lower()} {dec(b)} t" for a, b in v["conjuntos"]) + ". O peso efetivo também é limitado pelo PBT homologado do veículo."))
        cargas = [t["carga"] for t in T if v["slug"] in t["veiculos"]]
        if cargas: fq.append((f"Que tipos de carga o {cur} transporta?", f"Entre os tipos de carga da tabela da ANTT, o {cur} é usado com frequência para {', '.join(c.lower() for c in cargas[:5])}. Usos típicos: {', '.join(x.lower() for x in v['usos'])}."))
        cr = [("Início", "/"), ("Veículos de carga", "/veiculos/"), (cur, u)]
        body = f"""<article class="post data">{crumbs_html(E, cr)}<h1>{E(n)}: eixos, peso máximo e frete mínimo</h1><p class="snippet">{E(v['texto'].split('. ')[0] + '.')}</p>
<h2>Ficha técnica legal</h2>{fhtml}<h2>O que é {E(cur)}</h2><p>{E(v['texto'])}</p><h2>Limites de peso por eixo</h2>{tl or '<p>Os limites dependem da configuração adotada (caminhão com reboque ou cavalo com semirreboque) e seguem as mesmas regras de peso por eixo da Resolução CONTRAN 882/2021.</p>'}
<h2>Usos mais comuns</h2><ul>{''.join(f'<li>{E(x)}</li>' for x in v['usos'])}</ul>
<h2>Frete mínimo ANTT por tipo de carga</h2><p>Coeficientes da Tabela A (lotação com veículo do transportador): valor por km (CCD) + carga e descarga (CC). Calcule na <a href="/frete-minimo/">calculadora de frete mínimo</a>.</p>{ftab}
<h2>Perguntas frequentes</h2>{faq_block(E, fq)}{fonte}</article>"""
        words = len(re.findall(r"\w+", v["texto"] + " ".join(a for _, a in fq)))
        idx = words >= 250 and len(fq) >= 4
        ld = {"@context": "https://schema.org", "@graph": [{"@type": "Article", "headline": f"{n}: eixos, peso máximo e frete mínimo", "url": BASE + u, "inLanguage": "pt-BR", "publisher": {"@type": "Organization", "name": "Modal News"},
              "about": {"@type": "Thing", "name": n}, "citation": [CONTRAN, ato["url"]], "dateModified": ato["vigencia"]}, faq_ld(fq), crumbs_ld(BASE, cr)]}
        title = f"{cur}: eixos, peso máximo e frete mínimo ANTT"
        B.write(u, B.page(title[:65], f"{n}: limites legais de peso por eixo e comprimento (CONTRAN 882/2021), usos e frete mínimo ANTT por tipo de carga, com FAQs."[:158], u, body, jsonld=ld, robots=None if idx else "noindex,follow"))
        B.REL[u] = [(f"/frete-minimo/{cs(c)}/", f"Frete mínimo: {c}") for c in cargas[:3]] + [(f"/tipos-de-carga/{cs(c)}/", f"O que é {c.lower()}") for c in cargas[:3]] + \
                   [(f"/veiculos/{x['slug']}/", x["curto"]) for x in V if x is not v][:4] + [(f"/glossario/{g}/", f"Glossário: {g.replace('-', ' ')}") for g in v["gl"]] + \
                   [("/calculadoras/custo-diesel-viagem/", "Custo de diesel por viagem"), ("/calculadoras/cubagem/", "Calculadora de cubagem")] + [(f"/logistica/{B.slugify(c)}-{uf.lower()}/", f"Logística em {c}") for c, uf in cities[:3]]
        if idx: urls.append(u)
    for t in T:
        c = t["carga"]; s = cs(c); u = f"/tipos-de-carga/{s}/"; k = TA[c]; ok = [e for e in fm["eixos"] if k["ccd"].get(e)]
        vh = [vs[x] for x in t["veiculos"]]
        fq = [(f"O que é {c.lower()}?", t["texto"]),
              (f"Qual o frete mínimo para {c.lower()}?", f"Na tabela da ANTT em vigor desde {vig} (Tabela A), o coeficiente de deslocamento vai de {brl(k['ccd'][ok[0]])}/km com {ok[0]} eixos a {brl(k['ccd'][ok[-1]])}/km com {ok[-1]} eixos, mais o valor de carga e descarga. Veja a tabela completa e calcule pela distância na página de frete mínimo."),
              (f"Quais veículos transportam {c.lower()}?", f"Os mais usados são: {', '.join(x['curto'] for x in vh)}. A escolha depende do volume, da distância, do implemento exigido e dos limites de peso por eixo da Resolução CONTRAN 882/2021."),
              (f"Quais são exemplos de {c.lower()}?", f"Exemplos comuns: {', '.join(x.lower() for x in t['exemplos'])}. A classificação correta do tipo de carga define qual coeficiente da tabela de frete mínimo deve ser aplicado na contratação.")]
        if c.startswith("Perigosa"): fq.append(("Quais as exigências para transportar produto perigoso?", "A regulamentação da ANTT exige, entre outros pontos, motorista com curso de movimentação de produtos perigosos (MOPP), veículo e equipamentos adequados, rótulos de risco e painéis de segurança, documentação com informações de emergência e kit de emergência compatível com o produto."))
        rows = "".join(f"<tr><td>{e} eixos</td><td>{brl(k['ccd'][e])}/km</td><td>{brl(k['cc'][e])}</td><td>{brl(300 * k['ccd'][e] + k['cc'][e])}</td></tr>" for e in ok)
        cr = [("Início", "/"), ("Tipos de carga", "/tipos-de-carga/"), (c, u)]
        body = f"""<article class="post data">{crumbs_html(E, cr)}<h1>{E(c)}: o que é, exemplos e veículos</h1><p class="snippet">{E(t['texto'].split('. ')[0] + '.')}</p>
<h2>Definição</h2><p>{E(t['texto'])}</p><h2>Exemplos</h2><ul>{''.join(f'<li>{E(x)}</li>' for x in t['exemplos'])}</ul>
<h2>Veículos mais usados</h2><div class="chips">{''.join(f'<a class="chip" href="/veiculos/{x["slug"]}/">{E(x["curto"])}</a>' for x in vh)}</div>
<h2>Resumo do frete mínimo ANTT</h2><p>Tabela A, em vigor desde {vig}. Detalhes, outras tabelas e calculadora em <a href="/frete-minimo/{s}/">frete mínimo para {E(c.lower())}</a>.</p>
<div class="tblw"><table class="tbl"><thead><tr><th>Eixos</th><th>CCD</th><th>CC</th><th>Piso em 300 km</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>Perguntas frequentes</h2>{faq_block(E, fq)}{fonte}</article>"""
        ld = {"@context": "https://schema.org", "@graph": [{"@type": "DefinedTerm", "name": c, "description": t["texto"], "url": BASE + u, "inDefinedTermSet": BASE + "/tipos-de-carga/"}, faq_ld(fq), crumbs_ld(BASE, cr)]}
        B.write(u, B.page(f"{c}: o que é, exemplos e frete mínimo"[:65], (t["texto"][:150].rsplit(" ", 1)[0] + "…"), u, body, jsonld=ld))
        B.REL[u] = [(f"/frete-minimo/{s}/", f"Frete mínimo: {c}")] + [(f"/veiculos/{x['slug']}/", x["curto"]) for x in vh] + [(f"/tipos-de-carga/{cs(x['carga'])}/", x["carga"]) for x in T if x is not t][:4] + [("/glossario/carga-lotacao/", "Carga lotação"), ("/frete-minimo/", "Calculadora de frete mínimo")]
        B.REL.setdefault(f"/frete-minimo/{s}/", [])[0:0] = [(u, f"O que é {c.lower()}")] + [(f"/veiculos/{x['slug']}/", x["curto"]) for x in vh[:3]]
        urls.append(u)
    for lst, u, h, d, L in (("v", "/veiculos/", "Tipos de veículos de carga", "Tipos de caminhão e combinações de carga no Brasil: eixos, peso máximo legal (CONTRAN 882/2021) e frete mínimo ANTT.", [(f"/veiculos/{v['slug']}/", v["nome"], f"{v['eixos']} eixos" if v["eixos"] else "eixos variáveis") for v in V]),
                            ("t", "/tipos-de-carga/", "Tipos de carga", "Os 12 tipos de carga da tabela de frete mínimo da ANTT: definição, exemplos, veículos e coeficientes.", [(f"/tipos-de-carga/{cs(t['carga'])}/", t["carga"], ", ".join(t["exemplos"][:2])) for t in T])):
        body = f'<article class="post">{crumbs_html(E, [("Início", "/"), (h, u)])}<h1>{h}</h1><p class="snippet">{E(d)}</p><div class="tblw"><table class="tbl"><tbody>' + "".join(f'<tr><td><a href="{a}">{E(b)}</a></td><td>{E(cc)}</td></tr>' for a, b, cc in L) + f"</tbody></table></div>{fonte}</article>"
        B.write(u, B.page(h, d, u, body, jsonld={"@context": "https://schema.org", "@graph": [{"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": BASE + a} for i, (a, b, cc) in enumerate(L)]}, crumbs_ld(BASE, [("Início", "/"), (h, u)])]}))
        urls.insert(0, u)
    B.REL.setdefault("/frete-minimo/", [])[0:0] = [("/veiculos/", "Tipos de veículos de carga"), ("/tipos-de-carga/", "Tipos de carga")]
    print(f"Veículos: {len(V)}; tipos de carga: {len(T)}; indexáveis: {len(urls)}")
    return urls
