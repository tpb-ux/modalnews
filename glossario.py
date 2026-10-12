"""Glossário de Logística (pSEO) — gerado pelo build.py, sem IA no runtime.
Dados: data/glossario.yaml (termos), data/glossario_refs.yaml (links externos validados),
data/glossario_imagens.yaml (fotos com licença livre)."""
import json, re
from pathlib import Path
import yaml

G = "/glossario/"

def words(s): return len(s.split())

def sentences(s): return [x.strip() for x in re.split(r"(?<=[.!?])\s+", s) if x.strip()]

def fit(text, extra="", lo=40, hi=80):
    """Ajusta uma resposta para 40-80 palavras, cortando em fim de frase."""
    out = []
    for snt in sentences(text):
        if words(" ".join(out + [snt])) > hi and words(" ".join(out)) >= lo: break
        out.append(snt)
    ans = " ".join(out)
    if words(ans) < lo and extra:
        for snt in sentences(extra):
            if words(ans) >= lo: break
            ans += " " + snt
    if words(ans) > hi:
        ans = " ".join(ans.split()[:hi]).rstrip(",;:") + "…"
    return ans

def lower_first(s): return s[0].lower() + s[1:] if s and not s[:2].isupper() else s

def build(B, posts):
    E, BASE, CFG, EDS = B.E, B.BASE, B.CFG, B.EDS
    root = B.ROOT
    terms = yaml.safe_load((root / "data" / "glossario.yaml").read_text(encoding="utf-8"))
    load = lambda n: (yaml.safe_load((root / "data" / n).read_text(encoding="utf-8")) or {}) if (root / "data" / n).exists() else {}
    refs, imgs = load("glossario_refs.yaml"), load("glossario_imagens.yaml")
    upd = str(CFG.get("glossario_atualizado", "2026-10-12"))
    upd_br = "/".join(reversed(upd.split("-")))
    for t in terms: t["slug"] = B.slugify(t["t"])
    by = {t["t"]: t for t in terms}
    terms.sort(key=lambda t: B.slugify(t["t"]))
    # termos linkáveis (evita siglas de 2 letras e palavras muito genéricas)
    linkable = sorted([t for t in terms if len(t["t"]) >= 3], key=lambda t: -len(t["t"]))
    pats = {t["slug"]: re.compile(r"(?<![\w>/-])(" + re.escape(t["t"]) + r")(?![\w-])", re.I) for t in linkable}

    def interlink(html, skip=None, budget=6, prefix_target=""):
        """Linka a 1ª menção de outros termos do glossário dentro de HTML simples (só fora de tags/links)."""
        done = set(); n = 0
        for t in linkable:
            if n >= budget: break
            if t["slug"] == skip or t["slug"] in done: continue
            parts = re.split(r"(<a\b.*?</a>|<[^>]+>)", html, flags=re.S)
            for i, part in enumerate(parts):
                if part.startswith("<"): continue
                m = pats[t["slug"]].search(part)
                if m:
                    link = f'<a class="gl-link" href="{G}{t["slug"]}/" title="O que é {E(t["t"])}?">{m.group(1)}</a>'
                    parts[i] = part[:m.start()] + link + part[m.end():]
                    html = "".join(parts); done.add(t["slug"]); n += 1; break
        return html

    def related_posts(t, k=3):
        keys = [t["t"].lower()] + ([t["n"].lower()] if t.get("n") and len(t["n"]) > 3 else [])
        keys = [x for x in keys if len(x) >= 4]
        hits = [p for p in posts if any(x in (p["titulo"] + " " + p.get("resumo", "")).lower() for x in keys)]
        if len(hits) < k:
            hits += [p for p in posts if p["editoria"] == t.get("ed") and p not in hits][: k - len(hits)]
        return hits[:k]

    def faqs(t):
        T, d, ed = t["t"], t["d"], EDS.get(t.get("ed", "mercado"), "Mercado")
        rel = [by[r] for r in t.get("rel", []) if r in by]
        rest = " ".join(d[1:]) + " " + t["ex"]
        out = [(f"O que é {T}?", fit(" ".join(d), t["ex"]))]
        out.append((f"Como funciona {T} na prática?", fit(" ".join(d[1:]) + " Exemplo: " + t["ex"], d[0])))
        if rel:
            R = rel[0]
            out.append((f"Qual a diferença entre {T} e {R['t']}?", fit(
                f"{sentences(d[0])[0]} Já {lower_first(sentences(R['d'][0])[0])} Os dois conceitos aparecem juntos na área de {ed.lower()}, mas tratam de aspectos diferentes da operação.",
                rest)))
        out.append((f"Quando faz sentido usar {T}?", fit(
            f"{T} faz parte do dia a dia de empresas da área de {ed.lower()}. {d[-1]} Na prática, o tema costuma ser avaliado junto com "
            + (", ".join(r["t"] for r in rel[:3]) or "outros indicadores da operação") + ".", t["ex"])))
        out.append((f"Quais as vantagens de entender {T}?", fit(
            f"Conhecer {T} ajuda gestores, compradores e transportadores a tomar decisões melhores e a conversar com fornecedores na mesma linguagem. "
            + (sentences(d[1])[0] if len(d) > 1 else "") + f" Para quem acompanha o setor, o termo aparece com frequência em notícias de {ed.lower()} e em contratos logísticos.", rest)))
        if len(rel) > 1:
            out.append((f"Quais termos estão relacionados a {T}?", fit(
                " ".join(f"{r['t']}: {lower_first(sentences(r['d'][0])[0])}" for r in rel[:3]), rest)))
        return out

    urls = []
    for t in terms:
        T, url, ed = t["t"], f"{G}{t['slug']}/", t.get("ed", "mercado")
        rel = [by[r] for r in t.get("rel", []) if r in by]
        snippet = fit(t["d"][0], t["d"][1] if len(t["d"]) > 1 else "", 30, 60)
        fq = faqs(t)
        rp = related_posts(t)
        im = imgs.get(t["slug"]) or {"arquivo": f"static/img/editoria/{ed}.webp", "largura": 1200, "altura": 630, "proprio": True,
                                      "titulo_original": f"ilustração da editoria {EDS.get(ed, ed)}", "busca": ""}
        rf = refs.get(t["slug"], [])
        desc = f"{T}: {lower_first(snippet)}"
        desc = desc if len(desc) <= 155 else desc[:152].rsplit(" ", 1)[0] + "…"
        title = f"O que é {T}? Significado na logística"
        toc = [("definicao", f"O que significa {T}"), ("como-funciona", f"Como funciona {T}"), ("exemplo", f"Exemplo prático de {T}"),
               ("faq", f"Perguntas frequentes sobre {T}")] + ([("noticias", "Notícias relacionadas")] if rp else []) + \
              ([("relacionados", "Termos relacionados")] if rel else []) + ([("referencias", "Referências")] if rf else [])
        defs = interlink("".join(f"<p>{E(x)}</p>" for x in t["d"][:1]), t["slug"], 3)
        how = interlink("".join(f"<p>{E(x)}</p>" for x in t["d"][1:]), t["slug"], 3)
        fig = ""
        if im:
            src = "/" + im["arquivo"]; th = src[:-5] + "-480.webp"
            im.setdefault("licenca", ""); im.setdefault("autor", "")
            lic = f'<a href="{E(im["licenca_url"])}" target="_blank" rel="noopener license">{E(im["licenca"])}</a>' if im.get("licenca_url") else E(im["licenca"])
            aut = f'<a href="{E(im["origem"])}" target="_blank" rel="noopener">{E(im["autor"])}</a>' if im.get("origem") else E(im["autor"])
            fig = (f'<figure class="cover"><img src="{src}" srcset="{B.PREFIX}{th} 480w, {B.PREFIX}{src} {im["largura"]}w" sizes="(max-width: 800px) 100vw, 760px" '
                   f'width="{im["largura"]}" height="{im["altura"]}" alt="{E("Ilustração de " + T + " — " + (im.get("titulo_original") or im["busca"]))}" fetchpriority="high" decoding="async">' +
                   (f'<figcaption>Ilustração: {E(CFG["site_name"])}</figcaption></figure>' if im.get("proprio") else f'<figcaption>Foto: {aut} · Licença {lic} · via {E(im.get("provedor") or "Openverse")}</figcaption></figure>'))
        faq_html = "".join(f'<details class="faq" open><summary><h3>{E(q)}</h3></summary><p>{E(a)}</p></details>' for q, a in fq)
        rp_html = "".join(f'<li><a href="{p["url"]}">{E(p["titulo"])}</a> <span class="meta">· {E(EDS[p["editoria"]])}</span></li>' for p in rp)
        rel_html = "".join(f'<a class="chip" href="{G}{r["slug"]}/">{E(r["t"])}</a>' for r in rel)
        rf_html = "".join(f'<li><a href="{E(r["url"])}" target="_blank" rel="noopener">{E(r["titulo"])}</a></li>' for r in rf)
        b = f"""<article class="post gl"><nav class="crumbs" aria-label="breadcrumb"><a href="/">Início</a> › <a href="{G}">Glossário</a> › {E(T)}</nav>
<div class="kick"><a href="/{ed}/">{E(EDS.get(ed, ed))}</a></div>
<h1>O que é {E(T)}?</h1>{f'<p class="meta">{E(t["n"])}</p>' if t.get('n') else ''}
<p class="snippet"><strong>{E(T)}</strong> — {E(lower_first(snippet) if snippet.startswith(T) is False else snippet[len(T):].lstrip(" ,"))}</p>
<p class="meta">Atualizado em <time datetime="{upd}">{upd_br}</time> · Glossário de Logística {E(CFG['site_name'])}</p>
{fig}
<nav class="toc"><strong>Neste artigo</strong><ol>{"".join(f'<li><a href="#{a}">{E(n)}</a></li>' for a, n in toc)}</ol></nav>
<h2 id="definicao">O que significa {E(T)}</h2>{defs}
<h2 id="como-funciona">Como funciona {E(T)}</h2>{how}
<h2 id="exemplo">Exemplo prático de {E(T)}</h2><div class="exbox"><p>{interlink(E(t['ex']), t['slug'], 2)}</p></div>
<h2 id="faq">Perguntas frequentes sobre {E(T)}</h2>{faq_html}
{f'<h2 id="noticias">Notícias relacionadas</h2><ul class="rel-news">{rp_html}</ul>' if rp else ''}
{f'<h2 id="relacionados">Termos relacionados</h2><div class="chips">{rel_html}</div>' if rel else ''}
{f'<h2 id="referencias">Referências</h2><ul class="refs">{rf_html}</ul>' if rf else ''}
<p class="more-ed">Acompanhe as notícias de <a href="/{ed}/">{E(EDS.get(ed, ed))}</a> no {E(CFG['site_name'])} ou volte ao <a href="{G}">Glossário de Logística</a>.</p></article>"""
        page_url = BASE + url
        ld = {"@context": "https://schema.org", "@graph": [
            {"@type": "WebPage", "@id": page_url, "url": page_url, "name": title, "description": desc, "inLanguage": "pt-BR",
             "dateModified": upd, "breadcrumb": {"@id": page_url + "#breadcrumb"}, **({"primaryImageOfPage": BASE + "/" + im["arquivo"]} if im else {})},
            {"@type": "DefinedTerm", "name": T, **({"alternateName": t["n"]} if t.get("n") else {}), "description": snippet, "url": page_url,
             **({"image": BASE + "/" + im["arquivo"]} if im else {}),
             "inDefinedTermSet": {"@type": "DefinedTermSet", "name": f"Glossário de Logística — {CFG['site_name']}", "url": BASE + G}},
            {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in fq]},
            {"@type": "BreadcrumbList", "@id": page_url + "#breadcrumb", "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": n, "item": BASE + u} for i, (n, u) in enumerate([("Início", "/"), ("Glossário", G), (T, url)])]}]}
        B.write(url, B.page(f"{title} | {CFG['site_name']}", desc, url, b, BASE + "/" + im["arquivo"] if im else None, "article", ld))
        urls.append(url)

    # ---------- índice A-Z ----------
    groups = {}
    for t in terms: groups.setdefault(B.slugify(t["t"])[0].upper(), []).append(t)
    letters = "".join(f'<a href="#l-{k}">{k}</a>' for k in groups)
    lists = "".join(f'<section class="az" id="l-{k}"><h2>{k}</h2><ul>' + "".join(
        f'<li><a href="{G}{t["slug"]}/"><strong>{E(t["t"])}</strong>{(" — " + E(t["n"])) if t.get("n") else ""}</a></li>' for t in v) + "</ul></section>" for k, v in groups.items())
    n = len(terms)
    by_ed = {}
    for t in terms: by_ed.setdefault(t.get("ed", "mercado"), []).append(t)
    ed_html = "".join(f'<li><strong>{E(EDS[e])}</strong>: ' + ", ".join(f'<a href="{G}{t["slug"]}/">{E(t["t"])}</a>' for t in v[:6]) + "</li>" for e, v in by_ed.items() if e in EDS)
    ifaq = [
        ("O que é o Glossário de Logística do Modal News?", f"É uma referência gratuita com {n} termos de transporte, armazenagem, supply chain, comércio exterior, tecnologia e mercado logístico. Cada verbete traz definição curta, explicação de como funciona, exemplo prático, perguntas frequentes, termos relacionados e, quando disponível, links para fontes oficiais como ANTT, Receita Federal e ICC."),
        ("Quais são os termos de logística mais importantes para iniciantes?", "Para começar, vale entender os conceitos que aparecem em quase toda operação: frete, CT-e, lead time, estoque de segurança, picking, WMS, TMS, cross docking e last mile. No comércio exterior, os Incoterms (como FOB e CIF) e o despacho aduaneiro são indispensáveis. Todos têm página própria neste glossário."),
        ("Qual a diferença entre logística e supply chain?", "Logística cuida do fluxo físico e das informações de transporte, armazenagem e distribuição dentro de uma empresa ou entre parceiros. Supply chain é mais amplo: coordena toda a cadeia de suprimentos, de fornecedores de matéria-prima até o consumidor final, envolvendo compras, planejamento, produção, logística e vendas de forma integrada."),
        ("Os termos do glossário seguem a legislação brasileira?", "Sim, sempre que o termo depende de regra brasileira, como CT-e, MDF-e, RNTRC, frete mínimo, vale-pedágio, DU-E e DUIMP, a explicação considera as normas e órgãos nacionais e indica a fonte oficial. Como a legislação muda, confira sempre a referência do órgão responsável antes de tomar decisões fiscais ou contratuais."),
        ("Com que frequência o glossário é atualizado?", f"O glossário é revisado periodicamente para incluir novos termos e ajustar definições quando há mudanças de mercado, tecnologia ou legislação. A data da última atualização aparece no topo de cada página; a revisão mais recente foi em {upd_br}. Sugestões de novos termos ajudam a priorizar as próximas inclusões."),
        ("Posso usar as definições do glossário em treinamentos?", "Pode consultar e citar as definições com link para a página do Modal News. Elas foram escritas de forma didática, pensadas para equipes de operação, estudantes e profissionais que estão chegando ao setor. As imagens têm licenças próprias, indicadas em cada foto, que devem ser respeitadas em qualquer reutilização."),
    ]
    ifaq_html = "".join(f'<details class="faq" open><summary><h3>{E(q)}</h3></summary><p>{E(a)}</p></details>' for q, a in ifaq)
    page_url = BASE + G
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "@id": page_url, "url": page_url, "name": f"Glossário de Logística: {n} termos explicados", "inLanguage": "pt-BR", "dateModified": upd},
        {"@type": "DefinedTermSet", "name": f"Glossário de Logística — {CFG['site_name']}", "url": page_url,
         "hasDefinedTerm": [{"@type": "DefinedTerm", "name": t["t"], "url": f"{BASE}{G}{t['slug']}/"} for t in terms]},
        {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in ifaq]},
        {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Início", "item": BASE + "/"},
                                                        {"@type": "ListItem", "position": 2, "name": "Glossário", "item": page_url}]}]}
    body = f"""<article class="post gl-index"><nav class="crumbs" aria-label="breadcrumb"><a href="/">Início</a> › Glossário</nav>
<h1>Glossário de Logística</h1>
<p class="snippet"><strong>Glossário de Logística</strong> — {n} termos de transporte, armazenagem, supply chain, comércio exterior e tecnologia explicados em linguagem simples, com exemplo prático, perguntas frequentes e links para fontes oficiais. Um guia de consulta rápida para profissionais e estudantes do setor.</p>
<p class="meta">Atualizado em <time datetime="{upd}">{upd_br}</time></p>
<nav class="toc"><strong>Nesta página</strong><ol><li><a href="#az">Termos de A a Z</a></li><li><a href="#editorias">Termos por área</a></li><li><a href="#faq">Perguntas frequentes</a></li></ol></nav>
<h2 id="az">Termos de logística de A a Z</h2><nav class="letters">{letters}</nav>{lists}
<h2 id="editorias">Termos por área da logística</h2><ul class="by-ed">{ed_html}</ul>
<h2 id="faq">Perguntas frequentes sobre o glossário</h2>{ifaq_html}</article>"""
    B.write(G, B.page(f"Glossário de Logística: {n} termos explicados | {CFG['site_name']}",
                      f"Glossário de logística de A a Z com {n} termos: cross docking, WMS, TMS, Incoterms, FOB, CIF, CT-e, MDF-e, last mile e mais, com exemplos e FAQ.", G, body, jsonld=ld))
    print(f"Glossário: {n} termos, {sum(1 for t in terms if t['slug'] in imgs)} com foto livre (demais com ilustração própria), {sum(1 for t in terms if t['slug'] in refs)} com referências")
    return [G] + urls, interlink
