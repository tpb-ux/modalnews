"""IndexNow: detecta páginas indexáveis novas ou alteradas (hash do HTML sem partes voláteis) e notifica api.indexnow.org.
build.py chama diff() -> grava data/indexnow_pendentes.txt; o workflow roda `python indexnow.py ping` após o deploy e commita data/indexnow_hashes.json."""
import hashlib, json, re, sys, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent; HF = ROOT / "data/indexnow_hashes.json"; PF = ROOT / "data/indexnow_pendentes.txt"
def _norm(h): return re.sub(r'style\.css\?v=\w+|<script type="application/ld\+json">\{"@context": "https://schema.org", "@graph": \[\{"@type": "NewsMediaOrganization".*?</script>', "", h)
def diff(B):
    old = json.loads(HF.read_text()) if HF.exists() else {}; new = {}; changed = []
    for f in B.OUT.rglob("index.html"):
        h = f.read_text(encoding="utf-8", errors="ignore")
        if 'name="robots" content="noindex' in h: continue
        rel = "/" + str(f.parent.relative_to(B.OUT)).replace("\\", "/") + "/"; rel = "/" if rel == "/./" else rel
        new[rel] = hashlib.sha1(_norm(h).encode()).hexdigest()[:16]
        if old.get(rel) != new[rel]: changed.append(B.BASE + rel)
    PF.write_text("\n".join(sorted(changed)), encoding="utf-8"); (ROOT / "data/indexnow_hashes.next.json").write_text(json.dumps(new, separators=(",", ":")))
    print(f"IndexNow: {len(changed)} URL(s) novas/alteradas")
def ping():
    import yaml
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text()); key = cfg.get("indexnow_key"); base = cfg["base_url"].rstrip("/")
    urls = [u for u in PF.read_text().split("\n") if u] if PF.exists() else []
    nxt = ROOT / "data/indexnow_hashes.next.json"
    if not key or not urls: print("IndexNow: nada a enviar")
    else:
        ok = True
        for i in range(0, len(urls), 10000):
            body = json.dumps({"host": base.split("//")[1], "key": key, "keyLocation": f"{base}/{key}.txt", "urlList": urls[i:i + 10000]}).encode()
            try:
                r = urllib.request.urlopen(urllib.request.Request("https://api.indexnow.org/indexnow", data=body, headers={"Content-Type": "application/json; charset=utf-8"}), timeout=60)
                print("IndexNow:", r.status, len(urls[i:i + 10000]), "URLs")
            except Exception as e: ok = False; print("IndexNow erro:", e)
        if not ok: return
    if nxt.exists(): HF.write_text(nxt.read_text()); nxt.unlink()
if __name__ == "__main__" and sys.argv[1:] == ["ping"]: ping()
