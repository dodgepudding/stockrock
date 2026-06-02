<script setup>
import { ref, computed, onMounted, watch } from "vue";
import Watchlist from "./Watchlist.vue";

const tab = ref("screen");
const watchlistRef = ref(null);
const watchlistCodes = ref(new Set());

const strategies = ref([]);
const selectedId = ref("");
const strategyParams = ref({});
const provider = ref("akshare");
const lookbackDays = ref(120);
const excludeSt = ref(true);
const excludeBj = ref(true);
const includeKcb = ref(true);
const includeCyb = ref(true);
const maxSymbols = ref("");

const jobId = ref(null);
const status = ref("");
const total = ref(0);
const processed = ref(0);
const hits = ref([]);
const error = ref("");
const loading = ref(false);
const watchMsg = ref("");
const selectedHits = ref(new Set());

const selectedStrategy = computed(() =>
  strategies.value.find((s) => s.id === selectedId.value)
);

const editableParams = computed(
  () => selectedStrategy.value?.params || []
);

function resetStrategyParams() {
  const next = {};
  for (const p of editableParams.value) {
    next[p.key] = p.default;
  }
  strategyParams.value = next;
}

watch(selectedId, resetStrategyParams);

const progress = computed(() =>
  total.value ? Math.round((processed.value / total.value) * 100) : 0
);

const allHitsSelected = computed(
  () =>
    hits.value.length > 0 && selectedHits.value.size === hits.value.length
);

const someHitsSelected = computed(() => selectedHits.value.size > 0);

watch(hits, () => {
  selectedHits.value = new Set();
});

function toggleHit(code) {
  const next = new Set(selectedHits.value);
  if (next.has(code)) next.delete(code);
  else next.add(code);
  selectedHits.value = next;
}

function toggleSelectAllHits() {
  if (allHitsSelected.value) {
    selectedHits.value = new Set();
  } else {
    selectedHits.value = new Set(hits.value.map((h) => h.code));
  }
}

async function loadWatchlistCodes() {
  try {
    const res = await fetch("/api/watchlist");
    const data = await res.json();
    watchlistCodes.value = new Set((data.items || []).map((x) => x.code));
  } catch {
    watchlistCodes.value = new Set();
  }
}

async function addToWatchlist(h) {
  watchMsg.value = "";
  try {
    const res = await fetch("/api/watchlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        code: String(h.code),
        name: h.name || "",
        source_strategy: selectedStrategy.value?.name || selectedId.value || "",
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();
    const code = data.item?.code || h.code;
    watchlistCodes.value = new Set(watchlistCodes.value).add(code);
    watchMsg.value = `已加入自选：${code} ${h.name || ""}`.trim();
  } catch (e) {
    watchMsg.value = e.message;
  }
}

async function addSelectedToWatchlist() {
  const list = hits.value.filter((h) => selectedHits.value.has(h.code));
  if (!list.length) {
    watchMsg.value = "请先勾选要加入的股票";
    return;
  }
  watchMsg.value = "";
  try {
    const res = await fetch("/api/watchlist/batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        items: list.map((h) => ({
          code: String(h.code),
          name: h.name || "",
          source_strategy: selectedStrategy.value?.name || selectedId.value || "",
        })),
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || res.statusText);
    }
    const next = new Set(watchlistCodes.value);
    list.forEach((h) => next.add(h.code));
    watchlistCodes.value = next;
    watchMsg.value = `已加入 ${list.length} 只到自选`;
    selectedHits.value = new Set();
  } catch (e) {
    watchMsg.value = e.message;
  }
}

async function addAllHits() {
  if (!hits.value.length) return;
  watchMsg.value = "";
  try {
    const res = await fetch("/api/watchlist/batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        items: hits.value.map((h) => ({
          code: h.code,
          name: h.name || "",
          source_strategy: selectedStrategy.value?.name || selectedId.value || "",
        })),
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || res.statusText);
    }
    hits.value.forEach((h) => watchlistCodes.value.add(h.code));
    watchMsg.value = `已批量加入 ${hits.value.length} 只`;
  } catch (e) {
    watchMsg.value = e.message;
  }
}

