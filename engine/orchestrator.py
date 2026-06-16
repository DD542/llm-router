# engine/orchestrator.py
"""
Orchestrateur : pré-traitement fichier -> compression -> classification ->
routing -> escalade par qualité -> chiffrage vs baseline.
Pipeline unifié de bout en bout.
"""
from dataclasses import dataclass

from config import BASELINE_MODEL, get_model
from engine.classifier import classify, Classification
from engine.compressor import compress, Compressed
from engine.router import route, Decision
from engine.tokens import count, estimate_output
from engine.preprocessor import preprocess_file, FileResult
from engine.llm_client import call_model, LLMResponse
from engine.quality import evaluate, QualityScore
from engine.escalation import run_with_escalation, EscalationResult


@dataclass
class Result:
    prompt_original: str
    final_input: str
    classification: Classification
    compression: Compressed
    decision: Decision
    tokens_in: int
    tokens_out: int
    cost_engine: float
    cost_baseline: float
    file: FileResult = None
    response: LLMResponse = None
    quality: QualityScore = None
    measured: bool = False
    final_model: str = None
    escalated: bool = False
    attempts: int = 0

    @property
    def saved(self):
        return self.cost_baseline - self.cost_engine

    @property
    def saved_pct(self):
        return 0.0 if self.cost_baseline == 0 else self.saved / self.cost_baseline


def process(prompt, file_path=None, use_ollama=True, compress_on=True,
            budget_cap=None, file_token_budget=None,
            execute=False, assess=False, escalate=False):
    """
    execute=True  : appelle réellement le modèle.
    assess=True   : note la qualité (nécessite execute=True).
    escalate=True : ré-route vers un modèle supérieur si qualité insuffisante
                    (implique execute + assess).
    """
    file_res, file_text, file_tokens_raw = None, "", 0

    # 1. Classification préliminaire (prompt seul) -> stratégie fichier
    pre_cls = classify(prompt, use_ollama=use_ollama)

    # 2. Pré-traitement fichier
    if file_path:
        file_res = preprocess_file(file_path, task_type=pre_cls.task_type,
                                   token_budget=file_token_budget)
        file_text = file_res.text
        file_tokens_raw = file_res.tokens_raw

    # 3. Fusion
    combined = f"{prompt}\n\n[CONTENU DU FICHIER]\n{file_text}" if file_text else prompt

    # 4. Compression
    comp = compress(combined, enabled=compress_on)

    # 5. Classification finale -> routing
    cls = classify(comp.text, use_ollama=use_ollama)
    tokens_in = comp.tokens_after
    tokens_out_est = estimate_output(cls.task_type)
    dec = route(cls, tokens_in, tokens_out_est, budget_cap=budget_cap)

    # 6. Exécution
    response, quality = None, None
    measured, final_model, escalated, attempts = False, dec.model.name, False, 0
    tokens_out = tokens_out_est

    if escalate:
        # Pipeline complet avec ré-routage par qualité
        esc = run_with_escalation(comp.text, dec.model.name,
                                  tokens_in, tokens_out_est)
        response = esc.final_response
        quality = esc.final_quality
        final_model = esc.final_model
        escalated = esc.escalated
        attempts = len(esc.attempts)
        if response.ok:
            tokens_out = response.tokens_out
            measured = True
    elif execute:
        response = call_model(comp.text, dec.model.name)
        if response.ok:
            tokens_out = response.tokens_out
            measured = True
            if assess:
                quality = evaluate(prompt, response.text)

    # 7. Coûts (sur le modèle finalement retenu)
    chosen = get_model(final_model)
    cost_engine = chosen.cost(tokens_in, tokens_out)
    base = get_model(BASELINE_MODEL)
    cost_baseline = base.cost(count(prompt) + file_tokens_raw, tokens_out)

    return Result(
        prompt_original=prompt, final_input=comp.text, classification=cls,
        compression=comp, decision=dec, tokens_in=tokens_in,
        tokens_out=tokens_out, cost_engine=cost_engine,
        cost_baseline=cost_baseline, file=file_res, response=response,
        quality=quality, measured=measured, final_model=final_model,
        escalated=escalated, attempts=attempts,
    )


def report(r):
    tag = "MESURE" if r.measured else "estime"
    lines = ["-" * 64, f"Requete      : {r.prompt_original[:55]}"]
    if r.file:
        lines.append(f"Fichier      : {r.file.kind} ({r.file.pages}p), "
                     f"{r.file.tokens_raw}->{r.file.tokens} tokens [{r.file.strategy}]")
    lines += [
        f"Tokens       : {r.compression.tokens_before}->{r.tokens_in} in / "
        f"{r.tokens_out} out ({tag})",
        f"Tache        : {r.classification.task_type} (tier>={r.classification.min_tier})",
        f"Modele initial: {r.decision.model.name}",
    ]
    if r.escalated:
        lines.append(f"Escalade     : oui ({r.attempts} tentatives) -> {r.final_model}")
    else:
        lines.append(f"Modele final : {r.final_model}")
    if r.response and r.response.ok:
        lines.append(f"Latence      : {r.response.latency_s}s")
    if r.quality:
        flag = "OK" if r.quality.score >= 7 else "--"
        lines.append(f"Qualite      : {r.quality.score}/10 {flag} - {r.quality.reason}")
    lines += [
        f"Cout moteur  : {r.cost_engine:.6f} $",
        f"Cout baseline: {r.cost_baseline:.6f} $",
        f"ECONOMIE     : {r.saved:.6f} $  (-{r.saved_pct:.0%})",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print("# Pipeline complet avec escalade")
    print(report(process(
        "Resume en trois points l'interet du mobile money en Afrique.",
        use_ollama=False, escalate=True)))
