# engine/policy.py
"""
Routing auto-apprenant : apprend de l'historique (logs/metrics.jsonl) quel
tier de depart convient a chaque type de tache, et ajuste le plancher.

Signal : si une tache a souvent du ESCALADER (le tier de depart n'a pas suffi),
on releve son plancher pour demarrer plus haut la prochaine fois.
"""
import json
from pathlib import Path

from config import TASK_MIN_TIER

LOG_PATH = Path("logs/metrics.jsonl")
POLICY_PATH = Path("logs/policy.json")
QUALITY_OK = 7.0
MIN_SAMPLES = 4
SUCCESS_FLOOR = 0.6
MAX_TIER = 4


def _load_log():
    """Lit le journal directement (evite un import circulaire avec metrics)."""
    if not LOG_PATH.exists():
        return []
    with LOG_PATH.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def learn(min_samples=MIN_SAMPLES, success_floor=SUCCESS_FLOOR):
    rows = _load_log()
    by_task = {}
    for r in rows:
        t = r.get("task_type")
        if t:
            by_task.setdefault(t, []).append(r)

    policy = {}
    for task, items in by_task.items():
        n = len(items)
        base = TASK_MIN_TIER.get(task, 2)
        ok = sum(1 for x in items
                 if not x.get("escalated") and (x.get("quality") or 0) >= QUALITY_OK)
        rate = ok / n if n else 0.0

        if n < min_samples:
            policy[task] = {"min_tier": base, "samples": n,
                            "rate": round(rate, 2), "learned": False,
                            "note": "donnees insuffisantes, plancher par defaut"}
        elif rate < success_floor:
            policy[task] = {"min_tier": min(base + 1, MAX_TIER), "samples": n,
                            "rate": round(rate, 2), "learned": True,
                            "note": f"succes au depart {rate:.0%} < {success_floor:.0%} -> +1 tier"}
        else:
            policy[task] = {"min_tier": base, "samples": n,
                            "rate": round(rate, 2), "learned": True,
                            "note": f"succes au depart {rate:.0%} -> plancher conserve"}
    return policy


def save_policy(policy):
    POLICY_PATH.parent.mkdir(parents=True, exist_ok=True)
    POLICY_PATH.write_text(json.dumps(policy, ensure_ascii=False, indent=2),
                           encoding="utf-8")


def load_policy():
    if not POLICY_PATH.exists():
        return {}
    try:
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def effective_min_tier(task_type, default_tier):
    pol = load_policy().get(task_type)
    if pol and pol.get("learned"):
        return max(default_tier, pol["min_tier"])
    return default_tier


if __name__ == "__main__":
    pol = learn()
    save_policy(pol)
    print("Politique de routing apprise (logs/policy.json) :\n")
    print(f"{'TACHE':<10}{'DEFAUT':<9}{'APPRIS':<9}{'SUCCES':<8}NOTE")
    for task, p in pol.items():
        base = TASK_MIN_TIER.get(task, 2)
        print(f"{task:<10}tier {base:<4}tier {p['min_tier']:<4}"
              f"{p['rate']*100:>4.0f}%   {p['note']}")
