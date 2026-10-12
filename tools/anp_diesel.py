#!/usr/bin/env python3
"""Baixa o Levantamento de Preços de Combustíveis (LPC) semanal da ANP e grava data/diesel.json.
Fonte: https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/levantamento-de-precos-de-combustiveis-ultimas-semanas-pesquisadas
Mantém as últimas 8 semanas. Só diesel (S10 e S500 comum). Sem estimativas: apenas os números publicados pela ANP."""
import io, json, re, sys, urllib.request
from pathlib import Path
import openpyxl
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "diesel.json"
PAGE = "https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/levantamento-de-precos-de-combustiveis-ultimas-semanas-pesquisadas"
UA = "Mozilla/5.0 (compatible; ModalNewsBot/1.0)"
UF = {"ACRE": "AC", "ALAGOAS": "AL", "AMAPA": "AP", "AMAZONAS": "AM", "BAHIA": "BA", "CEARA": "CE", "DISTRITO FEDERAL": "DF", "ESPIRITO SANTO": "ES",
      "GOIAS": "GO", "MARANHAO": "MA", "MATO GROSSO": "MT", "MATO GROSSO DO SUL": "MS", "MINAS GERAIS": "MG", "PARA": "PA", "PARAIBA": "PB", "PARANA": "PR",
      "PERNAMBUCO": "PE", "PIAUI": "PI", "RIO DE JANEIRO": "RJ", "RIO GRANDE DO NORTE": "RN", "RIO GRANDE DO SUL": "RS", "RONDONIA": "RO", "RORAIMA": "RR",
      "SANTA CATARINA": "SC", "SAO PAULO": "SP", "SERGIPE": "SE", "TOCANTINS": "TO"}
PROD = {"OLEO DIESEL S10": "s10", "OLEO DIESEL": "s500"}

def get(url, raw=False):
    r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=90).read()
    return r if raw else r.decode("utf-8", "ignore")

def parse(data):
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    week = {"municipios": {}, "estados": {}, "brasil": {}}
    for ws, key in (("MUNICIPIOS", "municipios"), ("ESTADOS", "estados"), ("BRASIL", "brasil")):
        hdr = None
        for row in wb[ws].iter_rows(values_only=True):
            if row and row[0] == "DATA INICIAL": hdr = list(row); continue
            if not hdr or not row or row[0] is None: continue
            r = dict(zip(hdr, row)); p = PROD.get(str(r.get("PRODUTO", "")).strip())
            if not p: continue
            week["ini"], week["fim"] = r["DATA INICIAL"].date().isoformat(), r["DATA FINAL"].date().isoformat()
            v = {"media": r["PREÇO MÉDIO REVENDA"], "min": r["PREÇO MÍNIMO REVENDA"], "max": r["PREÇO MÁXIMO REVENDA"], "postos": r["NÚMERO DE POSTOS PESQUISADOS"]}
            if key == "municipios":
                k = f'{r["MUNICÍPIO"].strip()}|{UF[r["ESTADO"].strip()]}'
            elif key == "estados": k = UF[r["ESTADOS"].strip()]
            else: k = "BR"
            week[key].setdefault(k, {})[p] = v
    return week

def main():
    html = get(PAGE)
    files = sorted(set(re.findall(r'https://[^"]+resumo_semanal_lpc_(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})\.xlsx', html)), reverse=True)[:8]
    urls = {f[1]: f"https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/arquivos-lpc/{f[0][:4]}/resumo_semanal_lpc_{f[0]}_{f[1]}.xlsx" for f in files}
    db = json.loads(OUT.read_text()) if OUT.exists() else {"fonte": PAGE, "semanas": {}}
    for fim, u in urls.items():
        if fim in db["semanas"]: continue
        try:
            w = parse(get(u, raw=True)); w["arquivo"] = u; db["semanas"][fim] = w; print("ok", fim)
        except Exception as ex: print("! falhou", u, ex)
    db["semanas"] = dict(sorted(db["semanas"].items(), reverse=True)[:8])
    OUT.write_text(json.dumps(db, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("semanas:", list(db["semanas"]))

if __name__ == "__main__": main()
