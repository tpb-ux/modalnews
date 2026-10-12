"""Versão 1 — portos organizados completos, aeroportos de carga (ANAC), pedágios com tarifa (ANTT), referência de diesel da ANTT,
utilidades (contêineres, Incoterms), rotas entre cidades (OSRM + ANTT), busca interna e expediente."""
import json, re, sys, yaml
from paginas import UFN, brl, dbr, norm, crumbs_html, crumbs_ld, faq_block, faq_ld
import geo, tarifas
num = lambda v, d=0: (f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", "."))
INV = {v: k for k, v in UFN.items()}

def _ctx(B):
    ROOT = B.ROOT; sys.path.insert(0, str(ROOT / "tools")); import osrm
    IC = json.loads((ROOT / "data/ibge_cidades.json").read_text())["municipios"]
    db = json.loads((ROOT / "data/diesel.json").read_text()); cur = db["semanas"][max(db["semanas"])]
    ib = geo.ibge(); cid = {}
    for k, v in cur["municipios"].items():
        n, uf = k.split("|"); key = f"{norm(n)}|{uf}"
        if key in ib: cid[str(ib[key]["ibge"])] = {"nome": ib[key]["nome"], "uf": uf, "url": f"/logistica/{B.slugify(ib[key]['nome'])}-{uf.lower()}/", "s10": (v.get("s10") or {}).get("media")}
    return osrm, IC, cur, cid

def _near_block(B, osrm, IC, cid, g, uf, label):
    E = B.E; cap = IC.get(geo.code(geo.CAPITAIS[uf], uf))
    near = sorted([(geo.km(g, IC[c]), c) for c in cid if IC.get(c) and IC[c] is not g], key=lambda x: x[0])[:4]
    dst = ([cap] if cap and cap is not g else []) + [IC[c] for _, c in near]
    rd = osrm.table(g, dst, offline=True)
    rows = []
    if cap and cap is not g: rows.append((f"{geo.CAPITAIS[uf]} (capital)", f"/logistica/{B.slugify(geo.CAPITAIS[uf])}-{uf.lower()}/" if geo.code(geo.CAPITAIS[uf], uf) in cid else None, rd[0], geo.km(g, cap)))
    off = 1 if rows else 0
    for i, (d, c) in enumerate(near): rows.append((f"{cid[c]['nome']} ({cid[c]['uf']})", cid[c]["url"], rd[i + off], d))
    if not any(r[2] for r in rows): return "", 0, rows
    html = "<div class='tblw'><table class='tbl'><thead><tr><th>Cidade</th><th>Por estrada*</th><th>Linha reta</th></tr></thead><tbody>" + "".join(
        f"<tr><td>{f'<a href={chr(39)}{u}{chr(39)}>{E(n)}</a>' if u else E(n)}</td><td>{num(r[0]) + ' km' if r else '—'}</td><td>{num(d)} km</td></tr>" for n, u, r, d in rows) + \
        f"</tbody></table></div><p class='src'>*{E(osrm.FONTE)}. Ponto de referência: centro do município de {E(label)}.</p>"
    return html, 1, rows

def portos(B):
    E, BASE, ROOT = B.E, B.BASE, B.ROOT; osrm, IC, cur, cid = _ctx(B)
    D = yaml.safe_load((ROOT / "data/portos_organizados.yaml").read_text()); PO = D["portos"]
    det = {p["slug"] for p in yaml.safe_load((ROOT / "data/portos.yaml").read_text())["portos"]}
    rod = json.loads((ROOT / "data/rodovias.json").read_text())["rodovias"]
    AE = json.loads((ROOT / "data/aeroportos.json").read_text())["aeroportos"]
    urls = []
    for s, nome, mun, uf, aut, site in PO:
        u = f"/portos/{s}/"; c = geo.code(mun, uf); g = IC.get(c); full = f"Porto de {nome}"
        B.REL.setdefault(u, [])[0:0] = [(f"/estados/{uf.lower()}/", f"Logística em {UFN[uf]}"), ("/portos/", "Todos os portos organizados"), ("/aeroportos/", "Aeroportos de carga")]
        if s in det or not g: continue
        pts = 2; fq = []; blocks = []
        ficha = [("Tipo", "Porto organizado (porto público)"), ("Município", f"{mun} ({uf})"), ("Autoridade portuária", aut)]
        if site: ficha.append(("Site oficial da autoridade", f"<a href='{E(site)}' target='_blank' rel='noopener'>{E(site.split('//')[1].strip('/'))}</a>")); pts += 1
        blocks.append("<dl class='deflist'>" + "".join(f"<dt>{E(a)}</dt><dd>{b if b.startswith('<a') else E(b)}</dd>" for a, b in ficha) + "</dl>" +
                      f"<p class='src'>Fonte: <a href='{D['url']}' target='_blank' rel='noopener'>{E(D['fonte'])}</a>. Tarifas portuárias: publicadas pela autoridade portuária, conforme a Resolução Normativa ANTAQ nº 61/2021.</p>")
        if g.get("pop"): blocks.append(f"<h2>Município-sede</h2><p>{E(mun)} tinha {num(g['pop'])} habitantes no Censo 2022" + (f" e PIB de R$ {num(g['pib_mil'] / 1e6, 2)} bilhões em {g['pib_mil_ano']}" if g.get("pib_mil") else "") + " (IBGE).</p>"); pts += 1
        nb, ok, rows = _near_block(B, osrm, IC, cid, g, uf, mun)
        if ok:
            blocks.append(f"<h2>Acesso rodoviário</h2>{nb}"); pts += 2
            r0 = rows[0]
            if r0[2]: fq.append((f"Qual a distância do {full} até {r0[0].split(' (')[0]}?", f"Cerca de {num(r0[2][0])} km por estrada entre os centros dos municípios, pelo cálculo de rota OSRM com dados do OpenStreetMap; em linha reta são {num(r0[3])} km."))
        pr = sorted([(geo.km(g, IC[geo.code(p['municipio'], p['uf'])]), br, p) for br, r in rod.items() for p in r["pracas"] if IC.get(geo.code(p["municipio"], p["uf"]))], key=lambda x: x[0])
        pr = [x for x in pr if x[0] <= 100][:6]
        if pr:
            blocks.append("<h2>Pedágios federais próximos</h2><ul>" + "".join(f"<li><a href='/rodovias/{br.lower()}/'>{br}</a> — praça {E(p['nome'])} ({E(p['municipio'])}/{p['uf']}), {num(d)} km em linha reta</li>" for d, br, p in pr) + "</ul>"); pts += 1
        ae = sorted([(geo.km(g, a), k, a) for k, a in AE.items() if a["dom"] + a["int"] >= 1000], key=lambda x: x[0])[:1]
        if ae:
            d, k, a = ae[0]; blocks.append(f"<h2>Aeroporto de carga mais próximo</h2><p><a href='/aeroportos/{k.lower()}/'>{E(a['nome_oficial'].title())} ({k})</a>, em {E(a['municipio_servido'])}, a {num(d)} km em linha reta, com {num(a['dom'] + a['int'])} t de carga e correio em 12 meses (ANAC).</p>")
        if c in cid and cid[c]["s10"]:
            blocks.append(f"<h2>Diesel no município</h2><p>Diesel S10 a {brl(cid[c]['s10'])}/l em média na semana de {dbr(cur['ini'])} a {dbr(cur['fim'])} (ANP). <a href='/diesel/{cid[c]['url'].split('/')[2]}/'>Preços do diesel em {E(mun)}</a>.</p>"); pts += 1
        fq += [(f"Quem administra o {full}?", f"A autoridade portuária do {full} é {aut}, segundo a lista de portos organizados da ANTAQ. A autoridade portuária responde pela gestão da área do porto organizado, pela infraestrutura comum e pela publicação das tarifas portuárias."),
               (f"O {full} é público ou privado?", f"É um porto organizado, ou seja, um porto público cuja área é delimitada por ato do Poder Executivo (Lei 12.815/2013). Dentro dele operam terminais arrendados; fora da área, terminais de uso privado (TUPs) operam por autorização."),
               (f"Onde ver as tarifas do {full}?", "Pela Resolução Normativa ANTAQ nº 61/2021, cada autoridade portuária deve publicar no próprio site as tabelas tarifárias vigentes e anteriores" + (f", no caso em {site}." if site else ".") )]
        if ae: fq.append((f"Qual o aeroporto de carga mais próximo do {full}?", f"É o {a['nome_oficial'].title()} ({k}), em {a['municipio_servido']}, a cerca de {num(d)} km em linha reta, com {num(a['dom'] + a['int'])} toneladas de carga e correio em 12 meses segundo a ANAC."))
        if pr: fq.append((f"Há pedágios federais perto do {full}?", f"Sim. Num raio de 100 km em linha reta há {len(pr)} praça(s) de pedágio de rodovias federais concedidas (cadastro da ANTT); a mais próxima é {pr[0][2]['nome']}, na {pr[0][1]}, a {num(pr[0][0])} km."))
        if c in cid and cid[c]["s10"]: fq.append((f"Quanto custa o diesel em {mun}?", f"Na semana de {dbr(cur['ini'])} a {dbr(cur['fim'])}, o diesel S10 custou em média {brl(cid[c]['s10'])} por litro em {mun}, segundo a ANP."))
        if g.get("pop"): fq.append((f"Qual o tamanho de {mun}, sede do {full}?", f"{mun} tinha {num(g['pop'])} habitantes no Censo 2022" + (f" e PIB de R$ {num(g['pib_mil'] / 1e6, 2)} bilhões em {g['pib_mil_ano']}" if g.get("pib_mil") else "") + ", segundo o IBGE."))
        cr = [("Início", "/"), ("Portos", "/portos/"), (full, u)]
        body = f"""<article class="post data">{crumbs_html(E, cr)}<h1>{E(full)} ({uf})</h1><p class="snippet">{E(f"O {full} é um porto organizado em {mun} ({UFN[uf]}), sob responsabilidade de {aut}. Veja acesso rodoviário com distâncias por estrada, pedágios federais próximos, aeroporto de carga mais próximo e fontes oficiais.")}</p>
<h2>Ficha do porto</h2>{''.join(blocks)}<h2>Perguntas frequentes</h2>{faq_block(E, fq)}</article>"""
        idx = pts >= 5 and len(fq) >= 3
        ld = {"@context": "https://schema.org", "@graph": [{"@type": ["Place", "CivicStructure"], "name": full, "url": BASE + u, "address": {"@type": "PostalAddress", "addressLocality": mun, "addressRegion": uf, "addressCountry": "BR"},
              "geo": {"@type": "GeoCoordinates", "latitude": g["lat"], "longitude": g["lon"]}, **({"sameAs": site} if site else {})}, faq_ld(fq), crumbs_ld(BASE, cr)]}
        B.write(u, B.page(f"{full} ({uf}): autoridade portuária, acesso e distâncias"[:65], f"{full}, em {mun} ({uf}): autoridade portuária {aut}, site oficial, distâncias por estrada, pedágios federais e aeroporto de carga mais próximo."[:158], u, body, jsonld=ld, robots=None if idx else "noindex,follow"))
        if idx: urls.append(u)
    return urls

def portos_index(B):
    E, BASE, ROOT = B.E, B.BASE, B.ROOT
    D = yaml.safe_load((ROOT / "data/portos_organizados.yaml").read_text()); u = "/portos/"
    rows = "".join(f"<tr><td><a href='/portos/{s}/'>{E(n)}</a></td><td>{E(m)}/{uf}</td><td>{E(a)}</td><td>{f'<a href={chr(39)}{E(st)}{chr(39)} target=_blank rel=noopener>site oficial</a>' if st else '—'}</td></tr>" for s, n, m, uf, a, st in sorted(D["portos"], key=lambda x: (x[3], x[1])))
    fq = [("Quantos portos organizados existem no Brasil?", f"A lista de portos organizados usada pela ANTAQ para aprovação de tarifas reúne {len(D['portos'])} portos, administrados por Companhias Docas federais ou por estados, municípios e consórcios por delegação."),
          ("Qual a diferença entre porto organizado e TUP?", "O porto organizado é público, tem área delimitada por ato do Poder Executivo e é gerido por uma autoridade portuária. O terminal de uso privado (TUP) fica fora dessa área e opera por autorização, nos termos da Lei 12.815/2013."),
          ("Onde encontrar dados de movimentação dos portos?", "A ANTAQ publica o Estatístico Aquaviário e boletins trimestrais com movimentação por porto, terminal, mercadoria e sentido. As páginas dos principais portos no Modal News trazem os números com link para a fonte.")]
    from collections import Counter as _C
    _uf = _C(x[3] for x in D["portos"]).most_common()
    fq.append(("Qual estado tem mais portos organizados?", f"{UFN[_uf[0][0]]}, com {_uf[0][1]} portos organizados na lista da ANTAQ" + (f", seguido de {UFN[_uf[1][0]]} ({_uf[1][1]})." if len(_uf) > 1 else ".")))
    fq.append(("Quem administra os portos organizados?", f"Na lista da ANTAQ há {len({x[4] for x in D['portos']})} autoridades portuárias diferentes, entre Companhias Docas federais, empresas estaduais, municípios e concessionárias; {sum(1 for x in D['portos'] if x[5])} portos têm site oficial indicado."))
    body = f'<article class="post data">{crumbs_html(E, [("Início", "/"), ("Portos", u)])}<h1>Portos organizados do Brasil</h1><p class="snippet">Os {len(D["portos"])} portos organizados (públicos) do país, com município, autoridade portuária e site oficial, segundo a ANTAQ. Cada página traz acesso rodoviário com distâncias por estrada, pedágios próximos e fontes oficiais.</p><div class="tblw"><table class="tbl"><thead><tr><th>Porto</th><th>Município</th><th>Autoridade portuária</th><th>Contato</th></tr></thead><tbody>{rows}</tbody></table></div><p class="src">Fonte: <a href="{D["url"]}" target="_blank" rel="noopener">{E(D["fonte"])}</a>.</p><h2>Perguntas frequentes</h2>{faq_block(E, fq)}</article>'
    B.write(u, B.page("Portos organizados do Brasil: lista, autoridades e acessos", f"Lista dos {len(D['portos'])} portos organizados do Brasil com autoridade portuária, site oficial, acesso rodoviário e dados ANTAQ.", u, body,
                      jsonld={"@context": "https://schema.org", "@graph": [{"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{BASE}/portos/{p[0]}/", "name": f"Porto de {p[1]}"} for i, p in enumerate(D["portos"])]}, faq_ld(fq), crumbs_ld(BASE, [("Início", "/"), ("Portos", u)])]}))

