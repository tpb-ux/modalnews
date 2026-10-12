"""Distâncias por estrada via OSRM (servidor público router.project-osrm.org, dados © OpenStreetMap contributors, ODbL).
Respeita a política de uso do servidor de demonstração: 1 requisição por segundo, com cache permanente em data/osrm_cache.json
(uma consulta por par de coordenadas, nunca repetida). Pontos = centroides municipais do IBGE (ou coordenadas oficiais quando houver)."""
import json, sys, time, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
SRV = "https://router.project-osrm.org"; CF = ROOT / "data/osrm_cache.json"
FONTE = "Distância por estrada calculada com OSRM (Open Source Routing Machine) sobre dados do OpenStreetMap (© colaboradores do OpenStreetMap, licença ODbL), entre os centros dos municípios (centroides IBGE)"
_c = None; _last = [0.0]; _dirty = [0]
def cache():
    global _c
    if _c is None: _c = json.loads(CF.read_text()) if CF.exists() else {"table": {}, "route": {}}
    return _c
def save():
    if _dirty[0]: CF.write_text(json.dumps(cache(), separators=(",", ":")), encoding="utf-8"); _dirty[0] = 0
def _get(u):
    w = 1.05 - (time.time() - _last[0])
    if w > 0: time.sleep(w)
    for i in range(4):
        try:
            _last[0] = time.time()
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "ModalNews/1.0 (+https://modalnews.com.br)"}), timeout=60) as r: return json.load(r)
        except Exception as e: err = e; time.sleep(3 * (i + 1))
    raise err
ck = lambda p: f"{p['lon']:.4f},{p['lat']:.4f}"
def table(src, dsts, offline=False):
    """Distância (km) e duração (min) de src para cada destino. Retorna lista de (km, min) ou None."""
    C = cache()["table"]; miss = [d for d in dsts if f"{ck(src)}|{ck(d)}" not in C]
    if miss and not offline:
        for i in range(0, len(miss), 80):
            part = miss[i:i + 80]; coords = ";".join([ck(src)] + [ck(d) for d in part])
            r = _get(f"{SRV}/table/v1/driving/{coords}?sources=0&annotations=distance,duration")
            if r.get("code") != "Ok": continue
            for j, d in enumerate(part):
                dist = r["distances"][0][j + 1]; dur = r["durations"][0][j + 1]
                C[f"{ck(src)}|{ck(d)}"] = [round(dist / 1000, 1), round(dur / 60)] if dist is not None else None
            _dirty[0] = 1
    return [C.get(f"{ck(src)}|{ck(d)}") for d in dsts]
def route(a, b, offline=False):
    """Rota com geometria simplificada (lista de [lon,lat]). Retorna dict km, min, geo ou None."""
    C = cache()["route"]; k = f"{ck(a)}|{ck(b)}"
    if k not in C and not offline:
        r = _get(f"{SRV}/route/v1/driving/{ck(a)};{ck(b)}?overview=simplified&geometries=geojson")
        if r.get("code") == "Ok":
            rt = r["routes"][0]; C[k] = {"km": round(rt["distance"] / 1000, 1), "min": round(rt["duration"] / 60), "geo": [[round(x, 4), round(y, 4)] for x, y in rt["geometry"]["coordinates"]]}
        else: C[k] = None
        _dirty[0] = 1
    return C.get(k)

