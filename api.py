# api.py  — API FastAPI exposant le moteur au dashboard Vue.
# Lancer : uvicorn api:app --reload --port 8000
import os
import tempfile

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

from engine.orchestrator import process
from engine.metrics import load, stats

app = FastAPI(title="llm-router API")

# Autorise le dashboard Vue (localhost:5173) a appeler l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/metrics")
def get_metrics():
    """Historique des requetes (logs/metrics.jsonl) + agregats."""
    return {"entries": load(), "stats": stats()}


@app.post("/api/simulate")
async def simulate(
    prompt: str = Form(...),
    execute: bool = Form(True),
    escalate: bool = Form(True),
    file: UploadFile = File(None),
):
    """Fait passer une requete dans le moteur et renvoie la decision + le cout."""
    file_path = None
    if file is not None and file.filename:
        suffix = os.path.splitext(file.filename)[1]
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(await file.read())
        tmp.close()
        file_path = tmp.name

    try:
        r = process(prompt, file_path=file_path, use_ollama=True,
                    execute=execute, escalate=escalate)
    finally:
        if file_path:
            try:
                os.unlink(file_path)
            except OSError:
                pass

    return {
        "task_type": r.classification.task_type,
        "model_initial": r.decision.model.name,
        "model_final": r.final_model,
        "escalated": r.escalated,
        "attempts": r.attempts,
        "tokens_before": r.compression.tokens_before,
        "tokens_in": r.tokens_in,
        "tokens_out": r.tokens_out,
        "cost_engine": r.cost_engine,
        "cost_baseline": r.cost_baseline,
        "saved": r.saved,
        "quality": r.quality.score if r.quality else None,
        "quality_reason": r.quality.reason if r.quality else None,
        "response": r.response.text if (r.response and r.response.ok) else None,
        "latency_s": r.response.latency_s if (r.response and r.response.ok) else None,
        "file_kind": r.file.kind if r.file else None,
        "file_pages": r.file.pages if r.file else None,
    }