def aeroportos(B):
    E, BASE, ROOT = B.E, B.BASE, B.ROOT; osrm, IC, cur, cid = _ctx(B)
    A = json.loads((ROOT / "data/aeroportos.json").read_text()); AE = A["aeroportos"]; per = A["periodo"]
    MES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]; mfmt = lambda m: f"{MES[int(m[5:]) - 1]}/{m[:4]}"
    lst = sorted([(k, a) for k, a in AE.items() if a["dom"] + a["int"] >= 1000], key=lambda x: -(x[1]["dom"] + x[1]["int"]))
    total = sum(a["dom"] + a["int"] for a in AE.values()); urls = []
    for rk, (k, a) in enumerate(lst, 1):
        u = f"/aeroportos/{k.lower()}/"; uf = INV.get(a["uf_servido"], a.get("uf")); nome = a["nome_oficial"].title(); t = a["dom"] + a["int"]
        g = IC.get(geo.code(a["municipio_servido"], uf)) or {"lat": a["lat"], "lon": a["lon"]}
        serie = sorted(a["mensal"].items())
        rows = "".join(f"<tr><td>{mfmt(m)}</td><td>{num(v)} t</td></tr>" for m, v in serie)
        nb, ok, rows2 = _near_block(B, osrm, IC, cid, g, uf, a["municipio_servido"]) if uf in geo.CAPITAIS else ("", 0, [])
        lead = f"O aeroporto {nome} ({k}), em {a['municipio_servido']} ({uf}), movimentou {num(t)} toneladas de carga e correio entre {mfmt(per[0])} e {mfmt(per[1])}, {rk}º no país entre os aeroportos com voos de carga e passageiros registrados pela ANAC."
        fq = [(f"Quanto o aeroporto {k} movimenta de carga?", f"Segundo os Dados Estatísticos do Transporte Aéreo da ANAC, foram {num(t)} toneladas de carga paga e correio (embarque e desembarque) em 12 meses, de {mfmt(per[0])} a {mfmt(per[1])}: {num(a['dom'])} t em voos domésticos e {num(a['int'])} t em voos internacionais."),
              (f"O aeroporto {k} opera à noite?", f"No cadastro de aeródromos públicos da ANAC, a operação noturna do {k} consta como: {a['op_noturna'] or 'não informada'}. Condições operacionais podem mudar; confira os avisos aeronáuticos (NOTAM) e o operador do aeroporto."),
              (f"Quanto da carga do {k} é internacional?", f"Cerca de {num(100 * a['int'] / t if t else 0, 1)}% das toneladas no período foram em voos internacionais, que incluem cargueiros e porões de voos de passageiros. O restante corresponde a voos domésticos.")]
        if serie:
            mx = max(serie, key=lambda x: x[1]); mn = min(serie, key=lambda x: x[1])
            fq.append((f"Qual foi o mês de maior movimento de carga no {k}?", f"Entre {mfmt(per[0])} e {mfmt(per[1])}, o pico foi em {mfmt(mx[0])}, com {num(mx[1])} t de carga e correio, e o menor movimento em {mfmt(mn[0])}, com {num(mn[1])} t (ANAC)."))
        fq.append((f"Qual a posição do {k} no ranking de carga aérea?", f"Com {num(t)} t em 12 meses, o {k} foi o {rk}º entre os {len(lst)} aeroportos com mais de mil toneladas no período, com {num(100 * t / total, 1)}% do total nacional (ANAC)."))
        fq.append((f"O {k} mais embarca ou desembarca carga?", f"No período, foram {num(a['emb'])} t embarcadas e {num(a['des'])} t desembarcadas, ou seja, o aeroporto {'mais embarca' if a['emb'] > a['des'] else 'mais desembarca' if a['des'] > a['emb'] else 'embarca e desembarca o mesmo volume'}, segundo a ANAC."))
        mesmo_uf = [(x, b_) for x, b_ in lst if INV.get(b_["uf_servido"], b_.get("uf")) == uf]
        uf_html = ""
        if len(mesmo_uf) > 1:
            pu = [x for x, _ in mesmo_uf].index(k) + 1
            fq.append((f"Qual o maior aeroporto de carga de {UFN[uf]}?", f"Entre os {len(mesmo_uf)} aeroportos de {UFN[uf]} com mais de mil toneladas em 12 meses, o líder é {mesmo_uf[0][1]['nome_oficial'].title()} ({mesmo_uf[0][0]}), com {num(mesmo_uf[0][1]['dom'] + mesmo_uf[0][1]['int'])} t; o {k} é o {pu}º do estado (ANAC)."))
            uf_html = f"<h2>Aeroportos de carga em {UFN[uf]}</h2><ul>" + "".join(f"<li>" + (f"<a href='/aeroportos/{x.lower()}/'>{E(b_['nome_oficial'].title())} ({x})</a>" if x != k else f"<strong>{E(b_['nome_oficial'].title())} ({x})</strong>") + f": {num(b_['dom'] + b_['int'])} t</li>" for x, b_ in mesmo_uf) + "</ul>"
        else:
            fq.append((f"Há outros aeroportos de carga em {UFN[uf]}?", f"Na estatística da ANAC do período, o {k} é o único aeroporto de {UFN[uf]} com mais de mil toneladas de carga e correio em 12 meses."))
        if len(serie) >= 6:
            v1 = sum(v for _, v in serie[:3]); v2 = sum(v for _, v in serie[-3:])
            uf_html += f"<h2>Tendência recente</h2><p>Os últimos 3 meses ({mfmt(serie[-3][0])} a {mfmt(serie[-1][0])}) somaram {num(v2)} t, contra {num(v1)} t nos 3 primeiros meses da série ({mfmt(serie[0][0])} a {mfmt(serie[2][0])}), variação de {('+' if v2 >= v1 else '') + num(100 * (v2 / v1 - 1), 1) if v1 else '—'}%.</p>"
        cr = [("Início", "/"), ("Aeroportos de carga", "/aeroportos/"), (f"{k}", u)]
        body = f"""<article class="post data">{crumbs_html(E, cr)}<h1>Aeroporto {E(nome)} ({k}): carga aérea</h1><p class="snippet">{E(lead)}</p>
<h2>Ficha</h2><dl class="deflist"><dt>Código OACI</dt><dd>{k}</dd><dt>Município servido</dt><dd>{E(a['municipio_servido'])} ({uf})</dd><dt>Carga + correio em 12 meses</dt><dd>{num(t)} t ({num(100 * t / total, 1)}% do total nacional no período)</dd><dt>Doméstica / internacional</dt><dd>{num(a['dom'])} t / {num(a['int'])} t</dd><dt>Embarcada / desembarcada</dt><dd>{num(a['emb'])} t / {num(a['des'])} t</dd><dt>Operação noturna (cadastro ANAC)</dt><dd>{E(a['op_noturna'] or '—')}</dd></dl>
{f"<p class='src'>Registro na ANAC: <a href='{E(a['portaria'])}' target='_blank' rel='noopener'>portaria de registro</a>.</p>" if a.get('portaria') else ''}
<h2>Movimento mensal de carga e correio</h2><div class="tblw"><table class="tbl"><thead><tr><th>Mês</th><th>Toneladas</th></tr></thead><tbody>{rows}</tbody></table></div>
{uf_html}{('<h2>Acesso rodoviário</h2>' + nb) if nb else ''}<h2>Perguntas frequentes</h2>{faq_block(E, fq)}
<p class="src">Fontes: ANAC — <a href="{A['fonte_movimento']}" target="_blank" rel="noopener">Dados Estatísticos do Transporte Aéreo</a> e <a href="{A['fonte_cadastro']}" target="_blank" rel="noopener">cadastro de aeródromos públicos</a>. Valores somam carga paga e correio, embarcados e desembarcados.</p></article>"""
        idx = t >= 1000 and len(serie) >= 6
        ld = {"@context": "https://schema.org", "@graph": [{"@type": "Airport", "name": nome, "icaoCode": k, "url": BASE + u, "geo": {"@type": "GeoCoordinates", "latitude": a["lat"], "longitude": a["lon"]}, "address": {"@type": "PostalAddress", "addressLocality": a["municipio_servido"], "addressRegion": uf, "addressCountry": "BR"}},
              {"@type": "Dataset", "name": f"Carga aérea mensal do aeroporto {k}", "url": BASE + u, "temporalCoverage": f"{per[0]}/{per[1]}", "isBasedOn": A["fonte_movimento"], "creator": {"@type": "Organization", "name": "Modal News"}, "license": "https://creativecommons.org/licenses/by/4.0/"}, faq_ld(fq), crumbs_ld(BASE, cr)]}
        B.write(u, B.page(f"Aeroporto {k} ({a['municipio_servido']}): carga aérea em toneladas"[:65], lead[:155].rsplit(" ", 1)[0] + "…", u, body, jsonld=ld, robots=None if idx else "noindex,follow"))
        B.REL[u] = [("/aeroportos/", "Ranking de aeroportos de carga"), (f"/estados/{uf.lower()}/", f"Logística em {UFN[uf]}"), ("/glossario/modal-aereo/", "O que é modal aéreo"), ("/glossario/awb/", "O que é AWB")] + [(f"/aeroportos/{x.lower()}/", f"Aeroporto {x}") for x, _ in lst[max(0, rk - 3):rk + 2] if x != k]
        if idx: urls.append(u)
    u = "/aeroportos/"
    rows = "".join(f"<tr><td>{i}</td><td><a href='/aeroportos/{k.lower()}/'>{E(a['nome_oficial'].title())} ({k})</a></td><td>{E(a['municipio_servido'])}/{INV.get(a['uf_servido'], '')}</td><td>{num(a['dom'] + a['int'])}</td><td>{num(a['int'])}</td></tr>" for i, (k, a) in enumerate(lst, 1))
    fq = [("Qual o aeroporto que mais movimenta carga no Brasil?", f"Entre {mfmt(per[0])} e {mfmt(per[1])}, o líder foi {lst[0][1]['nome_oficial'].title()} ({lst[0][0]}), com {num(lst[0][1]['dom'] + lst[0][1]['int'])} toneladas de carga e correio, seguido por {lst[1][1]['nome_oficial'].title()} ({lst[1][0]}), segundo a ANAC."),
          ("Como é calculada a carga por aeroporto?", "Somamos, nos Dados Estatísticos do Transporte Aéreo da ANAC, a carga paga e o correio em quilos de todas as etapas de voo que partem ou chegam a cada aeroporto brasileiro, nos últimos 12 meses disponíveis, e convertemos para toneladas."),
          ("A carga aérea inclui porão de voos de passageiros?", "Sim. Os dados da ANAC incluem a carga transportada tanto por aviões cargueiros quanto no porão de voos de passageiros, nas etapas domésticas e internacionais."),
          ("Qual a participação do maior aeroporto na carga aérea do país?", f"{lst[0][0]} respondeu por {num(100 * (lst[0][1]['dom'] + lst[0][1]['int']) / total, 1)}% das {num(total)} toneladas de carga e correio registradas pela ANAC entre {mfmt(per[0])} e {mfmt(per[1])}."),
          ("Quantos aeroportos movimentam mais de mil toneladas de carga por ano?", f"{len(lst)} aeroportos passaram de mil toneladas de carga e correio entre {mfmt(per[0])} e {mfmt(per[1])}, segundo a ANAC.")]
    body = f'<article class="post data">{crumbs_html(E, [("Início", "/"), ("Aeroportos de carga", u)])}<h1>Aeroportos de carga do Brasil: ranking em toneladas</h1><p class="snippet">Ranking dos aeroportos brasileiros por carga e correio movimentados entre {mfmt(per[0])} e {mfmt(per[1])}, com dados oficiais da ANAC. Lista os {len(lst)} aeroportos com pelo menos mil toneladas no período.</p><div class="tblw"><table class="tbl"><thead><tr><th>#</th><th>Aeroporto</th><th>Município</th><th>Total (t)</th><th>Internacional (t)</th></tr></thead><tbody>{rows}</tbody></table></div><h2>Perguntas frequentes</h2>{faq_block(E, fq)}<p class="src">Fonte: ANAC, <a href="{A["fonte_movimento"]}" target="_blank" rel="noopener">Dados Estatísticos do Transporte Aéreo</a>.</p></article>'
    B.write(u, B.page("Aeroportos de carga do Brasil: ranking ANAC em toneladas", f"Ranking dos aeroportos de carga do Brasil por toneladas de carga e correio em 12 meses, com dados oficiais da ANAC.", u, body,
                      jsonld={"@context": "https://schema.org", "@graph": [{"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{BASE}/aeroportos/{k.lower()}/"} for i, (k, _) in enumerate(lst)]}, faq_ld(fq), crumbs_ld(BASE, [("Início", "/"), ("Aeroportos de carga", u)])]}))
    return [u] + urls

