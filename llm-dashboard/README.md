# llm-router · dashboard

Frontend Vue 3 + API du moteur d'optimisation LLM.

Trois espaces :
- **Vue d'ensemble** — KPI, effondrement des coûts, répartition par modèle,
  qualité vs coût, latence par modèle, compression des tokens. Slicer interactif.
- **Simulateur** — tape une requête (ou importe un fichier), choisis un profil
  (Entreprise = budget $ / Particulier = quota tokens), et le moteur exécute en
  direct : tâche détectée, modèle choisi, coût réel vs baseline, qualité, et
  l'impact sur ton budget/quota.
- **Journal** — toutes les requêtes mesurées.

## Architecture

```
Vue 3 (ce dossier)  →  API FastAPI (api.py)  →  moteur Python (engine/)
     dashboard            /api/metrics              process()
                          /api/simulate
```

## 1. Lancer l'API (depuis le projet moteur `baseline/`)

```bash
pip install fastapi "uvicorn[standard]" python-multipart
uvicorn api:app --reload --port 8000
```

L'API expose `/api/metrics` (historique) et `/api/simulate` (exécution réelle).
Pour que le Simulateur fonctionne, Ollama doit tourner et ta clé Groq être dans `.env`.

## 2. Lancer le dashboard

```bash
npm install
npm run dev
```

Ouvre l'URL affichée (http://localhost:5173).
- Si l'API tourne → données live + simulateur fonctionnel.
- Sinon → données d'exemple (le simulateur affichera une erreur claire).

## Build de production

```bash
npm run build      # dist/
npm run preview
```

## Design

Deux tons sémantiques (ambre = coût, cyan = économie), fond bleu-encre,
typographie instrument (Space Grotesk / IBM Plex Mono). Graphes en SVG natif,
aucune librairie. Slicer par modèle réactif sur tout le tableau de bord.

## Stack

Vue 3 · Vite · FastAPI · SVG natif
