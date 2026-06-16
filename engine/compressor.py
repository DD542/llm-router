# engine/compressor.py
"""
Compresseur de prompt : réduit les tokens sans perte de sens.
v0 = nettoyage structurel déterministe (sûr, sans dépendance lourde).
Upgrade prévu : LLMLingua-2 pour la compression sémantique agressive.
"""
import re
from dataclasses import dataclass

from engine.tokens import count

_FILLERS = [
    r"\bs'il te pla[îi]t\b", r"\bs'il vous pla[îi]t\b", r"\bmerci d'avance\b",
    r"\bje voudrais que tu\b", r"\bje souhaiterais que tu\b",
    r"\bpourrais-tu\b", r"\bpeux-tu\b", r"\bj'aimerais que tu\b",
    r"\bje te prie de\b", r"\bn'h[ée]site pas [àa]\b",
    r"\bsois gentil de\b", r"\bje t'en prie\b",
]


@dataclass
class Compressed:
    text: str
    tokens_before: int
    tokens_after: int

    @property
    def ratio(self) -> float:
        if self.tokens_before == 0:
            return 0.0
        return 1 - self.tokens_after / self.tokens_before

    @property
    def saved(self) -> int:
        return self.tokens_before - self.tokens_after


def compress(text: str, enabled: bool = True) -> Compressed:
    """Compresse un prompt de façon sûre (aucune perte de contenu utile)."""
    before = count(text)
    if not enabled or not text:
        return Compressed(text, before, before)

    out = text

    # 1. Retirer les politesses
    for pat in _FILLERS:
        out = re.sub(pat, "", out, flags=re.IGNORECASE)

    # 2. Espaces multiples → un seul
    out = re.sub(r"[ \t]{2,}", " ", out)

    # 3. Ponctuation répétée : !!!/??? → simple, mais on PRÉSERVE l'ellipse
    out = re.sub(r"([!?])\1{1,}", r"\1", out)      # !!! → !  /  ??? → ?
    out = re.sub(r"\.{4,}", "...", out)            # ..... → ...  (garde ...)

    # 4. Lignes vides multiples → une seule
    out = re.sub(r"\n{3,}", "\n\n", out)

    # 5. Espaces avant ponctuation
    out = re.sub(r"\s+([!?.,;:])", r"\1", out)

    # 6. NETTOYAGE des orphelins (uniquement séparés par un espace,
    #    pour ne PAS toucher aux ellipses "...")
    out = re.sub(r",\s*([.!?])", r"\1", out)       # ",." → "."
    out = re.sub(r"([.!?])\s*,", r"\1", out)       # ".," → "."
    out = re.sub(r"([?!.])\s+([?!.])", r"\2", out) # "? !" → "!"  (espace requis)
    out = re.sub(r"^[\s,.;:!?]+", "", out)         # ponctuation en tête
    out = re.sub(r"\s{2,}", " ", out).strip()

    # 7. Majuscule en tête
    if out and out[0].islower():
        out = out[0].upper() + out[1:]

    if not out or count(out) > before:
        return Compressed(text, before, before)

    return Compressed(out, before, count(out))


if __name__ == "__main__":
    samples = [
        "Bonjour !!! Est-ce que tu pourrais s'il te plaît m'aider ??? Merci d'avance !!!",
        "Je voudrais que tu   analyses   ce texte  ...   et   que tu me donnes "
        "ton avis  ,  s'il te plaît .",
        "Résume ce document en trois points clés.",
    ]
    for s in samples:
        r = compress(s)
        print(f"-{r.saved} tokens ({r.ratio:.0%})  "
              f"{r.tokens_before}→{r.tokens_after}")
        print(f"  AVANT : {s}")
        print(f"  APRÈS : {r.text}\n")