<script setup>
import { ref, computed } from 'vue'
import { useMetrics } from './composables/useMetrics.js'
import AppSidebar from './components/AppSidebar.vue'
import TopBar from './components/TopBar.vue'
import KpiStrip from './components/KpiStrip.vue'
import CostCollapse from './components/CostCollapse.vue'
import ModelDonut from './components/ModelDonut.vue'
import Ledger from './components/Ledger.vue'
import QualityCostScatter from './components/QualityCostScatter.vue'
import LatencyByModel from './components/LatencyByModel.vue'
import TokenBars from './components/TokenBars.vue'
import Simulator from './components/Simulator.vue'

const { entries, source, byModel } = useMetrics()
const view = ref('overview')
const activeModel = ref(null)

const filtered = computed(() =>
  activeModel.value
    ? entries.value.filter(e => e.model_final === activeModel.value)
    : entries.value
)

const totals = computed(() => {
  const e = filtered.value
  const sum = (k) => e.reduce((a, x) => a + (x[k] || 0), 0)
  const base = sum('cost_baseline'), eng = sum('cost_engine')
  const tb = sum('tokens_before'), ti = sum('tokens_in')
  const q = e.filter(x => x.quality != null).map(x => x.quality)
  const l = e.filter(x => x.latency_s != null).map(x => x.latency_s)
  return {
    requests: e.length, escalated: e.filter(x => x.escalated).length,
    costBaseline: base, costEngine: eng, saved: base - eng,
    savedPct: base ? (base - eng) / base : 0,
    tokensSavedPct: tb ? 1 - ti / tb : 0,
    avgQuality: q.length ? q.reduce((a, b) => a + b, 0) / q.length : null,
    avgLatency: l.length ? l.reduce((a, b) => a + b, 0) / l.length : null,
  }
})

const today = new Date().toLocaleDateString('fr-FR',
  { day: '2-digit', month: 'short', year: 'numeric' })
</script>

<template>
  <div class="shell">
    <AppSidebar :view="view" :source="source" @nav="view = $event" />
    <main class="main">
      <TopBar :byModel="byModel" :active="activeModel" :date="today"
        @slice="activeModel = $event" />

      <div class="canvas">
        <!-- VUE D'ENSEMBLE -->
        <template v-if="view === 'overview'">
          <KpiStrip :totals="totals" />
          <CostCollapse :entries="filtered" />
          <div class="grid2">
            <ModelDonut :byModel="byModel" :active="activeModel"
              @slice="activeModel = $event" />
            <Ledger :entries="filtered" compact />
          </div>
          <div class="sec">Analyse</div>
          <div class="grid2">
            <QualityCostScatter :entries="filtered" />
            <LatencyByModel :entries="filtered" />
          </div>
          <TokenBars :entries="filtered" />
        </template>

        <!-- SIMULATEUR -->
        <template v-else-if="view === 'simulator'">
          <Simulator />
        </template>

        <!-- JOURNAL -->
        <template v-else>
          <KpiStrip :totals="totals" />
          <Ledger :entries="filtered" />
        </template>
      </div>
    </main>
  </div>
</template>

<style scoped>
.shell{display:flex; min-height:100vh}
.main{flex:1; min-width:0; display:flex; flex-direction:column}
.canvas{padding:26px 38px 60px; display:flex; flex-direction:column; gap:24px}
.grid2{display:grid; grid-template-columns:1fr 1.45fr; gap:24px}
.sec{font-family:var(--mono); font-size:11px; letter-spacing:.2em;
  text-transform:uppercase; color:var(--faint); margin-top:8px;
  padding-bottom:2px; border-bottom:1px solid var(--line)}
@media (max-width:1040px){.grid2{grid-template-columns:1fr}}
@media (max-width:720px){.shell{flex-direction:column}
  .canvas{padding:20px 18px 50px}}
</style>
