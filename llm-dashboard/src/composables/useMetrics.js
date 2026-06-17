import { ref, computed, onMounted } from 'vue'
import sample from '../data/sample.js'
import { fetchMetrics } from '../api.js'

export function useMetrics() {
  const entries = ref(sample)
  const source = ref('exemple')

  onMounted(async () => {
    // 1) API live
    try {
      const { entries: e } = await fetchMetrics()
      if (Array.isArray(e) && e.length) {
        entries.value = e; source.value = 'API · live'; return
      }
    } catch (_) { /* suite */ }
    // 2) fichier statique
    try {
      const res = await fetch('./metrics.json', { cache: 'no-store' })
      if (res.ok) {
        const d = await res.json()
        if (Array.isArray(d) && d.length) {
          entries.value = d; source.value = 'metrics.json'
        }
      }
    } catch (_) { /* garde l'exemple */ }
  })

  const byModel = computed(() => {
    const m = {}
    for (const x of entries.value) {
      const k = x.model_final || '?'
      m[k] = (m[k] || 0) + 1
    }
    return Object.entries(m).map(([name, count]) => ({ name, count }))
  })

  return { entries, source, byModel }
}
