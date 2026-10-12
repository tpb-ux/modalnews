"""Rotas entre cidades, busca interna estática e expediente."""
import json, re, html as H
from paginas import UFN, brl, dbr, norm, crumbs_html, crumbs_ld, faq_block, faq_ld
import geo, tarifas
num = lambda v, d=0: (f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", "."))

def rotas(B):
    E, BASE, ROOT = B.E, B.BASE, B.ROOT; f = ROOT / "data/rotas.json"
    if not f.exists(): return []
    R = json.loads(f.read_text()); fm = json.loads((ROOT / "data/frete_minimo.json").read_text()); cg = fm["tabelas"]["A"]["cargas"]["Carga Geral"]; ato = fm["ato"]
    db = json.loads((ROOT / "data/diesel.json").read_text()); cur = db["semanas"][max(db["semanas"])]; ib = geo.ibge()
    def s10(n, uf):
        for k, v in cur["municipios"].items():
            a, b = k.split("|")
            if b == uf and norm(a) == norm(n): return (v.get("s10") or {}).get("media")
    br_avg = cur["brasil"]["BR"]["s10"]["media"]; urls = []; idx_rows = []
    hr = lambda m: f"{m // 60} h {m % 60:02d} min"
    for r in R["rotas"]:
        a, b = r["a"], r["b"]; sa = f"{B.slugify(a['nome'])}-{a['uf'].lower()}"; sb = f"{B.slugify(b['nome'])}-{b['uf'].lower()}"
        u = f"/rotas/{sa}-x-{sb}/"; dest = b.get("porto_nome") or f"{b['nome']} ({b['uf']})"; orig = f"{a['nome']} ({a['uf']})"
        km_ = r["km"]; pr = r["pracas"]; ts = [(p, tarifas.tarifa(p["conc"], p["nome"])) for p in pr]; known = [t for _, t in ts if t]; allk = len(known) == len(ts)
        d1, d2 = s10(a["nome"], a["uf"]), s10(b["nome"], b["uf"]); dm = ((d1 or br_avg) + (d2 or br_avg)) / 2
        litros = km_ / 2.5; custo_d = litros * dm
        f5 = km_ * cg["ccd"]["5"] + cg["cc"]["5"]; f6 = km_ * cg["ccd"]["6"] + cg["cc"]["6"]; f7 = km_ * cg["ccd"]["7"] + cg["cc"]["7"]
        ped5 = sum(known) * 5 if known else None
        lk = lambda u, t: f"<a href='{u}'>{t}</a>" if (B.OUT / u.strip("/") / "index.html").exists() else t
        rows = "".join(f"<tr><td>{lk('/rodovias/' + p['br'].lower() + '/', p['br'])}</td><td>{E(p['nome'])}</td><td>{E(p['mun'])}/{p['uf']}</td><td>{E(p['conc'].title())}</td><td>{brl(t * 5) if t else lk('/pedagios/' + B.slugify(p['conc']) + '/', 'ver tarifa')}</td></tr>" for p, t in ts)
        ped_html = (f"<p>No traçado calculado há <strong>{len(pr)} praça(s) de pedágio federais</strong> (ANTT)" + (f", que somam {brl(ped5)} para uma carreta de 5 eixos" + ("" if allk else " nas praças com tarifa identificada") if known else "") + ".</p><div class='tblw'><table class='tbl'><thead><tr><th>Rodovia</th><th>Praça</th><th>Município</th><th>Concessão</th><th>5 eixos</th></tr></thead><tbody>" + rows + "</tbody></table></div>") if pr else "<p>O traçado calculado não passa por praças de pedágio de rodovias federais concedidas (ANTT).</p>"
        ped_html += "<p class='src'>Somente praças federais (ANTT). Rodovias estaduais concedidas no trajeto cobram pedágio à parte e não estão incluídas. Praças identificadas por coordenadas oficiais da ANTT a até 250 m do traçado.</p>"
        brs = ", ".join(f"<a href='/rodovias/{x.lower()}/'>{x}</a>" if (B.OUT / "rodovias" / x.lower()).exists() else x for x, _ in r.get("brs", [])[:5])
        lead = f"De {orig} a {dest} são cerca de {num(km_)} km por estrada ({hr(r['min'])} de direção estimada, sem paradas). O piso de frete ANTT para carga geral em carreta de 5 eixos é {brl(f5)}" + (f", e as praças federais no caminho somam {brl(ped5)} para 5 eixos." if known and allk else ".")
        fq = [(f"Qual a distância de {a['nome']} a {b.get('porto_nome') or b['nome']} por estrada?", f"Cerca de {num(km_)} km entre os centros dos municípios, pelo cálculo de rota OSRM com dados do OpenStreetMap; em linha reta são {num(r['linha_reta'])} km. O tempo estimado é de {hr(r['min'])} sem paradas, e caminhões levam mais por limites de velocidade e jornada."),
              (f"Qual o frete mínimo de {a['nome']} para {b['nome']}?", f"Pela tabela A da ANTT ({ato['nome']}), carga geral em lotação custa no mínimo {brl(f5)} com 5 eixos, {brl(f6)} com 6 eixos e {brl(f7)} com 7 eixos para {num(km_)} km, sem pedágio. Outros tipos de carga têm coeficientes próprios."),
              (f"Quanto se gasta de diesel de {a['nome']} a {b['nome']}?", f"Com consumo de 2,5 km/l, são cerca de {num(litros)} litros; ao preço médio do S10 de {brl(dm)}/l (média de origem e destino na pesquisa ANP de {dbr(cur['ini'])} a {dbr(cur['fim'])}), o custo é de aproximadamente {brl(custo_d)}.")]
        if pr: fq.append((f"Quantos pedágios há de {a['nome']} a {b['nome']}?", f"No traçado calculado há {len(pr)} praça(s) de pedágio em rodovias federais concedidas: {', '.join(p['nome'] + ' (' + p['br'] + ')' for p in pr[:6])}. Rodovias estaduais com pedágio, se houver no caminho, não estão incluídas."))
        # --- blocos variáveis por dado real: outras cargas (ANTT), diesel origem×destino, sinuosidade, rotas da mesma origem
        cargas_all = fm["tabelas"]["A"]["cargas"]
        outras = [(n_, km_ * cargas_all[n_]["ccd"]["5"] + cargas_all[n_]["cc"]["5"]) for n_ in ("Granel sólido", "Granel líquido", "Frigorificada ou Aquecida", "Conteinerizada", "Perigosa (carga geral)") if n_ in cargas_all and "5" in cargas_all[n_]["ccd"]]
        outras_html = "<h2>Piso ANTT para outros tipos de carga (5 eixos)</h2><div class='tblw'><table class='tbl'><thead><tr><th>Tipo de carga</th><th>Piso para " + num(km_) + " km</th></tr></thead><tbody>" + "".join(f"<tr><td>{E(n_)}</td><td>{brl(v_)}</td></tr>" for n_, v_ in outras) + "</tbody></table></div>" if outras else ""
        if outras: fq.append((f"Qual o frete mínimo de {a['nome']} para {b['nome']} para outros tipos de carga?", "Com 5 eixos, pela Tabela A da ANTT: " + "; ".join(f"{n_.lower()}, {brl(v_)}" for n_, v_ in outras) + f" para {num(km_)} km, sem pedágio."))
        sinu = km_ / r["linha_reta"] if r.get("linha_reta") else None
        if sinu: fq.append((f"Por que a distância por estrada de {a['nome']} a {b['nome']} é maior que em linha reta?", f"O trajeto calculado tem {num(km_)} km, {num((sinu - 1) * 100)}% a mais que os {num(r['linha_reta'])} km em linha reta, porque segue a malha rodoviária, que contorna relevo, rios e áreas urbanas."))
        dz_html = ""
        if d1 and d2:
            mais = a["nome"] if d1 < d2 else b["nome"]
            fq.append((f"É mais barato abastecer em {a['nome']} ou em {b['nome']}?", f"Na pesquisa da ANP de {dbr(cur['ini'])} a {dbr(cur['fim'])}, o diesel S10 custou em média {brl(d1)} em {a['nome']} e {brl(d2)} em {b['nome']}; abastecer em {mais} custava {brl(abs(d1 - d2))} a menos por litro, ou {brl(abs(d1 - d2) * litros)} no volume estimado da viagem."))
            dz_html = f"<h2>Diesel na origem e no destino</h2><ul><li>{lk('/diesel/' + sa + '/', E(a['nome']))}: {brl(d1)}/l (S10)</li><li>{E(b['nome'])}: {brl(d2)}/l (S10)</li><li>Média nacional: {brl(br_avg)}/l</li></ul>"
        elif not (d1 or d2):
            fq.append((f"Qual preço de diesel foi usado no cálculo de {a['nome']} a {b['nome']}?", f"Nenhuma das duas cidades teve diesel S10 pesquisado pela ANP na semana de {dbr(cur['ini'])} a {dbr(cur['fim'])}; por isso usamos a média nacional de {brl(br_avg)} por litro."))
        mesma = [x for x in R["rotas"] if x["a"]["nome"] == a["nome"] and x["a"]["uf"] == a["uf"] and x is not r]
        mo_html = ""
        if mesma:
            def _u(x): return f"/rotas/{B.slugify(x['a']['nome'])}-{x['a']['uf'].lower()}-x-{B.slugify(x['b']['nome'])}-{x['b']['uf'].lower()}/"
            mo_html = f"<h2>Outras rotas saindo de {E(a['nome'])}</h2><ul>" + "".join(f"<li><a href='{_u(x)}'>{E(x['b'].get('porto_nome') or x['b']['nome'])}</a>: {num(x['km'])} km, {len(x['pracas'])} praça(s) federal(is)</li>" for x in sorted(mesma, key=lambda x: x["km"])[:8]) + "</ul>"
        if pr and known:
            fq.append((f"Quanto custa o pedágio ida e volta de {a['nome']} a {b['nome']}?", f"Para carreta de 5 eixos, as praças federais com tarifa identificada somam {brl(ped5)} por sentido, cerca de {brl(ped5 * 2)} ida e volta" + ("" if allk else ", sem contar praças cuja tarifa não foi identificada") + ". Pedágios estaduais não estão incluídos."))
        cr = [("Início", "/"), ("Rotas", "/rotas/"), (f"{a['nome']} × {b.get('porto_nome') or b['nome']}", u)]
        body = f"""<article class="post data">{crumbs_html(E, cr)}<h1>Frete {E(a['nome'])} × {E(b.get('porto_nome') or b['nome'])}: distância, pedágios e frete mínimo</h1><p class="snippet">{E(lead)}</p>
<dl class="deflist"><dt>Distância por estrada*</dt><dd>{num(km_)} km</dd><dt>Tempo estimado*</dt><dd>{hr(r['min'])}</dd><dt>Linha reta</dt><dd>{num(r['linha_reta'])} km</dd>{f"<dt>Principais rodovias</dt><dd>{brs}</dd>" if brs else ''}</dl>
<p class="src">*{E(R['fonte'])}. Tempo do roteador para automóvel, sem paradas.</p>
<h2>Frete mínimo ANTT (carga geral, lotação)</h2><div class="tblw"><table class="tbl"><thead><tr><th>Veículo</th><th>Piso para {num(km_)} km</th></tr></thead><tbody><tr><td><a href="/veiculos/carreta-cinco-eixos/">Carreta 5 eixos</a></td><td>{brl(f5)}</td></tr><tr><td><a href="/veiculos/carreta-ls/">Carreta LS 6 eixos</a></td><td>{brl(f6)}</td></tr><tr><td><a href="/veiculos/bitrem/">Bitrem 7 eixos</a></td><td>{brl(f7)}</td></tr></tbody></table></div>
<p class="src">{E(ato['nome'])}, Tabela A. Cálculo: km × CCD + CC. Outros tipos de carga na <a href="/frete-minimo/">calculadora de frete mínimo</a>.</p>
{outras_html}
<h2>Pedágios federais no trajeto</h2>{ped_html}
<h2>Custo estimado de diesel</h2><p>{num(litros)} litros a 2,5 km/l × {brl(dm)}/l (S10, média de origem e destino, ANP) ≈ <strong>{brl(custo_d)}</strong>. Simule com o seu consumo na <a href="/calculadoras/custo-diesel-viagem/">calculadora de custo de diesel</a>.</p>
{dz_html}{mo_html}
<h2>Perguntas frequentes</h2>{faq_block(E, fq)}</article>"""
        has_a = (B.OUT / "logistica" / sa).exists()
        idx = km_ > 0 and has_a
        ld = {"@context": "https://schema.org", "@graph": [{"@type": "WebPage", "name": f"Frete {a['nome']} × {b['nome']}", "url": BASE + u, "about": [{"@type": "City", "name": a["nome"]}, {"@type": "City", "name": b["nome"]}], "dateModified": cur["fim"]},
              {"@type": "Dataset", "name": f"Distância, pedágios e frete mínimo {a['nome']}–{b['nome']}", "url": BASE + u, "isBasedOn": ["https://www.openstreetmap.org/copyright", ato["url"], "https://dados.antt.gov.br/"], "creator": {"@type": "Organization", "name": "Modal News"}}, faq_ld(fq), crumbs_ld(BASE, cr)]}
        B.write(u, B.page(f"Frete {a['nome']} × {b.get('porto_nome') or b['nome']}: km, pedágio e piso ANTT"[:65], lead[:155].rsplit(" ", 1)[0] + "…", u, body, jsonld=ld, robots=None if idx else "noindex,follow"))
        rel = [(f"/logistica/{sa}/", f"Logística em {a['nome']}"), (f"/diesel/{sa}/", f"Diesel em {a['nome']}")]
        rel += [(f"/portos/{b['porto']}/", b["porto_nome"])] if b.get("porto") else [(f"/logistica/{sb}/", f"Logística em {b['nome']}")]
        B.REL[u] = rel + [("/frete-minimo/", "Calculadora de frete mínimo"), ("/pedagios/", "Pedágios federais"), ("/rotas/", "Outras rotas")]
        for p_ in (f"/logistica/{sa}/",) + ((f"/logistica/{sb}/",) if not b.get("porto") else (f"/portos/{b['porto']}/",)):
            B.REL.setdefault(p_, []).append((u, f"Rota {a['nome']} × {b.get('porto_nome') or b['nome']}"))
        idx_rows.append((u, orig, dest, km_, len(pr)))
        if idx: urls.append(u)
    u = "/rotas/"
    rows = "".join(f"<tr><td><a href='{x}'>{E(o)} × {E(d)}</a></td><td>{num(k)} km</td><td>{n}</td></tr>" for x, o, d, k, n in sorted(idx_rows, key=lambda t: (t[1], t[3])))
    body = f'<article class="post data">{crumbs_html(E, [("Início", "/"), ("Rotas", u)])}<h1>Rotas de frete entre cidades e portos</h1><p class="snippet">{len(idx_rows)} rotas entre as maiores cidades do país e delas até os principais portos, com distância por estrada (OSRM/OpenStreetMap), pedágios federais (ANTT), custo de diesel (ANP) e piso de frete (ANTT).</p><div class="tblw"><table class="tbl"><thead><tr><th>Rota</th><th>Distância</th><th>Pedágios federais</th></tr></thead><tbody>{rows}</tbody></table></div></article>'
    B.write(u, B.page("Rotas de frete: distância, pedágios e frete mínimo", f"{len(idx_rows)} rotas entre grandes cidades e portos com distância por estrada, pedágios federais, diesel e piso ANTT.", u, body, jsonld={"@context": "https://schema.org", "@graph": [crumbs_ld(BASE, [("Início", "/"), ("Rotas", u)])]}))
    return [u] + urls

def busca_page(B):
    E, BASE = B.E, B.BASE; u = "/busca/"
    js = """<script>(function(){var q=document.getElementById('q'),o=document.getElementById('res'),D=null;
function n(s){return s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase()}
function run(){var t=n(q.value.trim());if(!D||t.length<2){o.innerHTML='';return}var w=t.split(/\\s+/),r=[];
for(var i=0;i<D.length;i++){var d=D[i],h=n(d.t+' '+d.d),s=0;for(var j=0;j<w.length;j++){var k=h.indexOf(w[j]);if(k<0){s=-1;break}s+=n(d.t).indexOf(w[j])>=0?3:1}if(s>0)r.push([s,d])}
r.sort(function(a,b){return b[0]-a[0]});o.innerHTML=r.slice(0,30).map(function(x){return '<li><a href="'+x[1].u+'">'+x[1].t+'</a><br><small>'+x[1].d+'</small></li>'}).join('')||'<li>Nenhum resultado.</li>'}
fetch('/busca.json').then(function(r){return r.json()}).then(function(j){D=j;var p=new URLSearchParams(location.search).get('q');if(p){q.value=p}run()});q.addEventListener('input',run)})();</script>"""
    body = f'<article class="post">{crumbs_html(E, [("Início", "/"), ("Busca", u)])}<h1>Buscar no Modal News</h1><form role="search" action="/busca/" onsubmit="return false"><label for="q" class="vh">Termo de busca</label><input id="q" name="q" type="search" placeholder="Ex.: frete mínimo, Santos, cross docking" autocomplete="off" style="width:100%;padding:12px;font-size:1rem;border:1px solid #ccc;border-radius:6px"></form><ul id="res" class="rel-news" aria-live="polite"></ul></article>{js}'
    B.write(u, B.page("Buscar no Modal News", "Busca em notícias, glossário, dados de diesel, frete, portos, rodovias e guias.", u, body, robots="noindex,follow"))

def busca_index(B):
    """Varre public/ e gera /busca.json com páginas indexáveis (título, descrição, URL)."""
    out = []
    for f in sorted(B.OUT.rglob("index.html")):
        h = f.read_text(encoding="utf-8", errors="ignore")
        if 'name="robots" content="noindex' in h: continue
        t = re.search(r"<title>(.*?)</title>", h, re.S); d = re.search(r'<meta name="description" content="([^"]*)"', h)
        if not t: continue
        rel = "/" + str(f.parent.relative_to(B.OUT)).replace("\\", "/") + "/"; rel = "/" if rel == "/./" else rel
        out.append({"u": rel, "t": H.unescape(t.group(1).split(" | ")[0].strip()), "d": H.unescape(d.group(1))[:140] if d else ""})
    (B.OUT / "busca.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(out)

def expediente(B):
    E, BASE, CFG = B.E, B.BASE, B.CFG; u = "/expediente/"; org = CFG.get("empresa", {})
    end = org.get("endereco", {})
    contato = "".join(f"<dt>{E(k)}</dt><dd>{v}</dd>" for k, v in (("E-mail", f"<a href='mailto:{E(org['email'])}'>{E(org['email'])}</a>" if org.get("email") else ""),) if v)
    redes = [r for r in org.get("redes", []) if r]
    body = f"""<article class="post">{crumbs_html(E, [("Início", "/"), ("Expediente", u)])}<h1>Expediente e contato</h1>
<p>O Modal News é um portal de notícias e dados de logística, transporte e comércio exterior publicado por {E(org.get('razao_social', ''))}.</p>
<h2>Responsável pela publicação</h2><dl class="deflist"><dt>Razão social</dt><dd>{E(org.get('razao_social', ''))}</dd><dt>CNPJ</dt><dd>{E(org.get('cnpj', ''))}</dd>
<dt>Endereço</dt><dd>{E(end.get('logradouro', ''))}, {E(end.get('bairro', ''))}, {E(end.get('cidade', ''))}-{E(end.get('uf', ''))}, CEP {E(end.get('cep', ''))}</dd>{contato}</dl>
{('<h2>Redes</h2><ul>' + ''.join(f'<li><a href="{E(r)}" rel="me noopener" target="_blank">{E(r)}</a></li>' for r in redes) + '</ul>') if redes else ''}
<h2>Equipe e processo editorial</h2><p>O conteúdo de notícias é composto de resumos curtos com link para a fonte original; páginas de dados são geradas automaticamente a partir de bases oficiais (ANP, ANTT, ANTAQ, ANAC, IBGE, CONTRAN). Veja a <a href="/politica-editorial/">política editorial</a>, a <a href="/metodologia/">metodologia</a> e como pedir <a href="/correcoes/">correções</a>.</p></article>"""
    ld = {"@context": "https://schema.org", "@graph": [{"@type": "AboutPage", "url": BASE + u, "name": "Expediente e contato", "publisher": {"@id": BASE + "/#org"}}, crumbs_ld(BASE, [("Início", "/"), ("Expediente", u)])]}
    B.write(u, B.page("Expediente e contato | Modal News", f"Expediente do Modal News: {org.get('razao_social', '')}, CNPJ {org.get('cnpj', '')}, endereço e contato.", u, body, jsonld=ld))
    return [u]
