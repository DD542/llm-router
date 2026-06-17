<script setup>
defineProps({ view: String, source: String })
const emit = defineEmits(['nav'])
const items = [
  { id: 'overview', label: "Vue d'ensemble" },
  { id: 'simulator', label: 'Simulateur' },
  { id: 'ledger', label: 'Journal des requêtes' },
]
</script>

<template>
  <aside class="side">
    <div class="brand">
      <div class="mark">LR</div>
      <div class="brand-txt">
        <div class="brand-name">llm-router</div>
        <div class="brand-sub">benchmark</div>
      </div>
    </div>
    <nav class="nav">
      <button v-for="it in items" :key="it.id"
        class="nav-item" :class="{ active: view === it.id }"
        @click="emit('nav', it.id)">
        <span class="tick"></span>{{ it.label }}
      </button>
    </nav>
    <div class="side-foot">
      <div class="foot-k">Source</div>
      <div class="foot-v">{{ source }}</div>
    </div>
  </aside>
</template>

<style scoped>
.side{width:228px; flex:none; background:var(--panel);
  border-right:1px solid var(--line); padding:24px 18px;
  display:flex; flex-direction:column; min-height:100vh}
.brand{display:flex; align-items:center; gap:12px; padding:4px 6px 28px}
.mark{width:38px; height:38px; border-radius:var(--r);
  background:linear-gradient(135deg,var(--cool),#2f8d80);
  color:var(--ink); font-family:var(--display); font-weight:700;
  font-size:15px; display:grid; place-items:center; letter-spacing:-.02em}
.brand-name{font-family:var(--display); font-weight:500; font-size:16px}
.brand-sub{font-family:var(--mono); font-size:10px; color:var(--faint);
  letter-spacing:.18em; text-transform:uppercase}
.nav{display:flex; flex-direction:column; gap:2px; flex:1}
.nav-item{display:flex; align-items:center; gap:11px; padding:11px 12px;
  border-radius:var(--r); color:var(--muted); font-size:13.5px;
  text-align:left; transition:background .15s,color .15s}
.nav-item:hover{background:var(--panel-2); color:var(--text)}
.nav-item.active{background:var(--raise); color:var(--text)}
.tick{width:2px; height:14px; border-radius:2px; background:transparent}
.nav-item.active .tick{background:var(--cool)}
.side-foot{padding:14px 12px 4px; border-top:1px solid var(--line)}
.foot-k{font-family:var(--mono); font-size:10px; letter-spacing:.14em;
  text-transform:uppercase; color:var(--faint); margin-bottom:5px}
.foot-v{font-family:var(--mono); font-size:11px; color:var(--muted);
  word-break:break-all}
</style>