MULT = [("Automóvel (cat. 1)", 1), ("Caminhão leve/ônibus 2 eixos (cat. 2)", 2), ("Caminhão 3 eixos", 3), ("Caminhão/carreta 4 eixos", 4), ("Carreta 5 eixos", 5), ("Carreta 6 eixos", 6), ("Bitrem 7 eixos", 7)]
def pedagios(B):
    E, BASE, ROOT = B.E, B.BASE, B.ROOT
    rod = json.loads((ROOT / "data/rodovias.json").read_text())["rodovias"]; T = tarifas.dados()
    by = {}
    for br, r in rod.items():
        for p in r["pracas"]: by.setdefault(p["concessionaria"], []).append((br, p))
    urls = []; idxrows = []
    for conc, ps in sorted(by.items()):
        c = tarifas.concessao(conc); s = B.slugify(conc); u = f"/pedagios/{s}/"
        vals = [(br, p, tarifas.tarifa(conc, p["nome"])) for br, p in ps]; nt = sum(1 for *_, t in vals if t)
        fx = tarifas.faixa(conc)
        rows = "".join(f"<tr><td><a href='/rodovias/{br.lower()}/'>{br}</a></td><td>{E(p['nome'])}</td><td>{E(p['municipio'])}/{p['uf']}, km {num(p['km'], 1)}</td>" + (f"<td>{brl(t)}</td><td>{brl(t * 2)}</td><td>{brl(t * 5)}</td><td>{brl(t * 6)}</td>" if t else "<td colspan='4'>ver tabela oficial</td>") + "</tr>" for br, p, t in vals)
        brs = sorted({br for br, _ in ps}); ufs = sorted({p["uf"] for _, p in ps})
        lead = f"{conc.title()} administra {len(ps)} praça(s) de pedágio federais na(s) rodovia(s) {', '.join(brs)} ({', '.join(ufs)})" + (f", com tarifa de automóvel entre {brl(fx[0])} e {brl(fx[1])}" if fx and fx[0] != fx[1] else f", com tarifa de automóvel de {brl(fx[0])}" if fx else "") + "."
        fq = []
        if fx: fq.append((f"Quanto custa o pedágio da {conc.title()} para caminhão?", f"Nas tabelas da ANTT, a tarifa de veículos comerciais é a tarifa básica multiplicada pelo número de eixos: com a tarifa básica de {brl(fx[1])}, uma carreta de 5 eixos paga {brl(fx[1] * 5)} e uma de 6 eixos, {brl(fx[1] * 6)} por praça. Confira o valor de cada praça na tabela oficial."))
        fq.append(("Eixo suspenso paga pedágio?", "Pela Lei 13.103/2015, veículos de transporte de cargas que circularem vazios não pagam pelos eixos que mantiverem suspensos nas rodovias federais concedidas."))
        fq.append(("Quem paga o pedágio no transporte de carga?", "O embarcador, por meio do Vale-Pedágio obrigatório (Lei 10.209/2001), antecipado ao transportador, separado do valor do frete."))
        fq.append((f"Quantas praças de pedágio a {conc.title()} administra?", f"Pelo cadastro de praças da ANTT, são {len(ps)} praça(s) ativa(s) em rodovias federais: " + "; ".join(f"{p['nome']} ({br}, {p['municipio']}/{p['uf']})" for br, p in ps[:8]) + ("." if len(ps) <= 8 else f" e mais {len(ps) - 8}.")))
        tv = sorted([(t, p, br) for br, p, t in vals if t], key=lambda x: x[0])
        if len(tv) >= 2 and tv[0][0] != tv[-1][0]:
            fq.append((f"Qual a praça mais cara e a mais barata da {conc.title()}?", f"Na tabela da ANTT, a maior tarifa básica é a de {tv[-1][1]['nome']} ({tv[-1][2]}), {brl(tv[-1][0])}, e a menor a de {tv[0][1]['nome']} ({tv[0][2]}), {brl(tv[0][0])}. Para 5 eixos: {brl(tv[-1][0] * 5)} e {brl(tv[0][0] * 5)}."))
        elif tv:
            fq.append((f"Quanto custa passar por todas as praças da {conc.title()} com 5 eixos?", f"Somando as {len(tv)} praça(s) com tarifa identificada, uma carreta de 5 eixos paga {brl(sum(t for t, *_ in tv) * 5)} em um sentido, pela tabela da ANTT."))
        if len(fq) < 5: fq.append((f"Em quais rodovias e estados a {conc.title()} opera?", f"Nas rodovias federais {', '.join(brs)}, nos estados de {', '.join(UFN[x] for x in ufs)}, segundo o cadastro de praças da ANTT."))
        cr = [("Início", "/"), ("Pedágios", "/pedagios/"), (conc.title(), u)]
        body = f"""<article class="post data">{crumbs_html(E, cr)}<h1>Pedágios da {E(conc.title())}: praças e tarifas</h1><p class="snippet">{E(lead)}</p>
<div class="tblw"><table class="tbl"><thead><tr><th>Rodovia</th><th>Praça</th><th>Local</th><th>Automóvel</th><th>2 eixos (comercial)</th><th>5 eixos</th><th>6 eixos</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="src">Tarifas: {f"<a href='{E(c['url'])}' target='_blank' rel='noopener'>tabela oficial da ANTT</a>" + (f" (página atualizada em {c['atualizado']})" if c.get('atualizado') else '') if c else 'tabela oficial da concessão no portal da ANTT'}. Valores de veículos comerciais = tarifa básica × nº de eixos (multiplicador oficial das tabelas da ANTT). Praças: ANTT, dados abertos. Só mostramos o valor da praça quando a tabela oficial permite associá-lo sem ambiguidade.</p>
<h2>Perguntas frequentes</h2>{faq_block(E, fq)}</article>"""
        idx = nt >= 1 or bool(fx)
        ld = {"@context": "https://schema.org", "@graph": [{"@type": "Dataset", "name": f"Praças e tarifas de pedágio — {conc.title()}", "url": BASE + u, "isBasedOn": [c["url"]] if c else [], "creator": {"@type": "Organization", "name": "Modal News"}}, faq_ld(fq), crumbs_ld(BASE, cr)]}
        B.write(u, B.page(f"Pedágios {conc.title()}: praças e tarifas para caminhão"[:65], lead[:155], u, body, jsonld=ld, robots=None if idx else "noindex,follow"))
        B.REL[u] = [(f"/rodovias/{b.lower()}/", b) for b in brs] + [("/pedagios/", "Todas as concessões"), ("/glossario/vale-pedagio/", "O que é vale-pedágio"), ("/frete-minimo/", "Frete mínimo ANTT")]
        for b in brs: B.REL.setdefault(f"/rodovias/{b.lower()}/", []).insert(0, (u, f"Tarifas: {conc.title()}"))
        idxrows.append((u, conc.title(), ", ".join(brs), len(ps), fx))
        if idx: urls.append(u)
    u = "/pedagios/"
    rows = "".join(f"<tr><td><a href='{a}'>{E(b)}</a></td><td>{E(c)}</td><td>{d}</td><td>{(brl(f[0]) + (' a ' + brl(f[1]) if f[1] != f[0] else '')) if f else '—'}</td></tr>" for a, b, c, d, f in idxrows)
    body = f'<article class="post data">{crumbs_html(E, [("Início", "/"), ("Pedágios", u)])}<h1>Pedágios nas rodovias federais: tarifas por concessão</h1><p class="snippet">Praças de pedágio das rodovias federais concedidas, com a tarifa básica (automóvel) e o valor para caminhões de 2, 5 e 6 eixos, a partir das tabelas oficiais publicadas pela ANTT.</p><div class="tblw"><table class="tbl"><thead><tr><th>Concessão</th><th>Rodovias</th><th>Praças</th><th>Tarifa básica</th></tr></thead><tbody>{rows}</tbody></table></div><p class="src">Rodovias estaduais concedidas (por exemplo, as de São Paulo, Paraná e Rio Grande do Sul sob concessão estadual) têm tarifas próprias, definidas pelas agências estaduais, e não estão nesta lista.</p></article>'
    B.write(u, B.page("Pedágios nas rodovias federais: tarifas por concessão e eixo", "Tarifas de pedágio das rodovias federais concedidas: automóvel e caminhões de 2, 5 e 6 eixos, com fonte ANTT.", u, body, jsonld={"@context": "https://schema.org", "@graph": [crumbs_ld(BASE, [("Início", "/"), ("Pedágios", u)])]}))
    return [u] + urls

