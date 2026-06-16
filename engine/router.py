# engine/router.py
"""
Routeur : choisit le modèle le moins cher au-dessus du plancher de qualité
exigé par la classe de tâche.
"""
from dataclasses import dataclass

from config import MODELS, PREFER_LOCAL, Model
from engine.classifier import Classification


@dataclass
class Decision:
    model: Model
    est_cost: float          # coût estimé de l'appel (USD)
    reason: str              # explication lisible
    over_budget: bool = False


def _eligible(c: Classification, tokens_in: int) -> list[Model]:
    """Modèles qui respectent le plancher de qualité ET le contexte."""
    out = []
    for m in MODELS:
        if m.tier < c.min_tier:
            continue                      # sous le plancher de qualité
        if tokens_in > m.context:
            continue                      # requête trop longue pour ce modèle
        out.append(m)
    return out


def route(
    c: Classification,
    tokens_in: int,
    tokens_out: int,
    budget_cap: float | None = None,
) -> Decision:
    """
    Sélectionne le meilleur modèle.
    budget_cap : coût max accepté pour cette requête (USD), optionnel.
    """
    candidates = _eligible(c, tokens_in)

    if not candidates:
        # Aucun modèle au plancher ne tient le contexte → on prend le plus
        # gros disponible qui tient le contexte (dégradation maîtrisée).
        fitting = [m for m in MODELS if tokens_in <= m.context]
        chosen = max(fitting, key=lambda m: m.tier)
        return Decision(
            model=chosen,
            est_cost=chosen.cost(tokens_in, tokens_out),
            reason=f"Aucun modèle tier≥{c.min_tier} ne tient le contexte "
                   f"({tokens_in} tokens) → repli sur {chosen.name}.",
        )

    # Tri : coût croissant ; à coût ~égal, on privilégie le local si demandé.
    def sort_key(m: Model):
        cost = m.cost(tokens_in, tokens_out)
        local_bonus = 0 if (PREFER_LOCAL and m.local) else 1
        return (round(cost, 8), local_bonus, m.tier)

    candidates.sort(key=sort_key)
    chosen = candidates[0]
    cost = chosen.cost(tokens_in, tokens_out)

    reason = (f"Tâche '{c.task_type}' (tier≥{c.min_tier}) → "
              f"{chosen.name} (tier {chosen.tier})"
              + (" [local gratuit]" if chosen.local else "")
              + f", le moins cher qui passe le plancher.")

    over = budget_cap is not None and cost > budget_cap
    if over:
        reason += f" ⚠️ dépasse le plafond ({cost:.6f} $ > {budget_cap:.6f} $)."

    return Decision(model=chosen, est_cost=cost, reason=reason, over_budget=over)


if __name__ == "__main__":
    from engine.classifier import classify
    from engine.tokens import count, estimate_output

    tests = [
        "Bonjour, merci !",
        "Résume cet article en trois points.",
        "Analyse ce jeu de données et extrais les tendances.",
        "Analyse les implications juridiques de cette clause OHADA "
        "et propose une reformulation sécurisée.",
    ]
    for t in tests:
        c = classify(t, use_ollama=False)
        ti, to = count(t), estimate_output(c.task_type)
        d = route(c, ti, to)
        print(f"{c.task_type:<9} → {d.model.name:<20} "
              f"{d.est_cost:>10.6f} $ | {d.reason}")