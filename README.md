# llm-router

> Moteur d'optimisation de requêtes LLM : pré-traitement, compression, routing multi-modèles et contrôle qualité, avec mesure des coûts.
> LLM request optimization engine: preprocessing, compression, multi-model routing and quality control, with cost measurement.

`Français` | [`English`](#english)

---

## Français

### Présentation

`llm-router` est un moteur qui s'intercale entre une requête utilisateur et les modèles de langage pour **réduire le coût d'inférence sans dégrader la qualité**. Pour chaque requête, il pré-traite les fichiers joints, compresse le prompt, classe la tâche, route vers le modèle le moins cher capable de la traiter, exécute l'appel, puis note la qualité de la réponse. Chaque exécution est journalisée pour produire un benchmark mesuré (coût, tokens, qualité, latence).

Le projet privilégie l'exécution **locale et gratuite** (Ollama) par défaut, avec une bascule prévue vers les API commerciales.

### Pipeline

```
Requête (+ fichier)
  ├─ Pré-traitement fichier   → PDF/texte propre, tables en markdown, budget task-aware
  ├─ Compression              → réduction de tokens sans perte de sens
  ├─ Classification           → trivial / simple / moderate / complex
  ├─ Routing                  → modèle le moins cher au-dessus du plancher de qualité
  ├─ Exécution                → appel réel (Ollama local)
  ├─ Contrôle qualité         → note /10 par un modèle juge
  └─ Journalisation           → benchmark cumulé (coût, tokens, qualité, latence)
```

### Architecture

| Module | Rôle |
|--------|------|
| `config.py` | Catalogue des modèles, tarifs, niveaux de capacité (tiers) |
| `engine/tokens.py` | Comptage de tokens (tiktoken + fallback) |
| `engine/preprocessor.py` | Extraction PDF/texte (PyMuPDF), tables, réduction au budget |
| `engine/compressor.py` | Compression de prompt déterministe et sûre |
| `engine/classifier.py` | Classification de tâche (Ollama + fallback heuristique) |
| `engine/router.py` | Sélection du modèle le moins cher au-dessus du plancher |
| `engine/llm_client.py` | Appels réels aux modèles (Ollama) |
| `engine/quality.py` | Évaluation de la qualité des réponses (modèle juge) |
| `engine/orchestrator.py` | Assemblage du pipeline et chiffrage |
| `engine/metrics.py` | Journalisation persistante et statistiques agrégées |

### Principe de routing

Chaque classe de tâche définit un **plancher de qualité** (tier minimum). Le routeur sélectionne le modèle le moins cher dont le tier est supérieur ou égal à ce plancher. Une tâche simple peut donc être traitée par un modèle local gratuit, tandis qu'une tâche complexe est dirigée vers un modèle frontier. Le coût de chaque exécution est comparé à un **baseline** (l'ensemble de la requête envoyé au modèle le plus puissant, sans optimisation) pour quantifier l'économie réelle.

### Installation

```bash
pip install tiktoken pymupdf requests
```

