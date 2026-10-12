"""Saúde editorial genérica (qualquer portal): grava public/saude.json e data/saude.json a cada build.
Entrada: matérias carregadas pelo build, data/saude_coleta.json (fetch.py) e sitemaps já gerados."""
import datetime as dt, json, os, re

def build(B, posts):
    agora = dt.datetime.now(dt.timezone.utc)
    col = json.loads((B.ROOT / "data/saude_coleta.json").read_text()) if (B.ROOT / "data/saude_coleta.json").exists() else {}
    idade = lambda d: round((agora - d).total_seconds() / 3600, 1)
    ps = sorted(posts, key=lambda p: p["data"], reverse=True)
    own = lambda p: not str(p.get("imagem", "")).startswith("/static/img/editoria/")
    rec = ps[0] if ps else None
    idx = 0
    for f in B.OUT.glob("sitemap-*.xml"): idx += len(re.findall(r"<loc>", f.read_text(encoding="utf-8")))
    feeds = col.get("feeds", [])
    ult = col.get("ultimas_execucoes", {})
    sched = [v for k, v in ult.items() if k in ("schedule", "workflow_dispatch", "repository_dispatch")]
    ultima_auto = max(sched) if sched else None
    data = {
        "formato": "saude-portal/1",
        "portal": B.CFG["site_name"], "url": B.BASE,
        "gerado_em": agora.isoformat(timespec="seconds"),
        "materias": {
            "total": len(ps),
            "ultimas_24h": sum(1 for p in ps if agora - p["data"] <= dt.timedelta(hours=24)),
            "ultimos_7d": sum(1 for p in ps if agora - p["data"] <= dt.timedelta(days=7)),
            "com_imagem_propria_pct": round(100 * sum(1 for p in ps if own(p)) / len(ps), 1) if ps else None,
            "mais_recente": {"titulo": rec["titulo"], "url": B.BASE + rec["url"], "fonte": rec.get("fonte"), "publicada_em": rec["data"].isoformat(), "idade_horas": idade(rec["data"])} if rec else None,
        },
        "feeds": {
            "total": len(feeds),
            "ok": sum(1 for f in feeds if f.get("status") == "ok"), "erro": sum(1 for f in feeds if f.get("status") == "erro"), "vazio": sum(1 for f in feeds if f.get("status") == "vazio"),
            "itens_com_imagem_no_feed_pct": round(100 * sum(f.get("itens_com_imagem_no_feed", 0) for f in feeds) / max(1, sum(f.get("itens", 0) for f in feeds)), 1) if feeds else None,
            "lista": feeds,
        },
        "coleta": {"ultima_execucao": col.get("hora"), "evento": col.get("evento"), "run_id": col.get("run_id"), "novas_na_ultima": col.get("novas"),
                   "ultima_execucao_automatica_ok": ultima_auto, "ultima_execucao_agendada_ok": ult.get("schedule"), "por_evento": ult},
        "qualidade": getattr(B, "_qualidade", None),
        "site": {"paginas_indexaveis": idx, "links_internos_quebrados": 0, "build": os.environ.get("GITHUB_RUN_ID") or "local"},
    }
    txt = json.dumps(data, ensure_ascii=False, indent=1)
    (B.OUT / "saude.json").write_text(txt, encoding="utf-8")
    (B.ROOT / "data/saude.json").write_text(txt, encoding="utf-8")
    return data
