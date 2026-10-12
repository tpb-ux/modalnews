"""Fase 2 — páginas 'Logística e transporte em <cidade>' (/logistica/<cidade>-<uf>/).
Foco: logística/frete/acesso rodoviário e portuário da cidade (não canibaliza /diesel/<cidade>/, que tem os preços por posto/semana).
Dados: IBGE (centroide, Censo 2022, PIB), ANP (diesel), ANTT (praças de pedágio e volume), portos.yaml (ANTAQ/MPor), ANTT (frete mínimo)."""
import json, math, yaml
from paginas import UFN, norm, brl, dbr, crumbs_html, crumbs_ld, faq_block, faq_ld

def km(a, b):
    R = 6371; p1, p2 = math.radians(a["lat"]), math.radians(b["lat"]); dl = math.radians(b["lon"] - a["lon"]); dp = p2 - p1
    return 2 * R * math.asin(math.sqrt(math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))
num = lambda v: f"{v:,.0f}".replace(",", ".")
def dec(v, d=1): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def build(B):
    E, BASE, ROOT = B.E, B.BASE, B.ROOT
    ibge = json.loads((ROOT / "data/ibge_municipios.json").read_text()); IC = json.loads((ROOT / "data/ibge_cidades.json").read_text())["municipios"]
    code = lambda nome, uf: str((ibge.get(f"{norm(nome)}|{uf}") or {}).get("ibge", ""))
    db = json.loads((ROOT / "data/diesel.json").read_text()); sem = max(db["semanas"]); cur = db["semanas"][sem]
    rod = json.loads((ROOT / "data/rodovias.json").read_text())["rodovias"]
    portos = yaml.safe_load((ROOT / "data/portos.yaml").read_text())["portos"]
    fm = json.loads((ROOT / "data/frete_minimo.json").read_text()); cg = fm["tabelas"]["A"]["cargas"]["Carga Geral"]; ato = fm["ato"]
    pracas = []
    for br, r in rod.items():
        for p in r["pracas"]:
            g = IC.get(code(p["municipio"], p["uf"]))
            if g:
                vols = p.get("volume") or {}; ult = max(vols, key=lambda m: m[-4:] + m[:2]) if vols else None
                pracas.append({**p, "br": br, "g": g, "mes": ult, "com": (vols.get(ult) or {}).get("Comercial") if ult else None})
    import geo, sys as _s; _s.path.insert(0, str(ROOT / "tools")); import osrm
    PO = yaml.safe_load((ROOT / "data/portos_organizados.yaml").read_text())["portos"]
    pg = [({"slug": p[0], "nome": f"Porto de {p[1]}", "cidade": p[2], "uf": p[3]}, IC.get(code(p[2], p[3]))) for p in PO]; pg = [(p, g) for p, g in pg if g]
    AE = json.loads((ROOT / "data/aeroportos.json").read_text())["aeroportos"]; aes = [(k, a) for k, a in AE.items() if a["dom"] + a["int"] >= 1000]
    rg = json.loads((ROOT / "data/regic.json").read_text())["municipios"]
    subs = {}
    for cc, r in rg.items():
        pl = geo.polo_nome(r.get("polo"))
        if pl: subs.setdefault(pl, []).append(cc)
    urls = []; ni = 0; nidx = 0
    for k, v in cur["municipios"].items():
        nome, uf = k.split("|"); c = code(nome, uf); g = IC.get(c)
        if not g: continue
        disp = ibge[f"{norm(nome)}|{uf}"]["nome"]; sl = f"{B.slugify(disp)}-{uf.lower()}"; u = f"/logistica/{sl}/"; dsl = f"/diesel/{sl}/"
        s10 = (v.get("s10") or {}).get("media"); s500 = (v.get("s500") or {}).get("media"); postos = (v.get("s10") or v.get("s500"))["postos"]
        prox = sorted(((km(g, p["g"]), p) for p in pracas), key=lambda x: x[0]); prox = [x for x in prox if x[0] <= 100][:8]
        brs = sorted({p["br"] for _, p in prox})
        pts3 = sorted(((km(g, h), p, h) for p, h in pg), key=lambda x: x[0])[:3]
        ae2 = sorted(((km(g, a), k2, a) for k2, a in aes), key=lambda x: x[0])[:2]
        cap = IC.get(code(geo.CAPITAIS[uf], uf)); r0 = rg.get(c) or {}; pl = geo.polo_nome(r0.get("polo")); plg = IC.get(code(*pl)) if pl else None
        dests = [h for _, _, h in pts3] + [a for _, _, a in ae2] + [x for x in (cap, plg) if x and x is not g]
        road = osrm.table(g, dests, offline=True); rd_ = dict(zip([id(x) for x in dests], road))
        R = lambda h: rd_.get(id(h))
        pts3.sort(key=lambda x: (R(x[2]) or [9e9])[0])
        pts = [(d, p) for d, p, _ in pts3]
        pop, pib = g.get("pop"), g.get("pib_mil")
        cidade = f"{disp} ({uf})"
        # ---- seções
        perfil = []
        if pop: perfil.append(("População (Censo 2022)", num(pop) + " habitantes"))
        if pib: perfil.append((f"PIB a preços correntes ({g['pib_mil_ano']})", f"R$ {dec(pib / 1e6, 2)} bilhões"))
        if pop and pib: perfil.append((f"PIB per capita (cálculo: PIB {g['pib_mil_ano']} ÷ população 2022)", brl(pib * 1000 / pop)))
        perfil.append(("Área territorial", f"{dec(g['area_km2'])} km²"))
        perfil_html = "<dl class='deflist'>" + "".join(f"<dt>{E(a)}</dt><dd>{E(b)}</dd>" for a, b in perfil) + "</dl><p class='src'>Fonte: IBGE (Censo Demográfico 2022, PIB dos Municípios e Malhas Territoriais), via API oficial servicodados.ibge.gov.br.</p>"
        dz = f"<p>Na semana de {dbr(cur['ini'])} a {dbr(cur['fim'])}, a ANP pesquisou {postos} postos em {E(disp)}." + (f" O diesel S10 custou em média <strong>{brl(s10)}/l</strong>" if s10 else "") + (f" e o S500, {brl(s500)}/l" if s500 else "") + \
             f". Preços mínimos, máximos e histórico semanal estão na página <a href='{dsl}'>preço do diesel em {E(disp)}</a>.</p>"
        if s10:
            l = 100 / 2.5 * s10
            dz += f"<p>Para referência de custo: um caminhão pesado com consumo de 2,5 km/l gasta cerca de {brl(l)} de diesel S10 a cada 100 km ao preço médio da cidade (cálculo ilustrativo; use a <a href='/calculadoras/custo-diesel-viagem/'>calculadora de custo de diesel</a> com o seu consumo).</p>"
        if prox:
            rows = "".join(f"<tr><td><a href='/rodovias/{p['br'].lower()}/'>{p['br']}</a></td><td>{E(p['nome'])}</td><td>{E(p['municipio'])} ({p['uf']}), km {dec(p['km'])}</td><td>{E(p['concessionaria'].title())}</td><td>{dec(d, 0)} km</td><td>{num(p['com']) if p['com'] else '—'}{(' (' + p['mes'] + ')') if p['com'] else ''}</td></tr>" for d, p in prox)
            rd = f"<p>Há {len(prox)} praça(s) de pedágio de rodovias federais concedidas num raio de 100 km (em linha reta) de {E(disp)}, nas rodovias {', '.join(brs)}.</p><div class='tblw'><table class='tbl'><thead><tr><th>Rodovia</th><th>Praça</th><th>Local</th><th>Concessionária</th><th>Distância em linha reta*</th><th>Veículos comerciais no mês</th></tr></thead><tbody>{rows}</tbody></table></div><p class='src'>*Distância em linha reta entre os centros (centroides IBGE) dos municípios, não é a distância rodoviária. Praças e volumes: ANTT, dados abertos.</p>"
        else:
            rd = f"<p>Não há praças de pedágio de rodovias federais concedidas num raio de 100 km (em linha reta) de {E(disp)} no cadastro da ANTT. Rodovias estaduais e federais não concedidas não entram nesta lista.</p>"
        hr = lambda m: f"{m // 60}h{m % 60:02d}" if m else "—"
        pt = "<div class='tblw'><table class='tbl'><thead><tr><th>Porto organizado</th><th>Por estrada*</th><th>Tempo estimado*</th><th>Linha reta</th></tr></thead><tbody>" + "".join(f"<tr><td><a href='/portos/{p['slug']}/'>{E(p['nome'])}</a> ({E(p['cidade'])}, {p['uf']})</td><td>{num(R(h)[0]) + ' km' if R(h) else '—'}</td><td>{hr(R(h)[1]) if R(h) else '—'}</td><td>{num(d)} km</td></tr>" for d, p, h in pts3) + "</tbody></table></div>"
        aer = "<div class='tblw'><table class='tbl'><thead><tr><th>Aeroporto</th><th>Carga em 12 meses (ANAC)</th><th>Por estrada*</th><th>Linha reta</th></tr></thead><tbody>" + "".join(f"<tr><td><a href='/aeroportos/{k2.lower()}/'>{E(a['nome_oficial'].title())} ({k2})</a>, {E(a['municipio_servido'])}</td><td>{num(a['dom'] + a['int'])} t</td><td>{num(R(a)[0]) + ' km' if R(a) else '—'}</td><td>{num(d)} km</td></tr>" for d, k2, a in ae2) + "</tbody></table></div>"
        nota = f"<p class='src'>*{E(osrm.FONTE)}. O tempo é estimativa do roteador para automóvel, sem paradas; caminhões levam mais. Linha reta: entre centroides IBGE.</p>"
        pt += aer + nota
        polo = ""
        if r0:
            hier = r0.get("hier", ""); sb = subs.get((disp, uf)) or (subs.get(geo.polo_nome(r0.get("arranjo") or "") or ("", "")) if r0.get("arranjo") else None) or []
            polo = f"<p>Na classificação do IBGE (REGIC 2018), {E(disp)} é <strong>{E(hier.split(' - ')[0])}</strong>" + (f", parte do {E(r0['arranjo'])}" if r0.get("arranjo") else "") + "."
            if pl and pl != (disp, uf) and not (r0.get("arranjo") and pl[0] in r0["arranjo"]):
                plk = f"/logistica/{B.slugify(pl[0])}-{pl[1].lower()}/"; has = (pl[0], pl[1]) in [(ibge[k_]["nome"], k_.split("|")[1]) for k_ in [f"{norm(x.split('|')[0])}|{x.split('|')[1]}" for x in cur["municipios"]] if k_ in ibge]
                polo += f" Sua região de influência imediata é a de " + (f"<a href='{plk}'>{E(pl[0])} ({pl[1]})</a>" if has else f"{E(pl[0])} ({pl[1]})") + (f", a {num(R(plg)[0])} km por estrada" if plg and R(plg) else "") + "."
            if len(sb) > 1: polo += f" {len(sb)} municípios têm {E(disp if not r0.get('arranjo') else r0['arranjo'])} como centro de referência imediato para compras, serviços e deslocamentos."
            if cap and cap is not g and R(cap): polo += f" A capital, {E(geo.CAPITAIS[uf])}, fica a {num(R(cap)[0])} km por estrada."
            polo += "</p><p class='src'>Fonte: IBGE, Regiões de Influência das Cidades 2018 (REGIC). Os polos indicam centralidade urbana e de serviços, usada como referência para planejamento de distribuição.</p>"
        ex = [(x, x * cg["ccd"]["5"] + cg["cc"]["5"]) for x in (100, 300, 500)]
        fr = f"<p>O piso de frete da ANTT vale para todo o país e depende da distância, do tipo de carga e do número de eixos, não da cidade. Referência para carga geral, lotação, 5 eixos (Tabela A, {E(ato['nome'])}): " + "; ".join(f"{x} km = {brl(vv)}" for x, vv in ex) + ". Pedágio é pago à parte. Calcule a sua rota na <a href='/frete-minimo/'>calculadora de frete mínimo</a>.</p>"
        # ---- FAQ
        fq = []
        if s10: fq.append((f"Quanto custa o diesel para caminhão em {cidade}?", f"Na semana de {dbr(cur['ini'])} a {dbr(cur['fim'])}, o diesel S10 custou em média {brl(s10)} por litro em {disp}, segundo a pesquisa da ANP em {postos} postos. O preço muda toda semana; a página de diesel da cidade mostra mínimo, máximo e histórico."))
        if prox: fq.append((f"Quais rodovias federais com pedágio passam perto de {disp}?", f"Num raio de 100 km em linha reta há {len(prox)} praça(s) de pedágio federais, nas rodovias {', '.join(brs)}. A mais próxima é a praça {prox[0][1]['nome']}, em {prox[0][1]['municipio']} ({prox[0][1]['uf']}), na {prox[0][1]['br']}, operada pela {prox[0][1]['concessionaria'].title()}, segundo a ANTT."))
        if pts3 and R(pts3[0][2]): fq.append((f"Qual o porto mais próximo de {disp}?", f"Entre os 35 portos organizados do país (lista da ANTAQ), o mais próximo por estrada é o {pts3[0][1]['nome']}, a cerca de {num(R(pts3[0][2])[0])} km, segundo cálculo de rota com OSRM e dados do OpenStreetMap entre os centros dos municípios."))
        elif pts: fq.append((f"Qual o porto mais próximo de {disp}?", f"Entre os portos organizados, o mais próximo é o {pts[0][1]['nome']}, a cerca de {num(pts[0][0])} km em linha reta entre os centros dos municípios (IBGE)."))
        if ae2: fq.append((f"Qual o aeroporto de carga mais próximo de {disp}?", f"O aeroporto com movimento de carga mais próximo é {ae2[0][2]['nome_oficial'].title()} ({ae2[0][1]}), em {ae2[0][2]['municipio_servido']}, que movimentou {num(ae2[0][2]['dom'] + ae2[0][2]['int'])} toneladas de carga e correio em 12 meses, segundo a ANAC" + (f", a {num(R(ae2[0][2])[0])} km por estrada." if R(ae2[0][2]) else ".")))
        fq.append((f"Qual o frete mínimo saindo de {disp}?", f"O piso da ANTT não muda por cidade: é calculado pela distância da viagem, tipo de carga e número de eixos. Para carga geral com 5 eixos, uma viagem de 300 km tem piso de {brl(ex[1][1])}, sem pedágio. Use a calculadora para a sua rota."))
        if pop and pib: fq.append((f"Qual o tamanho da economia de {disp}?", f"Pelo IBGE, {disp} tinha {num(pop)} habitantes no Censo 2022 e PIB de R$ {dec(pib / 1e6, 2)} bilhões em {g['pib_mil_ano']}, o que dá cerca de {brl(pib * 1000 / pop)} por habitante (PIB do ano dividido pela população do Censo)."))
        dp = (1 if any(road) else 0) + (1 if r0 else 0) + (1 if s10 else 0) + (1 if s500 else 0) + (1 if pop else 0) + (1 if pib else 0) + min(len(prox), 4) + (1 if pts and pts[0][0] <= 400 else 0)
        idx = dp >= 5 and postos >= 3 and len(fq) >= 4
        lead = f"{disp} ({UFN[uf]}) em dados de logística: " + (f"{num(pop)} habitantes (Censo 2022), " if pop else "") + (f"diesel S10 a {brl(s10)}/l (ANP), " if s10 else "") + \
               (f"{len(prox)} praças de pedágio federais em até 100 km ({', '.join(brs)})" if prox else "sem praças de pedágio federais em até 100 km") + (f" e porto mais próximo: {pts3[0][1]['nome']}, a {num(R(pts3[0][2])[0])} km por estrada." if pts3 and R(pts3[0][2]) else f" e porto mais próximo: {pts[0][1]['nome']}, a {num(pts[0][0])} km em linha reta." if pts else ".")
        cr = [("Início", "/"), ("Estados", "/estados/"), (UFN[uf], f"/estados/{uf.lower()}/"), (f"Logística em {disp}", u)]
        body = f"""<article class="post data">{crumbs_html(E, cr)}<h1>Logística e transporte em {E(disp)} ({uf})</h1><p class="snippet">{E(lead)}</p>
<p class="upd">Dados atualizados: diesel semana {dbr(cur['ini'])}–{dbr(cur['fim'])}; pedágio e volumes ANTT; IBGE.</p>
<h2>Perfil econômico de {E(disp)}</h2>{perfil_html}<h2>Combustível para transporte de cargas</h2>{dz}
<h2>Rodovias federais e pedágios próximos</h2>{rd}<h2>Polo regional (IBGE)</h2>{polo}<h2>Portos e aeroportos de carga mais próximos</h2>{pt}<h2>Frete mínimo de referência (ANTT)</h2>{fr}
<h2>Perguntas frequentes</h2>{faq_block(E, fq)}
<p class="src">Metodologia: páginas geradas a partir de dados públicos oficiais, sem estimativas próprias além dos cálculos indicados. Veja a <a href="/metodologia/">metodologia</a>.</p></article>"""
        ld = {"@context": "https://schema.org", "@graph": [
            {"@type": "WebPage", "name": f"Logística e transporte em {cidade}", "url": BASE + u, "dateModified": cur["fim"], "about": {"@type": "City", "name": disp, "containedInPlace": {"@type": "State", "name": UFN[uf]},
             "geo": {"@type": "GeoCoordinates", "latitude": g["lat"], "longitude": g["lon"]}, "sameAs": f"https://cidades.ibge.gov.br/brasil/{uf.lower()}/{B.slugify(disp)}/panorama"}},
            {"@type": "Dataset", "name": f"Indicadores de logística de {cidade}", "description": lead, "url": BASE + u, "license": "https://creativecommons.org/licenses/by/4.0/", "creator": {"@type": "Organization", "name": "Modal News"},
             "isBasedOn": ["https://servicodados.ibge.gov.br/api/docs", "https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos", "https://dados.antt.gov.br/"], "temporalCoverage": f"{cur['ini']}/{cur['fim']}", "spatialCoverage": cidade},
            faq_ld(fq), crumbs_ld(BASE, cr)]}
        viz = sorted(((km(g, IC[code(*kk.split("|"))]), kk) for kk in cur["municipios"] if kk != k and IC.get(code(*kk.split("|")))), key=lambda x: x[0])[:5]
        def vlink(kk):
            n2, u2 = kk.split("|"); d2 = ibge[f"{norm(n2)}|{u2}"]["nome"]; return (f"/logistica/{B.slugify(d2)}-{u2.lower()}/", f"Logística em {d2} ({u2})")
        B.REL[u] = [(dsl, f"Preço do diesel em {disp}"), (f"/estados/{uf.lower()}/", f"Logística em {UFN[uf]}")] + [vlink(kk) for _, kk in viz] + \
                   [(f"/rodovias/{b.lower()}/", b) for b in brs[:3]] + [(f"/portos/{pts[0][1]['slug']}/", pts[0][1]["nome"])] + [("/frete-minimo/", "Frete mínimo ANTT")]
        title = f"Logística e transporte em {disp} ({uf}): rodovias, portos e frete"
        if len(title) > 65: title = f"Logística em {disp} ({uf}): rodovias, portos e frete"
        B.write(u, B.page(title, (lead[:152].rsplit(" ", 1)[0] + "…") if len(lead) > 155 else lead, u, body, jsonld=ld, robots=None if idx else "noindex,follow"))
        B.REL.setdefault(dsl, []).insert(0, (u, f"Logística e transporte em {disp}"))
        if idx: urls.append(u); nidx += 1
        ni += 1
    # índice
    u = "/logistica/"; by = {}
    for x in urls: by.setdefault(x.rstrip("/")[-2:].upper(), []).append(x)
    lst = "".join(f"<h2>{UFN[f]}</h2><div class='chips small'>" + "".join(f'<a class="chip" href="{x}">{E(x.split("/")[2][:-3].replace("-", " ").title())}</a>' for x in sorted(xs)) + "</div>" for f, xs in sorted(by.items(), key=lambda t: UFN[t[0]]))
    body = f'<article class="post">{crumbs_html(E, [("Início", "/"), ("Logística por cidade", u)])}<h1>Logística e transporte por cidade</h1><p class="snippet">{nidx} cidades com dados oficiais de logística: diesel (ANP), pedágios federais próximos (ANTT), porto mais próximo, população e PIB (IBGE) e frete mínimo de referência.</p>{lst}</article>'
    B.write(u, B.page("Logística e transporte por cidade: rodovias, portos e frete", f"{nidx} cidades brasileiras com indicadores oficiais de logística: diesel, pedágios federais próximos, portos, população e PIB.", u, body,
                      jsonld={"@context": "https://schema.org", "@graph": [crumbs_ld(BASE, [("Início", "/"), ("Logística por cidade", u)])]}))
    print(f"Logística por cidade: {ni} páginas, {nidx} indexáveis")
    return [u] + urls
