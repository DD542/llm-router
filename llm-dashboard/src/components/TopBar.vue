<script setup>
import { shortModel, modelColor } from '../utils/format.js'
defineProps({ byModel: Array, active: String, date: String })
const emit = defineEmits(['slice'])
</script>

<template>
  <header class="top">
    <div class="top-l">
      <div class="eyebrow">Moteur d'optimisation LLM</div>
      <h1>Performance &amp; économies</h1>
    </div>
    <div class="top-r">
      <div class="slicer">
        <span class="slicer-lab">Modèle</span>
        <button class="chip" :class="{ on: !active }" @click="emit('slice', null)">
          Tous
        </button>
        <button
          v-for="m in byModel" :key="m.name"
          class="chip" :class="{ on: active === m.name }"
          @click="emit('slice', active === m.name ? null : m.name)">
          <span class="cdot" :style="{ background: modelColor(m.name) }"></span>
          {{ shortModel(m.name) }}
        </button>
      </div>
      <div class="date">{{ date }}</div>
    </div>
  </header>
</template>

<style scoped>
.top{
  display:flex; justify-content:space-between; align-items:flex-start;
  gap:24px; padding:30px 38px 24px; border-bottom:1px solid var(--line);
  flex-wrap:wrap;
}
.eyebrow{font-family:var(--mono); font-size:11px; letter-spacing:.2em;
  text-transform:uppercase; color:var(--faint); margin-bottom:9px}
h1{font-family:var(--display); font-weight:500; font-size:25px;
  letter-spacing:-.02em}
.top-r{display:flex; flex-direction:column; align-items:flex-end; gap:12px}
.slicer{display:flex; align-items:center; gap:7px; flex-wrap:wrap;
  justify-content:flex-end}
.slicer-lab{font-family:var(--mono); font-size:10px; letter-spacing:.14em;
  text-transform:uppercase; color:var(--faint); margin-right:3px}
.chip{
  display:inline-flex; align-items:center; gap:7px; padding:6px 12px;
  border:1px solid var(--line); border-radius:99px; font-size:12px;
  color:var(--muted); font-family:var(--mono);
  transition:border-color .15s,color .15s,background .15s;
}
.chip:hover{color:var(--text); border-color:var(--muted)}
.chip.on{background:var(--cool-dim); border-color:var(--cool); color:var(--text)}
.cdot{width:8px; height:8px; border-radius:2px}
.date{font-family:var(--mono); font-size:11px; color:var(--faint)}

@media (max-width:640px){
  .top{padding:20px 18px 16px}
  h1{font-size:21px}
  .top-r{align-items:flex-start; width:100%}
  .slicer{justify-content:flex-start}
}
</style>