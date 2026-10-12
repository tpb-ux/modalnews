"""Páginas de dados (pSEO) e de confiança do Modal News. Sem IA: só dados públicos e textos fixos.
- /diesel/ (Brasil), /diesel/estado/<uf>/, /diesel/<cidade>-<uf>/  ← ANP, Levantamento de Preços de Combustíveis
- /calculadoras/cubagem/, /calculadoras/custo-diesel-viagem/
- /sobre/, /politica-editorial/, /metodologia/, /correcoes/, /privacidade/, /links-uteis/, /siglas/, 404.html
- llms.txt, saude.json"""
import datetime as dt, hashlib, json, unicodedata, re
from pathlib import Path

UFN = {"AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
       "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
       "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima",
       "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins"}
ANP_PAGE = "https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/levantamento-de-precos-de-combustiveis-ultimas-semanas-pesquisadas"

def brl(v): return ("R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")) if v is not None else "—"
def dbr(iso): return "/".join(reversed(iso.split("-")))
def pct(a, b): return f"{(a / b - 1) * 100:+.1f}%".replace(".", ",") if a and b else "—"
def norm(s): return re.sub(r"[^A-Z ]", "", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper().replace("-", " ").replace("'", " ")).strip()
def pick(key, opts): return opts[int(hashlib.md5(key.encode()).hexdigest(), 16) % len(opts)]

def faq_block(E, fq):
    return "".join(f'<details class="faq" open><summary><h3>{E(q)}</h3></summary><p>{E(a)}</p></details>' for q, a in fq)

def faq_ld(fq): return {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in fq]}

