# engine/quality.py
"""
Contrôle qualité : note la réponse d'un modèle sur 10 via un juge.
v0 = juge LOCAL (gratuit, appel séparé avec grille). Proxy clément mais utile.
Upgrade prévu : juge frontier (Opus/GPT) pour une note crédible (étape API).
"""
import json
import re
from dataclasses import dataclass

from engine.llm_client import call_ollama

JUDGE_MODEL = "qwen2.5:14b"   # mets "qwen2.5:3b" si tu utilises le 3b


@dataclass
class QualityScore:
    score: float          # 0 à 10
    reason: str
    source: str           # "local-judge" | "unavailable"
    ok: bool = True


_RUBRIC = """Tu es un évaluateur impartial. Note la RÉPONSE à la DEMANDE sur 10.
Critères : pertinence (répond bien à la demande), complétude (rien d'essentiel
ne manque), justesse (pas d'erreur manifeste). Sois strict.
Réponds UNIQUEMENT en JSON, sans texte autour : {{"score": <0-10>, "reason": "<12 mots max>"}}

DEMANDE :
{prompt}

RÉPONSE À ÉVALUER :
{response}

JSON :"""


def _parse(raw: str) -> QualityScore:
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return QualityScore(0.0, "parse échoué", "local-judge", ok=False)
    try:
        d = json.loads(m.group(0))
        score = max(0.0, min(10.0, float(d.get("score", 0))))
        return QualityScore(score, str(d.get("reason", ""))[:60], "local-judge")
    except Exception as e:
        return QualityScore(0.0, f"parse: {e}", "local-judge", ok=False)


def evaluate(prompt: str, response_text: str,
             judge_model: str = JUDGE_MODEL) -> QualityScore:
    """Note la qualité d'une réponse. Appel séparé au juge local."""
    if not response_text.strip():
        return QualityScore(0.0, "réponse vide", "local-judge", ok=False)
    p = _RUBRIC.format(prompt=prompt[:1500], response=response_text[:2000])
    r = call_ollama(p, judge_model, timeout=120)
    if not r.ok:
        return QualityScore(0.0, r.error, "unavailable", ok=False)
    return _parse(r.text)


if __name__ == "__main__":
    # Deux cas : une bonne réponse et une mauvaise, pour voir le juge discriminer
    print("Évaluation 1 (bonne réponse)...")
    r1 = evaluate("Traduis 'bonjour le monde' en anglais.", "Hello world")
    print(f"  Score : {r1.score}/10 — {r1.reason}\n")

    print("Évaluation 2 (réponse hors-sujet)...")
    r2 = evaluate("Traduis 'bonjour le monde' en anglais.",
                  "Le marché africain est en forte croissance.")
    print(f"  Score : {r2.score}/10 — {r2.reason}")