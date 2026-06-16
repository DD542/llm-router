# config.py
"""
Catalogue des modèles + tarifs + niveaux de capacité (tiers).
Prix en USD par 1 000 000 de tokens (in / out).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Model:
    name: str
    provider: str       # openai | anthropic | groq | local
    tier: int           # 1=nano, 2=mini, 3=mid, 4=frontier
    price_in: float
    price_out: float
    local: bool = False
    context: int = 128_000

    def cost(self, tokens_in: int, tokens_out: int) -> float:
        return (tokens_in / 1_000_000) * self.price_in + \
               (tokens_out / 1_000_000) * self.price_out


MODELS = [
    Model("local/qwen2.5:14b",  "local",     2, 0.00,  0.00,  local=True, context=32_000),
    Model("groq/llama-3.3-70b", "groq",      3, 0.00,  0.00,  context=128_000),
    Model("gpt-5-nano",         "openai",    1, 0.05,  0.40),
    Model("gpt-5-mini",         "openai",    2, 0.25,  2.00),
    Model("claude-haiku-4.5",   "anthropic", 2, 0.80,  4.00),
    Model("gpt-5",              "openai",    3, 1.75,  14.00),
    Model("claude-sonnet-4.6",  "anthropic", 3, 3.00,  15.00),
    Model("claude-opus-4.x",    "anthropic", 4, 15.00, 75.00, context=200_000),
]

BASELINE_MODEL = "claude-opus-4.x"

TASK_MIN_TIER = {
    "trivial":  1,
    "simple":   2,
    "moderate": 3,
    "complex":  4,
}

PREFER_LOCAL = True


def get_model(name: str) -> Model:
    for m in MODELS:
        if m.name == name:
            return m
    raise ValueError(f"Modèle inconnu : {name}")


if __name__ == "__main__":
    print(f"{'MODÈLE':<22}{'TIER':<6}{'IN':>8}{'OUT':>8}{'COÛT/appel':>14}")
    for m in sorted(MODELS, key=lambda x: x.cost(1000, 500)):
        print(f"{m.name:<22}{m.tier:<6}{m.price_in:>8}{m.price_out:>8}"
              f"{m.cost(1000, 500):>14.6f} $")
    print(f"\nBaseline (référence éco) : {BASELINE_MODEL}")
