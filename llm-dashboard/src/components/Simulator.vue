<script setup>
import { ref, computed } from 'vue'
import { simulate } from '../api.js'
import { usd, pct, shortModel } from '../utils/format.js'

const profile = ref('entreprise')     // 'entreprise' | 'particulier'
const budget = ref(20)                // $/mois (entreprise)
const quota = ref(100000)             // tokens (particulier)
const prompt = ref('')
const file = ref(null)
const fileName = ref('')
const escalate = ref(true)

const loading = ref(false)
const error = ref('')
const result = ref(null)

function onFile(e) {
  const f = e.target.files[0]
  file.value = f || null
  fileName.value = f ? f.name : ''
}

async function run() {
  if (!prompt.value.trim()) { error.value = 'Saisis une requête.'; return }
  error.value = ''; loading.value = true; result.value = null
  try {
    result.value = await simulate({
      prompt: prompt.value, file: file.value,
      execute: true, escalate: escalate.value,
    })
  } catch (e) {
    error.value = "API injoignable. Lance le serveur : uvicorn api:app --port 8000"
  } finally {
    loading.value = false
  }
}

// --- Nuance budget / quota ---
const budgetView = computed(() => {
  const r = result.value
  if (!r) return null
  if (profile.value === 'entreprise') {
    const ce = r.cost_engine, cb = r.cost_baseline
    const reqEngine = ce > 0 ? Math.floor(budget.value / ce) : Infinity
    const reqBase = cb > 0 ? Math.floor(budget.value / cb) : Infinity
    return { mode: 'entreprise', reqEngine, reqBase, ce, cb }
  } else {
    const used = r.tokens_in + r.tokens_out
    const usedBase = r.tokens_before + r.tokens_out
    return {
      mode: 'particulier', used, usedBase,
      fracEngine: Math.min(used / quota.value, 1),
      fracBase: Math.min(usedBase / quota.value, 1),
    }
  }
})

function nf(v) { return v === Infinity ? '∞' : v.toLocaleString('fr-FR') }
</script>

