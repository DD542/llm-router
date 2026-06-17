<script setup>
import { computed } from 'vue'
import { usd, pct } from '../utils/format.js'
const props = defineProps({ totals: Object })
const tiles = computed(() => {
  const t = props.totals
  return [
    { k: 'Économie totale', v: usd(t.saved), s: 'vs tout-frontier', accent: true },
    { k: 'Réduction du coût', v: pct(t.savedPct), s: 'sur le lot mesuré', accent: true },
    { k: 'Qualité moyenne', v: t.avgQuality != null ? t.avgQuality.toFixed(1) : '—', s: 'jugée par modèle 70B' },
    { k: 'Requêtes', v: String(t.requests), s: 'mesurées' },
    { k: 'Escalades', v: String(t.escalated), s: 'réacheminements' },
    { k: 'Latence moy.', v: t.avgLatency != null ? t.avgLatency.toFixed(0) + 's' : '—', s: 'appels réels' },
  ]
})
</script>

<template>
  <div class="kpis">
    <div v-for="(t, i) in tiles" :key="i" class="kpi">
      <div class="kpi-k">{{ t.k }}</div>
      <div class="kpi-v" :class="{ accent: t.accent }">{{ t.v }}</div>
      <div class="kpi-s">{{ t.s }}</div>
    </div>
  </div>
</template>

<style scoped>
.kpis{
  display:grid; grid-template-columns:repeat(6,1fr);
  border:1px solid var(--line); border-radius:var(--r); overflow:hidden;
  background:var(--panel);
}
.kpi{padding:20px 18px; border-right:1px solid var(--line)}
.kpi:last-child{border-right:none}
.kpi-k{font-family:var(--mono); font-size:10px; letter-spacing:.12em;
  text-transform:uppercase; color:var(--faint); margin-bottom:13px}
.kpi-v{font-family:var(--display); font-weight:500; font-size:29px;
  letter-spacing:-.02em}
.kpi-v.accent{color:var(--cool)}
.kpi-s{font-size:11px; color:var(--muted); margin-top:6px}
@media (max-width:980px){.kpis{grid-template-columns:repeat(3,1fr)}
  .kpi{border-bottom:1px solid var(--line)}}
@media (max-width:560px){.kpis{grid-template-columns:repeat(2,1fr)}}
</style>
