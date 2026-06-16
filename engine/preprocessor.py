# engine/preprocessor.py
"""
Pré-traitement de fichiers : transforme un fichier (PDF d'abord) en texte
propre et compact AVANT de l'envoyer à l'IA, sans détruire le contenu.
Stratégie adaptée à la tâche (task-aware) + garde-fou budget de tokens.
"""
import os
import logging
logging.getLogger("fitz").setLevel(logging.ERROR)
from dataclasses import dataclass, field

from engine.tokens import count

try:
    import fitz  # PyMuPDF
    _HAS_FITZ = True
except ImportError:
    _HAS_FITZ = False


@dataclass
class FileResult:
    text: str               # texte propre prêt pour l'IA
    source: str             # chemin du fichier
    kind: str               # pdf | text | scanned | unsupported
    pages: int = 0
    tokens: int = 0         # tokens du texte final
    tokens_raw: int = 0     # tokens avant pré-traitement
    strategy: str = "full"  # full | condensed
    warnings: list = field(default_factory=list)

    @property
    def reduced_pct(self):
        if self.tokens_raw == 0:
            return 0.0
        return 1 - self.tokens / self.tokens_raw


def _table_to_md(tab):
    """Convertit une table PyMuPDF en markdown compact."""
    rows = tab.extract()
    if not rows:
        return ""
    rows = [[(c or "").strip() for c in r] for r in rows]
    header = rows[0]
    md = ["| " + " | ".join(header) + " |",
          "| " + " | ".join("---" for _ in header) + " |"]
    for r in rows[1:]:
        md.append("| " + " | ".join(r) + " |")
    return "\n".join(md)


def extract_pdf(path):
    """Extrait texte + tables en markdown, dans l'ordre de lecture.
    Le texte des zones de table est exclu du flux pour éviter les doublons."""
    doc = fitz.open(path)
    blocks_all, total_text, table_count = [], 0, 0

    for page in doc:
        # 1. Tables : markdown + bbox pour exclusion du texte
        tbl_rects = []
        try:
            for t in page.find_tables().tables:
                md = _table_to_md(t)
                if md:
                    r = fitz.Rect(t.bbox)
                    tbl_rects.append(r)
                    blocks_all.append((page.number, r.y0, md))
                    table_count += 1
        except Exception:
            pass

        # 2. Blocs de texte, en sautant ceux situés dans une table
        for b in page.get_text("blocks"):
            x0, y0, x1, y1, txt = b[0], b[1], b[2], b[3], (b[4] or "").strip()
            if not txt:
                continue
            brect = fitz.Rect(x0, y0, x1, y1)
            if any(brect.intersects(tr) for tr in tbl_rects):
                continue
            total_text += len(txt)
            blocks_all.append((page.number, y0, txt))

    pages = doc.page_count
    doc.close()

    # Détection de PDF scanné : quasi aucun texte extractible
    if total_text < 20 * pages:
        return None, pages, table_count, True

    # Ordre de lecture : par page puis position verticale
    blocks_all.sort(key=lambda x: (x[0], x[1]))
    text = "\n\n".join(b[2] for b in blocks_all).strip()
    return text, pages, table_count, False


# Tâches où on PEUT condenser sans risque (résumé, vue d'ensemble)
_CONDENSABLE = {"trivial", "simple", "moderate"}
# Tâches de précision : on ne tronque JAMAIS (risque de perdre l'info clé)
_PRECISION = {"complex"}


def _fit_to_budget(text, budget, task_type):
    """Réduit le texte au budget de tokens selon la tâche."""
    tok = count(text)
    if budget is None or tok <= budget:
        return text, "full", None

    if task_type in _PRECISION:
        return text, "full", (f"Contenu {tok} tokens > budget {budget}, "
                              f"conservé entier (tâche de précision).")

    # Condensable : début + fin (le cœur informatif est souvent là),
    # avec un marqueur clair au milieu. Pas de perte silencieuse.
    paras = text.split("\n\n")
    head, tail, acc = [], [], 0
    half = budget // 2
    for p in paras:
        c = count(p)
        if acc + c > half:
            break
        head.append(p); acc += c
    acc2 = 0
    for p in reversed(paras):
        c = count(p)
        if acc2 + c > half:
            break
        tail.insert(0, p); acc2 += c
    reduced = ("\n\n".join(head) +
               "\n\n[... section centrale omise pour rester dans le budget ...]\n\n" +
               "\n\n".join(tail))
    return reduced, "condensed", (f"Contenu {tok} tokens réduit à ~{budget} "
                                  f"(début+fin conservés).")


def preprocess_file(path, task_type="simple", token_budget=None):
    """
    Transforme un fichier en texte prêt pour l'IA.
    task_type    : pilote la stratégie de réduction.
    token_budget : plafond de tokens pour le contenu du fichier (optionnel).
    """
    if not os.path.exists(path):
        return FileResult("", path, "unsupported",
                          warnings=[f"Fichier introuvable : {path}"])

    ext = os.path.splitext(path)[1].lower()

    # --- PDF ---
    if ext == ".pdf":
        if not _HAS_FITZ:
            return FileResult("", path, "unsupported",
                              warnings=["PyMuPDF manquant : pip install pymupdf"])
        text, pages, tables, scanned = extract_pdf(path)
        if scanned:
            return FileResult("", path, "scanned", pages=pages,
                              warnings=["PDF scanné (pas de couche texte). "
                                        "OCR requis — non géré dans cette version."])
        raw = count(text)
        fitted, strat, warn = _fit_to_budget(text, token_budget, task_type)
        res = FileResult(fitted, path, "pdf", pages=pages,
                         tokens=count(fitted), tokens_raw=raw, strategy=strat)
        if tables:
            res.warnings.append(f"{tables} table(s) préservée(s) en markdown.")
        if warn:
            res.warnings.append(warn)
        return res

    # --- Texte brut ---
    if ext in (".txt", ".md"):
        with open(path, encoding="utf-8", errors="ignore") as f:
            text = f.read()
        raw = count(text)
        fitted, strat, warn = _fit_to_budget(text, token_budget, task_type)
        res = FileResult(fitted, path, "text", pages=1,
                         tokens=count(fitted), tokens_raw=raw, strategy=strat)
        if warn:
            res.warnings.append(warn)
        return res

    # --- Non géré (vidéo, image, docx) : prochains plug-ins ---
    return FileResult("", path, "unsupported",
                      warnings=[f"Type '{ext}' pas encore géré "
                                "(vidéo/image/docx = prochains modules)."])


if __name__ == "__main__":
    # Mets ici le chemin d'un PDF de test à toi
    r = preprocess_file("sample.pdf", task_type="simple")
    print(f"Type      : {r.kind} ({r.pages} pages)")
    print(f"Tokens    : {r.tokens_raw} -> {r.tokens} (-{r.reduced_pct:.0%})")
    print(f"Stratégie : {r.strategy}")
    for w in r.warnings:
        print(f"  ! {w}")
    print("\n--- Texte extrait (prêt pour l'IA) ---")
    print(r.text[:800])