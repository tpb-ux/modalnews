"""Utilidades geográficas compartilhadas: capitais, polos REGIC (IBGE), distância em linha reta."""
import json, math, re
from pathlib import Path
from paginas import norm
ROOT = Path(__file__).resolve().parent
CAPITAIS = {"AC": "Rio Branco", "AL": "Maceió", "AP": "Macapá", "AM": "Manaus", "BA": "Salvador", "CE": "Fortaleza", "DF": "Brasília", "ES": "Vitória", "GO": "Goiânia", "MA": "São Luís",
            "MT": "Cuiabá", "MS": "Campo Grande", "MG": "Belo Horizonte", "PA": "Belém", "PB": "João Pessoa", "PR": "Curitiba", "PE": "Recife", "PI": "Teresina", "RJ": "Rio de Janeiro",
            "RN": "Natal", "RS": "Porto Alegre", "RO": "Porto Velho", "RR": "Boa Vista", "SC": "Florianópolis", "SP": "São Paulo", "SE": "Aracaju", "TO": "Palmas"}
_ib = None
def ibge():
    global _ib
    if _ib is None: _ib = json.loads((ROOT / "data/ibge_municipios.json").read_text())
    return _ib
def code(nome, uf): return str((ibge().get(f"{norm(nome)}|{uf}") or {}).get("ibge", ""))
def polo_nome(txt):
    """'Cacoal (RO) - Capital Regional C (2C)' -> ('Cacoal','RO'); 'Arranjo Populacional de Porto Velho/RO - ...' -> ('Porto Velho','RO')."""
    if not isinstance(txt, str): return None
    m = re.match(r"Arranjo Populacional de (.+?)/([A-Z]{2})", txt)
    if m: return m.group(1).split(" - ")[0], m.group(2)
    m = re.match(r"(.+?) \(([A-Z]{2})\)", txt)
    return (m.group(1), m.group(2)) if m else None
def km(a, b):
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"]); dl = math.radians(b["lon"] - a["lon"]); dp = p2 - p1
    return 2 * 6371 * math.asin(math.sqrt(math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))
