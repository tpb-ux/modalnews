"""Lote 2: frete mínimo ANTT, portos (ANTAQ/MPor), rodovias concedidas (ANTT) e guias HowTo. Só dados oficiais."""
import json, re, yaml
from paginas import brl, dbr, faq_block, faq_ld, crumbs_ld, crumbs_html, UFN
MES = ["", "jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
def num(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
def words(h): return len(re.sub(r"<[^>]+>", " ", h).split())
def table(rows, head):
    return f'<div class="tbl"><table><thead><tr>{"".join(f"<th>{h}</th>" for h in head)}</tr></thead><tbody>' + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table></div>"
def link(u, t): return f'<a href="{u}" target="_blank" rel="noopener">{t}</a>'

# ------------------------------------------------------------------ FRETE MÍNIMO
def frete_minimo(B):
    E, BASE = B.E, B.BASE
    f = B.ROOT / "data" / "frete_minimo.json"
    if not f.exists(): return [], {}
    D = json.loads(f.read_text(encoding="utf-8")); ato, EIX, T = D["ato"], D["eixos"], D["tabelas"]
    vig = dbr(ato["vigencia"]); urls = []; lm = {}
    fonte = f'<p class="meta">Fonte: {link(ato["url"], E(ato["nome"]))} (ANTTlegis), em vigor desde {vig}, que reajusta o Anexo II da {E(ato["resolucao_base"])}. Diesel S10 de referência: {brl(ato["diesel_ref"])}/l ({E(ato["diesel_ref_semana"])}). Base legal: {link(ato["lei"], "Lei nº 13.703/2018")}.</p>'
    aviso = '<p class="warn">Valor de referência calculado pela tabela oficial da ANTT. Não substitui a consulta ao ato oficial nem considera regras específicas (como retorno vazio, operações de alto desempenho fora das tabelas C/D ou valores de pedágio, que são pagos à parte). Confira sempre o ato vigente.</p>'
    def slug(s): return B.slugify(s)
    def tab_rows(t, carga):
        c = T[t]["cargas"][carga]; return [[f"{e} eixos", (brl(c["ccd"][e]) + "/km") if c["ccd"][e] else "—", brl(c["cc"][e]) if c["cc"][e] else "—"] for e in EIX]
    js = json.dumps({"eixos": EIX, "t": {k: {"titulo": v["titulo"], "c": v["cargas"]} for k, v in T.items()}}, ensure_ascii=False)
    # páginas por tipo de carga (Tabela A)
    for carga, c in T["A"]["cargas"].items():
        u = f"/frete-minimo/{slug(carga)}/"; ok = [e for e in EIX if c["ccd"][e]]
        e0 = "5" if "5" in ok else ok[0]; ex_km = 500; ex_v = ex_km * c["ccd"][e0] + c["cc"][e0]
        fq = [(f"Qual o frete mínimo da ANTT para {carga.lower()}?", f"Pela {ato['nome']}, em vigor desde {vig}, o piso para {carga.lower()} com {e0} eixos (Tabela A) é de {brl(c['ccd'][e0])} por km mais {brl(c['cc'][e0])} de carga e descarga. Em {ex_km} km, o mínimo é {brl(ex_v)}."),
              ("Como calcular o frete mínimo?", "Multiplique a distância em km pelo coeficiente de deslocamento (CCD) do tipo de carga e do número de eixos carregados, e some o coeficiente de carga e descarga (CC). O resultado é o piso por viagem, sem pedágio, que é pago à parte."),
              ("Quando a tabela de frete mínimo muda?", "A ANTT publica novos coeficientes na revisão periódica e sempre que o preço do diesel varia mais de 5% em relação ao valor de referência, como prevê o § 3º do art. 5º da Lei 13.703/2018. Este portal atualiza a página quando sai um novo ato.")]
        v1000 = 1000 * c["ccd"][e0] + c["cc"][e0]
        fq.append((f"Quanto é o frete mínimo de {carga.lower()} para 1.000 km?", f"Com {e0} eixos, 1.000 km × {brl(c['ccd'][e0])} + {brl(c['cc'][e0])} = {brl(v1000)}, pela {ato['nome']}. Pedágio é pago à parte, por meio do Vale-Pedágio."))
        if len(ok) > 1:
            lo_, hi_ = ok[0], ok[-1]
            fq.append((f"Quanto o número de eixos muda o frete mínimo de {carga.lower()}?", f"Na Tabela A, o coeficiente por km vai de {brl(c['ccd'][lo_])} com {lo_} eixos a {brl(c['ccd'][hi_])} com {hi_} eixos. Em {ex_km} km, o piso passa de {brl(ex_km * c['ccd'][lo_] + c['cc'][lo_])} para {brl(ex_km * c['ccd'][hi_] + c['cc'][hi_])}."))
        cgx = T["A"]["cargas"].get("Carga Geral")
        if cgx and carga != "Carga Geral" and cgx["ccd"].get(e0):
            vg = ex_km * cgx["ccd"][e0] + cgx["cc"][e0]
            fq.append((f"O frete mínimo de {carga.lower()} é mais caro que o de carga geral?", f"Em {ex_km} km com {e0} eixos, o piso de {carga.lower()} é {brl(ex_v)}, contra {brl(vg)} da carga geral, diferença de {brl(ex_v - vg)} ({f"{(ex_v / vg - 1) * 100:+.1f}".replace(".", ",")}%)."))
        elif carga == "Carga Geral":
            gs = T["A"]["cargas"].get("Granel sólido")
            if gs and gs["ccd"].get(e0): fq.append(("Carga geral paga mais que granel sólido?", f"Em {ex_km} km com {e0} eixos, carga geral tem piso de {brl(ex_v)} e granel sólido, {brl(ex_km * gs['ccd'][e0] + gs['cc'][e0])}, pela {ato['nome']}."))
        body = f"""<article class="post data">{crumbs_html(E, [("Início", "/"), ("Frete mínimo", "/frete-minimo/"), (carga, u)])}
<h1>Frete mínimo ANTT para {E(carga.lower())}</h1>
<p class="snippet">{E(f"O piso mínimo de frete para {carga.lower()} em carga lotação vai de {brl(c['ccd'][ok[0]])}/km ({ok[0]} eixos) a {brl(c['ccd'][ok[-1]])}/km ({ok[-1]} eixos), mais o valor fixo de carga e descarga, segundo a tabela da ANTT em vigor desde {vig}.")}</p>{fonte}
<h2>Tabela A — composição veicular ou caminhão simples</h2>{table(tab_rows("A", carga), ["Eixos carregados", "Deslocamento (CCD)", "Carga e descarga (CC)"])}
<h2>Tabela B — apenas unidade de tração</h2>{table(tab_rows("B", carga), ["Eixos carregados", "Deslocamento (CCD)", "Carga e descarga (CC)"])}
<h2>Exemplo de cálculo</h2><p>Viagem de {ex_km} km com {carga.lower()} em veículo de {e0} eixos (Tabela A): {ex_km} × {brl(c['ccd'][e0])} + {brl(c['cc'][e0])} = <strong>{brl(ex_v)}</strong>. Faça outros cálculos na <a href="/frete-minimo/">calculadora de frete mínimo</a>.</p>{aviso}
<h2>Perguntas frequentes</h2>{faq_block(E, fq)}
<h2>Outros tipos de carga</h2><div class="chips">{"".join(f'<a class="chip" href="/frete-minimo/{slug(k)}/">{E(k)}</a>' for k in T["A"]["cargas"] if k != carga)}</div></article>"""
        ld = {"@context": "https://schema.org", "@graph": [{"@type": "Dataset", "name": f"Piso mínimo de frete ANTT — {carga}", "creator": {"@type": "Organization", "name": "Agência Nacional de Transportes Terrestres (ANTT)"}, "isBasedOn": ato["url"], "dateModified": ato["vigencia"], "license": "https://dados.gov.br/dados/conteudo/licencas"}, faq_ld(fq), crumbs_ld(BASE, [("Início", "/"), ("Frete mínimo", "/frete-minimo/"), (carga, u)])]}
        B.write(u, B.page(f"Frete mínimo ANTT {carga.lower()}: tabela por eixo"[:60], f"Tabela de frete mínimo da ANTT para {carga.lower()} por número de eixos, em vigor desde {vig}: coeficientes CCD e CC, exemplo de cálculo e calculadora."[:155], u, body, jsonld=ld))
        urls.append(u); lm[u] = ato["vigencia"]
    # índice + calculadora
    u = "/frete-minimo/"; cg = T["A"]["cargas"]["Carga Geral"]
    fq = [("O que é o frete mínimo da ANTT?", "É o piso que deve ser pago no transporte rodoviário remunerado de carga lotação, instituído pela Lei 13.703/2018 (Política Nacional de Pisos Mínimos do Transporte Rodoviário de Cargas). A ANTT publica os coeficientes por tipo de carga e número de eixos carregados."),
          ("Qual a tabela de frete mínimo vigente?", f"A tabela vigente é a da {ato['nome']}, em vigor desde {vig}. Ela usa como referência o diesel S10 a {brl(ato['diesel_ref'])} por litro, média Brasil da ANP na semana de {ato['diesel_ref_semana'].split(' (')[0]}."),
          ("Qual a diferença entre as tabelas A, B, C e D?", "A tabela A vale quando se contrata a composição veicular completa ou o caminhão simples. A B, quando se contrata só o cavalo mecânico. As tabelas C e D repetem essas situações para operações de alto desempenho, definidas na resolução da ANTT."),
          ("O pedágio está incluído no frete mínimo?", "Não. O piso calculado pela tabela da ANTT não inclui pedágio. O valor do pedágio deve ser pago à parte pelo contratante, por meio do vale-pedágio obrigatório previsto na Lei 10.209/2001."),
          ("Quanto é o frete mínimo de uma carreta de 5 eixos com carga geral?", f"Pela tabela A vigente, carga geral com 5 eixos tem CCD de {brl(cg['ccd']['5'])} por km e CC de {brl(cg['cc']['5'])}. Para 1.000 km, o piso é {brl(1000 * cg['ccd']['5'] + cg['cc']['5'])}, sem pedágio.")]
    sel = "".join(f'<option value="{E(k)}"{" selected" if k == "Carga Geral" else ""}>{E(k)}</option>' for k in T["A"]["cargas"])
    body = f"""<article class="post data">{crumbs_html(E, [("Início", "/"), ("Frete mínimo", u)])}
<h1>Frete mínimo ANTT: tabela vigente e calculadora</h1>
<p class="snippet">{E(f"A tabela de frete mínimo da ANTT em vigor desde {vig} ({ato['nome']}) define o piso do transporte rodoviário de carga lotação por tipo de carga e número de eixos. Frete mínimo = distância × CCD + CC. Calcule abaixo.")}</p>{fonte}
<form class="calc" id="fm" onsubmit="return false">
<label>Tabela<select id="tb">{"".join(f'<option value="{k}">{k} — {E(v["titulo"])}</option>' for k, v in T.items())}</select></label>
<label>Tipo de carga<select id="cg">{sel}</select></label>
<label>Eixos carregados<select id="ex"></select></label>
<label>Distância (km)<input type="number" id="km" value="500" min="1"></label></form>
<div class="calc-out" id="fout" aria-live="polite"></div>{aviso}
<script>(function(){{var D={js},$=function(i){{return document.getElementById(i)}};function brl(v){{return v.toLocaleString('pt-BR',{{style:'currency',currency:'BRL'}})}}
function fill(){{var c=D.t[$('tb').value].c[$('cg').value],cur=$('ex').value,o='';D.eixos.forEach(function(e){{if(c&&c.ccd[e])o+='<option value="'+e+'"'+(e===cur?' selected':'')+'>'+e+' eixos</option>'}});$('ex').innerHTML=o||'<option>—</option>';if(!$('ex').value&&$('ex').options.length)$('ex').selectedIndex=$('ex').options.length>3?3:0;go()}}
function go(){{var c=D.t[$('tb').value].c[$('cg').value],e=$('ex').value,km=+$('km').value||0;if(!c||!c.ccd[e]){{$('fout').innerHTML='<p>Combinação sem coeficiente na tabela oficial.</p>';return}}var v=km*c.ccd[e]+c.cc[e];
$('fout').innerHTML='<p><strong>Frete mínimo:</strong> '+brl(v)+'</p><p>'+km+' km × '+brl(c.ccd[e])+'/km + '+brl(c.cc[e])+' (carga e descarga)</p>'}}
['tb','cg'].forEach(function(i){{$(i).addEventListener('change',fill)}});$('ex').addEventListener('change',go);$('km').addEventListener('input',go);$('ex').innerHTML='<option value="5">5</option>';fill()}})();</script>
<h2>Tabela A vigente: deslocamento (CCD, R$/km)</h2>{table([[f'<a href="/frete-minimo/{slug(k)}/">{E(k)}</a>'] + [num(v["ccd"][e], 4) if v["ccd"][e] else "—" for e in EIX] for k, v in T["A"]["cargas"].items()], ["Tipo de carga"] + [f"{e} eixos" for e in EIX])}
<h2>Tabela A vigente: carga e descarga (CC, R$)</h2>{table([[E(k)] + [num(v["cc"][e], 2) if v["cc"][e] else "—" for e in EIX] for k, v in T["A"]["cargas"].items()], ["Tipo de carga"] + [f"{e} eixos" for e in EIX])}
<p>Células com "—" são configurações de eixos não usadas para aquele tipo de carga, conforme nota do próprio ato. As tabelas B, C e D estão na calculadora acima e nas páginas de cada tipo de carga.</p>
<h2>Como o frete mínimo é calculado</h2><p>O piso é a soma de duas parcelas: o custo de deslocamento, proporcional à distância (km × CCD), e o custo de carga e descarga, fixo por viagem (CC). Os coeficientes variam conforme o tipo de carga, o número de eixos carregados e a forma de contratação. Veja o passo a passo no <a href="/guias/como-calcular-frete-minimo-antt/">guia de cálculo do frete mínimo</a> e o verbete <a href="/glossario/frete-minimo/">frete mínimo</a>. Para o custo de combustível da viagem, use a <a href="/calculadoras/custo-diesel-viagem/">calculadora de diesel</a> e o <a href="/diesel/">preço do diesel por cidade</a>.</p>
<h2>Perguntas frequentes sobre frete mínimo</h2>{faq_block(E, fq)}</article>"""
    ld = {"@context": "https://schema.org", "@graph": [{"@type": "WebApplication", "name": "Calculadora de frete mínimo ANTT", "url": BASE + u, "applicationCategory": "BusinessApplication", "operatingSystem": "Web", "offers": {"@type": "Offer", "price": "0", "priceCurrency": "BRL"}},
          {"@type": "Dataset", "name": "Coeficientes do piso mínimo de frete — ANTT", "creator": {"@type": "Organization", "name": "ANTT"}, "isBasedOn": ato["url"], "dateModified": ato["vigencia"], "license": "https://dados.gov.br/dados/conteudo/licencas"}, faq_ld(fq), crumbs_ld(BASE, [("Início", "/"), ("Frete mínimo", u)])]}
    B.write(u, B.page("Frete mínimo ANTT 2026: tabela vigente e calculadora", f"Tabela de frete mínimo da ANTT em vigor desde {vig} e calculadora por tipo de carga e eixos. Fórmula, exemplos e link para o ato oficial."[:155], u, body, jsonld=ld))
    urls.insert(0, u); lm[u] = ato["vigencia"]
    return urls, lm

# ------------------------------------------------------------------ PORTOS
def portos(B):
    E, BASE = B.E, B.BASE
    D = yaml.safe_load((B.ROOT / "data" / "portos.yaml").read_text(encoding="utf-8")); F = D["fontes"]
    def fl(k): return link(F[k]["url"], E(F[k]["nome"]))
    urls = []; lm = {}
    news_all = getattr(B, "_posts", [])
    for p in D["portos"]:
        u = f"/portos/{p['slug']}/"; nome = p["nome"]; short = re.sub(r"^Porto (de|do|da) ", "", nome); art = "no" if nome.startswith("Porto do ") else "em"; artp = "do" if nome.startswith("Porto do ") else "de"
        data_pts = 0; blocks = []; fq = []; used = set()
        if p.get("t3"):
            t, var, rk = p["t3"]; data_pts += 3; used.add("boletim3t25")
            blocks.append(f"<h2>Movimentação de cargas {art} {E(short)}</h2><p>No 3º trimestre de 2025, o {E(nome)} movimentou <strong>{num(t, 1)} milhões de toneladas</strong>, variação de {var} sobre o 3º trimestre de 2024, e ficou em <strong>{rk}º lugar</strong> entre os portos organizados do país, segundo a ANTAQ.</p>")
            fq.append((f"Quanto o {nome} movimenta?", f"No 3º trimestre de 2025, o {nome} movimentou {num(t, 1)} milhões de toneladas, {var} em relação ao mesmo trimestre de 2024, segundo o Boletim Estatístico Aquaviário da ANTAQ. Foi o {rk}º maior porto organizado do Brasil no período."))
        if p.get("teu3"):
            teu, var = p["teu3"]; data_pts += 2
            blocks.append(f"<p>Em contêineres, foram <strong>{num(teu)} mil TEUs</strong> no 3º trimestre de 2025 ({var}), de acordo com a mesma publicação.</p>")
            fq.append((f"Quantos contêineres o {nome} movimenta?", f"Segundo a ANTAQ, o {nome} movimentou {num(teu)} mil TEUs no 3º trimestre de 2025, variação de {var} sobre o 3º trimestre de 2024. TEU é a unidade equivalente a um contêiner de 20 pés."))
        if p.get("perfil3t"):
            data_pts += len(p["perfil3t"])
            rows = [[E(m), num(a, 2), num(b, 2), f"{(a / b - 1) * 100:+.1f}%".replace(".", ",")] for m, a, b in p["perfil3t"]]
            blocks.append(f"<h2>Principais cargas {art} {E(short)}</h2>{table(rows, ['Mercadoria', '3º tri 2025 (mi t)', '3º tri 2024 (mi t)', 'Variação'])}<p class='meta'>Fonte: {fl('boletim3t25')}, figura 7.</p>")
        if p.get("graos25"):
            data_pts += 1; used.add("anuario25")
            blocks.append(f"<p>Na exportação de milho e soja, o {E(nome)} aparece com <strong>{num(p['graos25'], 1)} milhões de toneladas</strong> em 2025 no mapa das principais instalações do Desempenho Aquaviário 2025 da ANTAQ.</p>")
        for o in p.get("outros", []):
            data_pts += 1; used.add(o["f"]); blocks.append(f"<p>{E(o['txt'])} <span class='meta'>(Fonte: {fl(o['f'])})</span></p>")
        if p.get("s1_26"):
            data_pts += len(p["s1_26"]); used.add("mpor1s26")
            blocks.append(f"<h2>{E(nome)} no 1º semestre de 2026</h2><ul>" + "".join(f"<li>{E(x)}</li>" for x in p["s1_26"]) + f"</ul><p class='meta'>Fonte: {fl('mpor1s26')}, com dados enviados pelas autoridades portuárias.</p>")
            fq.append((f"Quanto o {nome} movimentou em 2026?", p["s1_26"][0] + " Dados do Ministério de Portos e Aeroportos, com base em informações da autoridade portuária."))
        info = [["Localização", f"{E(p['cidade'])} ({p['uf']})"]] + ([["Administração", E(p["autoridade"])]] if p.get("autoridade") else []) + ([["Site oficial", link(p["site"], E(p["site"].split('/')[2]))]] if p.get("site") else [])
        if p.get("autoridade"): fq.append((f"Quem administra o {nome}?", f"O {nome}, em {p['cidade']} ({p['uf']}), é um porto organizado sob administração {'do' if p['autoridade'].startswith(('Complexo','Porto')) else 'da'} {p['autoridade']}. Como porto público, está sob regulação da ANTAQ e da política do Ministério de Portos e Aeroportos."))
        if p.get("perfil3t"):
            m0 = p["perfil3t"][0]; fq.append((f"Quais as principais cargas do {nome}?", f"No 3º trimestre de 2025, a mercadoria de maior volume foi {m0[0].lower()}, com {num(m0[1], 2)} milhões de toneladas; também se destacaram " + ", ".join(x[0].lower() for x in p["perfil3t"][1:4]) + " (ANTAQ, Boletim Estatístico Aquaviário)."))
        if p.get("site"): fq.append((f"Qual o site oficial do {nome}?", f"O site oficial da administração do porto é {p['site']}, onde ficam tabelas tarifárias, regulamentos e avisos de operação."))
        fq.append((f"O {nome} é público ou privado?", f"É um porto organizado, isto é, um porto público com área delimitada por ato do Poder Executivo (Lei 12.815/2013). Dentro dele operam terminais arrendados; fora da área, terminais de uso privado operam por autorização da ANTAQ."))
        if len(fq) < 5 and p.get("graos25"): fq.append((f"O {nome} exporta grãos?", f"Sim. No Desempenho Aquaviário 2025 da ANTAQ, o {nome} aparece com {num(p['graos25'], 1)} milhões de toneladas de milho e soja exportadas em 2025."))
        if len(fq) < 5: fq.append((f"Onde ver as tarifas do {nome}?", "Pela Resolução Normativa ANTAQ nº 61/2021, cada autoridade portuária deve publicar no próprio site as tabelas tarifárias vigentes e anteriores."))
        keys = [short.lower(), nome.lower()]
        rel = [x for x in news_all if any(k in (x["titulo"] + " " + x.get("resumo", "")).lower() for k in keys)][:5]
        rel_html = ("<h2>Notícias sobre o " + E(nome) + "</h2><ul class='rel-news'>" + "".join(f'<li><a href="{x["url"]}">{E(x["titulo"])}</a></li>' for x in rel) + "</ul>") if rel else ""
        srcs = "".join(f"<li>{fl(k)}</li>" for k in F if k in used)
        lead = (f"O {nome} é um porto público localizado em {p['cidade']} ({p['uf']})" + (f", sob administração {'do' if p['autoridade'].startswith(('Complexo','Porto')) else 'da'} {p['autoridade']}" if p.get("autoridade") else "") + ". " +
                (f"No 3º trimestre de 2025, movimentou {num(p['t3'][0], 1)} milhões de toneladas ({p['t3'][1]}), o {'' if p['t3'][2] == 1 else str(p['t3'][2]) + 'º '}maior volume entre os portos organizados, segundo a ANTAQ." if p.get("t3") else (p["s1_26"][0] if p.get("s1_26") else "")))
        body = f"""<article class="post data">{crumbs_html(E, [("Início", "/"), ("Portos", "/portos/"), (nome, u)])}
<h1>{E(nome)}: movimentação e perfil de cargas</h1><p class="snippet">{E(lead)}</p>
{table(info, ["", ""])}{"".join(blocks)}
<p>Veja também o ranking na página de <a href="/portos/">portos brasileiros</a> e os verbetes <a href="/glossario/teu/">TEU</a>, <a href="/glossario/cabotagem/">cabotagem</a>, <a href="/glossario/demurrage/">demurrage</a> e <a href="/glossario/despacho-aduaneiro/">despacho aduaneiro</a>.</p>
{f'<h2>Perguntas frequentes sobre o {E(nome)}</h2>' + faq_block(E, fq) if fq else ''}{rel_html}
<h2>Fontes</h2><ul class="refs">{srcs}</ul></article>"""
        idx = data_pts >= 5
        ld = {"@context": "https://schema.org", "@graph": [{"@type": "Place", "name": nome, "url": BASE + u, "address": {"@type": "PostalAddress", "addressLocality": p["cidade"], "addressRegion": p["uf"], "addressCountry": "BR"}, **({"sameAs": [p["site"]]} if p.get("site") else {})}]
              + ([faq_ld(fq)] if fq else []) + [crumbs_ld(BASE, [("Início", "/"), ("Portos", "/portos/"), (nome, u)])]}
        B.write(u, B.page(f"{nome}: movimentação de cargas e dados oficiais"[:60], (lead if len(lead) <= 155 else lead[:152].rsplit(" ", 1)[0] + "…"), u, body, jsonld=ld, robots=None if idx else "noindex,follow"))
        if idx: urls.append(u); lm[u] = "2026-10-12"
        p["_idx"] = idx
    # índice
    u = "/portos/"
    rk = sorted([p for p in D["portos"] if p.get("t3")], key=lambda p: p["t3"][2])
    rows = [[f"{p['t3'][2]}º", f'<a href="/portos/{p["slug"]}/">{E(p["nome"])}</a>', p["uf"], num(p["t3"][0], 1), p["t3"][1]] for p in rk]
    outros = [p for p in D["portos"] if not p.get("t3")]
    fq = [("Qual o maior porto do Brasil?", f"Entre os portos organizados, o Porto de Santos (SP) lidera: movimentou {num(rk[0]['t3'][0], 1)} milhões de toneladas no 3º trimestre de 2025, segundo a ANTAQ, e 92,8 milhões t no 1º semestre de 2026, segundo o Ministério de Portos e Aeroportos."),
          ("Quanto os portos brasileiros movimentaram em 2025?", "Segundo o Desempenho Aquaviário 2025 da ANTAQ, o sistema aquaviário brasileiro movimentou 1,403 bilhão de toneladas em 2025, alta de 6,1% sobre 2024. Granéis sólidos responderam por 59,8% do total."),
          ("Qual a diferença entre porto organizado e terminal de uso privado?", "Porto organizado é o porto público, administrado por uma autoridade portuária e construído para atender a navegação e a movimentação de cargas em geral. Terminal de uso privado (TUP) é explorado por empresa autorizada, fora da área do porto organizado.")]
    body = f"""<article class="post data">{crumbs_html(E, [("Início", "/"), ("Portos", u)])}
<h1>Portos brasileiros: ranking e movimentação de cargas</h1>
<p class="snippet">{E(D['brasil'][0]['txt'])} No 3º trimestre de 2025, o Porto de Santos liderou entre os portos organizados, com {num(rk[0]['t3'][0], 1)} milhões de toneladas, segundo a ANTAQ.</p>
<h2>Panorama nacional</h2><ul>{"".join(f"<li>{E(x['txt'])} <span class='meta'>({fl(x['f'])})</span></li>" for x in D['brasil'])}</ul>
<h2>Maiores portos organizados — 3º trimestre de 2025</h2>{table(rows, ["#", "Porto", "UF", "Milhões t", "Var. 3T25/3T24"])}<p class="meta">Fonte: {fl('boletim3t25')}, tabela 1.</p>
<h2>Outros portos com dados de 2026</h2><div class="chips">{"".join(f'<a class="chip" href="/portos/{p["slug"]}/">{E(p["nome"])}</a>' for p in outros)}</div>
<h2>Perguntas frequentes</h2>{faq_block(E, fq)}</article>"""
    ld = {"@context": "https://schema.org", "@graph": [{"@type": "ItemList", "name": "Maiores portos organizados do Brasil", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{BASE}/portos/{p['slug']}/", "name": p["nome"]} for i, p in enumerate(rk)]}, faq_ld(fq), crumbs_ld(BASE, [("Início", "/"), ("Portos", u)])]}
    B.write(u, B.page("Portos brasileiros: ranking e movimentação de cargas", "Ranking dos maiores portos organizados do Brasil com dados oficiais da ANTAQ e do MPor: toneladas, contêineres, principais cargas e 1º semestre de 2026.", u, body, jsonld=ld))
    urls.insert(0, u); lm[u] = "2026-10-12"
    return urls, lm

# ------------------------------------------------------------------ RODOVIAS
def rodovias(B):
    E, BASE = B.E, B.BASE
    f = B.ROOT / "data" / "rodovias.json"
    if not f.exists(): return [], {}
    D = json.loads(f.read_text(encoding="utf-8")); R = D["rodovias"]; urls = []; lm = {}
    src = f'{link("https://dados.antt.gov.br/dataset/praca-de-pedagio", "ANTT — Dados das praças de pedágio")} e {link("https://dados.antt.gov.br/dataset/volume-trafego-praca-pedagio", "ANTT — Volume de tráfego por praça de pedágio")}'
    news_all = getattr(B, "_posts", [])
    summary = []
    for br, r in sorted(R.items(), key=lambda x: int(x[0][3:])):
        u = f"/rodovias/{br.lower()}/"; P = r["pracas"]
        months = sorted({m for p in P for m in p["volume"]}, key=lambda m: (m[3:], m[:2]))
        last = months[-1] if months else None
        def tot(m, t): return sum(p["volume"].get(m, {}).get(t, 0) for p in P)
        com = sum(tot(m, "Comercial") for m in months); allv = sum(tot(m, t) for m in months for t in ("Comercial", "Passeio", "Moto"))
        share = com / allv * 100 if allv else 0
        mrows = [[f"{MES[int(m[:2])]}/{m[3:]}", num(tot(m, 'Comercial')), num(tot(m, 'Passeio')), num(tot(m, 'Moto'))] for m in months]
        prow = [[E(p["nome"]), p["uf"], E(p["municipio"]), num(p["km"], 1).replace(",0", ""), E(p["concessionaria"].title()), num(sum(v.get("Comercial", 0) for v in p["volume"].values())) if p["volume"] else "—"] for p in P]
        top = max(P, key=lambda p: sum(v.get("Comercial", 0) for v in p["volume"].values()))
        per = f"{MES[int(months[0][:2])]} a {MES[int(last[:2])]}/{last[3:]}" if months else ""
        lead = (f"A {br} tem {len(P)} praças de pedágio federais ativas sob concessão da ANTT em {', '.join(r['ufs'])}, operadas por {len(r['concessionarias'])} concessionária(s)."
                + (f" De {per}, as praças registraram {num(com)} passagens de veículos comerciais, {num(share, 1)}% do tráfego pedagiado." if months else ""))
        fq = [(f"Quantos pedágios tem a {br}?", f"Segundo o cadastro de praças de pedágio da ANTT, a {br} tem {len(P)} praças ativas em trechos federais concedidos, nos estados de {', '.join(UFN[x] for x in r['ufs'])}. Trechos administrados por estados ou pelo DNIT não entram nesta contagem."),
              (f"Quais concessionárias administram a {br}?", f"Nos trechos federais concedidos, a {br} é operada por: {', '.join(c.title() for c in r['concessionarias'])}, conforme dados abertos da ANTT. Cada concessionária responde por um trecho definido em contrato.")]
        if months: fq.append((f"Quantos caminhões passam pela {br}?", f"De {per}, as praças de pedágio federais da {br} registraram {num(com)} passagens de veículos comerciais (caminhões e ônibus), segundo a ANTT. A praça com maior volume comercial foi {top['nome']} ({top['uf']}). Cada passagem é contada uma vez por praça."))
        if months:
            mc = max(months, key=lambda m: tot(m, "Comercial"))
            fq.append((f"Qual a participação dos caminhões no tráfego da {br}?", f"De {per}, veículos comerciais foram {num(share, 1)}% das passagens nas praças federais da {br} ({num(com)} de {num(allv)}), segundo a ANTT."))
            fq.append((f"Em que mês a {br} teve mais tráfego de caminhões?", f"No período com dados, o maior volume comercial foi em {MES[int(mc[:2])]}/{mc[3:]}, com {num(tot(mc, 'Comercial'))} passagens de veículos comerciais nas praças federais (ANTT)."))
        fq.append((f"Em quais municípios ficam as praças de pedágio da {br}?", f"Pelo cadastro da ANTT: " + "; ".join(f"{p['nome']} em {p['municipio']} ({p['uf']}), km {num(p['km'], 1).replace(',0', '')}" for p in P[:8]) + ("." if len(P) <= 8 else f" e mais {len(P) - 8}.")))
        rel = [x for x in news_all if re.search(rf"\b{br}\b|\bBR {br[3:]}\b", x["titulo"] + " " + x.get("resumo", ""), re.I)][:5]
        body = f"""<article class="post data">{crumbs_html(E, [("Início", "/"), ("Rodovias", "/rodovias/"), (br, u)])}
<h1>{br}: pedágios, concessionárias e tráfego de caminhões</h1><p class="snippet">{E(lead)}</p>
<p class="meta">Fontes: {src}. Volumes de {D['ano']} somados a partir dos dados mensais publicados; cobre só as praças federais concedidas.</p>
<h2>Praças de pedágio da {br}</h2>{table(prow, ["Praça", "UF", "Município", "km", "Concessionária", f"Comerciais {D['ano']}"])}
{f'<h2>Tráfego mensal na {br} em {D["ano"]}</h2>' + table(mrows, ["Mês", "Comerciais", "Passeio", "Motos"]) if months else ''}
<p>O tráfego comercial inclui caminhões e ônibus. Para o custo da viagem, veja a <a href="/frete-minimo/">tabela de frete mínimo</a>, o <a href="/diesel/">preço do diesel</a> e o verbete <a href="/glossario/vale-pedagio/">vale-pedágio</a>.</p>
<h2>Perguntas frequentes sobre a {br}</h2>{faq_block(E, fq)}
{("<h2>Notícias sobre a " + br + "</h2><ul class='rel-news'>" + "".join(f'<li><a href="{x["url"]}">{E(x["titulo"])}</a></li>' for x in rel) + "</ul>") if rel else ""}</article>"""
        idx = len(P) >= 2 and bool(months)
        ld = {"@context": "https://schema.org", "@graph": [{"@type": "Place", "name": br, "url": BASE + u, "additionalType": "https://schema.org/Road"},
              {"@type": "Dataset", "name": f"Praças de pedágio e tráfego na {br}", "creator": {"@type": "Organization", "name": "ANTT"}, "isBasedOn": D["fonte_volume"], "dateModified": D["gerado"], "license": "https://dados.gov.br/dados/conteudo/licencas"}, faq_ld(fq), crumbs_ld(BASE, [("Início", "/"), ("Rodovias", "/rodovias/"), (br, u)])]}
        B.write(u, B.page(f"{br}: pedágios, concessionárias e tráfego de caminhões"[:60], E(lead)[:155], u, body, jsonld=ld, robots=None if idx else "noindex,follow"))
        if idx: urls.append(u); lm[u] = D["gerado"]
        summary.append((br, len(P), r["ufs"], com, share))
    u = "/rodovias/"
    rows = [[f'<a href="/rodovias/{b.lower()}/">{b}</a>', n_, ", ".join(ufs), num(c), f"{num(s, 1)}%"] for b, n_, ufs, c, s in sorted(summary, key=lambda x: -x[3])]
    body = f"""<article class="post data">{crumbs_html(E, [("Início", "/"), ("Rodovias", u)])}
<h1>Rodovias federais concedidas: pedágios e tráfego de caminhões</h1>
<p class="snippet">{len(R)} rodovias federais têm praças de pedágio concedidas pela ANTT, somando {sum(x[1] for x in summary)} praças ativas. A tabela mostra quantos veículos comerciais passaram por elas em {D['ano']}, com dados abertos da ANTT.</p>
<p class="meta">Fontes: {src}.</p>{table(rows, ["Rodovia", "Praças", "UFs", f"Veículos comerciais {D['ano']}", "Participação comercial"])}</article>"""
    B.write(u, B.page("Rodovias federais: pedágios e tráfego de caminhões (ANTT)", f"Praças de pedágio, concessionárias e volume de caminhões nas {len(R)} rodovias federais concedidas, com dados abertos da ANTT de {D['ano']}."[:155], u, body,
                      jsonld={"@context": "https://schema.org", "@graph": [crumbs_ld(BASE, [("Início", "/"), ("Rodovias", u)])]}))
    urls.insert(0, u); lm[u] = D["gerado"]
    return urls, lm

# ------------------------------------------------------------------ GUIAS
def guias(B):
    E, BASE = B.E, B.BASE
    G = yaml.safe_load((B.ROOT / "data" / "guias.yaml").read_text(encoding="utf-8")); urls = []; lm = {}; gate = []
    for g in G:
        u = f"/guias/{g['slug']}/"
        steps = "".join(f'<li id="passo-{i+1}"><h3>{E(s["nome"])}</h3><p>{B.E(s["texto"])}</p></li>' for i, s in enumerate(g["passos"]))
        fq = [(q["q"], q["a"]) for q in g["faq"]]
        extra = "".join(f"<h2>{E(s['h2'])}</h2>" + "".join(f"<p>{E(x)}</p>" for x in s["p"]) for s in g.get("secoes", []))
        fontes = "".join(f'<li>{link(x["url"], E(x["nome"]))}</li>' for x in g.get("fontes", []))
        inner = f"""<p class="snippet">{E(g['resumo'])}</p>
<div class="keypts"><h2>O que você precisa</h2><ul>{"".join(f"<li>{E(x)}</li>" for x in g['requisitos'])}</ul></div>
<h2>Passo a passo: {E(g['titulo'].lower())}</h2><ol class="steps">{steps}</ol>{extra}
<h2>Perguntas frequentes</h2>{faq_block(E, fq)}
<h2>Fontes oficiais</h2><ul class="refs">{fontes}</ul>"""
        inner = B._interlink(inner, budget=10) if hasattr(B, "_interlink") else inner
        body = f'<article class="post">{crumbs_html(E, [("Início", "/"), ("Guias", "/guias/"), (g["titulo"], u)])}<h1>{E(g["titulo"])}</h1><p class="meta">Atualizado em {dbr(g["atualizado"])}</p>{inner}</article>'
        wc = words(inner); idx = wc >= 800 and len(fq) >= 5
        if not idx: gate.append(f"{g['slug']}: {wc} palavras, {len(fq)} FAQs")
        ld = {"@context": "https://schema.org", "@graph": [{"@type": "HowTo", "name": g["titulo"], "description": g["resumo"], "url": BASE + u, "dateModified": g["atualizado"],
              "supply": [{"@type": "HowToSupply", "name": x} for x in g["requisitos"]],
              "step": [{"@type": "HowToStep", "position": i + 1, "name": s["nome"], "text": s["texto"], "url": f"{BASE}{u}#passo-{i+1}"} for i, s in enumerate(g["passos"])]},
              faq_ld(fq), crumbs_ld(BASE, [("Início", "/"), ("Guias", "/guias/"), (g["titulo"], u)])]}
        B.write(u, B.page(g["seo_title"], g["descricao"], u, body, jsonld=ld, robots=None if idx else "noindex,follow"))
        if idx: urls.append(u); lm[u] = g["atualizado"]
    u = "/guias/"
    body = f'<article class="post">{crumbs_html(E, [("Início", "/"), ("Guias", u)])}<h1>Guias práticos de logística e transporte</h1><p class="snippet">Passo a passo para tarefas do dia a dia do transporte de cargas e do comércio exterior, com base na legislação e nas fontes oficiais.</p><ul class="deflist">' + "".join(f'<li><a href="/guias/{g["slug"]}/"><strong>{E(g["titulo"])}</strong></a> — {E(g["resumo"][:140])}…</li>' for g in G) + "</ul></article>"
    B.write(u, B.page("Guias práticos de logística: CT-e, MDF-e, frete e exportação", "Guias passo a passo: como emitir CT-e e MDF-e, como calcular o frete mínimo da ANTT e como exportar, com fontes oficiais.", u, body,
                      jsonld={"@context": "https://schema.org", "@graph": [crumbs_ld(BASE, [("Início", "/"), ("Guias", u)])]}))
    urls.insert(0, u); lm[u] = max(g["atualizado"] for g in G)
    if gate: print("Guias em noindex:", gate)
    return urls, lm
