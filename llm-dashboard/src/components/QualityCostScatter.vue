<script setup>
import { computed } from 'vue'
import { modelColor, shortModel } from '../utils/format.js'
const props = defineProps({ entries: Array })

const W = 420, H = 250, P = 38
const maxCost = computed(() =>
  Math.max(...props.entries.map(e => e.cost_baseline || 0), 0.001))

function x(c) { return P + (c / maxCost.value) * (W - P - 14) }
function y(q) { return (H - P) - (q / 10) * (H - P - 14) }

const pts = computed(() => props.entries
  .filter(e => e.quality != null)
  .map(e => ({
    cx: x(e.cost_baseline || 0), cy: y(e.quality),
    color: modelColor(e.model_final), model: e.model_final,
    q: e.quality, cost: e.cost_baseline,
  })))

const models = computed(() => [...new Set(props.entries.map(e => e.model_final))])
const thrY = y(7)
</script>

<template>
  <section class="panel">
    <div class="head">
      <h2>Qualité vs coût évité</h2>
      <span class="hint">chaque point = une requête</span>
    </div>
    <svg :viewBox="`0 0 ${W} ${H}`" class="chart">
      <!-- grille -->
      <line v-for="g in [0,2.5,5,7.5,10]" :key="'h'+g"
        :x1="P" :x2="W-14" :y1="y(g)" :y2="y(g)"
        stroke="var(--line)" stroke-width="1" opacity=".5" />
      <text v-for="g in [0,5,10]" :key="'t'+g"
        :x="P-8" :y="y(g)+4" text-anchor="end"
        fill="var(--faint)" font-size="10" font-family="var(--mono)">{{ g }}</text>
      <!-- seuil qualite -->
      <line :x1="P" :x2="W-14" :y1="thrY" :y2="thrY"
        stroke="var(--cool)" stroke-width="1" stroke-dasharray="4 4" opacity=".6" />
      <text :x="W-16" :y="thrY-6" text-anchor="end"
        fill="var(--cool)" font-size="9" font-family="var(--mono)">seuil 7</text>
      <!-- points -->
      <circle v-for="(p,i) in pts" :key="i" :cx="p.cx" :cy="p.cy" r="6"
        :fill="p.color" fill-opacity=".85" stroke="var(--ink)" stroke-width="1.5">
        <title>{{ shortModel(p.model) }} — qualité {{ p.q }}/10</title>
      </circle>
      <!-- axes labels -->
      <text :x="P" :y="H-8" fill="var(--faint)" font-size="9"
        font-family="var(--mono)">$0</text>
      <text :x="W-14" :y="H-8" text-anchor="end" fill="var(--faint)" font-size="9"
        font-family="var(--mono)">coût évité →</text>
      <text :x="12" :y="P-14" fill="var(--faint)" font-size="9"
        font-family="var(--mono)" transform="rotate(0)">qualité ↑</text>
    </svg>
    <div class="leg">
      <span v-for="m in models" :key="m" class="li">
        <i :style="{ background: modelColor(m) }"></i>{{ shortModel(m) }}
      </span>
    </div>
  </section>
</template>

<style scoped>
.panel{background:var(--panel); border:1px solid var(--line);
  border-radius:var(--r); padding:22px 24px; height:100%}
.head{display:flex; justify-content:space-between; align-items:baseline;
  margin-bottom:14px}
h2{font-family:var(--display); font-weight:500; font-size:17px}
.hint{font-family:var(--mono); font-size:10px; color:var(--faint)}
.chart{width:100%; height:auto; display:block}
.leg{display:flex; gap:16px; flex-wrap:wrap; margin-top:12px;
  font-family:var(--mono); font-size:11px; color:var(--muted)}
.li{display:inline-flex; align-items:center; gap:6px}
.li i{width:8px; height:8px; border-radius:2px}
</style>
