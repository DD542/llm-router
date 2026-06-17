# engine/orchestrator.py
"""
Orchestrateur : pre-traitement fichier -> compression -> classification ->
routing (avec plancher auto-appris) -> escalade par qualite -> chiffrage.
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
from engine.escalation import run_with_escalation
from engine.policy import effective_min_tier


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
    learned_tier: bool = False

    @property
    def saved(self):
        return self.cost_baseline - self.cost_engine

    @property
    def saved_pct(self):
        return 0.0 if self.cost_baseline == 0 else self.saved / self.cost_baseline


def process(prompt, file_path=None, use_ollama=True, compress_on=True,
            budget_cap=None, file_token_budget=None,
            execute=False, assess=False, escalate=False):
    file_res, file_text, file_tokens_raw = None, "", 0

    pre_cls = classify(prompt, use_ollama=use_ollama)

    if file_path:
        file_res = preprocess_file(file_path, task_type=pre_cls.task_type,
                                   token_budget=file_token_budget)
        file_text = file_res.text
        file_tokens_raw = file_res.tokens_raw

    combined = f"{prompt}\n\n[CONTENU DU FICHIER]\n{file_text}" if file_text else prompt
    comp = compress(combined, enabled=compress_on)

    cls = classify(comp.text, use_ollama=use_ollama)

    # --- Routing auto-appris : releve le plancher si l'historique le justifie
    base_tier = cls.min_tier
    learned = effective_min_tier(cls.task_type, base_tier)
    cls.min_tier = learned
    learned_tier = learned > base_tier

    tokens_in = comp.tokens_after
    tokens_out_est = estimate_output(cls.task_type)
    dec = route(cls, tokens_in, tokens_out_est, budget_cap=budget_cap)

    response, quality = None, None
    measured, final_model, escalated, attempts = False, dec.model.name, False, 0
    tokens_out = tokens_out_est

    if escalate:
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
        escalated=escalated, attempts=attempts, learned_tier=learned_tier,
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
        f"Tache        : {r.classification.task_type} (tier>={r.classification.min_tier})"
        + ("  [plancher auto-appris]" if r.learned_tier else ""),
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
    print(report(process(
        "Resume en trois points l'interet du mobile money en Afrique.",
        use_ollama=False, escalate=True)))