def crumbs_ld(BASE, items): return {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": BASE + u} for i, (n, u) in enumerate(items)]}

def crumbs_html(E, items): return '<nav class="crumbs" aria-label="breadcrumb">' + " › ".join(f'<a href="{u}">{E(n)}</a>' for n, u in items[:-1]) + f" › {E(items[-1][0])}</nav>"

# ------------------------------------------------------------------ DIESEL (ANP)
def diesel(B):
    E, BASE, CFG = B.E, B.BASE, B.CFG
    f = B.ROOT / "data" / "diesel.json"
    if not f.exists(): return [], {}
    db = json.loads(f.read_text(encoding="utf-8"))
    ibge = json.loads((B.ROOT / "data" / "ibge_municipios.json").read_text(encoding="utf-8"))
    weeks = sorted(db["semanas"], reverse=True); cur, prev = db["semanas"][weeks[0]], db["semanas"][weeks[1]] if len(weeks) > 1 else {}
    per = f"{dbr(cur['ini'])} a {dbr(cur['fim'])}"; fim = cur["fim"]
    src = f'<a href="{ANP_PAGE}" target="_blank" rel="noopener">ANP — Levantamento de Preços de Combustíveis</a>'
    aviso = f'<p class="meta">Fonte: {src}, semana de {per}. Preços médios de revenda em R$/litro. "Diesel S500" corresponde ao produto "óleo diesel" (B S500 comum) do levantamento. Atualização semanal automática.</p>'
    def ds(name, uf, rec):
        return {"@type": "Dataset", "name": name, "description": f"Preço médio de revenda do óleo diesel S10 e S500 {('em ' + uf) if uf else 'no Brasil'} — semana de {per}, segundo a ANP.",
                "creator": {"@type": "Organization", "name": "Agência Nacional do Petróleo, Gás Natural e Biocombustíveis (ANP)", "url": "https://www.gov.br/anp"},
                "isBasedOn": ANP_PAGE, "license": "https://dados.gov.br/dados/conteudo/licencas", "temporalCoverage": f"{cur['ini']}/{cur['fim']}", "dateModified": fim,
                "variableMeasured": ["Preço médio do diesel S10 (R$/l)", "Preço médio do diesel S500 (R$/l)"], "inLanguage": "pt-BR", **({"spatialCoverage": uf} if uf else {})}
    def table(rows, head):
        return f'<div class="tbl"><table><thead><tr>{"".join(f"<th>{h}</th>" for h in head)}</tr></thead><tbody>' + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table></div>"
    def hist(getter):
        rows = []
        for w in weeks:
            v = getter(db["semanas"][w])
            if v: rows.append([f'{dbr(db["semanas"][w]["ini"])} a {dbr(w)}', brl((v.get("s10") or {}).get("media")), brl((v.get("s500") or {}).get("media"))])
        return table(rows, ["Semana", "Diesel S10", "Diesel S500"])
    cities = {}
    for k, v in cur["municipios"].items():
        nome, uf = k.split("|"); m = ibge.get(f"{norm(nome)}|{uf}")
        disp = m["nome"] if m else nome.title()
        cities[k] = {"nome": disp, "uf": uf, "slug": f"{B.slugify(disp)}-{uf.lower()}", "ibge": m["ibge"] if m else None, "d": v}
    urls, lastmod = [], {}
    BRv = cur["brasil"]["BR"]; BRp = prev.get("brasil", {}).get("BR", {})
    # ---- cidade
    for k, c in cities.items():
        uf, nome, d = c["uf"], c["nome"], c["d"]; s10, s5 = d.get("s10"), d.get("s500"); st = cur["estados"].get(uf, {})
        pv = prev.get("municipios", {}).get(k, {})
        url = f"/diesel/{c['slug']}/"; label = f"{nome} ({uf})"
        main_v = s10 or s5; main_n = "S10" if s10 else "S500"
        abert = pick(c["slug"], [
            f"O diesel {main_n} custou em média {brl(main_v['media'])} por litro em {label} na semana de {per}, segundo a ANP.",
            f"Em {label}, o preço médio do diesel {main_n} foi de {brl(main_v['media'])} por litro na semana de {per}, conforme levantamento da ANP.",
            f"Na semana de {per}, a ANP encontrou o diesel {main_n} a {brl(main_v['media'])} por litro, em média, nos postos pesquisados de {label}.",
            f"Quem abasteceu em {label} na semana de {per} pagou em média {brl(main_v['media'])} pelo litro do diesel {main_n}, de acordo com a ANP."])
        extra = f" Foram pesquisados {main_v['postos']} postos; o menor preço encontrado foi {brl(main_v['min'])} e o maior, {brl(main_v['max'])}."
        rows = []
        for nm, v, pvv in (("Diesel S10", s10, pv.get("s10")), ("Diesel S500", s5, pv.get("s500"))):
            if v: rows.append([nm, brl(v["media"]), brl(v["min"]), brl(v["max"]), v["postos"], pct(v["media"], (pvv or {}).get("media"))])
        comp = []
        for nm, key in (("S10", "s10"), ("S500", "s500")):
            if d.get(key) and st.get(key): comp.append([f"Diesel {nm}", brl(d[key]["media"]), brl(st[key]["media"]), brl(BRv.get(key, {}).get("media"))])
        viz = sorted([x for x in cities.values() if x["uf"] == uf and x is not c], key=lambda x: -(x["d"].get("s10") or x["d"].get("s500"))["postos"])[:6]
        fq = [(f"Qual o preço do diesel em {nome} hoje?", f"Na semana de {per}, o diesel {main_n} teve preço médio de {brl(main_v['media'])} por litro em {label}, com mínimo de {brl(main_v['min'])} e máximo de {brl(main_v['max'])}, segundo o levantamento semanal da ANP em {main_v['postos']} postos.")]
        if s10 and st.get("s10"):
            diff = s10["media"] - st["s10"]["media"]
            fq.append((f"O diesel em {nome} está mais caro que a média de {UFN[uf]}?", f"Na semana de {per}, o diesel S10 em {label} custou {brl(s10['media'])}, {'acima' if diff > 0 else 'abaixo' if diff < 0 else 'igual'} da média estadual de {brl(st['s10']['media'])} por litro{f', uma diferença de {brl(abs(diff))}' if diff else ''}. Dados da ANP."))
        if s10 and s5:
            fq.append((f"Qual a diferença de preço entre diesel S10 e S500 em {nome}?", f"Na semana de {per}, o S10 custou em média {brl(s10['media'])} e o S500, {brl(s5['media'])} por litro em {label}. O S10 tem menor teor de enxofre e é exigido por caminhões fabricados a partir de 2012 com motores Euro 5 ou mais recentes."))
        if pv.get("s10") and s10:
            fq.append((f"O preço do diesel subiu em {nome} nesta semana?", f"O diesel S10 em {label} passou de {brl(pv['s10']['media'])} para {brl(s10['media'])} por litro entre a semana anterior e a semana de {per}, variação de {pct(s10['media'], pv['s10']['media'])}, segundo a ANP."))
        # --- dados próprios da cidade: ranking no estado/Brasil, tendência de 8 semanas, custo de tanque
        mk = "s10" if s10 else "s500"
        pares_uf = sorted([x for x in cities.values() if x["uf"] == uf and x["d"].get(mk)], key=lambda x: x["d"][mk]["media"])
        pares_br = sorted([x for x in cities.values() if x["d"].get(mk)], key=lambda x: x["d"][mk]["media"])
        pos_uf = next(i for i, x in enumerate(pares_uf) if x is c) + 1; pos_br = next(i for i, x in enumerate(pares_br) if x is c) + 1
        serie = [(w, ((db["semanas"][w]["municipios"].get(k) or {}).get(mk) or {}).get("media")) for w in weeks]; serie = [(w, v) for w, v in serie if v]
        brm = (BRv.get(mk) or {}).get("media"); stm = (st.get(mk) or {}).get("media")
        fq.append((f"Em que posição {nome} está no ranking do diesel {main_n} de {UFN[uf]}?", f"Na semana de {per}, {label} teve o {pos_uf}º menor preço médio do diesel {main_n} entre as {len(pares_uf)} cidades de {UFN[uf]} pesquisadas pela ANP, e o {pos_br}º menor entre as {len(pares_br)} cidades do país com esse produto na pesquisa."))
        if brm: fq.append((f"O diesel em {nome} está acima da média do Brasil?", f"Na semana de {per}, o diesel {main_n} em {label} custou {brl(main_v['media'])}, {'acima' if main_v['media'] > brm else 'abaixo' if main_v['media'] < brm else 'igual'} da média nacional de {brl(brm)} por litro ({pct(main_v['media'], brm)}), segundo a ANP."))
        fq.append((f"Quanto custa encher um tanque de 300 litros de diesel em {nome}?", f"Pelo preço médio do diesel {main_n} da semana de {per} ({brl(main_v['media'])}/l), 300 litros custam cerca de {brl(main_v['media'] * 300)}; no posto mais barato pesquisado ({brl(main_v['min'])}/l) seriam {brl(main_v['min'] * 300)}. Estimativa a partir dos preços da ANP."))
        if len(serie) >= 2:
            hi = max(serie, key=lambda x: x[1]); lo = min(serie, key=lambda x: x[1])
            fq.append((f"Como o preço do diesel variou em {nome} nas últimas semanas?", f"Nas {len(serie)} semanas com dados da ANP para {label}, o diesel {main_n} teve média mais alta de {brl(hi[1])} (semana encerrada em {dbr(hi[0])}) e mais baixa de {brl(lo[1])} (semana encerrada em {dbr(lo[0])}). Na semana de {per}, ficou em {brl(main_v['media'])}."))
        fq.append((f"Quantos postos a ANP pesquisou em {nome}?", f"Na semana de {per}, a ANP pesquisou {main_v['postos']} posto(s) com diesel {main_n} em {label}. A diferença entre o maior ({brl(main_v['max'])}) e o menor preço ({brl(main_v['min'])}) foi de {brl(main_v['max'] - main_v['min'])} por litro."))
        rk_html = (f"<h2>{E(nome)} no ranking do diesel {main_n}</h2><ul><li>{pos_uf}º menor preço entre {len(pares_uf)} cidades pesquisadas em {UFN[uf]}" + (f" (média estadual {brl(stm)})" if stm else "") + f"</li><li>{pos_br}º menor preço entre {len(pares_br)} cidades do Brasil" + (f" (média nacional {brl(brm)}, diferença de {pct(main_v['media'], brm)})" if brm else "") + "</li>"
                   + (f"<li>Faixa nas últimas {len(serie)} semanas: de {brl(min(v for _, v in serie))} a {brl(max(v for _, v in serie))}</li>" if len(serie) >= 2 else "")
                   + f"<li>Diferença entre o posto mais caro e o mais barato: {brl(main_v['max'] - main_v['min'])} por litro em {main_v['postos']} posto(s)</li></ul>")
        if len(pares_uf) > 1:
            vz = [x for x in pares_uf if x is not c]; mais_barata = vz[0]; mais_cara = vz[-1]
            rk_html += f"<p>Em {UFN[uf]}, a cidade com {main_n} mais barato na semana foi <a href=\"/diesel/{mais_barata['slug']}/\">{E(mais_barata['nome'])}</a> ({brl(mais_barata['d'][mk]['media'])}) e a mais cara, <a href=\"/diesel/{mais_cara['slug']}/\">{E(mais_cara['nome'])}</a> ({brl(mais_cara['d'][mk]['media'])}).</p>"
        # leitura da semana: frases escolhidas pelos próprios números (não por sorteio)
        lt = []
        if stm and brm:
            acima_uf, acima_br = main_v["media"] > stm, main_v["media"] > brm
            lt.append({(True, True): f"{nome} ficou acima tanto da média de {UFN[uf]} quanto da média do país, o que encarece o abastecimento local frente a outras praças.",
                       (True, False): f"O preço em {nome} superou a média de {UFN[uf]}, mas ficou abaixo da média nacional: o estado como um todo tem diesel mais barato que o país.",
                       (False, True): f"{nome} teve diesel mais barato que a média de {UFN[uf]}, embora ainda acima da média nacional, refletindo um estado de preços altos.",
                       (False, False): f"{nome} ficou abaixo das médias de {UFN[uf]} e do Brasil, o que torna a cidade um ponto de abastecimento competitivo na região."}[(acima_uf, acima_br)])
        if pv.get(mk) and pv[mk].get("media"):
            dv = main_v["media"] - pv[mk]["media"]
            lt.append(f"Na comparação com a semana anterior, o litro {'subiu ' + brl(dv) if dv > 0.004 else 'caiu ' + brl(-dv) if dv < -0.004 else 'ficou praticamente estável'}" + (f", indo de {brl(pv[mk]['media'])} para {brl(main_v['media'])}." if abs(dv) > 0.004 else "."))
        spr = main_v["max"] - main_v["min"]
        if main_v["postos"] < 5: lt.append(f"Com apenas {main_v['postos']} posto(s) na amostra, a média é sensível a poucos preços; vale comparar com cidades vizinhas.")
        elif spr >= 0.5: lt.append(f"A diferença de {brl(spr)} por litro entre os postos pesquisados é alta: pesquisar antes de abastecer pode render economia relevante numa carreta.")
        else: lt.append(f"Os preços entre os {main_v['postos']} postos pesquisados variaram pouco ({brl(spr)} por litro), indicando mercado local homogêneo.")
        if s10 and s5: lt.append(f"O S500 saiu {brl(abs(s10['media'] - s5['media']))} {'mais barato' if s5['media'] < s10['media'] else 'mais caro'} que o S10 por litro.")
        rk_html = f"<h2>Leitura da semana em {E(nome)}</h2><p>{E(' '.join(lt))}</p>" + rk_html
        uniq = len(rows) * 5 + len(comp) + (1 if pv else 0)
        robots = None if uniq >= 5 else "noindex,follow"
        body = f"""<article class="post data">{crumbs_html(E, [("Início", "/"), ("Diesel", "/diesel/"), (UFN[uf], f"/diesel/estado/{uf.lower()}/"), (label, url)])}
<h1>Preço do diesel em {E(label)}</h1><p class="snippet">{E(abert + extra)}</p>{aviso}
<h2>Preço do diesel em {E(nome)} nesta semana</h2>{table(rows, ["Produto", "Média", "Mínimo", "Máximo", "Postos", "Var. semana"])}
{f'<h2>{E(nome)} comparado ao estado e ao Brasil</h2>' + table(comp, ["Produto", label, UFN[uf], "Brasil"]) if comp else ''}
{rk_html}
<h2>Histórico do diesel em {E(nome)}</h2>{hist(lambda w: w["municipios"].get(k))}

<h2>Perguntas frequentes sobre o diesel em {E(nome)}</h2>{faq_block(E, fq)}
{f'<h2>Diesel em outras cidades de {UFN[uf]}</h2><div class="chips">' + "".join(f'<a class="chip" href="/diesel/{x["slug"]}/">{E(x["nome"])}</a>' for x in viz) + "</div>" if viz else ''}
<p class="src">Fonte: {src}. <a href="/metodologia/">Metodologia</a> · <a href="/calculadoras/custo-diesel-viagem/">Calcular custo de viagem</a></p></article>"""
        ld = {"@context": "https://schema.org", "@graph": [ds(f"Preço do diesel em {label}", f"{nome}, {UFN[uf]}", c), faq_ld(fq),
              crumbs_ld(BASE, [("Início", "/"), ("Diesel", "/diesel/"), (UFN[uf], f"/diesel/estado/{uf.lower()}/"), (label, url)])]}
        title = f"Preço do diesel em {nome} ({uf}) hoje: S10 e S500"
        desc = f"Diesel {main_n} a {brl(main_v['media'])}/l em média em {label} ({per}), segundo a ANP. Veja mínimo, máximo, histórico e comparação com {uf} e Brasil."
        B.write(url, B.page(title, desc[:155], url, body, jsonld=ld, robots=robots))
        if not robots: urls.append(url); lastmod[url] = fim
    # ---- estados
    for uf, d in sorted(cur["estados"].items()):
        url = f"/diesel/estado/{uf.lower()}/"; s10, s5 = d.get("s10"), d.get("s500"); pv = prev.get("estados", {}).get(uf, {})
        cs = sorted([x for x in cities.values() if x["uf"] == uf and x["d"].get("s10")], key=lambda x: x["d"]["s10"]["media"])
        rows = [[f'<a href="/diesel/{x["slug"]}/">{E(x["nome"])}</a>', brl(x["d"]["s10"]["media"]), brl((x["d"].get("s500") or {}).get("media")), x["d"]["s10"]["postos"]] for x in cs]
        fq = [(f"Qual o preço médio do diesel em {UFN[uf]}?", f"Na semana de {per}, o diesel S10 custou em média {brl(s10['media'])} por litro em {UFN[uf]}" + (f" e o S500, {brl(s5['media'])}" if s5 else "") + f", segundo a ANP, com {s10['postos']} postos pesquisados para o S10.")] if s10 else []
        if cs: fq.append((f"Onde o diesel S10 está mais barato em {UFN[uf]}?", f"Entre as cidades pesquisadas pela ANP na semana de {per}, o menor preço médio do S10 em {UFN[uf]} foi em {cs[0]['nome']}, com {brl(cs[0]['d']['s10']['media'])} por litro, e o maior em {cs[-1]['nome']}, com {brl(cs[-1]['d']['s10']['media'])}."))
        if s10 and BRv.get("s10"): fq.append((f"O diesel em {UFN[uf]} está acima da média nacional?", f"Na semana de {per}, o S10 em {UFN[uf]} custou {brl(s10['media'])}, contra média nacional de {brl(BRv['s10']['media'])} por litro, diferença de {pct(s10['media'], BRv['s10']['media'])}, conforme a ANP."))
        if s10:
            est_rank = sorted([(u2, d2["s10"]["media"]) for u2, d2 in cur["estados"].items() if d2.get("s10")], key=lambda x: x[1]); pe = [u2 for u2, _ in est_rank].index(uf) + 1
            fq.append((f"Em que posição {UFN[uf]} está no ranking do diesel entre os estados?", f"Na semana de {per}, {UFN[uf]} teve o {pe}º menor preço médio do diesel S10 entre as {len(est_rank)} unidades da federação pesquisadas pela ANP."))
            if pv.get("s10"): fq.append((f"O diesel subiu em {UFN[uf]} nesta semana?", f"O S10 passou de {brl(pv['s10']['media'])} para {brl(s10['media'])} por litro em {UFN[uf]} entre a semana anterior e a de {per} ({pct(s10['media'], pv['s10']['media'])}), segundo a ANP."))
            fq.append((f"Quantas cidades de {UFN[uf]} têm preço do diesel pesquisado pela ANP?", f"Na semana de {per}, a ANP pesquisou o diesel S10 em {len(cs)} cidade(s) de {UFN[uf]}, somando {s10['postos']} postos. As cidades fora da amostra não têm preço oficial naquela semana."))
            fq.append((f"Quanto custa encher um tanque de 300 litros em {UFN[uf]}?", f"Pela média estadual do S10 na semana de {per} ({brl(s10['media'])}/l), 300 litros custam cerca de {brl(s10['media'] * 300)}. Estimativa a partir dos preços da ANP."))
        body = f"""<article class="post data">{crumbs_html(E, [("Início", "/"), ("Diesel", "/diesel/"), (UFN[uf], url)])}
<h1>Preço do diesel em {UFN[uf]} ({uf})</h1>
<p class="snippet">{E(f"Na semana de {per}, o diesel S10 custou em média {brl((s10 or {}).get('media'))} por litro em {UFN[uf]}, variação de {pct((s10 or {}).get('media'), (pv.get('s10') or {}).get('media'))} sobre a semana anterior, segundo a ANP.")}</p>{aviso}
<h2>Diesel por cidade em {UFN[uf]}</h2>{table(rows, ["Cidade", "Diesel S10", "Diesel S500", "Postos (S10)"]) if rows else "<p>Sem cidades com S10 pesquisado nesta semana.</p>"}
<h2>Histórico do diesel em {UFN[uf]}</h2>{hist(lambda w: w["estados"].get(uf))}
<h2>Perguntas frequentes</h2>{faq_block(E, fq)}</article>"""
        ld = {"@context": "https://schema.org", "@graph": [ds(f"Preço do diesel em {UFN[uf]}", UFN[uf], d), faq_ld(fq), crumbs_ld(BASE, [("Início", "/"), ("Diesel", "/diesel/"), (UFN[uf], url)])]}
        B.write(url, B.page(f"Preço do diesel em {UFN[uf]} hoje: S10 e S500 por cidade", f"Diesel S10 a {brl((s10 or {}).get('media'))}/l em média em {UFN[uf]} ({per}). Preços por cidade, histórico e comparação com o Brasil. Dados da ANP."[:155], url, body, jsonld=ld))
        urls.append(url); lastmod[url] = fim
    # ---- Brasil
    url = "/diesel/"
    srows = [[f'<a href="/diesel/estado/{uf.lower()}/">{UFN[uf]}</a>', brl((d.get("s10") or {}).get("media")), brl((d.get("s500") or {}).get("media")), pct((d.get("s10") or {}).get("media"), (prev.get("estados", {}).get(uf, {}).get("s10") or {}).get("media"))]
             for uf, d in sorted(cur["estados"].items(), key=lambda x: -((x[1].get("s10") or {}).get("media") or 0))]
    cs = sorted([x for x in cities.values() if x["d"].get("s10")], key=lambda x: x["d"]["s10"]["media"])
    top = lambda L: table([[f'<a href="/diesel/{x["slug"]}/">{E(x["nome"])} ({x["uf"]})</a>', brl(x["d"]["s10"]["media"]), x["d"]["s10"]["postos"]] for x in L], ["Cidade", "Diesel S10", "Postos"])
    ests = sorted([(uf, d["s10"]["media"]) for uf, d in cur["estados"].items() if d.get("s10")], key=lambda x: x[1])
    fq = [("Qual o preço médio do diesel no Brasil hoje?", f"Na semana de {per}, o diesel S10 custou em média {brl(BRv['s10']['media'])} por litro no Brasil e o S500, {brl(BRv['s500']['media'])}, segundo levantamento da ANP em {BRv['s10']['postos']} e {BRv['s500']['postos']} postos, respectivamente."),
          ("Qual estado tem o diesel mais barato?", f"Na semana de {per}, o menor preço médio do diesel S10 foi em {UFN[ests[0][0]]}, com {brl(ests[0][1])} por litro, e o maior em {UFN[ests[-1][0]]}, com {brl(ests[-1][1])}, de acordo com a ANP."),
          ("O preço do diesel subiu nesta semana?", f"A média nacional do diesel S10 passou de {brl((BRp.get('s10') or {}).get('media'))} para {brl(BRv['s10']['media'])} por litro entre a semana anterior e a semana de {per}, variação de {pct(BRv['s10']['media'], (BRp.get('s10') or {}).get('media'))}, segundo a ANP."),
          ("Qual a diferença entre diesel S10 e S500?", "O número indica o teor máximo de enxofre: 10 e 500 partes por milhão. O S10 polui menos e é obrigatório para caminhões com motores Euro 5 ou mais recentes, fabricados a partir de 2012. O S500 ainda é usado por veículos mais antigos e máquinas, e costuma ser mais barato."),
          ("De onde vêm os preços do diesel desta página?", f"Do Levantamento de Preços de Combustíveis da ANP, que pesquisa semanalmente postos em centenas de municípios brasileiros. O Modal News baixa o arquivo oficial, organiza os números por cidade e estado e atualiza as páginas automaticamente, sem estimativas próprias.")]
    body = f"""<article class="post data">{crumbs_html(E, [("Início", "/"), ("Diesel", url)])}
<h1>Preço do diesel hoje no Brasil</h1>
<p class="snippet">{E(f"Na semana de {per}, o diesel S10 custou em média {brl(BRv['s10']['media'])} por litro no Brasil ({pct(BRv['s10']['media'], (BRp.get('s10') or {}).get('media'))} na semana) e o S500, {brl(BRv['s500']['media'])}, segundo a ANP.")}</p>{aviso}
<nav class="toc"><strong>Nesta página</strong><ol><li><a href="#estados">Diesel por estado</a></li><li><a href="#baratas">Cidades com diesel mais barato</a></li><li><a href="#caras">Cidades com diesel mais caro</a></li><li><a href="#historico">Histórico nacional</a></li><li><a href="#faq">Perguntas frequentes</a></li></ol></nav>
<h2 id="estados">Preço do diesel por estado</h2>{table(srows, ["Estado", "Diesel S10", "Diesel S500", "Var. S10 semana"])}
<h2 id="baratas">10 cidades com o diesel S10 mais barato</h2>{top(cs[:10])}
<h2 id="caras">10 cidades com o diesel S10 mais caro</h2>{top(cs[::-1][:10])}
<h2 id="historico">Histórico do diesel no Brasil</h2>{hist(lambda w: w["brasil"].get("BR"))}
<h2 id="faq">Perguntas frequentes sobre o preço do diesel</h2>{faq_block(E, fq)}
<h2>Todas as cidades pesquisadas</h2><p class="meta">{len(cities)} municípios com diesel pesquisado pela ANP nesta semana.</p><div class="chips small">{"".join(f'<a class="chip" href="/diesel/{x["slug"]}/">{E(x["nome"])} ({x["uf"]})</a>' for x in sorted(cities.values(), key=lambda x: B.slugify(x["nome"])))}</div></article>"""
    ld = {"@context": "https://schema.org", "@graph": [ds("Preço do diesel no Brasil por estado e cidade", None, BRv), faq_ld(fq), crumbs_ld(BASE, [("Início", "/"), ("Diesel", url)])]}
    B.write(url, B.page("Preço do diesel hoje: S10 e S500 por estado e cidade (ANP)", f"Diesel S10 a {brl(BRv['s10']['media'])}/l em média no Brasil ({per}). Preços por estado e por cidade, ranking e histórico semanal com dados da ANP."[:155], url, body, jsonld=ld))
    urls.append(url); lastmod[url] = fim
    js = {"semana": per, "fim": fim, "brasil": {k: v["media"] for k, v in BRv.items()}, "estados": {uf: {k: v["media"] for k, v in d.items()} for uf, d in cur["estados"].items()}}
    (B.OUT / "static" / "diesel.json").write_text(json.dumps(js, ensure_ascii=False), encoding="utf-8")
    print(f"Diesel: {len(cities)} cidades, {len(cur['estados'])} estados, semana {per}")
    return urls, lastmod

# ------------------------------------------------------------------ CALCULADORAS
def calculadoras(B):
    E, BASE, CFG = B.E, B.BASE, B.CFG; urls = []
    app = lambda name, url, desc: {"@type": "WebApplication", "name": name, "url": BASE + url, "applicationCategory": "BusinessApplication", "operatingSystem": "Web", "description": desc,
                                   "offers": {"@type": "Offer", "price": "0", "priceCurrency": "BRL"}, "inLanguage": "pt-BR"}
    # cubagem
    url = "/calculadoras/cubagem/"
    fq = [("Como calcular a cubagem de uma caixa?", "Multiplique comprimento, largura e altura em metros para obter o volume em metros cúbicos. Depois, multiplique o volume pelo fator de cubagem da transportadora. No rodoviário, o fator mais comum é 300 kg por metro cúbico. O frete é cobrado pelo maior valor entre peso real e peso cubado."),
          ("Qual o fator de cubagem no transporte rodoviário?", "O padrão mais usado no Brasil é 300 kg por metro cúbico, mas cada transportadora define o seu fator na tabela de frete. Correios e empresas de encomendas podem usar outros fatores. Confirme sempre o valor previsto no contrato ou na cotação antes de calcular."),
          ("Qual o fator de cubagem no transporte aéreo?", "No aéreo, a referência internacional é 1 metro cúbico para 166,7 kg, o mesmo que dividir o volume em centímetros cúbicos por 6.000. Como o espaço no avião é mais caro, cargas volumosas e leves pagam proporcionalmente mais do que no rodoviário."),
          ("Por que a transportadora cobra pelo peso cubado?", "Porque o caminhão pode lotar pelo volume antes de atingir o limite de peso. Uma carga leve e volumosa, como travesseiros ou isopor, ocupa espaço que poderia levar outras mercadorias. O peso cubado equilibra a cobrança entre cargas pesadas e compactas e cargas leves e volumosas."),
          ("Como reduzir o peso cubado das remessas?", "Use caixas do tamanho certo para cada produto, elimine espaços vazios, prefira embalagens desmontáveis e monte paletes compactos. No e-commerce, sugerir automaticamente a menor caixa possível para cada pedido costuma reduzir de forma visível o gasto com frete.")]
    body = f"""<article class="post data">{crumbs_html(E, [("Início", "/"), ("Calculadoras", "/calculadoras/cubagem/"), ("Cubagem", url)])}
<h1>Calculadora de cubagem e peso cubado</h1>
<p class="snippet">Informe as medidas da embalagem, a quantidade de volumes e o fator de cubagem. A calculadora mostra o volume em m³, o peso cubado e qual peso será usado na cobrança do frete.</p>
<form class="calc" id="cub" onsubmit="return false">
<label>Comprimento (cm)<input type="number" id="c" value="60" min="0" step="0.1"></label>
<label>Largura (cm)<input type="number" id="l" value="40" min="0" step="0.1"></label>
<label>Altura (cm)<input type="number" id="a" value="40" min="0" step="0.1"></label>
<label>Quantidade de volumes<input type="number" id="q" value="1" min="1" step="1"></label>
<label>Peso real total (kg)<input type="number" id="p" value="10" min="0" step="0.1"></label>
<label>Fator de cubagem (kg/m³)<select id="f"><option value="300">300 — rodoviário (padrão)</option><option value="166.7">166,7 — aéreo</option><option value="250">250</option><option value="200">200</option></select></label>
</form><div class="calc-out" id="out" aria-live="polite"></div>
<script>
(function(){{var $=function(i){{return document.getElementById(i)}};function n(v){{return isFinite(v)?v.toLocaleString('pt-BR',{{maximumFractionDigits:3}}):'—'}}
function go(){{var v=($('c').value*$('l').value*$('a').value)/1e6*$('q').value,cub=v*parseFloat($('f').value),pr=parseFloat($('p').value)||0,tax=Math.max(cub,pr);
$('out').innerHTML='<p><strong>Volume total:</strong> '+n(v)+' m³</p><p><strong>Peso cubado:</strong> '+n(cub)+' kg</p><p><strong>Peso taxável:</strong> '+n(tax)+' kg ('+(cub>pr?'peso cubado':'peso real')+')</p>'}}
document.querySelectorAll('#cub input,#cub select').forEach(function(e){{e.addEventListener('input',go)}});go()}})();
</script>
<h2>Como a cubagem é calculada</h2><p>Volume (m³) = comprimento × largura × altura (em metros) × número de volumes. Peso cubado (kg) = volume × fator de cubagem. Exemplo: uma caixa de 60 × 40 × 40 cm tem 0,096 m³; com fator 300, o peso cubado é 28,8 kg. Se a caixa pesa 10 kg, o frete é calculado sobre 28,8 kg.</p>
<p>Saiba mais no verbete <a href="/glossario/peso-cubado/">peso cubado</a> e em <a href="/glossario/cubagem/">cubagem</a>.</p>
<h2>Perguntas frequentes sobre cubagem</h2>{faq_block(E, fq)}</article>"""
    ld = {"@context": "https://schema.org", "@graph": [app("Calculadora de cubagem e peso cubado", url, "Calcula volume, peso cubado e peso taxável para frete."), faq_ld(fq),
          crumbs_ld(BASE, [("Início", "/"), ("Calculadoras", url), ("Cubagem", url)])]}
    B.write(url, B.page("Calculadora de cubagem: peso cubado online grátis", "Calcule a cubagem e o peso cubado da carga em m³ e kg, com fator 300 (rodoviário) ou 166,7 (aéreo), e veja qual peso a transportadora vai cobrar.", url, body, jsonld=ld)); urls.append(url)
    # custo diesel viagem
    url = "/calculadoras/custo-diesel-viagem/"
    fq2 = [("Quanto um caminhão gasta de diesel por quilômetro?", "Depende do tipo de veículo, carga, relevo e condução. Como referência de mercado, caminhões pesados carregados costumam fazer entre 2 e 3 km por litro, e veículos leves de carga bem mais. Use o consumo real medido na sua frota para ter uma estimativa confiável."),
           ("Como calcular o custo de diesel de uma viagem?", "Divida a distância em quilômetros pelo consumo em km por litro para obter os litros necessários. Multiplique os litros pelo preço do diesel. Exemplo: 400 km a 2,5 km/l consomem 160 litros; a R$ 6,50 por litro, o custo é de R$ 1.040, sem contar ida e volta."),
           ("Qual preço de diesel usar no cálculo?", "O ideal é usar o preço que você realmente paga. Como referência, a calculadora traz a média semanal da ANP por estado para o diesel S10 e S500, atualizada automaticamente. Em viagens longas, considere a média entre os estados onde vai abastecer."),
           ("O custo de diesel é o mesmo que o custo do frete?", "Não. O diesel é o maior item, mas o frete também inclui salário do motorista, pedágios, manutenção, pneus, depreciação, seguro, impostos e margem. Para cargas de lotação, a ANTT define um piso mínimo de frete que considera esses custos."),
           ("Devo considerar a viagem de volta?", "Sim, se o caminhão voltar vazio. O retorno sem carga também consome diesel e precisa ser coberto pelo frete de ida ou por um frete de retorno. Marque a opção de ida e volta na calculadora para ver o custo total do percurso.")]
    body = f"""<article class="post data">{crumbs_html(E, [("Início", "/"), ("Calculadoras", url), ("Custo de diesel", url)])}
<h1>Calculadora de custo de diesel por viagem</h1>
<p class="snippet">Informe a distância, o consumo do caminhão e o preço do diesel. O preço médio semanal da ANP por estado já vem preenchido como referência e pode ser alterado.</p>
<form class="calc" id="dv" onsubmit="return false">
<label>Distância (km)<input type="number" id="km" value="400" min="0"></label>
<label>Consumo (km/l)<input type="number" id="kml" value="2.5" min="0.1" step="0.1"></label>
<label>Estado de referência<select id="uf"></select></label>
<label>Produto<select id="pr"><option value="s10">Diesel S10</option><option value="s500">Diesel S500</option></select></label>
<label>Preço do litro (R$)<input type="number" id="pl" step="0.01"></label>
<label class="chk"><input type="checkbox" id="iv"> Ida e volta</label>
</form><div class="calc-out" id="dout" aria-live="polite"></div><p class="meta" id="dsrc"></p>
<script>
(function(){{var $=function(i){{return document.getElementById(i)}},D=null;function brl(v){{return v.toLocaleString('pt-BR',{{style:'currency',currency:'BRL'}})}}
function setp(){{if(!D)return;var u=$('uf').value,p=$('pr').value,v=u==='BR'?D.brasil[p]:(D.estados[u]||{{}})[p];if(v)$('pl').value=v.toFixed(2);go()}}
function go(){{var km=+$('km').value*($('iv').checked?2:1),l=km/(+$('kml').value||1),c=l*(+$('pl').value||0);$('dout').innerHTML='<p><strong>Diesel necessário:</strong> '+l.toLocaleString('pt-BR',{{maximumFractionDigits:1}})+' litros</p><p><strong>Custo de diesel:</strong> '+brl(c)+'</p><p><strong>Custo por km:</strong> '+brl(c/(km||1))+'</p>'}}
fetch('{B.PREFIX}/static/diesel.json').then(function(r){{return r.json()}}).then(function(d){{D=d;var o='<option value="BR">Brasil (média)</option>';Object.keys(d.estados).sort().forEach(function(u){{o+='<option value="'+u+'">'+u+'</option>'}});$('uf').innerHTML=o;$('dsrc').textContent='Preço de referência: média ANP da semana de '+d.semana+'.';setp()}});
['uf','pr'].forEach(function(i){{$(i).addEventListener('change',setp)}});['km','kml','pl','iv'].forEach(function(i){{$(i).addEventListener('input',go)}});go()}})();
</script>
<p>Veja o <a href="/diesel/">preço do diesel por estado e cidade</a> e o verbete <a href="/glossario/frete-minimo/">frete mínimo</a>.</p>
<h2>Perguntas frequentes sobre custo de diesel</h2>{faq_block(E, fq2)}</article>"""
    ld = {"@context": "https://schema.org", "@graph": [app("Calculadora de custo de diesel por viagem", url, "Calcula litros e custo de diesel de uma viagem de caminhão com preços médios da ANP."), faq_ld(fq2),
          crumbs_ld(BASE, [("Início", "/"), ("Calculadoras", url), ("Custo de diesel", url)])]}
    B.write(url, B.page("Calculadora de custo de diesel por viagem de caminhão", "Calcule quantos litros de diesel e quanto custa uma viagem de caminhão, com o preço médio semanal da ANP por estado já preenchido.", url, body, jsonld=ld)); urls.append(url)
    return urls

# ------------------------------------------------------------------ CONFIANÇA E APOIO
LINKS = [
 ("Regulação", [("ANTT — Agência Nacional de Transportes Terrestres", "https://www.gov.br/antt/pt-br"), ("ANTAQ — Agência Nacional de Transportes Aquaviários", "https://www.gov.br/antaq/pt-br")]),
 ("Documentos fiscais", [("Portal Nacional do CT-e", "https://www.cte.fazenda.gov.br/portal/"), ("Portal do MDF-e (SVRS)", "https://dfe-portal.svrs.rs.gov.br/Mdfe")]),
 ("Comércio exterior", [("Portal Siscomex", "https://www.gov.br/siscomex/pt-br"), ("Receita Federal — Aduana e Comércio Exterior", "https://www.gov.br/receitafederal/pt-br/assuntos/aduana-e-comercio-exterior"), ("MDIC — Drawback", "https://www.gov.br/mdic/pt-br/assuntos/comercio-exterior/drawback"), ("ICC — Incoterms® rules", "https://iccwbo.org/business-solutions/incoterms-rules/")]),
 ("Combustível", [("ANP — Levantamento de Preços de Combustíveis", ANP_PAGE)]),
 ("Entidades do setor", [("CNT — Confederação Nacional do Transporte", "https://www.cnt.org.br/"), ("NTC&Logística", "https://portalntc.org.br/"), ("ABOL — Associação Brasileira de Operadores Logísticos", "https://abolbrasil.org.br/"), ("GS1 Brasil", "https://www.gs1br.org/")]),
 ("Dados públicos", [("IBGE — Localidades (API)", "https://servicodados.ibge.gov.br/api/docs/localidades")]),
 ("Ferramentas do Modal News", [("Calculadora de cubagem", "/calculadoras/cubagem/"), ("Calculadora de custo de diesel", "/calculadoras/custo-diesel-viagem/"), ("Preço do diesel por cidade", "/diesel/"), ("Glossário de Logística", "/glossario/"), ("Siglas da logística", "/siglas/")]),
]

FAQ_INST = {
 "/sobre/": [("O Modal News é gratuito?", "Sim. Todo o conteúdo, inclusive glossário, páginas de dados e calculadoras, é de acesso livre e não exige cadastro."),
   ("O Modal News usa inteligência artificial para escrever notícias?", "Não. As notícias são resumos curtos extraídos dos feeds públicos das fontes, sempre com link para o original; as páginas de dados são geradas a partir de bases oficiais."),
   ("De onde vêm as notícias?", "De feeds RSS públicos de portais especializados em logística e transporte, listados no repositório do site. Só entram notícias que tenham foto na fonte; aqui a capa é um card gráfico do Modal News, sem reproduzir a foto de terceiros."),
   ("Com que frequência o site é atualizado?", "As notícias são coletadas a cada 30 minutos; dados como preço do diesel e tarifas de pedágio são atualizados quando os órgãos oficiais publicam novas versões."),
   ("Quem mantém o Modal News?", "A empresa indicada no expediente, que também traz CNPJ e endereço. O código que gera o site é aberto.")],
 "/politica-editorial/": [("O Modal News reescreve notícias de outros sites?", "Não. Publicamos o título original, um resumo curto do próprio feed e o link para a fonte."),
   ("Por que as páginas de notícias não aparecem no Google?", "Porque o conteúdo pertence à fonte original. Essas páginas levam noindex; o que indexamos é o conteúdo próprio do portal."),
   ("Como as notícias são escolhidas?", "Por fontes pré-selecionadas do setor e filtros automáticos de relevância, de palavras bloqueadas e de fontes bloqueadas."),
   ("Uma notícia fora do tema pode ser removida?", "Sim. Itens fora do tema são removidos, ficam registrados e não voltam a ser coletados."),
   ("As imagens das notícias são creditadas?", "Sim. Cada imagem traz o nome da fonte e a matéria tem link para o original. Titulares podem pedir remoção pela política descrita nos termos de uso.")],
 "/metodologia/": [("De onde vêm os preços do diesel?", "Do Levantamento de Preços de Combustíveis da ANP, publicado semanalmente."),
   ("Como são calculadas as distâncias entre cidades?", "Pelo roteador OSRM com dados do OpenStreetMap, entre os centros dos municípios, guardadas em cache."),
   ("De onde vêm as tarifas de pedágio e o frete mínimo?", "Dos dados abertos e das resoluções da ANTT, com o ato normativo indicado em cada página."),
   ("O Modal News faz estimativas próprias de preço?", "Não. Mostramos os números publicados pelas fontes; cálculos derivados, como custo de diesel de uma viagem, são indicados como estimativa e mostram a fórmula."),
   ("Onde vejo o código que gera os dados?", "No repositório público do site, indicado nesta página.")],
 "/correcoes/": [("Como peço uma correção?", "Pelos canais da página de contato ou abrindo um pedido no repositório público, informando página, trecho e a fonte que comprova a correção."),
   ("Em quanto tempo a correção é feita?", "Erros factuais são corrigidos assim que confirmados."),
   ("As correções ficam registradas?", "Sim, no histórico público de commits do repositório, com data e descrição."),
   ("E se o erro estiver numa notícia de outro portal?", "O erro deve ser comunicado à fonte original; podemos remover a notícia do Modal News."),
   ("Posso sugerir um termo novo para o glossário?", "Sim, pelos mesmos canais usados para correções.")],
 "/privacidade/": [("O Modal News usa cookies?", "Não usamos cookies próprios, ferramentas de audiência nem anúncios."),
   ("O site coleta meus dados pessoais?", "Não. Não há cadastro nem formulários próprios; a hospedagem (GitHub Pages) pode registrar dados técnicos de acesso para segurança."),
   ("Os valores digitados nas calculadoras são enviados a algum servidor?", "Não. Os cálculos são feitos no seu navegador."),
   ("Quem é o controlador para fins da LGPD?", "A empresa indicada nesta página e no expediente, com CNPJ e endereço."),
   ("Como exerço meus direitos de titular?", "Pelo canal indicado nesta página. Para assuntos com dados pessoais, não use o canal público de issues.")],
 "/contato/": [("Como falo com o Modal News?", "Pelos canais listados nesta página."),
   ("Como peço a remoção de uma imagem ou notícia?", "Envie a URL da página, o conteúdo e a comprovação de titularidade; a remoção ocorre em até 2 dias úteis, conforme os termos de uso."),
   ("Onde peço correção de um dado?", "Pelos mesmos canais; veja também a política de correções."),
   ("Posso enviar dados pessoais pelo canal público de issues?", "Não. O repositório é público; para assuntos de privacidade use a correspondência ou o e-mail, quando disponível."),
   ("Onde estão CNPJ e endereço da empresa responsável?", "Nesta página e no expediente.")],
 "/termos/": [("Posso reproduzir o conteúdo do Modal News?", "Textos próprios podem ser citados com link para a página de origem. Notícias de terceiros pertencem às fontes."),
   ("Como funciona a remoção de conteúdo a pedido do titular?", "O titular envia URL, conteúdo e comprovação pelos canais de contato; removemos em até 2 dias úteis e bloqueamos nova coleta."),
   ("Os dados das páginas são oficiais?", "Vêm de fontes oficiais indicadas em cada página, mas podem ter defasagem; confira sempre a fonte."),
   ("As calculadoras substituem tabelas oficiais?", "Não. Os resultados são estimativas."),
   ("Os termos podem mudar?", "Sim, e as mudanças ficam no histórico público do repositório.")],
}

def confianca(B, terms_count):
    E, BASE, CFG = B.E, B.BASE, B.CFG; urls = []
    repo = CFG.get("repo_url", "https://github.com/tpb-ux/modalnews")
    pages = {
     "/sobre/": ("Sobre o Modal News", "O que é o Modal News, para quem é feito e como o portal funciona.", f"""
<p>O Modal News é um portal de notícias e referência sobre logística, transporte, armazenagem, supply chain e comércio exterior no Brasil. O objetivo é reunir, num só lugar, as notícias do setor, um glossário técnico em português e páginas de dados públicos úteis para quem trabalha com carga.</p>
<h2>O que você encontra aqui</h2><ul><li><strong>Notícias do setor:</strong> curadoria automática de portais especializados, sempre com título original, resumo curto e link para a fonte.</li>
<li><strong>Glossário de Logística:</strong> {terms_count} verbetes escritos para o portal, com exemplos e referências oficiais.</li>
<li><strong>Dados públicos:</strong> preço do diesel por cidade e estado (ANP), atualizado toda semana.</li>
<li><strong>Calculadoras:</strong> cubagem e custo de diesel por viagem.</li></ul>
<h2>Como o portal é feito</h2><p>O site é estático, gerado por código aberto e publicado automaticamente. Não usamos inteligência artificial para escrever ou reescrever notícias. Veja a <a href="/politica-editorial/">política editorial</a> e a <a href="/metodologia/">metodologia de dados</a>.</p>"""),
     "/politica-editorial/": ("Política editorial", "Como o Modal News escolhe fontes, usa RSS, atribui créditos e separa notícia de referência.", """
<h2>Notícias de outras fontes</h2><p>As notícias da home e das editorias vêm de feeds RSS públicos de portais especializados do setor. Só publicamos notícias que tenham foto na fonte, mas não reproduzimos essa foto: a capa é um card gráfico produzido pelo Modal News. Para cada item publicamos apenas o título original, um resumo curto do próprio feed e o link "Leia na íntegra" para a fonte. Não reescrevemos nem reproduzimos o texto completo de terceiros.</p>
<p>As páginas individuais dessas notícias não são indexadas pelos buscadores (noindex), porque o conteúdo pertence à fonte original.</p>
<h2>Seleção e filtros</h2><p>Mantemos uma lista de fontes do setor e aplicamos filtros automáticos de relevância, bloqueio de fontes e de palavras (política, crimes, promoções e assuntos fora da logística). Itens removidos ficam registrados para não voltarem.</p>
<h2>Conteúdo próprio</h2><p>O glossário, as calculadoras e as páginas de dados são produzidos pelo Modal News. Textos de referência não trazem opinião. Dados numéricos sempre indicam fonte e data.</p>
<h2>Imagens</h2><p>Imagens de notícias são creditadas à fonte. Fotos do glossário vêm de bancos com licença livre (CC0, domínio público ou CC BY), com autor e licença na legenda. Ilustrações sem crédito são produzidas pelo portal.</p>"""),
     "/metodologia/": ("Metodologia de dados", "De onde vêm os números do Modal News, com que frequência são atualizados e quais são os limites.", f"""
<h2>Preço do diesel</h2><p><strong>Fonte:</strong> <a href="{ANP_PAGE}" target="_blank" rel="noopener">Levantamento de Preços de Combustíveis da ANP</a>, arquivo semanal "resumo semanal".<br><strong>Atualização:</strong> automática, sempre que a ANP publica uma nova semana.<br><strong>O que mostramos:</strong> preço médio, mínimo e máximo de revenda e número de postos, para óleo diesel S10 e óleo diesel (B S500 comum), por município, estado e Brasil. Guardamos as últimas 8 semanas.<br><strong>Limites:</strong> só aparecem municípios pesquisados pela ANP naquela semana. Não fazemos estimativas, médias próprias nem projeções. Nomes de municípios são padronizados pela base de localidades do IBGE.</p>
<h2>Calculadoras</h2><p>A calculadora de cubagem usa a fórmula volume × fator de cubagem, com fatores de referência (300 kg/m³ rodoviário, 166,7 kg/m³ aéreo) que podem ser alterados. A calculadora de custo de diesel usa distância ÷ consumo × preço, com o preço médio da ANP como valor inicial editável. Os resultados são estimativas e não substituem tabelas e contratos das transportadoras.</p>
<h2>Notícias</h2><p>Coletadas a cada 30 minutos de feeds RSS públicos, com deduplicação por link e título e filtros de relevância descritos na <a href="/politica-editorial/">política editorial</a>. Os resumos ficam fora do índice de buscadores (noindex). A imagem de cada resumo é um card gráfico produzido pelo Modal News (título, editoria e fonte), sem fotos de terceiros; fotos de fontes só são usadas quando a licença do veículo permite a reprodução e é citada.</p>
<h2>Rotas e distâncias</h2><p>Distância e tempo por estrada calculados com o OSRM (Open Source Routing Machine) sobre dados do OpenStreetMap (© colaboradores do OpenStreetMap, licença ODbL), entre os centroides IBGE dos municípios. O tempo é do roteador para automóvel, sem paradas; caminhões levam mais. Praças de pedágio federais (ANTT) entram quando estão a até 250 m do traçado; pedágios estaduais não estão incluídos. Só ficam no índice as rotas com ao menos uma praça federal no traçado.</p>
<h2>Cidades, estados e polos</h2><p>População e PIB: IBGE (Censo 2022, PIB dos Municípios, Malhas Territoriais), via API oficial servicodados.ibge.gov.br. Polos regionais: IBGE, Regiões de Influência das Cidades 2018 (REGIC). Distâncias em linha reta são medidas entre centroides IBGE. Praças e volumes de tráfego: ANTT, dados abertos.</p>
<h2>Qualidade e indexação</h2><p>Cada página de dados passa por regras automáticas antes de ir ao índice: mínimo de 300 palavras, dados suficientes e uma medida de texto próprio (a parcela do texto que não se repete nas demais páginas da mesma família). Páginas abaixo do corte continuam acessíveis, mas com noindex. As perguntas frequentes das páginas por cidade e rota são no máximo três, só com respostas que trazem dado da própria página. Os dados estão disponíveis em CSV na página de <a href="/dados/">dados abertos</a>.</p>
<h2>Código aberto</h2><p>Todo o processo está no repositório público <a href="{repo}" target="_blank" rel="noopener">{repo}</a>.</p>"""),
     "/correcoes/": ("Política de correções", "Como pedir correção de um conteúdo do Modal News e como as correções são registradas.", f"""
<p>Se você encontrou um erro em um verbete, em uma página de dados ou em uma calculadora, avise-nos. Corrigimos erros factuais assim que confirmados e registramos a alteração no histórico público do repositório.</p>
<h2>Como pedir uma correção</h2><p>Abra um pedido em <a href="{repo}/issues" target="_blank" rel="noopener">{repo}/issues</a> informando a página, o trecho e, se possível, a fonte que comprova a correção.</p>
<h2>Notícias de terceiros</h2><p>Erros no conteúdo de notícias de outros portais devem ser comunicados à fonte original, indicada no link "Leia na íntegra". Se a notícia não for do setor ou estiver incorreta, podemos removê-la do Modal News.</p>
<h2>Registro de correções</h2><p>Todas as alterações de conteúdo ficam no <a href="{repo}/commits/main" target="_blank" rel="noopener">histórico de commits</a>, com data e descrição.</p>"""),
     "/privacidade/": ("Política de privacidade", "Quais dados o Modal News coleta (nenhum por conta própria), cookies e hospedagem.", """
<p>O Modal News não tem cadastro, formulários, cookies próprios, ferramentas de análise de audiência nem anúncios. Não coletamos dados pessoais dos visitantes.</p>
<h2>Hospedagem</h2><p>O site é hospedado no GitHub Pages. Como qualquer servidor web, o provedor de hospedagem pode registrar dados técnicos de acesso, como endereço IP, para segurança e operação, conforme a <a href="https://docs.github.com/pt/site-policy/privacy-policies/github-general-privacy-statement" target="_blank" rel="noopener">declaração de privacidade do GitHub</a>.</p>
<h2>Links externos</h2><p>Ao clicar em links para fontes de notícias e órgãos públicos, você passa a seguir as políticas desses sites.</p>
<h2>Calculadoras</h2><p>Os cálculos são feitos no seu navegador. Os valores digitados não são enviados a nenhum servidor.</p>
<h2>Seus direitos (LGPD)</h2><p>Como não coletamos dados pessoais, não há dados seus armazenados pelo Modal News. Ainda assim, você pode exercer os direitos previstos no art. 18 da Lei 13.709/2018 (confirmação de tratamento, acesso, correção, eliminação e informação sobre compartilhamento).</p>
<h2>Controlador e canal do titular</h2><p>Controlador: <strong>{EMP_RS}</strong>, CNPJ {EMP_CNPJ}, {EMP_END}. {CANAL_LGPD} Respondemos em até 15 dias, conforme o art. 19 da LGPD. Veja também a página de <a href="/contato/">contato</a>.</p>"""),
     "/contato/": ("Contato", "Como falar com o Modal News: correções, remoção de conteúdo e imagens, privacidade (LGPD) e sugestões de pauta.", """
<p>O Modal News é mantido por <strong>{EMP_RS}</strong>, CNPJ {EMP_CNPJ}, {EMP_END}.</p>
<h2>Canais</h2><ul>{CANAIS}</ul>
<h2>Assuntos</h2><ul><li><strong>Correção de conteúdo:</strong> informe a página e o trecho; veja a <a href="/correcoes/">política de correções</a>.</li>
<li><strong>Remoção de notícia ou imagem:</strong> veja a <a href="/termos/#remocao">política de remoção</a> nos termos de uso.</li>
<li><strong>Privacidade e LGPD:</strong> veja a <a href="/privacidade/">política de privacidade</a>.</li>
<li><strong>Dados do expediente:</strong> veja o <a href="/expediente/">expediente</a>.</li></ul>"""),
     "/termos/": ("Termos de uso", "Regras de uso do Modal News: conteúdo de terceiros, imagens, dados públicos, calculadoras e política de remoção de conteúdo.", """
<h2>Aceitação</h2><p>Ao usar o Modal News você concorda com estes termos. O portal é gratuito, não exige cadastro e é mantido por <strong>{EMP_RS}</strong>, CNPJ {EMP_CNPJ}.</p>
<h2>Notícias de terceiros</h2><p>As notícias da home e das editorias são resumos curtos de feeds RSS públicos, sempre com o nome da fonte e o link "Leia na íntegra". Os direitos sobre o texto original pertencem aos respectivos veículos. As páginas individuais dessas notícias não são indexadas pelos buscadores.</p>
<h2>Imagens</h2><p>Imagens de notícias são as divulgadas pela própria fonte no feed ou na página da matéria, exibidas com crédito à fonte e link para o original. Fotos do glossário vêm de bancos com licença livre, com autor e licença na legenda.</p>
<h2 id="remocao">Política de remoção de conteúdo e imagens</h2><p>Se você é titular de direitos de um texto ou imagem exibido aqui e não autoriza o uso, envie o pedido por um dos canais da página de <a href="/contato/">contato</a> informando: a URL da página no Modal News, o conteúdo em questão e a comprovação de titularidade. Removemos o conteúdo em até 2 dias úteis após o recebimento, e o item fica registrado para não voltar a ser coletado.</p>
<h2>Dados públicos e calculadoras</h2><p>Preços, distâncias, tarifas e pisos de frete vêm de fontes oficiais indicadas em cada página (ANP, ANTT, IBGE, ANAC, ANTAQ, OpenStreetMap/OSRM) e podem conter defasagem. Os resultados das calculadoras são estimativas e não substituem contratos, tabelas e documentos oficiais. Veja a <a href="/metodologia/">metodologia</a>.</p>
<h2>Reprodução</h2><p>Textos próprios (glossário, guias e páginas de dados) podem ser citados com link para a página de origem.</p>
<h2>Alterações</h2><p>Estes termos podem ser atualizados; as mudanças ficam registradas no histórico público do repositório do site.</p>"""),
    }
    emp = CFG.get("empresa") or {}; en = emp.get("endereco") or {}
    email = (emp.get("email") or "").strip(); form = (emp.get("formulario_url") or "").strip(); dpo = (emp.get("encarregado_lgpd") or "").strip()
    canais = ([f'<li>E-mail: <a href="mailto:{E(email)}">{E(email)}</a></li>'] if email else []) + ([f'<li><a href="{E(form)}" target="_blank" rel="noopener">Formulário de contato</a></li>'] if form else []) \
        + [f'<li>Pedidos públicos (correções e remoções): <a href="{repo}/issues" target="_blank" rel="noopener">{repo}/issues</a></li>'] \
        + [f'<li>Correspondência: {E(emp.get("razao_social", ""))}, {E(en.get("logradouro", ""))}, {E(en.get("bairro", ""))}, {E(en.get("cidade", ""))}-{E(en.get("uf", ""))}, CEP {E(en.get("cep", ""))}</li>']
    canal = (f"Encarregado: {E(dpo)}. " if dpo else "") + (f'Pedidos do titular: <a href="mailto:{E(email)}">{E(email)}</a>.' if email else "Pedidos do titular podem ser enviados por correspondência ao endereço acima ou pelos canais da página de contato; para dados pessoais, não use o canal público de issues.")
    rep = {"{EMP_RS}": E(emp.get("razao_social", "")), "{EMP_CNPJ}": E(emp.get("cnpj", "")), "{EMP_END}": E(f'{en.get("logradouro", "")}, {en.get("bairro", "")}, {en.get("cidade", "")}-{en.get("uf", "")}, CEP {en.get("cep", "")}'), "{CANAIS}": "".join(canais), "{CANAL_LGPD}": canal}
    for url, (h1, desc, html) in pages.items():
        for k, v in rep.items(): html = html.replace(k, v)
        fq = FAQ_INST.get(url, [])
        body = f'<article class="post">{crumbs_html(E, [("Início", "/"), (h1, url)])}<h1>{E(h1)}</h1>{html}{faq_block(E, fq) if fq else ""}</article>'
        B.write(url, B.page(f"{h1} | {CFG['site_name']}", desc, url, body, jsonld={"@context": "https://schema.org", "@graph": [{"@type": "ContactPage" if url == "/contato/" else "WebPage", "name": h1, "url": BASE + url}, crumbs_ld(BASE, [("Início", "/"), (h1, url)])] + ([faq_ld(fq)] if fq else [])}))
        urls.append(url)
    # links úteis
    url = "/links-uteis/"
    html = "".join(f"<h2>{E(g)}</h2><ul class='refs'>" + "".join(f'<li><a href="{u}"' + (' target="_blank" rel="noopener"' if u.startswith("http") else "") + f">{E(n)}</a></li>" for n, u in L) + "</ul>" for g, L in LINKS)
    body = f'<article class="post">{crumbs_html(E, [("Início", "/"), ("Links úteis", url)])}<h1>Links úteis para logística e transporte</h1><p class="snippet">Atalhos para órgãos reguladores, portais fiscais, comércio exterior, preços de combustível e entidades do setor, além das ferramentas do Modal News. Todos os links externos são verificados.</p>{html}</article>'
    B.write(url, B.page("Links úteis de logística: ANTT, CT-e, MDF-e, Siscomex e ANP", "Links oficiais para ANTT, ANTAQ, CT-e, MDF-e, Siscomex, Receita Federal, ANP e entidades do setor de transporte e logística.", url, body,
                        jsonld={"@context": "https://schema.org", "@graph": [{"@type": "CollectionPage", "name": "Links úteis", "url": BASE + url}, crumbs_ld(BASE, [("Início", "/"), ("Links úteis", url)])]}))
    urls.append(url)
    # 404
    body404 = '<article class="post"><h1>Página não encontrada</h1><p>O endereço pode ter mudado. Tente um destes caminhos:</p><ul class="refs"><li><a href="/">Últimas notícias</a></li><li><a href="/glossario/">Glossário de Logística</a></li><li><a href="/siglas/">Siglas da logística</a></li><li><a href="/diesel/">Preço do diesel por cidade</a></li><li><a href="/calculadoras/cubagem/">Calculadora de cubagem</a></li></ul></article>'
    (B.OUT / "404.html").write_text(re.sub(r'(href|src)="/(?!/)', lambda m: f'{m.group(1)}="{B.PREFIX}/', B.page(f"Página não encontrada | {CFG['site_name']}", "Página não encontrada.", "/404.html", body404, robots="noindex")), encoding="utf-8")
    return urls

def siglas(B, terms):
    E, BASE = B.E, B.BASE; url = "/siglas/"
    sig = sorted([t for t in terms if t["t"].replace("-", "").replace("&", "").replace(" ", "").isupper() or (t["t"].isupper())], key=lambda t: t["t"].upper())
    rows = "".join(f'<tr><td><a href="/glossario/{t["slug"]}/"><strong>{E(t["t"])}</strong></a></td><td>{E(t.get("n") or "")}</td></tr>' for t in sig)
    body = f'<article class="post">{crumbs_html(E, [("Início", "/"), ("Siglas", url)])}<h1>Siglas da logística e do transporte</h1><p class="snippet">Lista de A a Z com {len(sig)} siglas usadas em transporte, armazenagem, supply chain e comércio exterior, com o nome por extenso e link para a explicação completa no Glossário de Logística.</p><div class="tbl"><table><thead><tr><th>Sigla</th><th>Significado</th></tr></thead><tbody>{rows}</tbody></table></div></article>'
    ld = {"@context": "https://schema.org", "@graph": [{"@type": "DefinedTermSet", "name": "Siglas da logística", "url": BASE + url,
          "hasDefinedTerm": [{"@type": "DefinedTerm", "name": t["t"], **({"alternateName": t["n"]} if t.get("n") else {}), "url": f"{BASE}/glossario/{t['slug']}/"} for t in sig]},
          crumbs_ld(BASE, [("Início", "/"), ("Siglas", url)])]}
    B.write(url, B.page("Siglas da logística: significado de CT-e, MDF-e, WMS, FOB e mais", f"{len(sig)} siglas de logística e transporte com significado: CT-e, MDF-e, RNTRC, WMS, TMS, FOB, CIF, OTIF, SLA, TEU e outras.", url, body, jsonld=ld))
    return [url]

def extras(B, info):
    """llms.txt e saude.json"""
    BASE, CFG = B.BASE, B.CFG
    llms = f"""# {CFG['site_name']}

> Portal brasileiro de notícias e referência sobre logística, transporte, supply chain e comércio exterior. Conteúdo próprio: glossário técnico em português, preços semanais do diesel por cidade (dados da ANP) e calculadoras.

## Referência
- [Glossário de Logística]({BASE}/glossario/): {info['termos']} verbetes com definição, exemplo, FAQ e fontes oficiais
- [Siglas da logística]({BASE}/siglas/)
- [Links úteis]({BASE}/links-uteis/)

## Dados
- [Preço do diesel no Brasil]({BASE}/diesel/): S10 e S500 por estado e por cidade, semanal, fonte ANP
- [Metodologia]({BASE}/metodologia/)

- [Frete mínimo ANTT]({BASE}/frete-minimo/): tabela vigente e calculadora
- [Portos brasileiros]({BASE}/portos/): movimentação oficial (ANTAQ, MPor)
- [Rodovias federais concedidas]({BASE}/rodovias/): pedágios e tráfego de caminhões (ANTT)
- [Guias práticos]({BASE}/guias/): CT-e, MDF-e, frete mínimo, exportação

## Ferramentas
- [Calculadora de cubagem]({BASE}/calculadoras/cubagem/)
- [Calculadora de custo de diesel por viagem]({BASE}/calculadoras/custo-diesel-viagem/)

## Sobre
- [Sobre]({BASE}/sobre/) · [Política editorial]({BASE}/politica-editorial/) · [Correções]({BASE}/correcoes/)
"""
    (B.OUT / "llms.txt").write_text(llms, encoding="utf-8")
