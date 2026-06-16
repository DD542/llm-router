# engine/escalation.py
"""
Ré-routage par qualité : si la réponse d'un modèle est sous le seuil,
escalade vers un modèle de tier supérieur. Les appels échoués ne sont pas retenus.
"""
from dataclasses import dataclass, field

from engine.llm_client import call_model, LLMResponse
from engine.quality import evaluate, QualityScore
from engine.router import next_tier_model
from config import get_model

QUALITY_THRESHOLD = 7.0
MAX_ESCALATIONS = 2


@dataclass
class Attempt:
    model: str
    response: LLMResponse
    quality: QualityScore


@dataclass
class EscalationResult:
    final_response: LLMResponse
    final_quality: QualityScore
    final_model: str
    attempts: list = field(default_factory=list)
    escalated: bool = False


def run_with_escalation(prompt, start_model_name, tokens_in, tokens_out,
                        judge_model=None):
    attempts = []
    model_name = start_model_name

    for _ in range(MAX_ESCALATIONS + 1):
        resp = call_model(prompt, model_name)

        if resp.ok:
            if judge_model:
                q = evaluate(prompt, resp.text, judge_model=judge_model)
            else:
                q = evaluate(prompt, resp.text)
            attempts.append(Attempt(model_name, resp, q))
            if q.ok and q.score >= QUALITY_THRESHOLD:
                break
        else:
            q = QualityScore(0.0, resp.error, "unavailable", ok=False)
            attempts.append(Attempt(model_name, resp, q))

        nxt = next_tier_model(get_model(model_name), tokens_in, tokens_out)
        if nxt is None:
            break
        model_name = nxt.name

    valid = [a for a in attempts if a.response.ok]
    best = max(valid, key=lambda a: a.quality.score) if valid else attempts[-1]

    return EscalationResult(
        final_response=best.response,
        final_quality=best.quality,
        final_model=best.model,
        attempts=attempts,
        escalated=len(attempts) > 1,
    )


if __name__ == "__main__":
    from engine.tokens import count, estimate_output
    prompt = ("Ecris une fonction Python qui implemente l'algorithme de "
              "Thompson sampling pour un bandit a K bras, avec mise a jour "
              "bayesienne des distributions Beta. Code complet et commente.")
    ti, to = count(prompt), estimate_output("complex")

    print(f"Seuil qualite : {QUALITY_THRESHOLD}/10")
    print(f"Depart        : local/qwen2.5:14b\n")

    res = run_with_escalation(prompt, "local/qwen2.5:14b", ti, to)

    for i, a in enumerate(res.attempts):
        ok = a.quality.ok and a.quality.score >= QUALITY_THRESHOLD
        flag = "OK" if ok else "--"
        extra = "" if a.response.ok else f"  (echec: {a.quality.reason})"
        print(f"Tentative {i+1} : {a.model:<22} qualite {a.quality.score}/10 {flag}{extra}")
    print(f"\n-> Modele retenu : {res.final_model} ({res.final_quality.score}/10)")
    print(f"-> Escalade      : {'oui' if res.escalated else 'non'}")
    print(f"\nReponse finale :\n{res.final_response.text[:300]}...")
