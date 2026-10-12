"""Monta alertas operacionais (sem rede): matéria mais recente > 24 h, feeds com erro, passos que falharam.
Uso: python tools/alerta.py "<passos falhos separados por espaço>" -> escreve alerta.md e sai 0; arquivo vazio = sem alerta."""
import datetime as dt, json, sys, yaml
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
def main():
    falhos = [s for s in (sys.argv[1] if len(sys.argv) > 1 else "").split() if s]
    linhas = []
    datas = []
    for f in (ROOT / "content").glob("*.md"):
        try:
            m = yaml.safe_load(f.read_text(encoding="utf-8").split("---", 2)[1]); d = m.get("data")
            if isinstance(d, str): d = dt.datetime.fromisoformat(d)
            if isinstance(d, dt.datetime):
                datas.append(d if d.tzinfo else d.replace(tzinfo=dt.timezone(dt.timedelta(hours=-3))))
        except Exception: pass
    agora = dt.datetime.now(dt.timezone.utc)
    if not datas: linhas.append("- Nenhuma matéria em content/.")
    else:
        idade = (agora - max(datas)).total_seconds() / 3600
        if idade > 24: linhas.append(f"- Matéria mais recente tem {idade:.0f} h (limite 24 h): {max(datas).isoformat()}.")
    sc = ROOT / "data/saude_coleta.json"
    if sc.exists():
        s = json.loads(sc.read_text())
        for e in s.get("erros", []): linhas.append(f"- Feed com erro: {e.get('feed')} ({e.get('url')}): {e.get('erro')}")
    for p in falhos: linhas.append(f"- Passo do workflow falhou: {p}")
    (ROOT / "alerta.md").write_text(("## Alerta automático do Modal News\n\n" + "\n".join(linhas) + "\n") if linhas else "", encoding="utf-8")
    print("\n".join(linhas) or "Sem alertas")
if __name__ == "__main__": main()
