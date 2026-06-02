<script setup>
import { ref, onMounted, onUnmounted } from "vue";

const items = ref([]);
const loading = ref(false);
const quotesLoading = ref(false);
const error = ref("");
const quoteBanner = ref("");
const manualCode = ref("");
const manualName = ref("");
const tradeLots = ref({});
const tradePrice = ref({});

let refreshTimer = null;

async function loadList() {
  loading.value = true;
  error.value = "";
  try {
    const res = await fetch("/api/watchlist");
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();
    items.value = (data.items || []).map((it) => ({
      ...it,
      quote_error: null,
      price: null,
    }));
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}

async function loadQuotes() {
  if (!items.value.length) {
    await loadList();
    if (!items.value.length) return;
  }
  quotesLoading.value = true;
  quoteBanner.value = "";
  try {
    const res = await fetch("/api/watchlist/quotes");
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();
    items.value = data.items || [];
    if (!data.quotes_ok && data.quote_error) {
      quoteBanner.value = `行情暂不可用：${data.quote_error}（列表仍可管理）`;
    }
  } catch (e) {
    quoteBanner.value = `行情加载失败：${e.message}（列表仍可管理）`;
  } finally {
    quotesLoading.value = false;
  }
}

async function refreshAll() {
  await loadList();
  await loadQuotes();
}

async function addManual() {
  const code = manualCode.value.trim();
  if (!code) return;
  error.value = "";
  try {
    const res = await fetch("/api/watchlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, name: manualName.value.trim() }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || res.statusText);
    }
    manualCode.value = "";
    manualName.value = "";
    await refreshAll();
  } catch (e) {
    error.value = e.message;
  }
}

async function removeItem(code) {
  error.value = "";
  try {
    const res = await fetch(`/api/watchlist/${encodeURIComponent(code)}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || res.statusText);
    }
    items.value = items.value.filter((x) => x.code !== code);
  } catch (e) {
    error.value = e.message;
  }
}

function lotsOf(code) {
  const v = Number(tradeLots.value[code] ?? 1);
  return Number.isFinite(v) && v > 0 ? Math.floor(v) : 1;
}

function priceOf(code, fallbackPrice = null) {
  const raw = tradePrice.value[code];
  if (raw == null || raw === "") return fallbackPrice;
  const v = Number(raw);
  return Number.isFinite(v) && v > 0 ? v : fallbackPrice;
}

async function buyItem(it) {
  error.value = "";
  try {
    const res = await fetch(`/api/watchlist/${encodeURIComponent(it.code)}/buy`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        lots: lotsOf(it.code),
        price: priceOf(it.code, it.price),
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || res.statusText);
    }
    await refreshAll();
  } catch (e) {
    error.value = e.message;
  }
}

async function sellItem(it, allClose = false) {
  error.value = "";
  try {
    const res = await fetch(`/api/watchlist/${encodeURIComponent(it.code)}/sell`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        lots: lotsOf(it.code),
        price: priceOf(it.code, it.price),
        all_close: allClose,
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || res.statusText);
    }
    await refreshAll();
  } catch (e) {
    error.value = e.message;
  }
}

function fmtNum(v, digits = 2) {
  if (v == null || Number.isNaN(v)) return "—";
  return Number(v).toFixed(digits);
}

function pctClass(v) {
  if (v == null) return "";
  return v > 0 ? "up" : v < 0 ? "down" : "";
}

function hasQuote(it) {
  return it.price != null && !it.quote_error;
}

function fmtDateTime(v) {
  if (!v) return "—";
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return String(v);
  return d.toLocaleString("zh-CN", { hour12: false });
}

onMounted(async () => {
  await loadList();
  loadQuotes();
  refreshTimer = setInterval(loadQuotes, 30000);
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});

defineExpose({ refreshAll, loadList });
</script>

<template>
  <section class="card">
    <div class="row-between">
      <h2 style="margin: 0; font-size: 1.1rem">自选列表</h2>
      <div class="btn-group">
        <button
          class="secondary"
          type="button"
          :disabled="loading || quotesLoading"
          @click="refreshAll"
        >
          {{ loading || quotesLoading ? "加载中…" : "刷新" }}
        </button>
        <button
          class="secondary"
          type="button"
          :disabled="quotesLoading || !items.length"
          @click="loadQuotes"
        >
          刷新行情
        </button>
      </div>
    </div>

    <div class="grid manual-add">
      <div>
        <label>股票代码</label>
        <input v-model="manualCode" placeholder="如 600519" maxlength="6" />
      </div>
      <div>
        <label>名称（可选）</label>
        <input v-model="manualName" placeholder="如 贵州茅台" />
      </div>
      <div class="manual-add-btn">
        <label>&nbsp;</label>
        <button type="button" :disabled="!manualCode.trim()" @click="addManual">
          添加自选
        </button>
      </div>
    </div>

    <p class="hint">
      先显示已保存的自选；交易时段显示实时价，盘外显示最近交易日收盘价
    </p>
    <p v-if="quoteBanner" class="hint warn-msg">{{ quoteBanner }}</p>
    <p v-if="error" class="error">{{ error }}</p>

    <table v-if="items.length">
      <thead>
        <tr>
          <th>代码</th>
          <th>名称</th>
          <th>主要板块</th>
          <th>来源策略</th>
          <th>加入时间</th>
          <th>价格</th>
          <th>涨跌幅</th>
          <th>涨跌额</th>
          <th>初始价</th>
          <th>自选涨跌</th>
          <th>持仓(手)</th>
          <th>持仓浮盈%</th>
          <th>已实现盈亏%</th>
          <th>最近买入</th>
          <th>最近卖出</th>
          <th>今开</th>
          <th>最高</th>
          <th>最低</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="it in items" :key="it.code">
          <td>{{ it.code }}</td>
          <td>{{ it.name || "—" }}</td>
          <td>{{ it.major_sector || "—" }}</td>
          <td>{{ it.source_strategy || "手动添加" }}</td>
          <td>{{ fmtDateTime(it.added_at) }}</td>
          <template v-if="hasQuote(it)">
            <td>
              {{ fmtNum(it.price) }}
              <span v-if="it.price_type === 'close'" class="muted price-tag">
                收盘{{ it.as_of ? ` ${it.as_of}` : "" }}
              </span>
            </td>
            <td :class="pctClass(it.change_pct)">{{ fmtNum(it.change_pct) }}%</td>
            <td :class="pctClass(it.change)">{{ fmtNum(it.change) }}</td>
          </template>
          <template v-else>
            <td colspan="3" class="muted">
              {{ it.quote_error || "行情未加载" }}
            </td>
          </template>
          <td>{{ fmtNum(it.initial_price) }}</td>
          <td :class="pctClass(it.initial_change_pct)">
            {{
              it.initial_change_pct != null
                ? `${fmtNum(it.initial_change_pct)}%`
                : "—"
            }}
          </td>
          <td>{{ it.position_lots ?? 0 }}</td>
          <td :class="pctClass(it.floating_pnl_pct)">
            {{
              it.floating_pnl_pct != null ? `${fmtNum(it.floating_pnl_pct)}%` : "—"
            }}
          </td>
          <td :class="pctClass(it.realized_pnl_pct)">
            {{
              it.realized_pnl_pct != null ? `${fmtNum(it.realized_pnl_pct)}%` : "—"
            }}
          </td>
          <td>
            {{
              it.last_buy_at
                ? `${fmtDateTime(it.last_buy_at)} @ ${fmtNum(it.last_buy_price)}`
                : "—"
            }}
          </td>
          <td>
            {{
              it.last_sell_at
                ? `${fmtDateTime(it.last_sell_at)} @ ${fmtNum(it.last_sell_price)}`
                : "—"
            }}
          </td>
          <template v-if="hasQuote(it)">
            <td>{{ fmtNum(it.open) }}</td>
            <td>{{ fmtNum(it.high) }}</td>
            <td>{{ fmtNum(it.low) }}</td>
          </template>
          <template v-else>
            <td colspan="3" class="muted">—</td>
          </template>
          <td>
            <div class="trade-tools">
              <input
                v-model.number="tradeLots[it.code]"
                type="number"
                min="1"
                step="1"
                placeholder="手数"
              />
              <input
                v-model="tradePrice[it.code]"
                type="number"
                min="0"
                step="0.01"
                placeholder="价格(可空)"
              />
              <button class="secondary btn-sm" type="button" @click="buyItem(it)">
                买入
              </button>
              <button class="secondary btn-sm" type="button" @click="sellItem(it)">
                卖出
              </button>
              <button
                class="secondary btn-sm"
                type="button"
                :disabled="!it.position_lots"
                @click="sellItem(it, true)"
              >
                清仓
              </button>
            </div>
            <button
              class="secondary btn-sm btn-danger"
              type="button"
              @click="removeItem(it.code)"
            >
              删除
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else-if="!loading" class="empty">
      暂无自选。可在「选股」结果中勾选后添加，或在上方输入代码添加
    </p>
  </section>
</template>
