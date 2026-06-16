# engine/metrics.py
"""
Logger persistant + benchmark. Enregistre chaque requête (vrais tokens,
latence, qualité, escalade) en JSONL et agrège les statistiques.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from engine.orchestrator import Result, process

LOG_PATH = Path("logs/metrics.jsonl")


def log(r: Result) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "measured": r.measured,
        "task_type": r.classification.task_type,
        "model_initial": r.decision.model.name,
        "model_final": r.final_model,
        "escalated": r.escalated,
        "attempts": r.attempts,
        "tokens_before": r.compression.tokens_before,
        "tokens_in": r.tokens_in,
        "tokens_out": r.tokens_out,
        "compression_ratio": round(r.compression.ratio, 4),
        "latency_s": r.response.latency_s if (r.response and r.response.ok) else None,
        "quality": r.quality.score if r.quality else None,
        "cost_engine": round(r.cost_engine, 8),
        "cost_baseline": round(r.cost_baseline, 8),
        "saved": round(r.saved, 8),
        "file_kind": r.file.kind if r.file else None,
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load():
    if not LOG_PATH.exists():
        return []
    with LOG_PATH.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def stats():
    e = load()
    if not e:
        return {"requests": 0}
    n = len(e)
    measured = sum(1 for x in e if x.get("measured"))
    n_escalated = sum(1 for x in e if x.get("escalated"))
    eng = sum(x.get("cost_engine", 0) for x in e)
    base = sum(x.get("cost_baseline", 0) for x in e)
    tb = sum(x.get("tokens_before", 0) for x in e)
    ti = sum(x.get("tokens_in", 0) for x in e)
    lats = [x["latency_s"] for x in e if x.get("latency_s") is not None]
    quals = [x["quality"] for x in e if x.get("quality") is not None]
    by_task, by_model = {}, {}
    for x in e:
        t = x.get("task_type", "?")
        m = x.get("model_final", x.get("model", "?"))
        by_task[t] = by_task.get(t, 0) + 1
        by_model[m] = by_model.get(m, 0) + 1
    return {
        "requests": n,
        "measured": measured,
        "n_escalated": n_escalated,
        "cost_engine": round(eng, 6),
        "cost_baseline": round(base, 6),
        "saved": round(base - eng, 6),
        "saved_pct": round((base - eng) / base, 4) if base else 0,
        "tokens_in_saved_pct": round(1 - ti / tb, 4) if tb else 0,
        "avg_latency_s": round(sum(lats) / len(lats), 2) if lats else None,
        "avg_quality": round(sum(quals) / len(quals), 2) if quals else None,
        "n_quality": len(quals),
        "by_task": by_task,
        "by_model": by_model,
    }


def print_stats():
    s = stats()
    if s["requests"] == 0:
        print("Aucune requete enregistree.")
        return
    print("=" * 52)
    print(f"  BENCHMARK  —  {s['requests']} requetes "
          f"({s['measured']} mesurees)")
    print("=" * 52)
    print(f"  Cout moteur      : {s['cost_engine']:.6f} $")
    print(f"  Cout baseline    : {s['cost_baseline']:.6f} $")
    print(f"  ECONOMIE         : {s['saved']:.6f} $  (-{s['saved_pct']:.0%})")
    print(f"  Tokens entree    : -{s['tokens_in_saved_pct']:.0%}")
    if s["avg_latency_s"] is not None:
        print(f"  Latence moyenne  : {s['avg_latency_s']}s (appels reels)")
    if s.get("avg_quality") is not None:
        print(f"  Qualite moyenne  : {s['avg_quality']}/10 (sur {s['n_quality']} reponses)")
    print(f"  Escalades        : {s['n_escalated']} / {s['requests']} requetes")
    print(f"  Par tache        : {s['by_task']}")
    print(f"  Par modele final : {s['by_model']}")
    print("=" * 52)


if __name__ == "__main__":
    # Pipeline complet avec escalade, execute reellement (gratuit : local + Groq).
    # Chaque requete = reponse + juge (+ escalade eventuelle) -> quelques minutes.
    prompts = [
        "Bonjour, merci d'avance !",
        "Resume en trois points l'interet du marche francophone africain.",
        "Traduis 'bonjour le monde' en anglais.",
        "Explique en deux phrases ce qu'est un token dans un LLM.",
        "Liste trois avantages du mobile money en Afrique de l'Ouest.",
    ]
    for p in prompts:
        r = process(p, use_ollama=False, escalate=True)
        log(r)
        esc = f"escalade->{r.final_model}" if r.escalated else "pas d'escalade"
        q = r.quality.score if r.quality else "?"
        print(f"[{r.final_model:<22}] qualite {q}/10 | {esc} | {p[:35]}...")

    print()
    print_stats()