<template>
  <div class="sim">
    <!-- Panneau de saisie -->
    <section class="panel input">
      <div class="head"><h2>Simulateur</h2>
        <span class="hint">le moteur décide et exécute en direct</span></div>

      <div class="field">
        <label>Profil</label>
        <div class="toggle">
          <button :class="{ on: profile==='entreprise' }"
            @click="profile='entreprise'">Entreprise · budget</button>
          <button :class="{ on: profile==='particulier' }"
            @click="profile='particulier'">Particulier · quota</button>
        </div>
      </div>

      <div class="field" v-if="profile==='entreprise'">
        <label>Budget mensuel ($)</label>
        <input type="number" v-model.number="budget" min="1" />
      </div>
      <div class="field" v-else>
        <label>Quota de tokens</label>
        <input type="number" v-model.number="quota" min="1000" step="1000" />
      </div>

      <div class="field">
        <label>Requête</label>
        <textarea v-model="prompt" rows="5"
          placeholder="Ex : Résume ce rapport et donne trois recommandations."></textarea>
      </div>

      <div class="field">
        <label>Fichier (optionnel · PDF, txt, md)</label>
        <label class="file-btn">
          <input type="file" accept=".pdf,.txt,.md" @change="onFile" hidden />
          {{ fileName || 'Choisir un fichier' }}
        </label>
      </div>

      <label class="check">
        <input type="checkbox" v-model="escalate" />
        Ré-routage par qualité (escalade auto)
      </label>

      <button class="run" :disabled="loading" @click="run">
        {{ loading ? 'Exécution en cours…' : 'Lancer la simulation' }}
      </button>
      <p v-if="error" class="err">{{ error }}</p>
    </section>

    <!-- Panneau de résultat -->
    <section class="panel out">
      <div v-if="loading" class="state">
        <div class="spin"></div>
        <p>Le moteur classe, route, exécute et juge la réponse…</p>
      </div>

      <div v-else-if="!result" class="state empty">
        <p>Le résultat de la simulation s'affichera ici :<br>
        modèle choisi, coût réel, qualité, et l'impact sur ton budget.</p>
      </div>

      <div v-else class="res">
        <!-- décision -->
        <div class="decision">
          <div class="dec-item"><span>Tâche</span><b>{{ result.task_type }}</b></div>
          <div class="dec-item"><span>Modèle</span>
            <b>{{ shortModel(result.model_final) }}</b>
            <em v-if="result.escalated" class="badge">escalade {{ result.attempts }}×</em>
          </div>
          <div class="dec-item"><span>Qualité</span>
            <b :class="result.quality>=7?'cool':'warm'">
              {{ result.quality != null ? result.quality + '/10' : '—' }}</b></div>
          <div class="dec-item"><span>Latence</span>
            <b>{{ result.latency_s != null ? result.latency_s + 's' : '—' }}</b></div>
        </div>

        <!-- coût -->
        <div class="cost">
          <div class="cost-box warm">
            <span>Sans optimisation</span><b>{{ usd(result.cost_baseline) }}</b></div>
          <div class="arrow">→</div>
          <div class="cost-box cool">
            <span>Avec le moteur</span><b>{{ usd(result.cost_engine) }}</b></div>
          <div class="cost-saved">−{{ pct(result.saved / (result.cost_baseline||1)) }}</div>
        </div>

        <!-- nuance budget / quota -->
        <div class="budget" v-if="budgetView">
          <template v-if="budgetView.mode==='entreprise'">
            <div class="b-title">Avec un budget de ${{ budget }}/mois</div>
            <div class="b-rows">
              <div class="b-row">
                <span>moteur</span>
                <div class="b-track"><div class="b-fill cool" style="width:100%"></div></div>
                <b class="cool">{{ nf(budgetView.reqEngine) }} req.</b>
              </div>
              <div class="b-row">
                <span>baseline</span>
                <div class="b-track"><div class="b-fill warm"
                  :style="{ width: budgetView.reqBase===Infinity ? '100%' :
                    Math.min(budgetView.reqBase / (budgetView.reqEngine===Infinity?budgetView.reqBase:budgetView.reqEngine) *100,100)+'%' }"></div></div>
                <b class="warm">{{ nf(budgetView.reqBase) }} req.</b>
              </div>
            </div>
            <p class="b-note">Nombre de requêtes de ce type que ton budget couvre.</p>
          </template>

          <template v-else>
            <div class="b-title">Sur un quota de {{ quota.toLocaleString('fr-FR') }} tokens</div>
            <div class="b-rows">
              <div class="b-row">
                <span>moteur</span>
                <div class="b-track"><div class="b-fill cool"
                  :style="{ width: budgetView.fracEngine*100+'%' }"></div></div>
                <b class="cool">{{ budgetView.used }} tk</b>
              </div>
              <div class="b-row">
                <span>baseline</span>
                <div class="b-track"><div class="b-fill warm"
                  :style="{ width: budgetView.fracBase*100+'%' }"></div></div>
                <b class="warm">{{ budgetView.usedBase }} tk</b>
              </div>
            </div>
            <p class="b-note">Part du quota consommée par cette requête.</p>
          </template>
        </div>

        <!-- réponse -->
        <details class="answer" open>
          <summary>Réponse du modèle</summary>
          <div class="ans-body">{{ result.response || '—' }}</div>
        </details>
      </div>
    </section>
  </div>
</template>

<style scoped>
.sim{display:grid; grid-template-columns:380px 1fr; gap:24px}
.panel{background:var(--panel); border:1px solid var(--line);
  border-radius:var(--r); padding:24px 26px}
.head{display:flex; justify-content:space-between; align-items:baseline;
  margin-bottom:20px; gap:12px}
h2{font-family:var(--display); font-weight:500; font-size:18px}
.hint{font-family:var(--mono); font-size:10px; color:var(--faint)}

.field{margin-bottom:16px}
label{display:block; font-family:var(--mono); font-size:10px; letter-spacing:.1em;
  text-transform:uppercase; color:var(--faint); margin-bottom:8px}
input[type=number], textarea{
  width:100%; background:var(--ink); border:1px solid var(--line);
  border-radius:var(--r); color:var(--text); padding:10px 12px;
  font-family:var(--body); font-size:14px; resize:vertical;
}
input:focus, textarea:focus{border-color:var(--cool); outline:none}
.toggle{display:flex; gap:6px}
.toggle button{flex:1; padding:9px; border:1px solid var(--line);
  border-radius:var(--r); color:var(--muted); font-size:12px;
  font-family:var(--mono)}
.toggle button.on{background:var(--cool-dim); border-color:var(--cool);
  color:var(--text)}
