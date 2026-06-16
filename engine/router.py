# engine/router.py
"""
Routeur : choisit le modèle le moins cher au-dessus du plancher de qualité
exigé par la classe de tâche. Fournit aussi next_tier_model pour l'escalade.
"""
from dataclasses import dataclass

from config import MODELS, PREFER_LOCAL, Model
from engine.classifier import Classification


@dataclass
class Decision:
    model: Model
    est_cost: float
    reason: str
    over_budget: bool = False


def _eligible(c: Classification, tokens_in: int) -> list:
    out = []
    for m in MODELS:
        if m.tier < c.min_tier:
            continue
        if tokens_in > m.context:
            continue
        out.append(m)
    return out


def route(c: Classification, tokens_in: int, tokens_out: int,
          budget_cap: float = None) -> Decision:
    candidates = _eligible(c, tokens_in)

    if not candidates:
        fitting = [m for m in MODELS if tokens_in <= m.context]
        chosen = max(fitting, key=lambda m: m.tier)
        return Decision(
            model=chosen,
            est_cost=chosen.cost(tokens_in, tokens_out),
            reason=f"Aucun modèle tier>={c.min_tier} ne tient le contexte "
                   f"({tokens_in} tokens) -> repli sur {chosen.name}.",
        )

    def sort_key(m: Model):
        cost = m.cost(tokens_in, tokens_out)
        local_bonus = 0 if (PREFER_LOCAL and m.local) else 1
        return (round(cost, 8), local_bonus, m.tier)

    candidates.sort(key=sort_key)
    chosen = candidates[0]
    cost = chosen.cost(tokens_in, tokens_out)

    reason = (f"Tache '{c.task_type}' (tier>={c.min_tier}) -> "
              f"{chosen.name} (tier {chosen.tier})"
              + (" [gratuit]" if chosen.cost(1000, 500) == 0 else "")
              + ", le moins cher qui passe le plancher.")

    over = budget_cap is not None and cost > budget_cap
    if over:
        reason += f" depasse le plafond ({cost:.6f} $ > {budget_cap:.6f} $)."

    return Decision(model=chosen, est_cost=cost, reason=reason, over_budget=over)


def next_tier_model(current_model: Model, tokens_in: int, tokens_out: int):
    """Modèle le moins cher d'un tier STRICTEMENT supérieur (cible d'escalade),
    ou None s'il n'y en a pas."""
    candidates = [
        m for m in MODELS
        if m.tier > current_model.tier and tokens_in <= m.context
    ]
    if not candidates:
        return None
    candidates.sort(
        key=lambda m: (
            round(m.cost(tokens_in, tokens_out), 8),
            0 if (PREFER_LOCAL and m.local) else 1,
        )
    )
    return candidates[0]


if __name__ == "__main__":
    from engine.classifier import classify
    from engine.tokens import count, estimate_output

    tests = [
        "Bonjour, merci !",
        "Resume cet article en trois points.",
        "Analyse ce jeu de donnees et extrais les tendances.",
        "Analyse les implications juridiques de cette clause OHADA.",
    ]
    for t in tests:
        c = classify(t, use_ollama=False)
        ti, to = count(t), estimate_output(c.task_type)
        d = route(c, ti, to)
        print(f"{c.task_type:<9} -> {d.model.name:<20} {d.est_cost:>10.6f} $")
