# engine/llm_client.py
"""
Client d'appel réel aux modèles. Pour l'instant : Ollama (local, gratuit).
Renvoie la réponse + les VRAIS tokens (comptés par le moteur, pas estimés).
"""
import time
from dataclasses import dataclass

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

OLLAMA_URL = "http://localhost:11434/api/generate"


@dataclass
class LLMResponse:
    text: str
    tokens_in: int          # vrais tokens d'entrée (comptés par Ollama)
    tokens_out: int         # vrais tokens de sortie
    latency_s: float        # temps de réponse réel
    model: str
    ok: bool = True
    error: str = ""


def call_ollama(prompt: str, model: str, timeout: int = 120) -> LLMResponse:
    """Appel réel à Ollama. Renvoie la réponse et les vrais tokens."""
    if not _HAS_REQUESTS:
        return LLMResponse("", 0, 0, 0.0, model, ok=False,
                           error="requests manquant : pip install requests")
    t0 = time.time()
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": model,
            "prompt": prompt,
            "stream": False,
        }, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return LLMResponse(
            text=data.get("response", "").strip(),
            tokens_in=data.get("prompt_eval_count", 0),
            tokens_out=data.get("eval_count", 0),
            latency_s=round(time.time() - t0, 2),
            model=model,
        )
    except requests.exceptions.ConnectionError:
        return LLMResponse("", 0, 0, 0.0, model, ok=False,
                           error="Ollama injoignable. Lance `ollama serve`.")
    except Exception as e:
        return LLMResponse("", 0, 0, round(time.time() - t0, 2), model,
                           ok=False, error=str(e))


def call_model(prompt: str, model_name: str) -> LLMResponse:
    """
    Aiguillage selon le modèle. Pour l'instant seuls les modèles 'local/...'
    sont appelés réellement ; les autres renverront une erreur claire
    (on les branchera avec les API payantes plus tard).
    """
    if model_name.startswith("local/"):
        # "local/qwen2.5:14b" -> "qwen2.5:14b"
        ollama_name = model_name.split("/", 1)[1]
        return call_ollama(prompt, ollama_name)

    return LLMResponse("", 0, 0, 0.0, model_name, ok=False,
                       error=f"Modèle payant '{model_name}' : appel réel pas "
                             f"encore branché (API à venir).")


if __name__ == "__main__":
    print("Test d'un appel réel à Ollama...\n")
    resp = call_model("Dis bonjour en une phrase courte.", "local/qwen2.5:14b")
    if resp.ok:
        print(f"Modèle    : {resp.model}")
        print(f"Tokens    : {resp.tokens_in} in / {resp.tokens_out} out")
        print(f"Latence   : {resp.latency_s}s")
        print(f"Réponse   : {resp.text}")
    else:
        print(f"❌ Erreur : {resp.error}")