function switchTab(name) {
  tab.value = name;
  if (name === "watchlist") {
    loadWatchlistCodes();
    watchlistRef.value?.refreshAll?.();
  }
}

async function loadStrategies() {
  const res = await fetch("/api/strategies");
  const data = await res.json();
  strategies.value = data.strategies || [];
  if (strategies.value.length && !selectedId.value) {
    selectedId.value = strategies.value[0].id;
  }
  resetStrategyParams();
}

async function startScreen() {
  loading.value = true;
  error.value = "";
  hits.value = [];
  jobId.value = null;
  status.value = "running";

  try {
    const body = {
      strategy_id: selectedId.value,
      provider: provider.value,
      lookback_days: lookbackDays.value,
      exclude_st: excludeSt.value,
      exclude_bj: excludeBj.value,
      include_kcb: includeKcb.value,
      include_cyb: includeCyb.value,
      max_symbols: maxSymbols.value ? parseInt(maxSymbols.value, 10) : null,
    };
    if (Object.keys(strategyParams.value).length) {
      body.strategy_params = { ...strategyParams.value };
    }

    const res = await fetch("/api/screen", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || res.statusText);
    }
    const { job_id } = await res.json();
    jobId.value = job_id;
    watchJob(job_id);
  } catch (e) {
    error.value = e.message;
    status.value = "failed";
    loading.value = false;
  }
}

function watchJob(id) {
  const es = new EventSource(`/api/screen/${id}/events`);
  es.onmessage = (ev) => {
    const data = JSON.parse(ev.data);
    status.value = data.status;
    total.value = data.total;
    processed.value = data.processed;
    hits.value = data.hits || [];
    if (data.error) error.value = data.error;
    if (data.status === "completed" || data.status === "failed") {
      es.close();
      loading.value = false;
    }
  };
  es.onerror = () => {
    es.close();
    pollJob(id);
  };
}

async function pollJob(id) {
  const timer = setInterval(async () => {
    const res = await fetch(`/api/screen/${id}`);
    const data = await res.json();
    status.value = data.status;
    total.value = data.total;
    processed.value = data.processed;
    hits.value = data.hits || [];
    if (data.error) error.value = data.error;
    if (data.status === "completed" || data.status === "failed") {
      clearInterval(timer);
      loading.value = false;
    }
  }, 1000);
}

function exportCsv() {
  if (!hits.value.length) return;
  const header = ["代码", "名称", "收盘价", "信号日"];
  const rows = hits.value.map((h) => [h.code, h.name, h.close, h.date]);
  const csv = [header, ...rows]
    .map((r) => r.map((c) => `"${c}"`).join(","))
    .join("\n");
  const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `stockrock_${selectedId.value}_${Date.now()}.csv`;
  a.click();
}

onMounted(() => {
  loadStrategies();
  loadWatchlistCodes();
});
</script>

