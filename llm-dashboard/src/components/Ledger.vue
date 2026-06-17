<script setup>
import { usd, shortModel } from '../utils/format.js'
defineProps({ entries: Array, compact: Boolean })
function qClass(q) {
  if (q == null) return ''
  return q >= 7 ? 'q-ok' : q >= 4 ? 'q-mid' : 'q-low'
}
</script>

<template>
  <section class="panel" :class="{ compact }">
    <div class="head" v-if="!compact"><h2>Journal des requêtes</h2></div>
    <div class="scroll">
      <table>
        <thead>
          <tr>
            <th>Tâche</th>
            <th>Modèle final</th>
            <th class="num">Qualité</th>
            <th class="num">Tokens</th>
            <th class="num">Sortie</th>
            <th class="num">Esc.</th>
            <th class="num">Fichier</th>
            <th class="num">Baseline</th>
            <th class="num">Moteur</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(e, i) in entries" :key="i">
            <td class="task">{{ e.task_type }}</td>
            <td class="model">{{ shortModel(e.model_final) }}</td>
            <td class="num" :class="qClass(e.quality)">
              {{ e.quality != null ? e.quality.toFixed(0) : '—' }}
            </td>
            <td class="num soft">{{ e.tokens_before }}→{{ e.tokens_in }}</td>
            <td class="num soft">{{ e.tokens_out }}</td>
            <td class="num">
              <span v-if="e.escalated" class="esc">{{ e.attempts }}×</span>
              <span v-else class="soft">—</span>
            </td>
            <td class="num soft">{{ e.file_kind || '—' }}</td>
            <td class="num warm">{{ usd(e.cost_baseline) }}</td>
            <td class="num cool">{{ usd(e.cost_engine) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="!entries.length" class="empty">
        Aucune requête pour ce filtre.
      </div>
    </div>
  </section>
</template>

<style scoped>
.panel{background:var(--panel); border:1px solid var(--line);
  border-radius:var(--r); padding:20px 10px}
.panel.compact{padding:14px 6px; height:100%}
.head{padding:4px 16px 16px}
h2{font-family:var(--display); font-weight:500; font-size:18px}
.scroll{overflow-x:auto}
table{width:100%; border-collapse:collapse; font-size:13px}
th{font-family:var(--mono); font-size:10px; letter-spacing:.1em;
  text-transform:uppercase; color:var(--faint); text-align:left;
  padding:0 14px 12px; border-bottom:1px solid var(--line); font-weight:500;
  white-space:nowrap}
th.num,td.num{text-align:right; font-family:var(--mono)}
td{padding:13px 14px; border-bottom:1px solid var(--line-soft);
  color:var(--muted); white-space:nowrap}
tbody tr:last-child td{border-bottom:none}
tbody tr{transition:background .12s}
tbody tr:hover{background:var(--panel-2)}
.task{color:var(--text)}
.model{font-family:var(--mono); font-size:12px; color:var(--text)}
.soft{color:var(--faint)}
.q-ok{color:var(--cool)} .q-mid{color:var(--warm)} .q-low{color:var(--bad)}
.warm{color:var(--warm)} .cool{color:var(--cool)}
.esc{color:var(--warm)}
.empty{padding:30px 16px; text-align:center; color:var(--faint);
  font-family:var(--mono); font-size:12px}
</style>