.file-btn{display:block; background:var(--ink); border:1px dashed var(--line);
  border-radius:var(--r); padding:10px 12px; color:var(--muted);
  font-family:var(--mono); font-size:12px; cursor:pointer; text-transform:none;
  letter-spacing:0}
.file-btn:hover{border-color:var(--muted)}
.check{display:flex; align-items:center; gap:8px; font-family:var(--body);
  font-size:13px; color:var(--muted); text-transform:none; letter-spacing:0;
  margin-bottom:18px; cursor:pointer}
.check input{accent-color:var(--cool)}
.run{width:100%; padding:13px; background:var(--cool); color:var(--ink);
  border-radius:var(--r); font-family:var(--display); font-weight:500;
  font-size:14px; transition:opacity .15s}
.run:hover{opacity:.9} .run:disabled{opacity:.5; cursor:wait}
.err{color:var(--bad); font-size:12px; margin-top:10px;
  font-family:var(--mono)}

/* résultat */
.out{min-height:420px}
.state{height:100%; display:flex; flex-direction:column; align-items:center;
  justify-content:center; gap:16px; color:var(--muted); text-align:center;
  min-height:380px}
.state.empty p{max-width:300px; line-height:1.7; font-size:14px}
.spin{width:34px; height:34px; border:3px solid var(--line);
  border-top-color:var(--cool); border-radius:50%; animation:spin 1s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

.decision{display:grid; grid-template-columns:repeat(2,1fr); gap:1px;
  background:var(--line); border:1px solid var(--line); border-radius:var(--r);
  overflow:hidden; margin-bottom:20px}
.dec-item{background:var(--panel); padding:14px 16px; display:flex;
  flex-direction:column; gap:5px}
.dec-item span{font-family:var(--mono); font-size:10px; letter-spacing:.1em;
  text-transform:uppercase; color:var(--faint)}
.dec-item b{font-family:var(--display); font-weight:500; font-size:18px}
.dec-item .cool{color:var(--cool)} .dec-item .warm{color:var(--warm)}
.badge{font-family:var(--mono); font-size:10px; color:var(--warm);
  font-style:normal; background:var(--warm-dim); padding:2px 7px;
  border-radius:99px; width:fit-content; margin-top:2px}

.cost{display:flex; align-items:center; gap:14px; margin-bottom:20px;
  padding:18px; background:var(--ink); border-radius:var(--r); flex-wrap:wrap}
.cost-box{display:flex; flex-direction:column; gap:4px; flex:1; min-width:110px}
.cost-box span{font-family:var(--mono); font-size:10px; letter-spacing:.08em;
  text-transform:uppercase; color:var(--faint)}
.cost-box b{font-family:var(--display); font-size:22px; font-weight:500}
.cost-box.warm b{color:var(--warm)} .cost-box.cool b{color:var(--cool)}
.arrow{color:var(--faint); font-size:18px}
.cost-saved{font-family:var(--display); font-weight:700; font-size:24px;
  color:var(--cool); margin-left:auto}

.budget{margin-bottom:20px}
.b-title{font-family:var(--mono); font-size:12px; color:var(--text);
  margin-bottom:12px}
.b-rows{display:flex; flex-direction:column; gap:9px}
.b-row{display:grid; grid-template-columns:64px 1fr 84px; gap:12px;
  align-items:center}
.b-row span{font-family:var(--mono); font-size:11px; color:var(--muted)}
.b-track{height:12px; background:#0C1623; border-radius:2px; overflow:hidden}
.b-fill{height:100%; border-radius:2px; transition:width .5s}
.b-fill.cool{background:var(--cool)} .b-fill.warm{background:var(--warm); opacity:.6}
.b-row b{font-family:var(--mono); font-size:12px; text-align:right}
.b-row .cool{color:var(--cool)} .b-row .warm{color:var(--warm)}
.b-note{font-size:11px; color:var(--faint); margin-top:10px}

.answer{border-top:1px solid var(--line); padding-top:16px}
summary{font-family:var(--mono); font-size:11px; letter-spacing:.1em;
  text-transform:uppercase; color:var(--faint); cursor:pointer; margin-bottom:12px}
.ans-body{font-size:14px; line-height:1.7; color:var(--text);
  white-space:pre-wrap; max-height:280px; overflow:auto}
@media (max-width:920px){.sim{grid-template-columns:1fr}}
</style>
