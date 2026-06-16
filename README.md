# llm-router

> Moteur d'optimisation de requêtes LLM : pré-traitement, compression, routing multi-modèles, contrôle qualité et ré-routage automatique, avec mesure des coûts.
> LLM request optimization engine: preprocessing, compression, multi-model routing, quality control and automatic re-routing, with cost measurement.

`Français` | [`English`](#english)

---

## Français

### Présentation

`llm-router` s'intercale entre une requête utilisateur et les modèles de langage pour **réduire le coût d'inférence sans dégrader la qualité**. Pour chaque requête, il pré-traite les fichiers joints, compresse le prompt, classe la tâche, route vers le modèle le moins cher capable de la traiter, exécute l'appel, **note la qualité de la réponse via un modèle juge**, et **escalade automatiquement** vers un modèle supérieur si la qualité est insuffisante. Chaque exécution est journalisée pour produire un benchmark mesuré.

Le projet fonctionne intégralement avec des modèles **gratuits** par défaut : Ollama en local et le tier gratuit de Groq (Llama 3.3 70B). Le support des API payantes (Anthropic) est intégré et prêt, derrière un garde-fou de dépense.

### Pipeline

```
Requête (+ fichier)
  ├─ Pré-traitement fichier   → PDF/texte propre, tables en markdown, budget task-aware
  ├─ Compression              → réduction de tokens sans perte de sens
  ├─ Classification           → trivial / simple / moderate / complex
  ├─ Routing                  → modèle le moins cher au-dessus du plancher de qualité
  ├─ Exécution                → appel réel (Ollama / Groq / Anthropic)
  ├─ Contrôle qualité         → note /10 par un modèle juge (Groq 70B)
  ├─ Ré-routage (escalade)    → si qualité < seuil, montée vers un modèle supérieur
  └─ Journalisation           → benchmark cumulé (coût, tokens, qualité, latence, escalades)
```

### Architecture

| Module | Rôle |
|--------|------|
| `config.py` | Catalogue des modèles, tarifs, niveaux de capacité (tiers) |
| `engine/tokens.py` | Comptage de tokens (tiktoken + fallback) |
| `engine/preprocessor.py` | Extraction PDF/texte (PyMuPDF), tables, réduction au budget |
| `engine/compressor.py` | Compression de prompt déterministe et sûre |
| `engine/classifier.py` | Classification de tâche (Ollama + fallback heuristique) |
| `engine/router.py` | Sélection du modèle le moins cher au-dessus du plancher + cible d'escalade |
| `engine/llm_client.py` | Appels réels : Ollama, Groq, Anthropic (clés via `.env`, garde-fou) |
| `engine/quality.py` | Évaluation de la qualité des réponses (modèle juge) |
| `engine/escalation.py` | Ré-routage par qualité : escalade vers un tier supérieur |
| `engine/orchestrator.py` | Assemblage du pipeline complet et chiffrage |
| `engine/metrics.py` | Journalisation persistante et statistiques agrégées |

### Principe de fonctionnement

Chaque classe de tâche définit un **plancher de qualité** (tier minimum). Le routeur sélectionne le modèle le moins cher dont le tier est supérieur ou égal à ce plancher. Après exécution, un **modèle juge** note la réponse sur 10. Si la note est sous le seuil configuré, le moteur **escalade** vers un modèle de tier supérieur et compare. Il conserve la meilleure réponse valide. Le coût de chaque exécution est comparé à un **baseline** (la requête entière envoyée au modèle le plus puissant, sans optimisation) pour quantifier l'économie réelle.

### Installation

```bash
pip install tiktoken pymupdf requests groq anthropic python-dotenv
```

Exécution locale via [Ollama](https://ollama.com) :

```bash
ollama pull qwen2.5:14b   # ou qwen2.5:3b pour une machine modeste
```

Clés API (gratuites pour Groq) dans un fichier `.env` à la racine :

```
GROQ_API_KEY=...
ANTHROPIC_API_KEY=...    # optionnel
```

### Utilisation

```bash
# Tester un module isolément
python config.py
python -m engine.preprocessor "chemin/vers/document.pdf"
python -m engine.escalation

# Lancer le pipeline complet et le benchmark
python -m engine.metrics
```

Exemple programmatique :

```python
from engine.orchestrator import process, report

r = process(
    "Résume ce rapport en trois points.",
    file_path="rapport.pdf",
    escalate=True,   # pipeline complet : exécution + qualité + ré-routage
)
print(report(r))
```

### Benchmark (illustratif)

Mesure sur un petit échantillon, exécution gratuite (Ollama `qwen2.5:14b`, juge Groq `llama-3.3-70b`) :

```
5 requêtes (5 mesurées)
Coût moteur      : 0.000000 $
Coût baseline    : 0.063480 $   (tout envoyé à un modèle frontier)
Économie         : -100 %       (routing vers modèle local gratuit)
Tokens entrée    : -9 %
Qualité moyenne  : 9.0 / 10     (jugée par un modèle 70B)
Latence moyenne  : 20 s
Escalades        : 0 / 5        (le modèle local suffisait)
```

Lecture : sur cet échantillon, le routing vers un modèle local gratuit suffit, et la qualité — vérifiée par un juge plus puissant — reste élevée (9/10), sans qu'aucune escalade ne soit nécessaire. Le moteur valide donc l'économie au lieu de la supposer.

### Feuille de route

- [x] Routing par plancher de qualité
- [x] Contrôle qualité par modèle juge
- [x] Ré-routage automatique par escalade
- [x] Support Groq (tier gratuit) et Anthropic (avec garde-fou de dépense)
- [ ] Pré-traitement de nouveaux formats : image, vidéo, docx
- [ ] Compression sémantique avancée (LLMLingua-2)
- [ ] Routing auto-apprenant par utilisateur (seuils ajustés selon l'historique)
- [ ] Tableau de bord de visualisation du benchmark

### Avertissement

Les tarifs du catalogue (`config.py`) sont représentatifs et doivent être ajustés aux prix réels. Le comptage de tokens utilise `tiktoken` comme estimateur commun (approximation pour les modèles non-OpenAI). Projet expérimental, non destiné tel quel à un usage en production.

---

## English

### Overview

`llm-router` sits between a user request and language models to **reduce inference cost without degrading quality**. For each request, it preprocesses attached files, compresses the prompt, classifies the task, routes to the cheapest capable model, executes the call, **scores the response quality via a judge model**, and **automatically escalates** to a higher model when quality falls short. Every execution is logged into a measured benchmark.

The project runs entirely on **free** models by default: local Ollama and Groq's free tier (Llama 3.3 70B). Paid API support (Anthropic) is built in and ready, behind a spend guardrail.

### Pipeline

```
Request (+ file)
  ├─ File preprocessing   → clean PDF/text, tables as markdown, task-aware budget
  ├─ Compression          → token reduction without loss of meaning
  ├─ Classification       → trivial / simple / moderate / complex
  ├─ Routing              → cheapest model above the quality floor
  ├─ Execution            → real call (Ollama / Groq / Anthropic)
  ├─ Quality control      → /10 score from a judge model (Groq 70B)
  ├─ Re-routing (escalate)→ if quality < threshold, move up to a higher model
  └─ Logging              → cumulative benchmark (cost, tokens, quality, latency, escalations)
```

### Architecture

| Module | Role |
|--------|------|
| `config.py` | Model catalogue, pricing, capability tiers |
| `engine/tokens.py` | Token counting (tiktoken + fallback) |
| `engine/preprocessor.py` | PDF/text extraction (PyMuPDF), tables, budget reduction |
| `engine/compressor.py` | Deterministic, safe prompt compression |
| `engine/classifier.py` | Task classification (Ollama + heuristic fallback) |
| `engine/router.py` | Cheapest-model-above-floor selection + escalation target |
| `engine/llm_client.py` | Real calls: Ollama, Groq, Anthropic (keys via `.env`, guardrail) |
| `engine/quality.py` | Response quality evaluation (judge model) |
| `engine/escalation.py` | Quality-driven re-routing: escalate to a higher tier |
| `engine/orchestrator.py` | Full pipeline assembly and cost accounting |
| `engine/metrics.py` | Persistent logging and aggregated statistics |

### How it works

Each task class defines a **quality floor** (minimum tier). The router selects the cheapest model whose tier meets that floor. After execution, a **judge model** scores the response out of 10. If the score is below the configured threshold, the engine **escalates** to a higher-tier model and compares, keeping the best valid response. Each execution's cost is compared against a **baseline** (the whole request sent to the most capable model, unoptimised) to quantify the actual saving.

### Installation

```bash
pip install tiktoken pymupdf requests groq anthropic python-dotenv
```

Local execution via [Ollama](https://ollama.com):

```bash
ollama pull qwen2.5:14b   # or qwen2.5:3b for a modest machine
```

API keys (free for Groq) in a `.env` file at the root:

```
GROQ_API_KEY=...
ANTHROPIC_API_KEY=...    # optional
```

### Usage

```bash
# Test a module in isolation
python config.py
python -m engine.preprocessor "path/to/document.pdf"
python -m engine.escalation

# Run the full pipeline and benchmark
python -m engine.metrics
```

Programmatic example:

```python
from engine.orchestrator import process, report

r = process(
    "Summarise this report in three points.",
    file_path="report.pdf",
    escalate=True,   # full pipeline: execution + quality + re-routing
)
print(report(r))
```

### Benchmark (illustrative)

Measured on a small sample, free execution (Ollama `qwen2.5:14b`, Groq `llama-3.3-70b` judge):

```
5 requests (5 measured)
Engine cost      : $0.000000
Baseline cost    : $0.063480   (everything sent to a frontier model)
Saving           : -100 %      (routed to free local model)
Input tokens     : -9 %
Avg. quality     : 9.0 / 10    (judged by a 70B model)
Avg. latency     : 20 s
Escalations      : 0 / 5       (the local model was sufficient)
```

Reading: on this sample, routing to a free local model is sufficient, and quality — verified by a stronger judge — stays high (9/10) with no escalation needed. The engine validates the saving rather than assuming it.

### Roadmap

- [x] Quality-floor routing
- [x] Judge-model quality control
- [x] Automatic escalation re-routing
- [x] Groq (free tier) and Anthropic (with spend guardrail) support
- [ ] Preprocessing for more formats: image, video, docx
- [ ] Advanced semantic compression (LLMLingua-2)
- [ ] Per-user self-learning routing (thresholds tuned from history)
- [ ] Benchmark visualisation dashboard

### Disclaimer

Catalogue pricing (`config.py`) is representative and must be adjusted to real prices. Token counting uses `tiktoken` as a common estimator (approximate for non-OpenAI models). Experimental project, not intended for production use as-is.

---

**Stack** : Python · Ollama (qwen2.5) · Groq (Llama 3.3 70B) · Anthropic · tiktoken · PyMuPDF
