"""Completa data/glossario_refs.yaml: busca na Wikipédia pt (título compatível) e adiciona referência setorial por editoria. Tudo validado com HTTP 200."""
import json, sys, urllib.parse
from pathlib import Path
import yaml
sys.path.insert(0, str(Path(__file__).resolve().parent))
from glossario_assets import ROOT, get, ok, slugify
ED = {"transporte": ("ANTT — Agência Nacional de Transportes Terrestres", "https://www.gov.br/antt/pt-br"),
      "comercio-exterior": ("Receita Federal — Aduana e Comércio Exterior", "https://www.gov.br/receitafederal/pt-br/assuntos/aduana-e-comercio-exterior"),
      "armazenagem": ("ABOL — Associação Brasileira de Operadores Logísticos", "https://abolbrasil.org.br/"),
      "supply-chain": ("ABOL — Associação Brasileira de Operadores Logísticos", "https://abolbrasil.org.br/"),
      "mercado": ("ABOL — Associação Brasileira de Operadores Logísticos", "https://abolbrasil.org.br/"),
      "tecnologia": ("GS1 Brasil — Associação Brasileira de Automação", "https://www.gs1br.org/")}
f = ROOT / "data" / "glossario_refs.yaml"; refs = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
valid = {}
terms = yaml.safe_load((ROOT / "data" / "glossario.yaml").read_text(encoding="utf-8"))
for t in terms:
    s = slugify(t["t"]); lst = refs.get(s, [])
    if not any("wikipedia" in r["url"] for r in lst):
        for q in [t["t"]] + ([t["n"]] if t.get("n") else []):
            try:
                res = json.loads(get("https://pt.wikipedia.org/w/api.php?" + urllib.parse.urlencode({"action": "opensearch", "search": q, "limit": 3, "namespace": 0, "format": "json"}))[1])
            except Exception: continue
            hit = next((u for ti, u in zip(res[1], res[3]) if slugify(ti) == slugify(q) or slugify(q) in slugify(ti).split("-") or slugify(ti).startswith(slugify(q))), None)
            if hit and ok(hit): lst.append({"titulo": f"{urllib.parse.unquote(hit.rsplit('/', 1)[1]).replace('_', ' ')} — Wikipédia", "url": hit}); break
    nome, u = ED[t.get("ed", "mercado")]
    if u not in valid: valid[u] = ok(u)
    if len(lst) < 2 and valid[u] and all(r["url"] != u for r in lst): lst.append({"titulo": nome, "url": u})
    if lst: refs[s] = lst[:3]
    print(s, len(lst))
f.write_text("# Referências externas validadas (HTTP 200) — tools/glossario_assets.py + tools/refs_fill.py\n" + yaml.safe_dump(refs, allow_unicode=True, sort_keys=True), encoding="utf-8")
print("termos com refs:", len(refs), "validação editorias:", valid)