def diesel_antt(B):
    E, BASE, ROOT = B.E, B.BASE, B.ROOT
    fm = json.loads((ROOT / "data/frete_minimo.json").read_text())["ato"]; db = json.loads((ROOT / "data/diesel.json").read_text()); ks = sorted(db["semanas"]); cur = db["semanas"][ks[-1]]
    a = cur["brasil"]["BR"]["s10"]["media"]; r = fm["diesel_ref"]; var = (a / r - 1) * 100; u = "/diesel/referencia-antt/"
    hist = "".join(f"<tr><td>{dbr(db['semanas'][k]['ini'])} a {dbr(db['semanas'][k]['fim'])}</td><td>{brl(db['semanas'][k]['brasil']['BR']['s10']['media'])}</td><td>{num((db['semanas'][k]['brasil']['BR']['s10']['media'] / r - 1) * 100, 1)}%</td></tr>" for k in ks[::-1])
    fq = [("Qual o preço do diesel usado pela ANTT no frete mínimo?", f"A {fm['nome']} adotou {brl(r)} por litro como preço de referência do diesel, que corresponde à média nacional do diesel S10 da ANP na semana de {fm['diesel_ref_semana'].split(' (')[0]}."),
          ("Quando a ANTT atualiza a tabela de frete pelo diesel?", "A Lei 13.703/2018 prevê a atualização dos pisos sempre que o preço do diesel no mercado nacional oscilar além do limite fixado na lei e na regulamentação da ANTT, além da revisão periódica dos coeficientes."),
          ("Qual a diferença entre o diesel da ANP e o de referência da ANTT?", f"A ANP divulga toda semana o preço médio de revenda pesquisado nos postos. A ANTT fixa, em cada portaria, um valor de referência para calcular os coeficientes. Hoje a média ANP mais recente ({brl(a)}) está {num(var, 1)}% {'acima' if var >= 0 else 'abaixo'} da referência.")]
    _ws = [(k, db["semanas"][k]["brasil"]["BR"]["s10"]["media"]) for k in ks]
    fq.append(("Quanto o diesel da ANP está acima ou abaixo da referência da ANTT?", f"Na semana de {dbr(cur['ini'])} a {dbr(cur['fim'])}, a média nacional do S10 foi {brl(a)}, {('+' if var >= 0 else '') + num(var, 1)}% em relação à referência de {brl(r)} da {fm['nome']}."))
    fq.append(("Como o diesel variou nas últimas semanas?", f"Nas {len(_ws)} semanas guardadas, a média nacional do S10 foi de {brl(min(v for _, v in _ws))} a {brl(max(v for _, v in _ws))} por litro (ANP)."))
    body = f"""<article class="post data">{crumbs_html(E, [("Início", "/"), ("Diesel", "/diesel/"), ("Referência ANTT", u)])}<h1>Diesel de referência da ANTT × preço ANP</h1>
<p class="snippet">{E(f"O preço de referência do diesel na tabela de frete mínimo vigente é {brl(r)}/l ({fm['nome']}). A média nacional do S10 pesquisada pela ANP na semana de {dbr(cur['ini'])} a {dbr(cur['fim'])} foi {brl(a)}/l, {num(var, 1)}% em relação à referência.")}</p>
<h2>Acompanhamento semanal</h2><div class="tblw"><table class="tbl"><thead><tr><th>Semana (ANP)</th><th>Diesel S10 Brasil</th><th>Diferença para a referência ANTT</th></tr></thead><tbody>{hist}</tbody></table></div>
<h2>Perguntas frequentes</h2>{faq_block(E, fq)}<p class="src">Fontes: <a href="{E(fm['url'])}" target="_blank" rel="noopener">{E(fm['nome'])}</a>; <a href="{E(fm['noticia'])}" target="_blank" rel="noopener">ANTT</a>; ANP, levantamento semanal de preços. Ver <a href="/frete-minimo/">tabela de frete mínimo</a>.</p></article>"""
    B.write(u, B.page("Diesel de referência da ANTT × preço ANP (frete mínimo)", f"Preço de referência do diesel da ANTT ({brl(r)}/l) na tabela de frete mínimo comparado à média semanal ANP.", u, body,
                      jsonld={"@context": "https://schema.org", "@graph": [{"@type": "Dataset", "name": "Diesel de referência ANTT × média ANP", "url": BASE + u, "isBasedOn": [fm["url"], cur["arquivo"]], "creator": {"@type": "Organization", "name": "Modal News"}}, faq_ld(fq), crumbs_ld(BASE, [("Início", "/"), ("Diesel", "/diesel/"), ("Referência ANTT", u)])]}))
    for p in ("/diesel/", "/frete-minimo/"): B.REL.setdefault(p, []).insert(0, (u, "Diesel de referência da ANTT"))
    B.REL[u] = [("/diesel/", "Preço do diesel por cidade"), ("/frete-minimo/", "Frete mínimo ANTT"), ("/resumo-semanal/", "Resumo semanal")]
    return [u]

