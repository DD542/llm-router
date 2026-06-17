# llm-router

> Moteur d'optimisation de requêtes LLM : pré-traitement multi-formats, compression, routing multi-modèles, contrôle qualité, ré-routage auto-apprenant — avec API et tableau de bord.
> LLM request optimization engine: multi-format preprocessing, compression, multi-model routing, quality control, self-learning re-routing — with API and dashboard.

`Français` | [`English`](#english)

---

## Français

### Présentation

`llm-router` s'intercale entre une requête et les modèles de langage pour **réduire le coût d'inférence sans dégrader la qualité**. Pour chaque demande, il pré-traite les fichiers joints, compresse le prompt, classe la tâche, route vers le modèle le moins cher capable de la traiter, exécute l'appel, note la qualité via un modèle juge, et **escalade** vers un modèle supérieur seulement si nécessaire. Il **apprend de son historique** pour démarrer au bon niveau au fil du temps.

Le projet tourne intégralement avec des modèles **gratuits** par défaut (Ollama local + tier gratuit de Groq). Le support des API payantes (Anthropic) est intégré, derrière un garde-fou de dépense.

### Pipeline

```
Requête (+ fichier)
  ├─ Pré-traitement    → PDF, texte, image (OCR / vision), vidéo (transcription + scènes)
  ├─ Compression       → réduction de tokens sans perte de sens
  ├─ Classification    → trivial / simple / moderate / complex
  ├─ Routing           → modèle le moins cher au-dessus du plancher (auto-appris)
  ├─ Exécution         → appel réel (Ollama / Groq / Anthropic)
  ├─ Contrôle qualité  → note /10 par un modèle juge
  ├─ Ré-routage        → escalade vers un modèle supérieur si qualité insuffisante
  └─ Journalisation    → benchmark mesuré (coût, tokens, qualité, latence, escalades)
```

### Composants

| Module | Rôle |
|--------|------|
| `config.py` | Catalogue des modèles, tarifs, niveaux (tiers) |
| `engine/tokens.py` | Comptage de tokens |
| `engine/preprocessor.py` | Extraction PDF / texte / image / vidéo, budget task-aware |
| `engine/media.py` | Image (OCR Tesseract + vision llava), vidéo (Whisper + scènes) |
| `engine/compressor.py` | Compression de prompt déterministe |
| `engine/classifier.py` | Classification de tâche (Ollama + fallback) |
| `engine/router.py` | Sélection du modèle + cible d'escalade |
| `engine/policy.py` | Routing auto-apprenant (apprend du journal) |
| `engine/llm_client.py` | Appels réels : Ollama, Groq, Anthropic |
| `engine/quality.py` | Évaluation qualité (modèle juge) |
| `engine/escalation.py` | Ré-routage par qualité |
| `engine/orchestrator.py` | Pipeline complet + chiffrage |
| `engine/metrics.py` | Journalisation + statistiques |
| `api.py` | API FastAPI exposant le moteur |
| `llm-dashboard/` | Tableau de bord Vue 3 (KPI, graphes, simulateur) |

### Installation

```bash
pip install -r requirements.txt
ollama pull qwen2.5:14b
ollama pull llava            # vision (images / vidéos)
```

Pour l'OCR : installer le binaire **Tesseract** (+ pack de langue `fra`).
Clés API dans un fichier `.env` à la racine :

```
GROQ_API_KEY=...
ANTHROPIC_API_KEY=...    # optionnel
```

### Utilisation — moteur

```bash
python -m engine.preprocessor "document.pdf"
python -m engine.metrics        # pipeline complet + benchmark
python -m engine.policy         # rafraîchit la politique de routing apprise
```

```python
from engine.orchestrator import process, report
r = process("Résume ce rapport.", file_path="rapport.pdf", escalate=True)
print(report(r))
```

### Utilisation — API + dashboard

```bash
# 1. API (depuis la racine)
uvicorn api:app --reload --port 8000

# 2. Dashboard (depuis llm-dashboard/)
npm install
npm run dev
```

Le tableau de bord offre une **vue d'ensemble** (KPI, effondrement des coûts, répartition par modèle, qualité vs coût, latence, compression), un **journal** des requêtes, et un **simulateur** : on tape une requête ou on importe un fichier, on choisit un profil (Entreprise = budget / Particulier = quota), et le moteur exécute en direct en montrant la décision, le coût réel vs baseline, et l'impact sur le budget.

### Benchmark (illustratif)

```
Routing vers modèles gratuits/locaux suffisant pour la majorité des requêtes
Qualité moyenne : ≈9/10 (vérifiée par un modèle juge)
Coût réservé aux seules tâches qui le nécessitent
```

La vraie optimisation n'est pas « moins cher » mais le point d'équilibre qualité/coût, prouvé par la mesure.

### Feuille de route

- [x] Pré-traitement multi-formats (PDF, texte, image, vidéo)
- [x] Routing par plancher de qualité + ré-routage par escalade
- [x] Routing auto-apprenant
- [x] API FastAPI + dashboard Vue 3 avec simulateur
- [ ] Compression sémantique avancée (LLMLingua-2)
- [ ] Apprentissage par utilisateur (profils distincts)

### Avertissement

Tarifs du catalogue (`config.py`) représentatifs, à ajuster. Comptage de tokens via `tiktoken` (approximation pour les modèles non-OpenAI). Projet expérimental.

---

## English

### Overview

`llm-router` sits between a request and language models to **cut inference cost without degrading quality**. For each request it preprocesses attached files, compresses the prompt, classifies the task, routes to the cheapest capable model, executes, scores quality via a judge model, and **escalates** only when needed. It **learns from history** to start at the right tier over time.

Runs entirely on **free** models by default (local Ollama + Groq free tier). Paid APIs (Anthropic) supported behind a spend guardrail.

### Pipeline

```
Request (+ file)
  ├─ Preprocessing   → PDF, text, image (OCR / vision), video (transcription + scenes)
  ├─ Compression     → token reduction without loss of meaning
  ├─ Classification  → trivial / simple / moderate / complex
  ├─ Routing         → cheapest model above the floor (self-learned)
  ├─ Execution       → real call (Ollama / Groq / Anthropic)
  ├─ Quality control → /10 score from a judge model
  ├─ Re-routing      → escalate to a higher model if quality is insufficient
  └─ Logging         → measured benchmark (cost, tokens, quality, latency, escalations)
```

### Components

| Module | Role |
|--------|------|
| `config.py` | Model catalogue, pricing, tiers |
| `engine/preprocessor.py` + `engine/media.py` | Multi-format extraction (PDF, text, image, video) |
| `engine/compressor.py` | Prompt compression |
| `engine/classifier.py` | Task classification |
| `engine/router.py` + `engine/policy.py` | Routing + self-learning policy |
| `engine/llm_client.py` | Real calls: Ollama, Groq, Anthropic |
| `engine/quality.py` + `engine/escalation.py` | Quality scoring + re-routing |
| `engine/orchestrator.py` | Full pipeline + cost accounting |
| `engine/metrics.py` | Logging + statistics |
| `api.py` | FastAPI backend |
| `llm-dashboard/` | Vue 3 dashboard (KPIs, charts, simulator) |

### Setup

```bash
pip install -r requirements.txt
ollama pull qwen2.5:14b
ollama pull llava
```

Install the **Tesseract** binary for OCR. API keys in `.env`:

```
GROQ_API_KEY=...
ANTHROPIC_API_KEY=...    # optional
```

### Usage — engine

```bash
python -m engine.metrics        # full pipeline + benchmark
python -m engine.policy         # refresh learned routing policy
```

```python
from engine.orchestrator import process, report
r = process("Summarise this report.", file_path="report.pdf", escalate=True)
print(report(r))
```

### Usage — API + dashboard

```bash
uvicorn api:app --reload --port 8000      # from root
cd llm-dashboard && npm install && npm run dev
```

The dashboard provides an **overview** (KPIs, cost collapse, model split, quality vs cost, latency, compression), a request **ledger**, and a **simulator**: type a request or upload a file, pick a profile (Business = budget / Individual = token quota), and the engine runs live, showing the decision, real vs baseline cost, and budget impact.

### Roadmap

- [x] Multi-format preprocessing (PDF, text, image, video)
- [x] Quality-floor routing + escalation re-routing
- [x] Self-learning routing
- [x] FastAPI backend + Vue 3 dashboard with simulator
- [ ] Advanced semantic compression (LLMLingua-2)
- [ ] Per-user learning (distinct profiles)

### Disclaimer

Catalogue pricing (`config.py`) is representative; adjust to real prices. Token counting uses `tiktoken` (approximate for non-OpenAI models). Experimental project.

---

**Stack** : Python · Ollama · Groq · Anthropic · FastAPI · Vue 3 · Tesseract · Whisper
