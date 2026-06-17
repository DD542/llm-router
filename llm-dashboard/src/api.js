// Point d'acces a l'API du moteur (FastAPI). Change le port si besoin.
export const API_BASE = 'http://localhost:8000'

export async function fetchMetrics() {
  const res = await fetch(`${API_BASE}/api/metrics`, { cache: 'no-store' })
  if (!res.ok) throw new Error('API ' + res.status)
  return res.json() // { entries, stats }
}

export async function simulate({ prompt, file, execute, escalate }) {
  const fd = new FormData()
  fd.append('prompt', prompt)
  fd.append('execute', execute ? 'true' : 'false')
  fd.append('escalate', escalate ? 'true' : 'false')
  if (file) fd.append('file', file)
  const res = await fetch(`${API_BASE}/api/simulate`, { method: 'POST', body: fd })
  if (!res.ok) throw new Error('API ' + res.status)
  return res.json()
}
