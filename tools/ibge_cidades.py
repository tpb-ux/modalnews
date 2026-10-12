"""Baixa dados oficiais do IBGE (API servicodados) para os municípios usados no site:
centroide (malhas v3), população residente (Censo 2022, agregado 4709) e PIB a preços correntes (agregado 5938).
Saída: data/ibge_cidades.json. Atualização incremental: só busca códigos ainda ausentes."""
import json, sys, time, urllib.request, yaml
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
from paginas import norm
API = "https://servicodados.ibge.gov.br/api/v3"
def get(u):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "ModalNews/1.0"}), timeout=40) as r:
                b = r.read(); import gzip
                return json.loads(gzip.decompress(b) if b[:2] == b"\x1f\x8b" else b)
        except Exception as e: err = e; time.sleep(2 * (i + 1))
    raise err
def main():
    ibge = json.loads((ROOT / "data/ibge_municipios.json").read_text()); db = json.loads((ROOT / "data/diesel.json").read_text())
    keys = {k for s in db["semanas"].values() for k in s["municipios"]}
    keys |= {f"{p['municipio']}|{p['uf']}" for r in json.loads((ROOT / "data/rodovias.json").read_text())["rodovias"].values() for p in r["pracas"]}
    keys |= {f"{p['cidade']}|{p['uf']}" for p in yaml.safe_load((ROOT / "data/portos.yaml").read_text())["portos"]}
    codes = {str(ibge[f"{norm(n)}|{uf}"]["ibge"]) for n, uf in (k.split("|") for k in keys) if f"{norm(n)}|{uf}" in ibge}
    out_f = ROOT / "data/ibge_cidades.json"; out = json.loads(out_f.read_text()) if out_f.exists() else {"municipios": {}}
    falt = sorted(c for c in codes if c not in out["municipios"])
    print(len(codes), "municípios;", len(falt), "a buscar")
    def cen(c):
        try: d = get(f"{API}/malhas/municipios/{c}/metadados")[0]
        except Exception as e: print("falhou", c, e); return c, None
        return c, {"lat": d["centroide"]["latitude"], "lon": d["centroide"]["longitude"], "area_km2": float(d["area"]["dimensao"])}
    with ThreadPoolExecutor(4) as ex:
        for c, v in ex.map(cen, falt): 
            if v: out["municipios"][c] = v
    for i in range(0, len(falt), 80):
        lote = ",".join(c for c in falt[i:i + 80] if c in out["municipios"])
        for ag, var, campo in (("4709", "93", "pop"), ("5938", "37", "pib_mil")):
            for s in get(f"{API}/agregados/{ag}/periodos/-1/variaveis/{var}?localidades=N6[{lote}]")[0]["resultados"][0]["series"]:
                ano, val = next(iter(s["serie"].items()))
                if val and val.strip("-.X"): out["municipios"][s["localidade"]["id"]][campo] = int(val); out["municipios"][s["localidade"]["id"]][campo + "_ano"] = int(ano)
    out["fontes"] = {"centroide": f"{API}/malhas/municipios/{{id}}/metadados", "pop": "IBGE, Censo Demográfico 2022 (SIDRA tabela 4709)", "pib": "IBGE, PIB dos Municípios (SIDRA tabela 5938)"}
    out["atualizado"] = time.strftime("%Y-%m-%d")
    out_f.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"); print("ok", len(out["municipios"]))
if __name__ == "__main__": main()
