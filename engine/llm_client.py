# engine/llm_client.py
"""
Client d'appel réel aux modèles.
- Ollama (local, gratuit)
- Groq (API, tier gratuit) : Llama 3.3 70B, clé depuis .env
- Anthropic (API, payant) : clé depuis .env, garde-fou de dépense
"""
import os
import time
from dataclasses import dataclass

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import anthropic
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False

try:
    from groq import Groq
    _HAS_GROQ = True
except ImportError:
    _HAS_GROQ = False

from config import get_model

OLLAMA_URL = "http://localhost:11434/api/generate"

ANTHROPIC_MODEL_MAP = {
    "claude-haiku-4.5": "claude-haiku-4-5-20251001",
    "claude-sonnet-4.6": "claude-sonnet-4-6",
    "claude-opus-4.x": "claude-opus-4-8",
}

GROQ_MODEL_MAP = {
    "groq/llama-3.3-70b": "llama-3.3-70b-versatile",
}

MAX_SPEND_USD = 0.50
MAX_TOKENS_OUT = 1024
_spent = 0.0


def spent_so_far():
    return round(_spent, 6)


@dataclass
class LLMResponse:
    text: str
    tokens_in: int
    tokens_out: int
    latency_s: float
    model: str
    ok: bool = True
    error: str = ""


# --- Ollama -----------------------------------------------------------------
def call_ollama(prompt, model, timeout=120):
    if not _HAS_REQUESTS:
        return LLMResponse("", 0, 0, 0.0, model, False, "requests manquant")
    t0 = time.time()
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": model, "prompt": prompt, "stream": False,
        }, timeout=timeout)
        r.raise_for_status()
        d = r.json()
        return LLMResponse(d.get("response", "").strip(),
                           d.get("prompt_eval_count", 0),
                           d.get("eval_count", 0),
                           round(time.time() - t0, 2), model)
    except requests.exceptions.ConnectionError:
        return LLMResponse("", 0, 0, 0.0, model, False,
                           "Ollama injoignable. Lance `ollama serve`.")
    except Exception as e:
        return LLMResponse("", 0, 0, round(time.time() - t0, 2), model, False, str(e))


# --- Groq -------------------------------------------------------------------
def call_groq(prompt, catalogue_name, max_tokens=MAX_TOKENS_OUT):
    if not _HAS_GROQ:
        return LLMResponse("", 0, 0, 0.0, catalogue_name, False,
                           "SDK manquant : pip install groq")
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return LLMResponse("", 0, 0, 0.0, catalogue_name, False,
                           "GROQ_API_KEY absente du .env")
    api_model = GROQ_MODEL_MAP.get(catalogue_name, catalogue_name)
    t0 = time.time()
    try:
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model=api_model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = (resp.choices[0].message.content or "").strip()
        u = resp.usage
        return LLMResponse(text, u.prompt_tokens, u.completion_tokens,
                           round(time.time() - t0, 2), catalogue_name)
    except Exception as e:
        return LLMResponse("", 0, 0, round(time.time() - t0, 2),
                           catalogue_name, False, str(e))


# --- Anthropic --------------------------------------------------------------
def call_anthropic(prompt, catalogue_name, max_tokens=MAX_TOKENS_OUT):
    global _spent
    if not _HAS_ANTHROPIC:
        return LLMResponse("", 0, 0, 0.0, catalogue_name, False,
                           "SDK manquant : pip install anthropic")
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return LLMResponse("", 0, 0, 0.0, catalogue_name, False,
                           "ANTHROPIC_API_KEY absente du .env")
    if _spent >= MAX_SPEND_USD:
        return LLMResponse("", 0, 0, 0.0, catalogue_name, False,
                           f"Plafond de dépense atteint ({MAX_SPEND_USD} $).")
    api_model = ANTHROPIC_MODEL_MAP.get(catalogue_name, catalogue_name)
    t0 = time.time()
    try:
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model=api_model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in msg.content if b.type == "text").strip()
        ti, to = msg.usage.input_tokens, msg.usage.output_tokens
        _spent += get_model(catalogue_name).cost(ti, to)
        return LLMResponse(text, ti, to, round(time.time() - t0, 2), catalogue_name)
    except Exception as e:
        return LLMResponse("", 0, 0, round(time.time() - t0, 2),
                           catalogue_name, False, str(e))


# --- Aiguillage -------------------------------------------------------------
def call_model(prompt, model_name):
    if model_name.startswith("local/"):
        return call_ollama(prompt, model_name.split("/", 1)[1])
    try:
        provider = get_model(model_name).provider
    except Exception:
        provider = "unknown"
    if provider == "groq":
        return call_groq(prompt, model_name)
    if provider == "anthropic":
        return call_anthropic(prompt, model_name)
    return LLMResponse("", 0, 0, 0.0, model_name, False,
                       f"Provider '{provider}' pas encore branché.")


if __name__ == "__main__":
    print("Test appel Groq Llama 70B (réel, gratuit)...\n")
    r = call_model("Dis bonjour en une phrase.", "groq/llama-3.3-70b")
    if r.ok:
        print(f"Modèle  : {r.model}")
        print(f"Tokens  : {r.tokens_in} in / {r.tokens_out} out")
        print(f"Latence : {r.latency_s}s")
        print(f"Réponse : {r.text}")
    else:
        print(f"❌ {r.error}")