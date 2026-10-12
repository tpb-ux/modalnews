"""Tarifas de pedágio das concessões federais: lê as páginas oficiais 'Tarifas de Pedágio' de cada concessão no portal da ANTT
(gov.br/antt/.../lista-de-concessoes/<concessão>/tarifas-de-pedagio) e guarda a tarifa da categoria 1 (multiplicador 1,0) por praça/coluna.
Saída: data/pedagio_tarifas.json. Valores das demais categorias = tarifa base × multiplicador oficial (caminhões: nº de eixos)."""
import json, re, time, urllib.request
from pathlib import Path
from bs4 import BeautifulSoup
ROOT = Path(__file__).resolve().parent.parent; BASE = "https://www.gov.br/antt/pt-br/assuntos/rodovias/concessionarias/lista-de-concessoes"
def get(u):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 ModalNews"}), timeout=60) as r: return r.read().decode("utf-8", "replace")
        except Exception as e: err = e; time.sleep(3)
    raise err
num = lambda s: float(s.replace(".", "").replace(",", ".")) if re.fullmatch(r"\d{1,3}(\.\d{3})*,\d{2}", s.strip()) else None
def parse(html):
    soup = BeautifulSoup(html, "lxml"); out = []
    upd = re.search(r"Atualizado em (\d{2}/\d{2}/\d{4})", soup.get_text(" ")); upd = upd.group(1) if upd else None
    for tb in soup.find_all("table"):
        rows = [[c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])] for tr in tb.find_all("tr")]
        lab = []; head = ""
        prev = tb.find_previous(["h2", "h3", "h4", "strong"]); head = prev.get_text(" ", strip=True) if prev else ""
        for r in rows:
            ps = [c for c in r if re.fullmatch(r"P\s?\d+[A-Z]?", c.strip())]
            if len(ps) >= 2: lab = [p.replace(" ", "") for p in ps]
            if any("Automóvel, caminhonete e furgão" in c or "Automóvel, caminhonete e furgao" in c for c in r):
                vals = [num(c) for c in r]; vals = [v for v in vals if v is not None]
                if vals: out.append({"titulo": head, "labels": lab if len(lab) == len(vals) else [], "cat1": vals})
                break
    return out, upd
def main():
    import datetime as dt
    f = ROOT / "data/pedagio_tarifas.json"
    if f.exists() and "--forcar" not in __import__("sys").argv:
        g = json.loads(f.read_text()).get("gerado")
        if g and (dt.date.today() - dt.date.fromisoformat(g)).days < 7: print("tarifas: dados com menos de 7 dias"); return
    lc = get(BASE); slugs = sorted(set(re.findall(r'lista-de-concessoes/([A-Za-z0-9\-]+)"', lc)) - {""})
    res = {}
    for s in slugs:
        if "encerrado" in s or "caducidade" in s: continue
        try:
            pg = get(f"{BASE}/{s}"); links = sorted(set(re.findall(rf'href="({BASE}/{s}/[^"]*tarifa[^"]*)"', pg)))
            if not links: print("sem link", s); continue
            u = links[0]; html = get(u); tabs, upd = parse(html)
            if not tabs and links[1:]: u = links[1]; tabs, upd = parse(get(u))
            nome = re.search(r"<title>([^<]*)</title>", pg); nome = nome.group(1).split("—")[0].strip() if nome else s
            if tabs: res[s] = {"nome": nome, "url": u, "atualizado": upd, "tabelas": tabs}; print("ok", s, tabs[0]["cat1"][:5], tabs[0]["labels"][:5])
            else: print("sem tabela", s, u)
        except Exception as e: print("erro", s, e)
        time.sleep(1)
    (ROOT / "data/pedagio_tarifas.json").write_text(json.dumps({"fonte": BASE, "gerado": time.strftime("%Y-%m-%d"), "concessoes": res}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(res), "concessões com tarifa")
if __name__ == "__main__": main()
