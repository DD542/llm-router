<script setup>
import { computed } from 'vue'
import { shortModel, modelColor } from '../utils/format.js'
const props = defineProps({ byModel: Array, active: String })
const emit = defineEmits(['slice'])

const SIZE = 180, STROKE = 24
const R = (SIZE - STROKE) / 2
const C = 2 * Math.PI * R
const total = computed(() => props.byModel.reduce((a, m) => a + m.count, 0) || 1)

const segs = computed(() => {
  let off = 0
  return props.byModel.map(m => {
    const frac = m.count / total.value
    const dash = frac * C
    const s = {
      name: m.name, count: m.count, color: modelColor(m.name),
      dash, gap: C - dash, offset: -off,
      dim: props.active && props.active !== m.name,
    }
    off += dash
    return s
  })
})
</script>

<template>
  <section class="panel">
    <div class="head"><h2>Répartition par modèle</h2></div>
    <div class="body">
      <div class="chart">
        <svg :viewBox="`0 0 ${SIZE} ${SIZE}`" :width="SIZE" :height="SIZE">
          <circle :cx="SIZE/2" :cy="SIZE/2" :r="R" fill="none"
            stroke="var(--line)" :stroke-width="STROKE" opacity=".4" />
          <circle v-for="s in segs" :key="s.name"
            :cx="SIZE/2" :cy="SIZE/2" :r="R" fill="none"
            :stroke="s.color" :stroke-width="STROKE"
            :stroke-dasharray="`${s.dash} ${s.gap}`"
            :stroke-dashoffset="s.offset"
            :transform="`rotate(-90 ${SIZE/2} ${SIZE/2})`"
            :style="{ opacity: s.dim ? 0.22 : 1, transition:'opacity .2s' }" />
        </svg>
        <div class="center">
          <div class="c-num">{{ total }}</div>
          <div class="c-lab">requêtes</div>
        </div>
      </div>
      <div class="legend">
        <button v-for="s in segs" :key="s.name" class="leg"
          :class="{ dim: s.dim }"
          @click="emit('slice', active === s.name ? null : s.name)">
          <span class="dot" :style="{ background: s.color }"></span>
          <span class="nm">{{ shortModel(s.name) }}</span>
          <span class="vl">{{ s.count }}</span>
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.panel{background:var(--panel); border:1px solid var(--line);
  border-radius:var(--r); padding:24px 26px; height:100%}
.head{margin-bottom:18px}
h2{font-family:var(--display); font-weight:500; font-size:18px}
.body{display:flex; align-items:center; gap:26px; flex-wrap:wrap}
.chart{position:relative; flex:none}
.center{position:absolute; inset:0; display:grid; place-content:center;
  text-align:center}
.c-num{font-family:var(--display); font-weight:600; font-size:30px}
.c-lab{font-family:var(--mono); font-size:10px; letter-spacing:.14em;
  text-transform:uppercase; color:var(--faint)}
.legend{display:flex; flex-direction:column; gap:3px; flex:1; min-width:160px}
.leg{display:flex; align-items:center; gap:10px; padding:7px 8px;
  border-radius:var(--r); font-family:var(--mono); font-size:12px;
  transition:background .15s,opacity .15s; text-align:left}
.leg:hover{background:var(--panel-2)}
.leg.dim{opacity:.4}
.dot{width:9px; height:9px; border-radius:2px; flex:none}
.nm{flex:1; color:var(--muted)}
.vl{color:var(--text)}
</style>
