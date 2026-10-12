"""Carga aérea por aeroporto (ANAC, Dados Estatísticos do Transporte Aéreo) + cadastro de aeródromos públicos (ANAC).
Uso: python tools/anac_carga.py <Dados_Estatisticos_2021_a_2030.json> — agrega os últimos 12 meses disponíveis.
Saída: data/aeroportos.json (só aeroportos brasileiros com carga paga + correio > 0)."""
import csv, io, json, sys, ijson
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
URL_EST = "https://sistemas.anac.gov.br/dadosabertos/Voos%20e%20opera%C3%A7%C3%B5es%20a%C3%A9reas/Dados%20Estat%C3%ADsticos%20do%20Transporte%20A%C3%A9reo/"
URL_AER = "https://sistemas.anac.gov.br/dadosabertos/Aerodromos/Aer%C3%B3dromos%20P%C3%BAblicos/Lista%20de%20aer%C3%B3dromos%20p%C3%BAblicos/AerodromosPublicos.csv"
f = lambda v: float(str(v).replace(",", ".")) if v not in (None, "") else 0.0
def main(path):
    per = {}
    with open(path, "rb") as fh:
        for r in ijson.items(fh, "item", multiple_values=True):
            k = (int(r["ANO"]), int(r["MES"])); kg = f(r.get("CARGA_PAGA_KG")) + f(r.get("CORREIO_KG"))
            if not kg: continue
            nat = "int" if r.get("NATUREZA") == "INTERNACIONAL" else "dom"
            for lado, s in (("emb", r.get("AEROPORTO_DE_ORIGEM_SIGLA")), ("des", r.get("AEROPORTO_DE_DESTINO_SIGLA"))):
                if (r.get(f"AEROPORTO_DE_{'ORIGEM' if lado == 'emb' else 'DESTINO'}_PAIS") or "") != "BRASIL": continue
                a = per.setdefault(k, {}).setdefault(s, {"nome": r.get(f"AEROPORTO_DE_{'ORIGEM' if lado == 'emb' else 'DESTINO'}_NOME"), "uf": r.get(f"AEROPORTO_DE_{'ORIGEM' if lado == 'emb' else 'DESTINO'}_UF"), "dom": 0, "int": 0, "emb": 0, "des": 0})
                a[nat] += kg; a[lado] += kg
    meses = sorted(per)[-12:]; tot = {}
    for k in meses:
        for s, a in per[k].items():
            t = tot.setdefault(s, {"nome": a["nome"], "uf": a["uf"], "dom": 0, "int": 0, "emb": 0, "des": 0, "mensal": {}})
            for x in ("dom", "int", "emb", "des"): t[x] += a[x]
            t["mensal"][f"{k[0]}-{k[1]:02d}"] = round((a["dom"] + a["int"]) / 1000, 1)
    raw = (ROOT / "data/raw/AerodromosPublicos.csv").read_bytes().decode("latin1").split("\n", 1)[1]
    cad = {r["Código OACI"]: r for r in csv.DictReader(io.StringIO(raw), delimiter=";")}
    out = {}
    for s, t in tot.items():
        c = cad.get(s)
        if not c: continue
        out[s] = {**{k: (round(v / 1000, 1) if k in ("dom", "int", "emb", "des") else v) for k, v in t.items()}, "nome_oficial": c["Nome"], "municipio_servido": c["Município Servido"], "uf_servido": c["UF Servido"],
                  "lat": float(c["LATGEOPOINT"]), "lon": float(c["LONGEOPOINT"]), "op_noturna": c["Operação Noturna"], "portaria": c.get("Link Portaria") or None}
    meta = {"fonte_movimento": URL_EST, "fonte_cadastro": URL_AER, "periodo": [f"{meses[0][0]}-{meses[0][1]:02d}", f"{meses[-1][0]}-{meses[-1][1]:02d}"], "unidade": "toneladas (carga paga + correio, embarcada + desembarcada)"}
    (ROOT / "data/aeroportos.json").write_text(json.dumps({**meta, "aeroportos": out}, ensure_ascii=False, indent=0), encoding="utf-8")
    top = sorted(out.items(), key=lambda x: -(x[1]["dom"] + x[1]["int"]))[:10]
    print(meta["periodo"], len(out), [(k, round(v["dom"] + v["int"])) for k, v in top])
if __name__ == "__main__": main(sys.argv[1])
