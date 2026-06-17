<script setup>
import { computed } from 'vue'
import { modelColor, shortModel } from '../utils/format.js'
const props = defineProps({ entries: Array })

const rows = computed(() => {
  const m = {}
  for (const e of props.entries) {
    if (e.latency_s == null) continue
    const k = e.model_final
    if (!m[k]) m[k] = { sum: 0, n: 0 }
    m[k].sum += e.latency_s; m[k].n++
  }
  const arr = Object.entries(m).map(([name, v]) => ({
    name, avg: v.sum / v.n,
  }))
  arr.sort((a, b) => b.avg - a.avg)
  return arr
})
const maxAvg = computed(() => Math.max(...rows.value.map(r => r.avg), 1))
</script>

<template>
  <section class="panel">
    <div class="head"><h2>Latence moyenne par modèle</h2></div>
    <div class="bars">
      <div v-for="r in rows" :key="r.name" class="row">
        <div class="nm">{{ shortModel(r.name) }}</div>
        <div class="track">
          <div class="fill" :style="{
            width: (r.avg / maxAvg * 100) + '%',
            background: modelColor(r.name) }"></div>
        </div>
        <div class="val">{{ r.avg.toFixed(1) }}s</div>
      </div>
      <div v-if="!rows.length" class="empty">Aucune latence mesurée.</div>
    </div>
  </section>
</template>

<style scoped>
.panel{background:var(--panel); border:1px solid var(--line);
  border-radius:var(--r); padding:22px 24px; height:100%}
.head{margin-bottom:18px}
h2{font-family:var(--display); font-weight:500; font-size:17px}
.bars{display:flex; flex-direction:column; gap:14px}
.row{display:grid; grid-template-columns:120px 1fr 52px; gap:14px;
  align-items:center}
.nm{font-family:var(--mono); font-size:12px; color:var(--muted)}
.track{height:14px; background:#0C1623; border-radius:2px; overflow:hidden}
.fill{height:100%; border-radius:2px;
  animation:grow .8s cubic-bezier(.2,.8,.2,1) both; transform-origin:left}
.val{font-family:var(--mono); font-size:12px; text-align:right; color:var(--text)}
.empty{font-family:var(--mono); font-size:12px; color:var(--faint)}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
</style>
