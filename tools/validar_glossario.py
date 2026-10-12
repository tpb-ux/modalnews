"""Valida páginas do glossário: JSON-LD parseável, FAQPage com >=5 perguntas, respostas 40-80 palavras, H1 único, meta description única."""
import json, re, sys
from pathlib import Path
pub = Path(__file__).resolve().parent.parent / "public" / "glossario"
erros, descs, n = [], {}, 0
for f in [pub / "index.html"] + sorted(pub.glob("*/index.html")):
    h = f.read_text(encoding="utf-8"); n += 1
    try: ld = [json.loads(x) for x in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S)]
    except Exception as ex: erros.append(f"{f}: JSON-LD inválido {ex}"); continue
    faq = [g for x in ld for g in x.get("@graph", [x]) if g.get("@type") == "FAQPage"]
    qs = faq[0]["mainEntity"] if faq else []
    if len(qs) < 5: erros.append(f"{f.parent.name}: {len(qs)} FAQs")
    for q in qs:
        w = len(q["acceptedAnswer"]["text"].split())
        if not 40 <= w <= 80: erros.append(f"{f.parent.name}: resposta com {w} palavras: {q['name']}")
    if h.count("<h1") != 1: erros.append(f"{f.parent.name}: h1={h.count('<h1')}")
    if len(re.findall(r'<details class="faq"', h)) != len(qs): erros.append(f"{f.parent.name}: FAQ visível != JSON-LD")
    d = re.search(r'<meta name="description" content="([^"]*)"', h).group(1)
    if d in descs: erros.append(f"{f.parent.name}: description repetida de {descs[d]}")
    descs[d] = f.parent.name
print(f"{n} páginas verificadas, {len(erros)} problema(s)"); print("\n".join(erros[:40]))
sys.exit(1 if erros else 0)
