#!/usr/bin/env python3
"""Rodovias federais concedidas: praças de pedágio (cadastro ANTT) + volume mensal de veículos por praça (ANTT, dados abertos).
Fontes: https://dados.antt.gov.br/dataset/praca-de-pedagio e https://dados.antt.gov.br/dataset/volume-trafego-praca-pedagio
Grava data/rodovias.json. Não estima nada: soma os volumes publicados."""
import csv, io, json, re, unicodedata, urllib.request, datetime as dt
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
API = "https://dados.antt.gov.br/api/3/action/package_show?id="
def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "ModalNewsBot/1.0"}), timeout=180).read()
def n(s): return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower())
def res(pkg, pat):
    rs = json.loads(get(API + pkg))["result"]["resources"]
    c = [r for r in rs if re.search(pat, r["url"]) and r["url"].endswith(".csv")]
    return sorted(c, key=lambda r: r["url"])[-1]["url"]
def rows(u):
    raw = get(u)
    try: t = raw.decode("utf-8-sig")
    except UnicodeDecodeError: t = raw.decode("latin-1")
    return list(csv.DictReader(io.StringIO(t), delimiter=";"))
def main():
    import sys
    f = ROOT / "data" / "rodovias.json"
    if f.exists() and "--force" not in sys.argv:
        age = (dt.date.today() - dt.date.fromisoformat(json.loads(f.read_text())["gerado"])).days
        if age < 7: print(f"rodovias.json com {age} dia(s); nada a fazer"); return
    year = dt.date.today().year
    pu = res("praca-de-pedagio", r"dados-dos-pracas-de-pedagio"); vu = res("volume-trafego-praca-pedagio", rf"{year}_mensal_consolidado")
    pr = [r for r in rows(pu) if r["situacao"].strip().lower() == "ativo"]
    vol = rows(vu)
    # volume por (concessionária, praça, mês, tipo)
    agg = {}
    for r in vol:
        k = (n(r["concessionaria"]), n(r["praca"]))
        m = r["mes_ano"]; t = r["tipo_de_veiculo"].strip()
        v = float(r["volume_total"].replace(".", "").replace(",", ".") or 0)
        agg.setdefault(k, {}).setdefault(m, {}).setdefault(t, 0); agg[k][m][t] += v
    keys = list(agg)
    def find(c, p):
        cc, pp = n(c), n(p)
        same = [k for k in keys if k[0] == cc]
        for k in same:
            if k[1] == pp: return k
        c = [k for k in same if pp in k[1] or k[1] in pp]
        return min(c, key=lambda k: abs(len(k[1]) - len(pp))) if c else None
    rod = {}
    unmatched = 0
    for r in pr:
        br = r["rodovia"].strip().upper().replace(" ", "")
        if not re.match(r"BR-\d{3}$", br): continue
        k = find(r["concessionaria"], r["praca_de_pedagio"])
        if not k: unmatched += 1
        d = rod.setdefault(br, {"concessionarias": set(), "ufs": set(), "pracas": []})
        d["concessionarias"].add(r["concessionaria"].strip()); d["ufs"].add(r["uf"].strip())
        d["pracas"].append({"nome": r["praca_de_pedagio"].strip(), "concessionaria": r["concessionaria"].strip(), "uf": r["uf"].strip(),
                            "km": float(r["km_m"].replace(",", ".") or 0), "municipio": r["municipal"].strip(), "volume": agg.get(k, {}) if k else {}})
    for br, d in rod.items():
        d["concessionarias"] = sorted(d["concessionarias"]); d["ufs"] = sorted(d["ufs"]); d["pracas"].sort(key=lambda p: (p["uf"], p["km"]))
    out = {"fonte_pracas": pu, "fonte_volume": vu, "ano": year, "gerado": dt.date.today().isoformat(), "rodovias": rod}
    (ROOT / "data" / "rodovias.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(len(rod), "rodovias;", sum(len(d["pracas"]) for d in rod.values()), "praças; sem volume:", unmatched)
if __name__ == "__main__": main()