CONT = [("20' Dry (DC)", "6,058", "2,438", "2,591", "1 TEU", "Carga geral seca"), ("40' Dry (DC)", "12,192", "2,438", "2,591", "2 TEU", "Carga geral de maior volume"), ("40' High Cube (HC)", "12,192", "2,438", "2,896", "2 TEU", "Cargas leves e volumosas"),
        ("20' Reefer", "6,058", "2,438", "2,591", "1 TEU", "Carga refrigerada (com unidade de frio)"), ("40' Reefer HC", "12,192", "2,438", "2,896", "2 TEU", "Carga refrigerada"), ("20'/40' Open Top", "6,058 / 12,192", "2,438", "2,591", "1 / 2 TEU", "Carga alta carregada por cima"),
        ("20'/40' Flat Rack", "6,058 / 12,192", "2,438", "2,591 (base dobrável)", "1 / 2 TEU", "Máquinas e cargas de projeto"), ("20' Tank (ISO tank)", "6,058", "2,438", "2,591", "1 TEU", "Granéis líquidos")]
INC = [("EXW", "Ex Works", "Qualquer", "No estabelecimento do vendedor, à disposição do comprador", "Comprador"), ("FCA", "Free Carrier", "Qualquer", "Na entrega ao transportador indicado pelo comprador", "Comprador"),
       ("CPT", "Carriage Paid To", "Qualquer", "Na entrega ao primeiro transportador", "Vendedor (até o destino)"), ("CIP", "Carriage and Insurance Paid To", "Qualquer", "Na entrega ao primeiro transportador", "Vendedor (frete e seguro amplo)"),
       ("DAP", "Delivered at Place", "Qualquer", "No local de destino, pronto para descarga", "Vendedor"), ("DPU", "Delivered at Place Unloaded", "Qualquer", "No local de destino, descarregada", "Vendedor"),
       ("DDP", "Delivered Duty Paid", "Qualquer", "No destino, com tributos de importação pagos", "Vendedor"), ("FAS", "Free Alongside Ship", "Marítimo/hidroviário", "Ao lado do navio no porto de embarque", "Comprador"),
       ("FOB", "Free on Board", "Marítimo/hidroviário", "A bordo do navio no porto de embarque", "Comprador"), ("CFR", "Cost and Freight", "Marítimo/hidroviário", "A bordo do navio no porto de embarque", "Vendedor (até o porto de destino)"),
       ("CIF", "Cost, Insurance and Freight", "Marítimo/hidroviário", "A bordo do navio no porto de embarque", "Vendedor (frete e seguro mínimo)")]
