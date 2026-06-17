"""
Convertit logs/metrics.jsonl (du projet moteur) en public/metrics.json
consommé par le dashboard Vue.

Usage :
  python make-data.py "C:\\Users\\menga\\PycharmProjects\\baseline\\logs\\metrics.jsonl"
"""
import json
import sys
import pathlib

src = sys.argv[1] if len(sys.argv) > 1 else "metrics.jsonl"
rows = [json.loads(l) for l in open(src, encoding="utf-8") if l.strip()]
pathlib.Path("public").mkdir(exist_ok=True)
out = pathlib.Path("public/metrics.json")
out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{out} ecrit : {len(rows)} requetes")
