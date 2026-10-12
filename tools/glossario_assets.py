#!/usr/bin/env python3
"""Gera (uma vez, localmente) imagens e referências externas do glossário.
- Imagens: Openverse (sem chave), licenças CC0 / PDM / CC BY; salva WebP em static/img/glossario/<slug>.webp (+ -480)
  e registra origem/autor/licença em data/glossario_imagens.yaml.
- Referências: Wikipedia pt (via API) + fontes oficiais mapeadas; cada URL validada com HTTP 200.
  Salva em data/glossario_refs.yaml.
Uso: python tools/glossario_assets.py [--so-refs|--so-imagens]"""
import io, json, sys, time, urllib.parse, urllib.request
from pathlib import Path
import yaml
from PIL import Image
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
from build import slugify
UA = "ModalNewsBot/1.0 (+https://tpb-ux.github.io/modalnews/; glossario)"
IMGDIR = ROOT / "static" / "img" / "glossario"; IMGDIR.mkdir(parents=True, exist_ok=True)

Q2 = {"cross-docking":"loading dock trucks","wms":"warehouse scanner","tms":"truck logistics","picking":"warehouse worker shelves","ct-e":"truck cargo","carga-lotacao":"semi trailer truck","seguro-de-carga":"cargo truck accident","condominio-logistico":"warehouse building","curva-abc":"warehouse inventory","sku":"barcode scanner","inventario-ciclico":"warehouse inventory","acuracidade-de-estoque":"warehouse shelves inventory","fefo":"food warehouse","lote-economico":"warehouse pallets","vmi":"supermarket shelves","3pl":"warehouse forklift","fulfillment":"parcel warehouse","paletizacao":"pallets stacked","gemeo-digital":"factory automation","drawback":"export port","agente-de-carga":"cargo containers port","nearshoring":"factory workers","custo-logistico":"freight truck"}
Q = {  # busca de imagem (inglês) por slug
 "cross-docking":"cross docking warehouse trucks","wms":"warehouse barcode scanner","tms":"truck fleet dispatch office","erp":"business computer dashboard",
 "picking":"warehouse order picking","packing":"packing boxes warehouse","last-mile":"delivery van parcel","first-mile":"parcel pickup courier",
 "middle-mile":"semi truck highway","ct-e":"truck driver documents","mdf-e":"truck cargo inspection","rntrc":"brazil truck","frete":"cargo truck road",
 "frete-minimo":"diesel fuel truck","peso-cubado":"cardboard boxes stack","cubagem":"measuring box tape","carga-fracionada":"pallets loading truck",
 "carga-lotacao":"full truckload trailer","roteirizacao":"route map navigation","milk-run":"milk truck","modal-rodoviario":"trucks highway",
 "modal-ferroviario":"freight train","modal-aquaviario":"barge river cargo","modal-aereo":"cargo airplane","modal-dutoviario":"pipeline",
 "multimodal":"container train truck","intermodal":"intermodal container terminal","cabotagem":"coastal container ship","transit-time":"cargo ship ocean",
 "ad-valorem":"cargo insurance","gris":"truck security escort","seguro-de-carga":"damaged cargo","vale-pedagio":"toll plaza","frete-retorno":"empty truck trailer",
 "rastreamento":"gps tracking","telemetria":"truck dashboard","torre-de-controle":"control room screens","centro-de-distribuicao":"distribution center",
 "condominio-logistico":"logistics park warehouses","galpao-classe-aaa":"modern warehouse interior","taxa-de-vacancia":"empty warehouse","doca":"loading dock",
 "enderecamento":"warehouse aisle racks","putaway":"forklift pallet rack","slotting":"warehouse shelves","curva-abc":"inventory chart","sku":"product barcode",
 "inventario-ciclico":"inventory count warehouse","acuracidade-de-estoque":"stock taking","fifo":"pallets warehouse","fefo":"food expiry date",
 "estoque-de-seguranca":"stockpile warehouse","ponto-de-pedido":"stock shelves supermarket","lote-economico":"bulk goods","giro-de-estoque":"retail stock",
 "ruptura":"empty supermarket shelves","lead-time":"clock","otif":"delivery truck","nivel-de-servico":"customer service","sla":"contract signing",
 "supply-chain":"supply chain","s-op":"business meeting planning","mrp":"factory production line","just-in-time":"car assembly line","kanban":"kanban board",
 "efeito-chicote":"whip","vmi":"vending supplier shelves","logistica-reversa":"recycling","rastreabilidade":"barcode label","operador-logistico":"logistics warehouse",
 "3pl":"logistics company warehouse","4pl":"logistics network","fulfillment":"ecommerce fulfillment center","dark-store":"grocery delivery",
 "porta-palete":"pallet racking","palete-pbr":"wooden pallet","paletizacao":"palletized goods","yms":"truck yard","edi":"computer data network","rfid":"rfid tag",
 "codigo-de-barras":"barcode","iot":"internet of things sensor","agv":"automated guided vehicle","amr":"warehouse robot","automacao-de-armazem":"automated warehouse",
 "gemeo-digital":"3d simulation factory","incoterms":"international trade port","fob":"ship loading port crane","cif":"container ship","exw":"factory gate",
 "fca":"container terminal truck","ddp":"customs delivery","despacho-aduaneiro":"customs","canais-de-parametrizacao":"customs inspection","siscomex":"customs office",
 "du-e":"export containers","duimp":"import containers","ncm":"customs documents","drawback":"export manufacturing","ex-tarifario":"industrial machinery",
 "oea":"customs security","porto-seco":"dry port container","teu":"shipping containers stack","demurrage":"container yard","free-time":"container port",
 "armador":"container ship","bl":"bill of lading","awb":"air cargo","nvocc":"shipping containers","agente-de-carga":"freight forwarding",
 "nearshoring":"factory mexico","custo-logistico":"logistics costs"}