Exécution locale (optionnelle mais recommandée) via [Ollama](https://ollama.com) :

```bash
ollama pull qwen2.5:14b   # ou qwen2.5:3b pour une machine modeste
```

### Utilisation

```bash
# Tester chaque module isolément
python config.py
python -m engine.preprocessor "chemin/vers/document.pdf"
python -m engine.router

# Lancer le pipeline complet et le benchmark
python -m engine.metrics
```

Exemple d'appel programmatique :

```python
from engine.orchestrator import process, report

r = process(
    "Résume ce rapport en trois points.",
    file_path="rapport.pdf",
    execute=True,   # appel réel
    assess=True,    # évaluation qualité
)
print(report(r))
```

### Benchmark (illustratif)

Mesure sur un petit échantillon, exécution 100 % locale (Ollama `qwen2.5:14b`) :

```
5 requêtes (5 mesurées)
Coût moteur     : 0.000000 $
Coût baseline   : 0.063480 $   (tout envoyé à un modèle frontier)
Économie        : -100 %       (routing vers modèle local gratuit)
Tokens entrée   : -9 %
Qualité moyenne : 6.8 / 10
Latence moyenne : 16 s
```

Ces chiffres sont indicatifs : l'économie de 100 % reflète un routing vers un modèle local gratuit, et la qualité de 6,8/10 illustre le compromis à arbitrer. Un juge plus fiable (modèle frontier) et un ré-routage par seuil de qualité sont prévus (voir feuille de route).

### Feuille de route

- [ ] Client API commercial (Anthropic / OpenAI) pour les tâches frontier
- [ ] Juge de qualité frontier (notation plus fiable que le juge local)
- [ ] Ré-routage automatique : escalade vers un modèle supérieur si la qualité est sous le seuil
- [ ] Pré-traitement de nouveaux formats : image, vidéo, docx
- [ ] Compression sémantique avancée (LLMLingua-2)
- [ ] Routing auto-apprenant par utilisateur (seuils ajustés selon l'historique)

### Avertissement

Les tarifs du catalogue (`config.py`) sont représentatifs et doivent être ajustés aux prix réels. Le comptage de tokens utilise `tiktoken` comme estimateur commun (approximation pour les modèles non-OpenAI). Ce projet est un moteur expérimental, non destiné tel quel à un usage en production.

---

## English

### Overview

`llm-router` is an engine that sits between a user request and language models to **reduce inference cost without degrading quality**. For each request, it preprocesses attached files, compresses the prompt, classifies the task, routes to the cheapest model capable of handling it, executes the call, then scores the response quality. Every execution is logged to produce a measured benchmark (cost, tokens, quality, latency).

The project favours **local, free execution** (Ollama) by default, with a planned switch to commercial APIs.

### Pipeline

```
Request (+ file)
  ├─ File preprocessing   → clean PDF/text, tables as markdown, task-aware budget
  ├─ Compression          → token reduction without loss of meaning
  ├─ Classification       → trivial / simple / moderate / complex
  ├─ Routing              → cheapest model above the quality floor
  ├─ Execution            → real call (local Ollama)
  ├─ Quality control      → /10 score from a judge model
  └─ Logging              → cumulative benchmark (cost, tokens, quality, latency)
```

### Architecture

| Module | Role |
|--------|------|
| `config.py` | Model catalogue, pricing, capability tiers |
| `engine/tokens.py` | Token counting (tiktoken + fallback) |
| `engine/preprocessor.py` | PDF/text extraction (PyMuPDF), tables, budget reduction |
| `engine/compressor.py` | Deterministic, safe prompt compression |
| `engine/classifier.py` | Task classification (Ollama + heuristic fallback) |
| `engine/router.py` | Cheapest-model-above-floor selection |
| `engine/llm_client.py` | Real model calls (Ollama) |
| `engine/quality.py` | Response quality evaluation (judge model) |
| `engine/orchestrator.py` | Pipeline assembly and cost accounting |
| `engine/metrics.py` | Persistent logging and aggregated statistics |

### Routing principle

Each task class defines a **quality floor** (minimum tier). The router selects the cheapest model whose tier is greater than or equal to that floor. A simple task can therefore be served by a free local model, while a complex task is directed to a frontier model. Each execution's cost is compared against a **baseline** (the whole request sent to the most capable model, unoptimised) to quantify the actual saving.

### Installation

```bash
pip install tiktoken pymupdf requests
```

Optional local execution via [Ollama](https://ollama.com):

```bash
ollama pull qwen2.5:14b   # or qwen2.5:3b for a modest machine
```

### Usage

```bash
# Test each module in isolation
python config.py
python -m engine.preprocessor "path/to/document.pdf"
python -m engine.router

# Run the full pipeline and benchmark
python -m engine.metrics
```

Programmatic example:

```python
from engine.orchestrator import process, report

r = process(
    "Summarise this report in three points.",
    file_path="report.pdf",
    execute=True,   # real call
    assess=True,    # quality evaluation
)
print(report(r))
```

### Benchmark (illustrative)

Measured on a small sample, fully local execution (Ollama `qwen2.5:14b`):

```
5 requests (5 measured)
Engine cost    : $0.000000
Baseline cost  : $0.063480   (everything sent to a frontier model)
Saving         : -100 %      (routed to free local model)
Input tokens   : -9 %
Avg. quality   : 6.8 / 10
Avg. latency   : 16 s
```

These figures are indicative: the 100% saving reflects routing to a free local model, and the 6.8/10 quality illustrates the trade-off to arbitrate. A more reliable judge (frontier model) and quality-threshold re-routing are planned (see roadmap).

### Roadmap

- [ ] Commercial API client (Anthropic / OpenAI) for frontier tasks
- [ ] Frontier quality judge (more reliable than the local judge)
- [ ] Automatic re-routing: escalate to a higher model when quality is below threshold
- [ ] Preprocessing for more formats: image, video, docx
- [ ] Advanced semantic compression (LLMLingua-2)
- [ ] Per-user self-learning routing (thresholds tuned from history)

### Disclaimer

Catalogue pricing (`config.py`) is representative and must be adjusted to real prices. Token counting uses `tiktoken` as a common estimator (approximate for non-OpenAI models). This is an experimental engine, not intended for production use as-is.

---

**Stack** : Python · Ollama (qwen2.5) · tiktoken · PyMuPDF
