"""Fase 5 — resumo semanal automático (sem IA): /resumo-semanal/<ano>-<semana>/ + índice.
Semana = semana de coleta da ANP (domingo a sábado); número ISO da semana pelo sábado final.
Dados: diesel ANP (data/diesel.json), ato vigente de frete mínimo ANTT, meses de tráfego de pedágio ANTT (data/pedagio_meses.json registra quando cada mês entrou no site) e notícias publicadas."""
import datetime as dt, json, re
from paginas import UFN, brl, dbr, pick, crumbs_html, crumbs_ld, faq_block, faq_ld

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
NA = {"AC", "BA", "PB", "PARAIBA"}; NO = {"AP", "AM", "CE", "DF", "ES", "MA", "PA", "PR", "PI", "RJ", "RN", "RS", "TO"}
def em(uf): return ("na " if uf in ("AC", "BA", "PB") else "no " if uf in NO else "em ") + UFN[uf]
def pp(a, b): return f"{(a / b - 1) * 100:+.1f}%".replace(".", ",") if a and b else "—"
def cts(a, b): d = round((a - b) * 100); return f"{abs(d)} centavo{'s' if abs(d) != 1 else ''}"

def build(B, posts):
    E, BASE, ROOT = B.E, B.BASE, B.ROOT
    db = json.loads((ROOT / "data/diesel.json").read_text()); ks = sorted(db["semanas"])
    fm = json.loads((ROOT / "data/frete_minimo.json").read_text())["ato"]
    rod = json.loads((ROOT / "data/rodovias.json").read_text())
    pm = registrar(ROOT)
    meses = sorted(pm, key=lambda m: m[-4:] + m[:2])
    def com(m): return sum((p.get("volume") or {}).get(m, {}).get("Comercial", 0) for r in rod["rodovias"].values() for p in r["pracas"])
    out = []; urls = []
    for i, k in enumerate(ks):
        s = db["semanas"][k]; prev = db["semanas"][ks[i - 1]] if i else None
        fim = dt.date.fromisoformat(s["fim"]); ini = dt.date.fromisoformat(s["ini"]); y, w, _ = fim.isocalendar(); slug = f"{y}-{w:02d}"; u = f"/resumo-semanal/{slug}/"
        br = s["brasil"]["BR"]; s10 = br["s10"]["media"]; s500 = (br.get("s500") or {}).get("media")
        sec = []; fq = []; pts = 0
        # diesel
        if prev:
            p10 = prev["brasil"]["BR"]["s10"]["media"]; d = s10 - p10
            verbo = ("subiu" if d > 0 else "caiu") if abs(d) >= 0.005 else "ficou estável"
            ref = f"semana de {dbr(prev['ini'])} a {dbr(prev['fim'])}"
            lead_d = pick(slug + "d", [
                f"O diesel S10 {verbo} na média nacional: {brl(s10)} por litro, ante {brl(p10)} na {ref} ({pp(s10, p10)}).",
                f"Na pesquisa semanal da ANP, o litro do diesel S10 {verbo} para {brl(s10)} em média no país ({pp(s10, p10)} sobre a {ref}).",
                f"A média nacional do diesel S10 {'chegou a' if d else 'se manteve em'} {brl(s10)}/l, {('com alta de ' if d > 0 else 'com queda de ') + cts(s10, p10) + ' por litro' if abs(d) >= 0.005 else 'praticamente igual'} em relação à {ref}."]) if verbo != "ficou estável" else f"O diesel S10 ficou estável na média nacional, em {brl(s10)} por litro, ante {brl(p10)} na {ref}."
            var = []
            for uf, v in s["estados"].items():
                a = (v.get("s10") or {}).get("media"); b = ((prev["estados"].get(uf) or {}).get("s10") or {}).get("media")
                if a and b: var.append(((a / b - 1) * 100, uf, a, b))
            var.sort()
            up = [x for x in var[::-1] if x[0] > 0][:3]; dn = [x for x in var if x[0] < 0][:3]
            fmt = lambda x: f"<a href='/diesel/estado/{x[1].lower()}/'>{UFN[x[1]]}</a> ({brl(x[2])}, {pp(x[2], x[3])})"
            txt = f"<p>{lead_d}</p>"
            if up: txt += "<p>" + pick(slug + "u", ["As maiores altas por estado foram: ", "Os estados com maior alta foram ", "Subiram mais: "]) + ", ".join(fmt(x) for x in up) + ".</p>"
            if dn: txt += "<p>" + pick(slug + "q", ["As maiores quedas foram: ", "Na outra ponta, recuaram mais ", "Caíram mais: "]) + ", ".join(fmt(x) for x in dn) + ".</p>"
            if s500: txt += f"<p>O diesel S500 teve média de {brl(s500)}/l" + (f" ({pp(s500, prev['brasil']['BR']['s500']['media'])})" if (prev["brasil"]["BR"].get("s500") or {}).get("media") else "") + ".</p>"
            rows = "".join(f"<tr><td><a href='/diesel/estado/{uf.lower()}/'>{UFN[uf]}</a></td><td>{brl(a)}</td><td>{brl(b)}</td><td>{pp(a, b)}</td></tr>" for _, uf, a, b in var[::-1])
            txt += f"<details><summary>Diesel S10 por estado (todas as UFs)</summary><div class='tblw'><table class='tbl'><thead><tr><th>UF</th><th>Semana</th><th>Anterior</th><th>Variação</th></tr></thead><tbody>{rows}</tbody></table></div></details>"
            sec.append(("Diesel", txt)); pts += 2
            REG = {"Norte": "AC AM AP PA RO RR TO", "Nordeste": "AL BA CE MA PB PE PI RN SE", "Centro-Oeste": "DF GO MS MT", "Sudeste": "ES MG RJ SP", "Sul": "PR RS SC"}
            def wavg(sem, ufs):
                xs = [((sem["estados"].get(u) or {}).get("s10") or {}) for u in ufs.split()]; xs = [x for x in xs if x.get("media") and x.get("postos")]
                return sum(x["media"] * x["postos"] for x in xs) / sum(x["postos"] for x in xs) if xs else None
            rr = [(rn, wavg(s, ufs), wavg(prev, ufs)) for rn, ufs in REG.items()]; rr = [x for x in rr if x[1] and x[2]]
            if rr:
                rows = "".join(f"<tr><td>{rn}</td><td>{brl(a)}</td><td>{pp(a, b)}</td></tr>" for rn, a, b in rr)
                mx = max(rr, key=lambda x: x[1]); mn = min(rr, key=lambda x: x[1])
                sec.append(("Diesel por região", f"<p>O {mx[0]} teve o diesel S10 mais caro da semana, em média {brl(mx[1])}/l, e o {mn[0]} o mais barato, {brl(mn[1])}/l. As médias regionais são ponderadas pelo número de postos pesquisados pela ANP em cada estado.</p><div class='tblw'><table class='tbl'><thead><tr><th>Região</th><th>S10 médio</th><th>Variação</th></tr></thead><tbody>{rows}</tbody></table></div>")); pts += 1
                fq.append((f"Qual região teve o diesel mais caro na semana de {dbr(s['ini'])} a {dbr(s['fim'])}?", f"O {mx[0]}, com diesel S10 a {brl(mx[1])} por litro em média, ponderada pelos postos pesquisados pela ANP. O mais barato foi o {mn[0]}, a {brl(mn[1])} por litro."))
            cv = []
            for kk, v in s["municipios"].items():
                a_ = v.get("s10") or {}; b_ = ((prev["municipios"].get(kk) or {}).get("s10") or {})
                if a_.get("media") and b_.get("media") and a_.get("postos", 0) >= 10: cv.append(((a_["media"] / b_["media"] - 1) * 100, kk, a_["media"], b_["media"]))
            if len(cv) >= 6:
                cv.sort(); cn = lambda kk: kk.split("|")[0].title() + " (" + kk.split("|")[1] + ")"
                cl = lambda x: f"{E(cn(x[1]))} ({brl(x[2])}, {pp(x[2], x[3])})"
                sec.append(("Cidades com maior variação", "<p>Entre as cidades com pelo menos 10 postos pesquisados, as maiores altas do S10 foram em " + ", ".join(cl(x) for x in cv[::-1][:3]) + "; as maiores quedas, em " + ", ".join(cl(x) for x in cv[:3]) + ".</p>")); pts += 1
            b0 = s["brasil"]["BR"]["s10"]
            if b0.get("min") and b0.get("max"): sec.append(("Dispersão de preços", f"<p>O menor preço de diesel S10 encontrado pela ANP no país na semana foi {brl(b0['min'])}/l e o maior, {brl(b0['max'])}/l, em {num_(b0.get('postos', 0))} postos pesquisados.</p>")); pts += 1
            fq.append((f"Quanto custou o diesel na semana de {dbr(s['ini'])} a {dbr(s['fim'])}?", f"Segundo a ANP, o diesel S10 custou em média {brl(s10)} por litro no Brasil, {pp(s10, p10)} em relação à semana anterior pesquisada." + (f" A maior alta estadual foi {em(up[0][1])} ({pp(up[0][2], up[0][3])})." if up else "") + (f" A maior queda foi {em(dn[0][1])} ({pp(dn[0][2], dn[0][3])})." if dn else "")))
        else:
            sec.append(("Diesel", f"<p>O diesel S10 teve média nacional de {brl(s10)} por litro na pesquisa da ANP.</p>")); pts += 1
        # frete mínimo
        pub = dt.date.fromisoformat(fm["publicacao"])
        if ini <= pub <= fim + dt.timedelta(days=1):
            sec.append(("Frete mínimo", f"<p>A ANTT publicou a {E(fm['nome'])}, com novos coeficientes do piso mínimo de frete em vigor desde {dbr(fm['vigencia'])} e diesel de referência de {brl(fm['diesel_ref'])}/l. Veja a <a href='/frete-minimo/'>tabela e a calculadora atualizadas</a>.</p>")); pts += 1
            fq.append(("O frete mínimo da ANTT mudou nesta semana?", f"Sim. A {fm['nome']} atualizou os coeficientes do piso mínimo de frete, com vigência a partir de {dbr(fm['vigencia'])} e preço de referência do diesel de {brl(fm['diesel_ref'])} por litro."))
        # pedágio
        novos = [m for m, d0 in pm.items() if (fim + dt.timedelta(days=1)).isoformat() <= d0 <= (fim + dt.timedelta(days=7)).isoformat()]
        if novos:
            m = max(novos, key=lambda m: m[-4:] + m[:2]); j = meses.index(m); a = com(m); b = com(meses[j - 1]) if j else None
            mn = f"{MESES[int(m[:2]) - 1]} de {m[-4:]}"
            sec.append(("Tráfego nas rodovias federais", f"<p>Os dados de tráfego das praças de pedágio federais de {mn} (ANTT) somaram {B_num(a)} passagens de veículos comerciais" + (f", {pp(a, b)} em relação ao mês anterior" if b else "") + ". Veja os números por rodovia em <a href='/rodovias/'>rodovias federais</a>.</p><p class='src'>Soma das praças com dados no cadastro de volume da ANTT; meses com praças sem informação podem afetar a comparação.</p>")); pts += 1
        # notícias
        wk = [p for p in posts if ini <= p["data"].date() <= fim]
        if wk:
            by = {}
            for p in wk: by.setdefault(p["editoria"], []).append(p)
            nt = f"<p>{pick(slug + 'n', ['O Modal News reuniu', 'Foram publicadas', 'A semana teve'])} {len(wk)} notícia{'s' if len(wk) > 1 else ''} de logística e transporte, com resumo e link para a fonte original.</p>"
            for ed, ps in sorted(by.items(), key=lambda t: -len(t[1])):
                nt += f"<h3><a href='/{ed}/'>{E(B.EDS[ed])}</a></h3><ul class='rel-news'>" + "".join(f"<li><a href='{p['url']}'>{E(p['titulo'])}</a> <span class='src'>({E(p['fonte'])})</span></li>" for p in ps[:8]) + "</ul>"
            sec.append(("Notícias da semana", nt)); pts += min(len(wk) // 3, 3)
            fq.append(("Quais foram as notícias de logística da semana?", f"Entre {dbr(s['ini'])} e {dbr(s['fim'])} o Modal News publicou {len(wk)} notícias em {len(by)} editorias. Destaques: " + "; ".join(p["titulo"] for p in wk[:3]) + "."))
        out.append((slug, u, s, sec, fq, pts, len(wk)))
    pmap = {o[0]: o for o in out}
    for n, (slug, u, s, sec, fq, pts, nw) in enumerate(out):
        tit = f"Resumo semanal da logística: {dbr(s['ini'])} a {dbr(s['fim'])}"
        nav = "<p class='pager'>" + (f"<a href='{out[n - 1][1]}'>← Semana anterior</a> " if n else "") + (f"<a href='{out[n + 1][1]}'>Semana seguinte →</a>" if n + 1 < len(out) else "") + "</p>"
        cr = [("Início", "/"), ("Resumo semanal", "/resumo-semanal/"), (f"Semana {slug}", u)]
        lead = re.sub(r"<[^>]+>", "", sec[0][1].split("</p>")[0])
        body = f"""<article class="post data">{crumbs_html(E, cr)}<h1>{E(tit)}</h1><p class="snippet">{E(lead)}</p><p class="upd">Gerado automaticamente a partir de dados oficiais da ANP e da ANTT e das notícias publicadas no Modal News. <a href="/metodologia/">Metodologia</a>.</p>
{''.join(f'<h2>{E(h)}</h2>{t}' for h, t in sec)}{('<h2>Perguntas frequentes</h2>' + faq_block(E, fq)) if fq else ''}{nav}
<p class="src">Fontes: <a href="{E(s['arquivo'])}" target="_blank" rel="noopener">ANP, levantamento de preços semanal</a>; ANTT (frete mínimo e tráfego de pedágio).</p></article>"""
        idx = pts >= 5 and len(fq) >= 2
        ld = {"@context": "https://schema.org", "@graph": [
            {"@type": "Article", "headline": tit, "url": BASE + u, "datePublished": s["fim"], "dateModified": s["fim"], "inLanguage": "pt-BR", "author": {"@type": "Organization", "name": "Modal News"}, "publisher": {"@type": "Organization", "name": "Modal News"}, "description": lead},
            {"@type": "Dataset", "name": f"Preço médio do diesel por estado, semana {dbr(s['ini'])} a {dbr(s['fim'])}", "url": BASE + u, "temporalCoverage": f"{s['ini']}/{s['fim']}", "spatialCoverage": "Brasil", "isBasedOn": s["arquivo"], "license": "https://creativecommons.org/licenses/by/4.0/", "creator": {"@type": "Organization", "name": "Modal News"}}]
            + ([faq_ld(fq)] if fq else []) + [crumbs_ld(BASE, cr)]}
        B.write(u, B.page(tit, (lead[:152].rsplit(" ", 1)[0] + "…") if len(lead) > 155 else lead, u, body, jsonld=ld, robots=None if idx else "noindex,follow"))
        B.REL[u] = [("/diesel/", "Preço do diesel hoje"), ("/frete-minimo/", "Frete mínimo ANTT"), ("/rodovias/", "Rodovias federais"), ("/estados/", "Logística por estado")]
        if idx: urls.append(u)
    u = "/resumo-semanal/"
    lst = "".join(f"<li><a href='{o[1]}'>Semana {o[0]}: {dbr(o[2]['ini'])} a {dbr(o[2]['fim'])}</a> — diesel S10 {brl(o[2]['brasil']['BR']['s10']['media'])}/l, {o[6]} notícias</li>" for o in out[::-1])
    body = f'<article class="post">{crumbs_html(E, [("Início", "/"), ("Resumo semanal", u)])}<h1>Resumo semanal da logística</h1><p class="snippet">Toda semana, um resumo gerado a partir de dados oficiais: variação do diesel (ANP) no Brasil e por estado, mudanças no frete mínimo e tráfego de pedágio (ANTT), e as notícias publicadas por editoria.</p><ul class="rel-news">{lst}</ul></article>'
    B.write(u, B.page("Resumo semanal da logística: diesel, frete e notícias", "Resumo semanal automático com dados oficiais: preço do diesel ANP por estado, frete mínimo ANTT, tráfego de pedágio e notícias de logística.", u, body,
                      jsonld={"@context": "https://schema.org", "@graph": [{"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": BASE + o[1]} for i, o in enumerate(out[::-1])]}, crumbs_ld(BASE, [("Início", "/"), ("Resumo semanal", u)])]}))
    last = out[-1][1]
    for p in ("/diesel/", "/frete-minimo/", "/rodovias/"): B.REL.setdefault(p, []).insert(0, (last, "Resumo semanal mais recente"))
    print(f"Resumo semanal: {len(out)} semanas, {len(urls)} indexáveis; atual {out[-1][0]}")
    B.LAST_RESUMO = last
    return [u] + urls

def num_(v): return f"{v:,.0f}".replace(",", ".")
def B_num(v): return f"{v:,.0f}".replace(",", ".")

def registrar(ROOT=None):
    """Registra a data em que cada mês de tráfego de pedágio entrou no site (rodado no workflow antes do commit)."""
    from pathlib import Path
    ROOT = ROOT or Path(__file__).resolve().parent
    rod = json.loads((ROOT / "data/rodovias.json").read_text())
    pm_f = ROOT / "data/pedagio_meses.json"; pm = json.loads(pm_f.read_text()) if pm_f.exists() else {}
    hoje = dt.date.today().isoformat()
    for m in {m for r in rod["rodovias"].values() for p in r["pracas"] for m in (p.get("volume") or {})}: pm.setdefault(m, hoje)
    pm_f.write_text(json.dumps(pm, ensure_ascii=False, indent=0)); return pm
if __name__ == "__main__": registrar()
