# engine/preprocessor.py
"""
Pre-traitement de fichiers : transforme un fichier en texte propre et compact
AVANT l'envoi a l'IA, sans detruire le contenu.
Formats : PDF, texte, image (OCR/vision), video (transcription + scenes).
Strategie adaptee a la tache (task-aware) + garde-fou budget de tokens.
"""
import os
from dataclasses import dataclass, field

from engine.tokens import count

try:
    import fitz  # PyMuPDF
    _HAS_FITZ = True
except ImportError:
    _HAS_FITZ = False

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".avif", ".gif")
VIDEO_EXTS = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".ts", ".m4v", ".mpeg", ".mpg")


@dataclass
class FileResult:
    text: str
    source: str
    kind: str
    pages: int = 0
    tokens: int = 0
    tokens_raw: int = 0
    strategy: str = "full"
    warnings: list = field(default_factory=list)

    @property
    def reduced_pct(self):
        if self.tokens_raw == 0:
            return 0.0
        return 1 - self.tokens / self.tokens_raw


# --- PDF ---------------------------------------------------------------------
def _table_to_md(tab):
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
    doc = fitz.open(path)
    blocks_all, total_text, table_count = [], 0, 0
    for page in doc:
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
    if total_text < 20 * pages:
        return None, pages, table_count, True
    blocks_all.sort(key=lambda x: (x[0], x[1]))
    text = "\n\n".join(b[2] for b in blocks_all).strip()
    return text, pages, table_count, False


# --- Budget task-aware -------------------------------------------------------
_CONDENSABLE = {"trivial", "simple", "moderate"}
_PRECISION = {"complex"}


def _fit_to_budget(text, budget, task_type):
    tok = count(text)
    if budget is None or tok <= budget:
        return text, "full", None
    if task_type in _PRECISION:
        return text, "full", (f"Contenu {tok} tokens > budget {budget}, "
                              f"conserve entier (tache de precision).")
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
    return reduced, "condensed", (f"Contenu {tok} tokens reduit a ~{budget} "
                                  f"(debut+fin conserves).")


def _wrap(text, path, kind, task_type, token_budget, extra_warnings=None,
          pages=1):
    """Applique le budget et construit le FileResult."""
    raw = count(text)
    fitted, strat, warn = _fit_to_budget(text, token_budget, task_type)
    res = FileResult(fitted, path, kind, pages=pages,
                     tokens=count(fitted), tokens_raw=raw, strategy=strat)
    if extra_warnings:
        res.warnings.extend(extra_warnings)
    if warn:
        res.warnings.append(warn)
    return res


# --- Point d'entree ----------------------------------------------------------
def preprocess_file(path, task_type="simple", token_budget=None):
    if not os.path.exists(path):
        return FileResult("", path, "unsupported",
                          warnings=[f"Fichier introuvable : {path}"])

    ext = os.path.splitext(path)[1].lower()

    # PDF
    if ext == ".pdf":
        if not _HAS_FITZ:
            return FileResult("", path, "unsupported",
                              warnings=["PyMuPDF manquant : pip install pymupdf"])
        text, pages, tables, scanned = extract_pdf(path)
        if scanned:
            return FileResult("", path, "scanned", pages=pages,
                              warnings=["PDF scanne (pas de couche texte). "
                                        "OCR requis."])
        res = _wrap(text, path, "pdf", task_type, token_budget, pages=pages)
        if tables:
            res.warnings.insert(0, f"{tables} table(s) preservee(s) en markdown.")
        return res

    # Texte brut
    if ext in (".txt", ".md"):
        with open(path, encoding="utf-8", errors="ignore") as f:
            text = f.read()
        return _wrap(text, path, "text", task_type, token_budget)

    # Image
    if ext in IMAGE_EXTS:
        from engine.media import extract_image
        text, kind, warns = extract_image(path)
        if not text:
            return FileResult("", path, kind, warnings=warns or
                              ["Aucun texte ni description extraits."])
        return _wrap(text, path, kind, task_type, token_budget,
                     extra_warnings=warns)

    # Video
    if ext in VIDEO_EXTS:
        from engine.media import extract_video
        text, kind, warns = extract_video(path)
        if not text:
            return FileResult("", path, kind, warnings=warns or
                              ["Aucune transcription ni scene extraites."])
        return _wrap(text, path, kind, task_type, token_budget,
                     extra_warnings=warns)

    return FileResult("", path, "unsupported",
                      warnings=[f"Type '{ext}' non gere."])


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "test_image.png"
    r = preprocess_file(path, task_type="simple")
    print(f"Type      : {r.kind} ({r.pages} pages)")
    print(f"Tokens    : {r.tokens_raw} -> {r.tokens}")
    print(f"Strategie : {r.strategy}")
    for w in r.warnings:
        print(f"  ! {w}")
    print("\n--- Texte extrait ---")
    print(r.text[:600])
