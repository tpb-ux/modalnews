"""Tarifa de pedágio por praça federal, a partir das tabelas oficiais da ANTT (data/pedagio_tarifas.json).
Só retorna valor quando a correspondência praça→tarifa é inequívoca (rótulo P<n> na tabela, tarifa única na concessão ou tabela com uma só coluna)."""
import json, re, statistics
from pathlib import Path
ROOT = Path(__file__).resolve().parent
MAP = {"AUTOPISTA FLUMINENSE": "autopista-fluminense", "AUTOPISTA LITORAL SUL": "autopista-litoral-sul", "AUTOPISTA PLANALTO SUL": "autopista-planalto-sul", "AUTOPISTA REGIS BITTENCOURT": "autopista-regis-bittencourt",
       "ECOVIAS CAPIXABA": "ecovias-capixaba", "ECOVIAS DO ARAGUAIA": "ecovias-araguaia", "ECOVIAS PONTE": "ecoponte", "ECOVIAS RIO MINAS": "ecoriominas", "LITORAL PIONEIRO": "epr-litoral-pioneiro",
       "MOTIVA MINAS SP": "motiva-minas-sp", "NOVA 364": "nova-364", "NOVA ROTA DO OESTE": "rota-do-oeste", "PANTANAL": "motiva-pantanal", "RIOSP": "ccr-rio-sp", "TRANSBRASILIANA": "Transbrasiliana",
       "VIA ARAUCÁRIA": "via-araucaria", "VIA BRASIL": "via-brasil", "VIA COSTEIRA": "ccr-viacosteira", "VIA SUL": "viasul"}
_T = None
def dados():
    global _T
    if _T is None:
        f = ROOT / "data/pedagio_tarifas.json"; _T = json.loads(f.read_text()) if f.exists() else {"concessoes": {}}
    return _T
def _clean(vals): return [v for v in vals if v >= 1.5]
def concessao(conc): return dados()["concessoes"].get(MAP.get(conc.upper(), ""))
def tarifa(conc, praca_nome):
    """Tarifa base (categoria 1, multiplicador 1,0) em R$ ou None."""
    c = concessao(conc)
    if not c: return None
    m = re.match(r"P\s?(\d+[A-Z]?)\b", praca_nome.strip()); pc = f"P{m.group(1)}" if m else None
    for t in c["tabelas"]:
        v = _clean(t["cat1"])
        if pc and t["labels"] and len(t["labels"]) == len(t["cat1"]) and pc in t["labels"]: return t["cat1"][t["labels"].index(pc)]
    allv = [x for t in c["tabelas"] for x in _clean(t["cat1"])]
    if allv and len(set(allv)) == 1: return allv[0]
    for t in c["tabelas"]:
        v = _clean(t["cat1"])
        if len(c["tabelas"]) == 1 and len(v) >= 3 and abs(v[1] - 2 * v[0]) < 0.02 and abs(v[2] - 1.5 * v[0]) < 0.02: return v[0]
    return None
def faixa(conc):
    c = concessao(conc)
    if not c: return None
    allv = sorted({x for t in c["tabelas"] for x in _clean(t["cat1"])})
    return (allv[0], allv[-1], c["url"], c.get("atualizado")) if allv else None
