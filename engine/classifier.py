# engine/classifier.py
"""
Classifieur de tâche : décide de la classe (trivial/simple/moderate/complex)
à partir de la requête. Utilise Ollama si dispo, sinon une heuristique locale.
"""
import json
import re
from dataclasses import dataclass

from config import TASK_MIN_TIER
from engine.tokens import count

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:14b"

VALID = ("trivial", "simple", "moderate", "complex")


@dataclass
class Classification:
    task_type: str          # trivial | simple | moderate | complex
    min_tier: int           # niveau de modèle minimum requis
    source: str             # "ollama" ou "heuristic"
    long_context: bool      # la requête est-elle longue ?


# --- Mode 1 : Ollama --------------------------------------------------------
_PROMPT = """Tu es un classifieur. Analyse la requête et réponds UNIQUEMENT en JSON,
sans texte autour, au format exact :
{{"task_type": "...", "long_context": false}}

task_type doit valoir l'une de ces valeurs :
- "trivial"  : salutation, formatage simple, traduction courte
- "simple"   : résumé court, reformulation, classification, question factuelle
- "moderate" : analyse, extraction structurée, code de complexité moyenne
- "complex"  : raisonnement juridique/médical, multi-étapes, code difficile

Requête : {req}
JSON :"""


def _classify_ollama(text: str) -> Classification | None:
    if not _HAS_REQUESTS:
        return None
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": _PROMPT.format(req=text[:2000]),
            "stream": False,
            "options": {"temperature": 0},
        }, timeout=30)
        r.raise_for_status()
        raw = r.json().get("response", "")
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        data = json.loads(match.group(0))
        tt = data.get("task_type", "").strip().lower()
        if tt not in VALID:
            return None
        return Classification(
            task_type=tt,
            min_tier=TASK_MIN_TIER[tt],
            source="ollama",
            long_context=bool(data.get("long_context", False)),
        )
    except Exception:
        return None  # tout échec → on bascule sur l'heuristique


# --- Mode 2 : Heuristique (fallback sans Ollama) ----------------------------
_COMPLEX_KW = ("juridique", "légal", "contrat", "clause", "médical", "diagnostic",
               "démontre", "prouve", "architecture", "optimise l'algorithme",
               "raisonnement", "stratégie complète")
_MODERATE_KW = ("analyse", "compare", "extrais", "structure", "code", "débogue",
                "fonction", "script", "explique en détail", "synthèse")
_TRIVIAL_KW = ("bonjour", "salut", "merci", "traduis", "mets en majuscule",
               "formate", "corrige la faute")


def _classify_heuristic(text: str) -> Classification:
    low = text.lower()
    tokens = count(text)
    long_ctx = tokens > 3000

    if any(k in low for k in _COMPLEX_KW) or tokens > 6000:
        tt = "complex"
    elif any(k in low for k in _MODERATE_KW) or tokens > 1500:
        tt = "moderate"
    elif any(k in low for k in _TRIVIAL_KW) and tokens < 40:
        tt = "trivial"
    else:
        tt = "simple"

    return Classification(
        task_type=tt,
        min_tier=TASK_MIN_TIER[tt],
        source="heuristic",
        long_context=long_ctx,
    )


# --- Point d'entrée ---------------------------------------------------------
def classify(text: str, use_ollama: bool = True) -> Classification:
    """Classe une requête. Essaie Ollama, retombe sur l'heuristique."""
    if use_ollama:
        result = _classify_ollama(text)
        if result is not None:
            return result
    return _classify_heuristic(text)


if __name__ == "__main__":
    tests = [
        "Bonjour, merci pour ton aide !",
        "Résume cet article en trois points.",
        "Analyse ce jeu de données et extrais les tendances principales.",
        "Analyse les implications juridiques de cette clause de non-concurrence "
        "au regard du droit OHADA et propose une reformulation sécurisée.",
    ]
    for t in tests:
        c = classify(t, use_ollama=True)
        print(f"[{c.source:<9}] {c.task_type:<9} (tier≥{c.min_tier}) "
              f"long={c.long_context} | {t[:50]}...")