REFS = {  # referências oficiais/setoriais (validadas antes de salvar)
 "incoterms":["https://iccwbo.org/business-solutions/incoterms-rules/"],"fob":["https://iccwbo.org/business-solutions/incoterms-rules/"],
 "cif":["https://iccwbo.org/business-solutions/incoterms-rules/"],"exw":["https://iccwbo.org/business-solutions/incoterms-rules/"],
 "fca":["https://iccwbo.org/business-solutions/incoterms-rules/"],"ddp":["https://iccwbo.org/business-solutions/incoterms-rules/"],
 "ct-e":["https://www.cte.fazenda.gov.br/portal/"],"mdf-e":["https://dfe-portal.svrs.rs.gov.br/Mdfe"],
 "rntrc":["https://www.gov.br/antt/pt-br/assuntos/cargas/rntrc"],"frete-minimo":["https://www.gov.br/antt/pt-br/assuntos/cargas/pisos-minimos-de-frete"],
 "vale-pedagio":["https://www.gov.br/antt/pt-br/assuntos/cargas/vale-pedagio-obrigatorio"],
 "siscomex":["https://www.gov.br/siscomex/pt-br"],"du-e":["https://www.gov.br/siscomex/pt-br"],"duimp":["https://www.gov.br/siscomex/pt-br"],
 "despacho-aduaneiro":["https://www.gov.br/receitafederal/pt-br/assuntos/aduana-e-comercio-exterior"],
 "canais-de-parametrizacao":["https://www.gov.br/receitafederal/pt-br/assuntos/aduana-e-comercio-exterior"],
 "oea":["https://www.gov.br/receitafederal/pt-br/assuntos/aduana-e-comercio-exterior/importacao-e-exportacao/oea"],
 "drawback":["https://www.gov.br/mdic/pt-br/assuntos/comercio-exterior/drawback"],"ex-tarifario":["https://www.gov.br/mdic/pt-br/assuntos/sdic/ex-tarifario"],
 "cabotagem":["https://www.gov.br/antaq/pt-br"],"modal-aquaviario":["https://www.gov.br/antaq/pt-br"],"modal-ferroviario":["https://www.gov.br/antt/pt-br"],
 "codigo-de-barras":["https://www.gs1br.org/"],"rfid":["https://www.gs1br.org/"],"logistica-reversa":["https://www.gov.br/mma/pt-br"],
 "operador-logistico":["https://abolbrasil.org.br/"],"3pl":["https://abolbrasil.org.br/"],"modal-rodoviario":["https://www.cnt.org.br/"],
}
WIKI = {"modal-rodoviario":"Transporte rodoviário","modal-ferroviario":"Transporte ferroviário","modal-aereo":"Transporte aéreo","modal-aquaviario":"Transporte aquaviário",
 "modal-dutoviario":"Dutoviário","supply-chain":"Cadeia de suprimentos","just-in-time":"Just in time","kanban":"Kanban","efeito-chicote":"Efeito chicote",
 "logistica-reversa":"Logística reversa","incoterms":"Incoterms","codigo-de-barras":"Código de barras","rfid":"RFID","iot":"Internet das coisas",
 "erp":"Sistema integrado de gestão empresarial","teu":"TEU","cabotagem":"Cabotagem","drawback":"Drawback","ncm":"Nomenclatura Comum do Mercosul",
 "curva-abc":"Curva ABC","fifo":"FIFO","mrp":"Planejamento das necessidades de materiais","cross-docking":"Cross docking","milk-run":"Milk run",
 "porto-seco":"Porto seco","agv":"Veículo guiado automaticamente","gemeo-digital":"Gêmeo digital","nearshoring":"Nearshoring","lote-economico":"Lote econômico",
 "multimodal":"Transporte multimodal","intermodal":"Transporte intermodal","armador":"Armador","bl":"Conhecimento de embarque","sku":"Stock keeping unit",
 "palete-pbr":"Palete","paletizacao":"Palete","porta-palete":"Porta-paletes","edi":"Intercâmbio eletrônico de dados","rastreabilidade":"Rastreabilidade",
 "telemetria":"Telemetria","s-op":"Sales and operations planning","3pl":"Terceirização logística","fulfillment":"Fulfillment","last-mile":"Última milha",
 "sla":"Acordo de nível de serviço","lead-time":"Lead time","ruptura":"Ruptura de estoque","fob":"Free on board","cif":"Cost, insurance and freight",
 "exw":"Ex works","ddp":"Delivered duty paid","ct-e":"Conhecimento de transporte eletrônico","wms":"Warehouse management system",
 "tms":"Transportation management system","giro-de-estoque":"Giro de estoque","estoque-de-seguranca":"Estoque de segurança","demurrage":"Sobre-estadia"}