<template>
  <h1>Stockrock</h1>
  <p class="subtitle">通达信公式 → Python 策略 · A股全市场选股</p>

  <nav class="tabs">
    <button
      type="button"
      :class="{ active: tab === 'screen' }"
      @click="switchTab('screen')"
    >
      选股
    </button>
    <button
      type="button"
      :class="{ active: tab === 'watchlist' }"
      @click="switchTab('watchlist')"
    >
      自选
    </button>
  </nav>

  <template v-if="tab === 'screen'">
    <section class="card">
      <h2 style="margin: 0 0 1rem; font-size: 1.1rem">筛选设置</h2>
      <div class="grid">
        <div>
          <label>策略</label>
          <select v-model="selectedId">
            <option v-for="s in strategies" :key="s.id" :value="s.id">
              {{ s.name }}
            </option>
          </select>
        </div>
        <div>
          <label>数据源</label>
          <select v-model="provider">
            <option value="akshare">AKShare（免费）</option>
            <option value="tushare">Tushare Pro</option>
          </select>
        </div>
        <div>
          <label>回看天数</label>
          <input v-model.number="lookbackDays" type="number" min="30" max="500" />
        </div>
        <div>
          <label>限流（测试用，留空=全市场）</label>
          <input v-model="maxSymbols" type="number" placeholder="例如 50" />
        </div>
        <div v-for="p in editableParams" :key="p.key">
          <label>{{ p.label }}</label>
          <input
            v-model.number="strategyParams[p.key]"
            type="number"
            :min="p.min"
            :max="p.max"
          />
        </div>
      </div>

      <div class="checks">
        <label><input v-model="excludeSt" type="checkbox" /> 剔除 ST</label>
        <label><input v-model="excludeBj" type="checkbox" /> 剔除北交所</label>
        <label><input v-model="includeKcb" type="checkbox" /> 含科创板</label>
        <label><input v-model="includeCyb" type="checkbox" /> 含创业板</label>
      </div>

      <div v-if="selectedStrategy?.description" style="margin-bottom: 0.75rem">
        <small style="color: var(--muted)">{{ selectedStrategy.description }}</small>
        <div v-if="selectedStrategy.tdx_formula" class="formula-box">
          {{ selectedStrategy.tdx_formula }}
        </div>
      </div>

      <button :disabled="loading || !selectedId" @click="startScreen">
        {{ loading ? "扫描中…" : "开始选股" }}
      </button>
    </section>

    <section v-if="loading || status" class="card">
      <h2 style="margin: 0 0 0.75rem; font-size: 1.1rem">进度</h2>
      <div class="progress-wrap">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progress + '%' }" />
        </div>
        <p class="progress-text">
          {{ status }} — {{ processed }} / {{ total }}（{{ progress }}%）
          <span v-if="hits.length"> · 命中 {{ hits.length }} 只</span>
        </p>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
    </section>

    <section class="card">
      <div class="row-between">
        <h2 style="margin: 0; font-size: 1.1rem">结果</h2>
        <div class="btn-group">
          <button
            v-if="hits.length"
            class="secondary"
            type="button"
            :disabled="!someHitsSelected"
            @click="addSelectedToWatchlist"
          >
            加入所选到自选
          </button>
          <button
            v-if="hits.length"
            class="secondary"
            type="button"
            @click="addAllHits"
          >
            全部加自选
          </button>
          <button
            v-if="hits.length"
            class="secondary"
            type="button"
            @click="exportCsv"
          >
            导出 CSV
          </button>
        </div>
      </div>
      <p v-if="watchMsg" class="hint success-msg">{{ watchMsg }}</p>
      <table v-if="hits.length" class="hits-table">
        <thead>
          <tr>
            <th class="col-check">
              <input
                type="checkbox"
                :checked="allHitsSelected"
                :indeterminate="someHitsSelected && !allHitsSelected"
                @change="toggleSelectAllHits"
              />
            </th>
            <th>代码</th>
            <th>名称</th>
            <th>主要板块</th>
            <th>收盘价</th>
            <th>信号日</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="h in hits" :key="h.code">
            <td class="col-check">
              <input
                type="checkbox"
                :checked="selectedHits.has(h.code)"
                @change="toggleHit(h.code)"
              />
            </td>
            <td>{{ h.code }}</td>
            <td>{{ h.name }}</td>
            <td>{{ h.major_sector || "—" }}</td>
            <td>{{ h.close?.toFixed?.(2) ?? h.close }}</td>
            <td>{{ h.date }}</td>
            <td>
              <button
                v-if="!watchlistCodes.has(h.code)"
                class="secondary btn-sm"
                type="button"
                @click.stop="addToWatchlist(h)"
              >
                加自选
              </button>
              <span v-else class="muted">已在自选</span>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty">暂无结果，请选择策略后点击「开始选股」</p>
    </section>
  </template>

  <Watchlist v-else ref="watchlistRef" />
</template>
