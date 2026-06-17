<script setup>
import { computed } from 'vue'
const props = defineProps({ entries: Array })

const rows = computed(() => {
  const m = {}
  for (const e of props.entries) {
    const k = e.task_type
    if (!m[k]) m[k] = { before: 0, after: 0 }
    m[k].before += e.tokens_before || 0
    m[k].after += e.tokens_in || 0
  }
  return Object.entries(m).map(([task, v]) => ({
    task, before: v.before, after: v.after,
    pct: v.before ? 1 - v.after / v.before : 0,
  }))
})
const maxB = computed(() => Math.max(...rows.value.map(r => r.before), 1))
</script>

<template>
  <section class="panel">
    <div class="head">
      <h2>Compression des tokens d'entrée</h2>
      <span class="legend">
        <i class="sw soft"></i>avant&nbsp;&nbsp;<i class="sw cool"></i>après
      </span>
    </div>
    <div class="bars">
      <div v-for="r in rows" :key="r.task" class="row">
        <div class="task">{{ r.task }}</div>
        <div class="track">
          <div class="before" :style="{ width: (r.before / maxB * 100) + '%' }"></div>
          <div class="after" :style="{ width: (r.after / maxB * 100) + '%' }"></div>
        </div>
        <div class="val">−{{ (r.pct * 100).toFixed(0) }}%</div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.panel{background:var(--panel); border:1px solid var(--line);
  border-radius:var(--r); padding:22px 26px}
.head{display:flex; justify-content:space-between; align-items:baseline;
  margin-bottom:18px}
h2{font-family:var(--display); font-weight:500; font-size:17px}
.legend{font-family:var(--mono); font-size:11px; color:var(--muted)}
.sw{width:9px; height:9px; border-radius:2px; display:inline-block;
  vertical-align:middle; margin-right:4px}
.sw.soft{background:var(--faint)} .sw.cool{background:var(--cool)}
.bars{display:flex; flex-direction:column; gap:13px}
.row{display:grid; grid-template-columns:96px 1fr 52px; gap:14px;
  align-items:center}
.task{font-family:var(--mono); font-size:12px; color:var(--muted)}
.track{position:relative; height:16px}
.before{position:absolute; top:0; left:0; height:7px; border-radius:2px;
  background:var(--faint); opacity:.5}
.after{position:absolute; bottom:0; left:0; height:7px; border-radius:2px;
  background:var(--cool); animation:grow .8s cubic-bezier(.2,.8,.2,1) both;
  transform-origin:left}
.val{font-family:var(--mono); font-size:12px; text-align:right; color:var(--cool)}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
</style>
