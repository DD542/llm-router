# engine/tokens.py
"""
Comptage de tokens (entrée précise, sortie estimée).
tiktoken sert d'estimateur commun. C'est une APPROXIMATION pour Anthropic/local
(tokenizers différents), suffisante pour mesurer des économies relatives.
"""
from functools import lru_cache

try:
    import tiktoken
    _HAS_TIKTOKEN = True
except ImportError:
    _HAS_TIKTOKEN = False


@lru_cache(maxsize=1)
def _encoder():
    # cl100k_base = encodage générique, bon proxy multi-fournisseurs
    return tiktoken.get_encoding("cl100k_base")


def count(text: str) -> int:
    """Nombre de tokens en entrée (précis si tiktoken dispo)."""
    if not text:
        return 0
    if _HAS_TIKTOKEN:
        return len(_encoder().encode(text))
    # Fallback : ~4 caractères par token (approximation FR/EN correcte)
    return max(1, len(text) // 4)


# Estimation de la sortie selon la classe de tâche : combien de tokens
# le modèle va probablement GÉNÉRER. Ajustable. Sert au calcul du coût total.
_OUTPUT_ESTIMATE = {
    "trivial":  120,
    "simple":   400,
    "moderate": 900,
    "complex":  1800,
}


def estimate_output(task_type: str) -> int:
    """Tokens de sortie estimés pour une classe de tâche."""
    return _OUTPUT_ESTIMATE.get(task_type, 600)


if __name__ == "__main__":
    backend = "tiktoken" if _HAS_TIKTOKEN else "fallback (chars/4)"
    print(f"Backend de comptage : {backend}\n")

    samples = [
        "Bonjour, peux-tu m'aider ?",
        "Résume ce document en trois points clés et donne une recommandation.",
        "Analyse les implications juridiques de cette clause de non-concurrence "
        "au regard du droit OHADA et propose une reformulation sécurisée." * 3,
    ]
    for s in samples:
        print(f"{count(s):>4} tokens  | {s[:60]}...")

    print("\nEstimations de sortie par tâche :")
    for t in ("trivial", "simple", "moderate", "complex"):
        print(f"  {t:<10} → {estimate_output(t)} tokens")