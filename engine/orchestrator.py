# engine/orchestrator.py
"""
Orchestrateur : pré-traitement fichier → compression → classification →
routing → appel réel → contrôle qualité → chiffrage vs baseline.
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
    use_ollama: bool = False
    response: LLMResponse = None
    measured: bool = False
    quality: QualityScore = None       # score qualité si évalué

    @property
    def saved(self):
        return self.cost_baseline - self.cost_engine

    @property
    def saved_pct(self):
        return 0.0 if self.cost_baseline == 0 else self.saved / self.cost_baseline


def process(prompt, file_path=None, use_ollama=True, compress_on=True,
            budget_cap=None, file_token_budget=None,
            execute=False, assess=False):
    """
    execute=True : appelle réellement le modèle (Ollama si local).
    assess=True  : note la qualité de la réponse (nécessite execute=True).
    """
    file_res, file_text, file_tokens_raw = None, "", 0

    # 1. Classification préliminaire → stratégie fichier
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

    # 5. Classification finale → routing
    cls = classify(comp.text, use_ollama=use_ollama)
    tokens_in = comp.tokens_after
    tokens_out_est = estimate_output(cls.task_type)
    dec = route(cls, tokens_in, tokens_out_est, budget_cap=budget_cap)

    # 6. Exécution réelle
    response, measured, tokens_out = None, False, tokens_out_est
    if execute:
        response = call_model(comp.text, dec.model.name)
        if response.ok:
            tokens_out = response.tokens_out
            measured = True

    # 7. Contrôle qualité (sur la réponse réelle)
    quality = None
    if assess and response and response.ok:
        quality = evaluate(prompt, response.text)

    # 8. Coûts
    cost_engine = dec.model.cost(tokens_in, tokens_out)
    base = get_model(BASELINE_MODEL)
    cost_baseline = base.cost(count(prompt) + file_tokens_raw, tokens_out)

    return Result(
        prompt_original=prompt, final_input=comp.text, classification=cls,
        compression=comp, decision=dec, tokens_in=tokens_in,
        tokens_out=tokens_out, cost_engine=cost_engine,
        cost_baseline=cost_baseline, file=file_res, use_ollama=use_ollama,
        response=response, measured=measured, quality=quality,
    )


def report(r):
    tag = "MESURÉ" if r.measured else "estimé"
    lines = ["─" * 64, f"Requête      : {r.prompt_original[:55]}"]
    if r.file:
        lines.append(f"Fichier      : {r.file.kind} ({r.file.pages}p), "
                     f"{r.file.tokens_raw}→{r.file.tokens} tokens [{r.file.strategy}]")
    lines += [
        f"Tokens       : {r.compression.tokens_before}→{r.tokens_in} in / "
        f"{r.tokens_out} out ({tag})",
        f"Tâche        : {r.classification.task_type} (tier≥{r.classification.min_tier})",
        f"Modèle       : {r.decision.model.name}",
    ]
    if r.response and r.response.ok:
        lines.append(f"Latence      : {r.response.latency_s}s")
    if r.quality:
        flag = "✓" if r.quality.score >= 7 else ("~" if r.quality.score >= 4 else "✗")
        lines.append(f"Qualité      : {flag} {r.quality.score}/10 — {r.quality.reason}")
    lines += [
        f"Coût moteur  : {r.cost_engine:.6f} $",
        f"Coût baseline: {r.cost_baseline:.6f} $",
        f"ÉCONOMIE     : {r.saved:.6f} $  (-{r.saved_pct:.0%})",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(report(process(
        "Résume en trois points l'intérêt du mobile money en Afrique.",
        use_ollama=False, execute=True, assess=True)))