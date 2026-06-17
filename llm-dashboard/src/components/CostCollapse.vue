<script setup>
import { computed, ref } from 'vue'
import { usd, pct } from '../utils/format.js'
const props = defineProps({ entries: Array })
const hover = ref(null)
const maxBase = computed(() =>
  Math.max(...props.entries.map(e => e.cost_baseline || 0), 1e-9))
const rows = computed(() => props.entries.map((e, i) => {
  const b = e.cost_baseline || 0
  const g = e.cost_engine || 0
  return {
    i, task: e.task_type, quality: e.quality,
    baseW: (b / maxBase.value) * 100,
    engW: Math.max((g / maxBase.value) * 100, 0.5),
    saved: b ? 1 - g / b : 0,
    base: b, eng: g,
  }
}))
</script>

<template>
  <section class="panel">
    <div class="head">
      <h2>Effondrement des coûts</h2>
      <div class="legend">
        <span><i class="sw warm"></i>baseline frontier</span>
        <span><i class="sw cool"></i>coût réel</span>
      </div>
    </div>

    <div class="bars">
      <div
        v-for="r in rows" :key="r.i" class="row"
        @mouseenter="hover = r.i" @mouseleave="hover = null">
        <div class="task">{{ r.task }}</div>
        <div class="track">
          <div class="base" :style="{ width: r.baseW + '%' }"></div>
          <div class="eng" :style="{ width: r.engW + '%' }"></div>
          <div v-if="hover === r.i" class="tip">
            baseline {{ usd(r.base) }} · moteur {{ usd(r.eng) }}
          </div>
        </div>
        <div class="meta">
          <span class="sv">−{{ pct(r.saved) }}</span>
          <span class="q">{{ r.quality != null ? r.quality.toFixed(0) + '/10' : '—' }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.panel{background:var(--panel); border:1px solid var(--line);
  border-radius:var(--r); padding:24px 26px}
.head{display:flex; justify-content:space-between; align-items:baseline;
  margin-bottom:20px; gap:16px; flex-wrap:wrap}
h2{font-family:var(--display); font-weight:500; font-size:18px}
.legend{display:flex; gap:18px; font-family:var(--mono); font-size:11px;
  color:var(--muted)}
.legend span{display:inline-flex; align-items:center; gap:6px}
.sw{width:9px; height:9px; border-radius:2px; display:inline-block}
.sw.warm{background:var(--warm)} .sw.cool{background:var(--cool)}
.bars{display:flex; flex-direction:column}
.row{display:grid; grid-template-columns:92px 1fr 96px; gap:16px;
  align-items:center; padding:8px 0}
.task{font-family:var(--mono); font-size:12px; color:var(--muted)}
.track{position:relative; height:18px; background:#101A26;
  border-radius:7px; overflow:visible}
.base{position:absolute; left:0; top:0; height:100%; border-radius:7px;
  background:linear-gradient(90deg,var(--warm),#566576); opacity:.5;
  transform-origin:left; animation:grow .8s cubic-bezier(.2,.8,.2,1) both}
.eng{position:absolute; left:0; top:0; height:100%; border-radius:7px;
  background:var(--accent); box-shadow:0 0 12px rgba(238,138,63,.5);
  transform-origin:left; animation:grow .8s cubic-bezier(.2,.8,.2,1) .12s both}
.tip{position:absolute; bottom:22px; left:0; white-space:nowrap;
  background:var(--raise); border:1px solid var(--line); border-radius:var(--r);
  padding:5px 9px; font-family:var(--mono); font-size:11px; color:var(--text);
  z-index:5}
.meta{font-family:var(--mono); font-size:12px; text-align:right;
  display:flex; flex-direction:column; gap:1px}
.meta .sv{color:var(--cool); font-weight:600}
.meta .q{color:var(--faint); font-size:11px}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
</style>