def destinos_cidade():
    """Pré-calcula, para cada cidade com página de logística, a distância por estrada até portos, aeroportos de carga, capital e polo REGIC."""
    import geo, yaml
    IC = json.loads((ROOT / "data/ibge_cidades.json").read_text())["municipios"]; db = json.loads((ROOT / "data/diesel.json").read_text())
    cur = db["semanas"][max(db["semanas"])]; rg = json.loads((ROOT / "data/regic.json").read_text())["municipios"]
    PO = yaml.safe_load((ROOT / "data/portos_organizados.yaml").read_text())["portos"]
    pts = [(p, IC.get(geo.code(p[2], p[3]))) for p in PO]; pts = [(p, g) for p, g in pts if g]
    AE = json.loads((ROOT / "data/aeroportos.json").read_text())["aeroportos"]; aes = [a for a in AE.values() if a["dom"] + a["int"] >= 1000]
    n = 0
    for k in cur["municipios"]:
        nome, uf = k.split("|"); c = geo.code(nome, uf); g = IC.get(c)
        if not g: continue
        dst = [h for _, h in sorted(pts, key=lambda x: geo.km(g, x[1]))[:3]] + sorted(aes, key=lambda a: geo.km(g, a))[:2]
        cap = IC.get(geo.code(geo.CAPITAIS[uf], uf)); pl = geo.polo_nome((rg.get(c) or {}).get("polo")); plg = IC.get(geo.code(*pl)) if pl else None
        dst += [x for x in (cap, plg) if x and x is not g]
        table(g, dst); n += 1
        if n % 25 == 0: save(); print(n, flush=True)
    save(); print("ok", n)
if __name__ == "__main__" and len(sys.argv) == 1: destinos_cidade()

def pontos_infra():
    """Para portos organizados e aeroportos de carga: pontos (centroide do município) e destinos (capital + 4 cidades com dados mais próximas)."""
    import geo, yaml
    IC = json.loads((ROOT / "data/ibge_cidades.json").read_text())["municipios"]; db = json.loads((ROOT / "data/diesel.json").read_text())
    cur = db["semanas"][max(db["semanas"])]; ib = geo.ibge()
    cid = [(k, IC[geo.code(*k.split("|"))]) for k in cur["municipios"] if IC.get(geo.code(*k.split("|")))]
    from paginas import UFN
    inv = {v: k for k, v in UFN.items()}
    out = []
    for p in yaml.safe_load((ROOT / "data/portos_organizados.yaml").read_text())["portos"]: out.append(("porto", p[0], p[2], p[3]))
    for k, a in json.loads((ROOT / "data/aeroportos.json").read_text())["aeroportos"].items():
        if a["dom"] + a["int"] >= 1000: out.append(("aero", k, a["municipio_servido"], inv.get(a["uf_servido"], a.get("uf"))))
    res = []
    for tipo, s, nome, uf in out:
        g = IC.get(geo.code(nome, uf))
        if not g: continue
        near = [h for kk, h in sorted(cid, key=lambda x: geo.km(g, x[1])) if h is not g][:4]
        cap = IC.get(geo.code(geo.CAPITAIS[uf], uf))
        res.append((tipo, s, g, [x for x in [cap] + near if x and x is not g], near))
    return res
def infra():
    for tipo, s, g, d, _ in pontos_infra(): table(g, d)
    save(); print("infra ok")
if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "infra": infra()

def route_full(a, b, offline=False):
    """Rota com geometria completa (para casar praças de pedágio) e rodovias citadas nos passos; o cache guarda só a geometria reduzida a pontos a cada ~300 m."""
    C = cache().setdefault("route_full", {}); k = f"{ck(a)}|{ck(b)}"
    if k not in C and not offline:
        r = _get(f"{SRV}/route/v1/driving/{ck(a)};{ck(b)}?overview=full&geometries=geojson&steps=true")
        if r.get("code") == "Ok":
            rt = r["routes"][0]; pts = rt["geometry"]["coordinates"]; red = [pts[0]]
            import re as _re
            for p in pts[1:]:
                if abs(p[0] - red[-1][0]) + abs(p[1] - red[-1][1]) > 0.005: red.append(p)
            red.append(pts[-1])
            brs = {}
            for st in rt["legs"][0]["steps"]:
                for m in _re.findall(r"BR-?\d{3}", (st.get("ref") or "") + " " + (st.get("name") or "")):
                    m = "BR-" + m[-3:]; brs[m] = brs.get(m, 0) + st["distance"]
            C[k] = {"km": round(rt["distance"] / 1000, 1), "min": round(rt["duration"] / 60), "geo": [[round(x, 4), round(y, 4)] for x, y in red],
                    "brs": [[b_, round(d / 1000)] for b_, d in sorted(brs.items(), key=lambda x: -x[1]) if d > 20000]}
        else: C[k] = None
        _dirty[0] = 1
    return C.get(k)