def utilidades(B):
    E, BASE = B.E, B.BASE; urls = []
    u = "/utilidades/tipos-de-conteineres/"
    rows = "".join(f"<tr><td>{E(a)}</td><td>{b} m</td><td>{c} m</td><td>{d} m</td><td>{e}</td><td>{E(f)}</td></tr>" for a, b, c, d, e, f in CONT)
    fq = [("Quais as medidas externas de um contêiner de 20 pés?", "Pela norma ISO 668, o contêiner de 20 pés tem 6,058 m de comprimento, 2,438 m de largura e 2,591 m de altura externa no modelo padrão. As medidas internas variam conforme o fabricante e a espessura das paredes."),
          ("Qual a diferença entre contêiner Dry e High Cube?", "O High Cube tem a mesma largura e comprimento do Dry, mas 2,896 m de altura externa, cerca de 30 cm a mais, o que aumenta o volume interno e favorece cargas leves e volumosas."),
          ("O que é TEU?", "TEU (twenty-foot equivalent unit) é a unidade equivalente a um contêiner de 20 pés. Um contêiner de 40 pés conta como 2 TEU. É a medida usada para capacidade de navios e movimentação de terminais."),
          ("Qual o peso máximo de um contêiner?", "A norma ISO 668 fixa a massa bruta máxima de contêineres de 20 e 40 pés em 30.480 kg; muitos equipamentos atuais são certificados para massa maior. O limite real é o da placa CSC do equipamento e, no transporte rodoviário, os limites de peso por eixo do CONTRAN.")]
    fq.append(("Qual contêiner usar para carga refrigerada?", "Os modelos Reefer, com unidade de frio própria: " + "; ".join(f"{x[0]} ({x[1]} m × {x[2]} m × {x[3]} m)" for x in CONT if "Reefer" in x[0]) + ". Medidas externas de referência (ISO 668)."))
    body = f'<article class="post data">{crumbs_html(E, [("Início", "/"), ("Utilidades", "/utilidades/"), ("Tipos de contêineres", u)])}<h1>Tipos de contêineres: medidas e usos</h1><p class="snippet">Os principais tipos de contêiner marítimo, com medidas externas padronizadas pela norma ISO 668, equivalência em TEU e usos mais comuns.</p><div class="tblw"><table class="tbl"><thead><tr><th>Tipo</th><th>Comprimento</th><th>Largura</th><th>Altura</th><th>TEU</th><th>Uso</th></tr></thead><tbody>{rows}</tbody></table></div><p class="src">Medidas externas nominais da ISO 668 (Série 1). Medidas internas, tara e capacidade variam por fabricante e constam na placa do equipamento.</p><h2>Perguntas frequentes</h2>{faq_block(E, fq)}</article>'
    B.write(u, B.page("Tipos de contêineres: medidas 20', 40', High Cube e Reefer", "Medidas externas dos contêineres 20 pés, 40 pés, High Cube, Reefer, Open Top e Flat Rack (ISO 668), TEU e usos.", u, body, jsonld={"@context": "https://schema.org", "@graph": [faq_ld(fq), crumbs_ld(BASE, [("Início", "/"), ("Utilidades", "/utilidades/"), ("Tipos de contêineres", u)])]}))
    B.REL[u] = [("/glossario/teu/", "O que é TEU"), ("/tipos-de-carga/conteinerizada/", "Carga conteinerizada"), ("/portos/", "Portos organizados"), ("/utilidades/incoterms/", "Tabela de Incoterms")]; urls.append(u)
    u = "/utilidades/incoterms/"
    rows = "".join(f"<tr><td><a href='/glossario/{s.lower()}/'>{s}</a></td><td lang='en'>{E(n)}</td><td>{E(m)}</td><td>{E(r)}</td><td>{E(f)}</td></tr>" if (B.OUT / "glossario" / s.lower()).exists() else f"<tr><td>{s}</td><td lang='en'>{E(n)}</td><td>{E(m)}</td><td>{E(r)}</td><td>{E(f)}</td></tr>" for s, n, m, r, f in INC)
    fq = [("Quantos Incoterms existem?", "A versão Incoterms 2020 da Câmara de Comércio Internacional tem 11 regras: 7 para qualquer modal (EXW, FCA, CPT, CIP, DAP, DPU, DDP) e 4 exclusivas para transporte marítimo e hidroviário (FAS, FOB, CFR, CIF)."),
          ("Qual a diferença entre CIF e CIP?", "Em CIF o vendedor contrata seguro com cobertura mínima e a regra serve só para o marítimo. Em CIP, usado em qualquer modal, a versão 2020 exige cobertura mais ampla."),
          ("Incoterm define quem paga o imposto?", "Só o DDP atribui ao vendedor os tributos de importação. Nas demais regras, os tributos de importação são do comprador; o Incoterm não trata de propriedade da mercadoria nem de forma de pagamento.")]
    fq.append(("Quais Incoterms servem só para transporte marítimo?", ", ".join(f"{x[0]} ({x[1]})" for x in INC if x[2] != "Qualquer") + ". As demais regras servem para qualquer modal."))
    fq.append(("Em quais Incoterms o comprador contrata o frete principal?", ", ".join(x[0] for x in INC if x[4].startswith("Comprador")) + ". Nas demais, o vendedor paga o transporte principal, conforme a tabela."))
    body = f'<article class="post data">{crumbs_html(E, [("Início", "/"), ("Utilidades", "/utilidades/"), ("Incoterms", u)])}<h1>Tabela de Incoterms 2020</h1><p class="snippet">As 11 regras Incoterms 2020 com modal aplicável, ponto de transferência de risco e quem paga o frete principal.</p><div class="tblw"><table class="tbl"><thead><tr><th>Sigla</th><th>Nome</th><th>Modal</th><th>Risco passa ao comprador</th><th>Frete principal</th></tr></thead><tbody>{rows}</tbody></table></div><p class="src">Referência: <a href="https://iccwbo.org/business-solutions/incoterms-rules/" target="_blank" rel="noopener">ICC — Incoterms 2020</a>. Veja também os comparativos <a href="/comparativos/fob-vs-cif/">FOB × CIF</a> e <a href="/comparativos/exw-vs-fca/">EXW × FCA</a>.</p><h2>Perguntas frequentes</h2>{faq_block(E, fq)}</article>'
    B.write(u, B.page("Tabela de Incoterms 2020: risco, frete e modal", "As 11 regras Incoterms 2020 (EXW, FCA, CPT, CIP, DAP, DPU, DDP, FAS, FOB, CFR, CIF) com transferência de risco e frete.", u, body, jsonld={"@context": "https://schema.org", "@graph": [faq_ld(fq), crumbs_ld(BASE, [("Início", "/"), ("Utilidades", "/utilidades/"), ("Incoterms", u)])]}))
    B.REL[u] = [("/glossario/incoterms/", "O que são Incoterms"), ("/comparativos/fob-vs-cif/", "FOB × CIF"), ("/comparativos/exw-vs-fca/", "EXW × FCA"), ("/guias/como-exportar/", "Como exportar")]; urls.append(u)
    B.REL.setdefault("/glossario/incoterms/", []).insert(0, (u, "Tabela de Incoterms 2020")); B.REL.setdefault("/glossario/teu/", []).insert(0, ("/utilidades/tipos-de-conteineres/", "Tipos de contêineres"))
    u = "/utilidades/"
    body = f'<article class="post">{crumbs_html(E, [("Início", "/"), ("Utilidades", u)])}<h1>Utilidades para logística e comércio exterior</h1><ul class="rel-news"><li><a href="/utilidades/tipos-de-conteineres/">Tipos de contêineres e medidas</a></li><li><a href="/utilidades/incoterms/">Tabela de Incoterms 2020</a></li><li><a href="/calculadoras/cubagem/">Calculadora de cubagem</a></li><li><a href="/calculadoras/custo-diesel-viagem/">Custo de diesel por viagem</a></li><li><a href="/frete-minimo/">Calculadora de frete mínimo</a></li><li><a href="/rotas/">Rotas entre cidades</a></li><li><a href="/pedagios/">Pedágios federais</a></li></ul></article>'
    B.write(u, B.page("Utilidades para logística: contêineres, Incoterms e calculadoras", "Ferramentas e tabelas de referência para logística e comércio exterior.", u, body, jsonld={"@context": "https://schema.org", "@graph": [crumbs_ld(BASE, [("Início", "/"), ("Utilidades", u)])]}))
    return [u] + urls
