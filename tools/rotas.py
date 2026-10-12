"""Rotas entre cidades (pares relevantes) com OSRM: distância, duração e praças de pedágio FEDERAIS (ANTT) no traçado.
Pares: (a) entre as 30 cidades mais populosas com dados de diesel, até 900 km em linha reta; (b) cada uma das 60 maiores cidades até o porto organizado
mais próximo dos 8 de maior porte. Saída: data/rotas.json. Usa cache OSRM (1 req/s)."""
import json, math, sys, urllib.request, csv, io, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
import geo, osrm, yaml
PORTOS_GRANDES = ["santos", "paranagua", "rio-grande", "itaqui", "suape", "itajai", "rio-de-janeiro", "salvador", "vitoria", "itaguai", "sao-francisco-do-sul", "fortaleza", "manaus", "belem"]
def norm_br(b):
    """'BR-40', '40', 'br 040' -> 'BR-040' (padrão oficial com 3 dígitos)."""
    m = re.search(r"(\d+)", str(b or ""))
    return f"BR-{int(m.group(1)):03d}" if m else str(b)
def pracas_antt():
    f = ROOT / "data/raw/pracas_antt.csv"
    if not f.exists():
        u = json.loads((ROOT / "data/rodovias.json").read_text())["fonte_pracas"]
        f.write_bytes(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "ModalNews"}), timeout=120).read())
    raw = f.read_bytes()
    try: txt = raw.decode("utf-8-sig")
    except UnicodeDecodeError: txt = raw.decode("cp1252", "replace")  # CSV da ANTT às vezes vem em Latin-1
    rows = list(csv.DictReader(io.StringIO(txt), delimiter=";"))
    out = []
    for r in rows:
        if r.get("situacao", "").lower() != "ativo": continue
        try: out.append({"conc": r["concessionaria"], "nome": r["praca_de_pedagio"], "br": norm_br(r["rodovia"]), "uf": r["uf"], "km": r["km_m"], "mun": r["municipal"], "lat": float(r["latitude"].replace(",", ".")), "lon": float(r["longitude"].replace(",", "."))})
        except Exception: pass
    return out
def seg_dist(p, a, b):
    # distância aproximada (km) do ponto p ao segmento ab, projeção equiretangular local
    kx = 111.32 * math.cos(math.radians(p["lat"])); ky = 110.57
    ax, ay = (a[0] - p["lon"]) * kx, (a[1] - p["lat"]) * ky; bx, by = (b[0] - p["lon"]) * kx, (b[1] - p["lat"]) * ky
    dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, -(ax * dx + ay * dy) / L))
    return math.hypot(ax + t * dx, ay + t * dy)
def main():
    IC = json.loads((ROOT / "data/ibge_cidades.json").read_text())["municipios"]; db = json.loads((ROOT / "data/diesel.json").read_text()); cur = db["semanas"][max(db["semanas"])]
    ib = geo.ibge(); cid = []
    for k in cur["municipios"]:
        n, uf = k.split("|"); c = geo.code(n, uf); g = IC.get(c)
        if g and g.get("pop"): cid.append({"nome": ib[f"{geo.norm(n)}|{uf}"]["nome"], "uf": uf, **g})
    cid.sort(key=lambda x: -x["pop"])
    PO = {p[0]: p for p in yaml.safe_load((ROOT / "data/portos_organizados.yaml").read_text())["portos"]}
    pares = []
    top = cid[:30]
    for i, a in enumerate(top):
        for b in top[i + 1:]:
            if geo.km(a, b) <= 900: pares.append((a, b, "cidade"))
    for a in cid[:60]:
        cands = [(geo.km(a, IC[geo.code(PO[s][2], PO[s][3])]), s) for s in PORTOS_GRANDES if IC.get(geo.code(PO[s][2], PO[s][3]))]
        d, s = min(cands); p = PO[s]; g = IC[geo.code(p[2], p[3])]
        if d > 15: pares.append((a, {"nome": p[2], "uf": p[3], "porto": s, "porto_nome": f"Porto de {p[1]}", **g}, "porto"))
    PR = pracas_antt(); out = []
    print(len(pares), "pares", len(PR), "praças"); n = 0
    for a, b, tipo in pares:
        r = osrm.route_full(a, b)
        n += 1
        if n % 20 == 0: osrm.save(); print(n, flush=True)
        if not r: continue
        geo_ = r["geo"]; hits = []
        for p in PR:
            if not (min(a["lat"], b["lat"]) - 3 < p["lat"] < max(a["lat"], b["lat"]) + 3): continue
            dm = min(seg_dist(p, geo_[j], geo_[j + 1]) for j in range(len(geo_) - 1))
            if dm <= 0.25: hits.append({k: p[k] for k in ("conc", "nome", "br", "uf", "km", "mun")})
        out.append({"a": {"nome": a["nome"], "uf": a["uf"]}, "b": {"nome": b["nome"], "uf": b["uf"], **({"porto": b["porto"], "porto_nome": b["porto_nome"]} if tipo == "porto" else {})}, "tipo": tipo,
                    "km": r["km"], "min": r["min"], "linha_reta": round(geo.km(a, b)), "pracas": hits, "brs": r.get("brs", [])})
    osrm.save()
    (ROOT / "data/rotas.json").write_text(json.dumps({"fonte": osrm.FONTE, "pracas": "ANTT, cadastro de praças de pedágio (dados abertos), coordenadas oficiais", "rotas": out}, ensure_ascii=False, indent=0), encoding="utf-8")
    print("rotas", len(out))
if __name__ == "__main__": main()
