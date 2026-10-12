#!/usr/bin/env python3
"""Extrai os coeficientes do piso mínimo de frete (ANTT) do texto oficial no ANTTlegis e grava data/frete_minimo.json.
Uso: python tools/antt_frete.py  (para um novo reajuste, atualize ATO abaixo com o número, data, diesel e URL do novo ato)."""
import html, json, re, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
ATO = {"nome": "Portaria SUROC/ANTT nº 22, de 28 de setembro de 2026", "publicacao": "2026-09-29", "vigencia": "2026-09-30",
       "diesel_ref": 7.33, "diesel_ref_semana": "20/09 a 26/09/2026 (média Brasil ANP, diesel S10)",
       "url": "https://anttlegis.antt.gov.br/action/ActionDatalegis.php?acao=abrirTextoAto&cod_menu=9230&cod_modulo=623&numeroAto=00000022&orgao=SUROC%2FANTT%2FMT&seqAto=000&tipo=POR&valorAno=2026",
       "noticia": "https://www.gov.br/antt/pt-br/assuntos/noticias-defeso-eleitoral/antt-atualiza-coeficientes-do-piso-minimo-do-frete-e-divulga-novo-preco-de-referencia-do-diesel",
       "resolucao_base": "Resolução ANTT nº 5.867, de 14 de janeiro de 2020 (Anexo II)", "lei": "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13703.htm"}
TAB = {"A": "Carga lotação — contratação da composição veicular ou caminhão simples",
       "B": "Carga lotação — contratação apenas da unidade de tração (cavalo mecânico)",
       "C": "Carga lotação de alto desempenho — composição veicular ou caminhão simples",
       "D": "Carga lotação de alto desempenho — apenas unidade de tração"}
EIX = ["2", "3", "4", "5", "6", "7", "9"]
def main():
    raw = urllib.request.urlopen(urllib.request.Request(ATO["url"], headers={"User-Agent": "Mozilla/5.0"}), timeout=90).read()
    s = raw.decode("utf-8", "ignore") if b"\xc3" in raw else raw.decode("latin-1")
    T = re.findall(r"<table.*?</table>", s, re.S | re.I)
    data = [t for t in T if "Deslocamento" in t]
    assert len(data) >= 4, "estrutura do ato mudou: revise manualmente"
    out = {}
    for name, t in zip("ABCD", data[:4]):
        cur = None; d = {}
        for tr in re.findall(r"<tr.*?</tr>", t, re.S | re.I):
            c = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip() for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)]
            if not c: continue
            if re.fullmatch(r"\d*", c[0]) and len(c) == 11: c = c[1:]
            if c[0]: cur = c[0]
            key = "ccd" if "CCD" in c[1] else "cc"
            d.setdefault(cur, {})[key] = {e: (float(v.replace(".", "").replace(",", ".")) if v else None) for e, v in zip(EIX, c[3:10])}
        out[name] = {"titulo": TAB[name], "cargas": d}
    (ROOT / "data" / "frete_minimo.json").write_text(json.dumps({"ato": ATO, "eixos": EIX, "tabelas": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    print({k: len(v["cargas"]) for k, v in out.items()})
if __name__ == "__main__": main()