def get(url, timeout=20, raw=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return (r.status, r.read() if raw else r.read(200000).decode("utf-8", "ignore"), r.geturl())

def ok(url):
    try: return get(url)[0] == 200
    except Exception: return False

def refs(terms):
    out = {}
    for t in terms:
        s = t["slug"]; lst = []
        if s in WIKI:
            u = "https://pt.wikipedia.org/wiki/" + urllib.parse.quote(WIKI[s].replace(" ", "_"))
            if ok(u): lst.append({"titulo": f"{WIKI[s]} — Wikipédia", "url": u})
        for u in REFS.get(s, []):
            if ok(u):
                host = urllib.parse.urlparse(u).netloc.replace("www.", "")
                nome = {"iccwbo.org": "ICC — Incoterms® rules", "gov.br": "gov.br", "gs1br.org": "GS1 Brasil", "abolbrasil.org.br": "ABOL — Associação Brasileira de Operadores Logísticos",
                        "cnt.org.br": "CNT — Confederação Nacional do Transporte", "cte.fazenda.gov.br": "Portal Nacional do CT-e", "dfe-portal.svrs.rs.gov.br": "Portal do MDF-e (SVRS)"}.get(host, host)
                if host == "gov.br": nome = {"antt": "ANTT", "siscomex": "Portal Siscomex", "receitafederal": "Receita Federal", "mdic": "MDIC", "antaq": "ANTAQ", "mma": "Ministério do Meio Ambiente"}.get(u.split("/")[3], "gov.br")
                lst.append({"titulo": nome, "url": u})
            else: print(f"  ref falhou: {u}")
        if lst: out[s] = lst[:3]
        print(f"refs {s}: {len(lst)}")
    (ROOT / "data" / "glossario_refs.yaml").write_text("# Referências externas validadas (HTTP 200) — gerado por tools/glossario_assets.py\n" + yaml.safe_dump(out, allow_unicode=True, sort_keys=True), encoding="utf-8")

def images(terms):
    reg_f = ROOT / "data" / "glossario_imagens.yaml"
    reg = yaml.safe_load(reg_f.read_text(encoding="utf-8")) if reg_f.exists() else {}
    reg = reg or {}; used = {v["id"] for v in reg.values()}
    for t in terms:
        s = t["slug"]
        if s in reg and (IMGDIR / f"{s}.webp").exists(): continue
        q = (Q2.get(s) if "--fallback" in sys.argv else None) or Q.get(s, "logistics"); found = None
        try:
            api = "https://api.openverse.org/v1/images/?" + urllib.parse.urlencode({"q": q, "license": "cc0,pdm,by", "page_size": 20, "mature": "false"})
            res = json.loads(get(api)[1])["results"]
        except Exception as ex: print(f"! {s}: api {ex}"); continue
        for r in res:
            if r["id"] in used or (r.get("width") or 0) < 800: continue
            hay = ((r.get("title") or "") + " " + " ".join(tg.get("name", "") for tg in r.get("tags") or [])).lower()
            kws = [w for w in q.lower().split() if len(w) > 3]
            if sum(1 for w in kws if w.rstrip("s") in hay) < min(2, len(kws)): continue  # relevância mínima
            try:
                st, data, _ = get(r["url"], 30, raw=True)
                im = Image.open(io.BytesIO(data)); im.load(); im = im.convert("RGB")
                if im.width < 800: continue
                big = im.resize((1200, round(im.height * 1200 / im.width)), Image.LANCZOS) if im.width > 1200 else im
                big.save(IMGDIR / f"{s}.webp", "WEBP", quality=80, method=6)
                im.resize((480, round(im.height * 480 / im.width)), Image.LANCZOS).save(IMGDIR / f"{s}-480.webp", "WEBP", quality=78, method=6)
                found = {"id": r["id"], "arquivo": f"static/img/glossario/{s}.webp", "largura": big.width, "altura": big.height,
                         "alt": f"{t['t']}: {r.get('title') or q}"[:150], "titulo_original": r.get("title"), "autor": r.get("creator") or "Autor desconhecido",
                         "autor_url": r.get("creator_url"), "licenca": f"{r['license'].upper()} {r.get('license_version') or ''}".strip(),
                         "licenca_url": r.get("license_url"), "origem": r.get("foreign_landing_url"), "provedor": r.get("source"), "busca": q}
                break
            except Exception: continue
        if found: reg[s] = found; used.add(found["id"]); print(f"img {s}: {found['provedor']} {found['licenca']}")
        else: print(f"! {s}: sem imagem")
        reg_f.write_text("# Origem e licença das imagens do glossário (Openverse) — gerado por tools/glossario_assets.py\n" + yaml.safe_dump(reg, allow_unicode=True, sort_keys=True), encoding="utf-8")
        time.sleep(0.5)

if __name__ == "__main__":
    terms = yaml.safe_load((ROOT / "data" / "glossario.yaml").read_text(encoding="utf-8"))
    for t in terms: t["slug"] = slugify(t["t"])
    if "--so-imagens" not in sys.argv: refs(terms)
    if "--so-refs" not in sys.argv: images(terms)
