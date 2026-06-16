# engine/quality.py
"""
Contrôle qualité : note la réponse d'un modèle sur 10 via un juge.
Juge par défaut = Groq Llama 70B (plus fiable que le juge local).
"""
import json
import re
from dataclasses import dataclass


@dataclass
class QualityScore:
    score: float
    reason: str
    source: str
    ok: bool = True


_RUBRIC = """Tu es un evaluateur impartial. Note la REPONSE a la DEMANDE sur 10.
Criteres : pertinence (repond bien a la demande), completude (rien d'essentiel
ne manque), justesse (pas d'erreur manifeste). Sois strict mais juste.
Reponds UNIQUEMENT en JSON, sans texte autour : {{"score": <0-10>, "reason": "<12 mots max>"}}

DEMANDE :
{prompt}

REPONSE A EVALUER :
{response}

JSON :"""


def _parse(raw: str) -> QualityScore:
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return QualityScore(0.0, "parse echoue", "judge", ok=False)
    try:
        d = json.loads(m.group(0))
        score = max(0.0, min(10.0, float(d.get("score", 0))))
        return QualityScore(score, str(d.get("reason", ""))[:60], "judge")
    except Exception as e:
        return QualityScore(0.0, f"parse: {e}", "judge", ok=False)


def evaluate(prompt: str, response_text: str,
             judge_model: str = "groq/llama-3.3-70b") -> QualityScore:
    """Note la qualité d'une réponse via un modèle juge (appel séparé)."""
    if not response_text.strip():
        return QualityScore(0.0, "reponse vide", "judge", ok=False)
    from engine.llm_client import call_model
    p = _RUBRIC.format(prompt=prompt[:1500], response=response_text[:2000])
    r = call_model(p, judge_model)
    if not r.ok:
        return QualityScore(0.0, r.error, "unavailable", ok=False)
    return _parse(r.text)


if __name__ == "__main__":
    print("Evaluation 1 (bonne reponse)...")
    r1 = evaluate("Traduis 'bonjour le monde' en anglais.", "Hello world")
    print(f"  Score : {r1.score}/10 - {r1.reason}\n")

    print("Evaluation 2 (hors-sujet)...")
    r2 = evaluate("Traduis 'bonjour le monde' en anglais.",
                  "Le marche africain est en forte croissance.")
    print(f"  Score : {r2.score}/10 - {r2.reason}")
