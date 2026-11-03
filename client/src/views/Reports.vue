<template>
  <div class="reports">
    <div class="page-header">
      <h2>{{ t("reports.title") }}</h2>
      <p>{{ t("reports.description") }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t("common.loading") }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="monthlyData.length === 0" class="loading">
      {{ t("common.noData") }}
    </div>
    <div v-else>
      <!-- Quarterly Performance -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t("reports.quarterly.title") }}</h3>
        </div>
        <div class="table-container">
          <table class="reports-table">
            <thead>
              <tr>
                <th>{{ t("reports.quarterly.quarter") }}</th>
                <th class="num">{{ t("reports.quarterly.totalOrders") }}</th>
                <th class="num">{{ t("reports.quarterly.totalRevenue") }}</th>
                <th class="num">{{ t("reports.quarterly.avgOrderValue") }}</th>
                <th class="num">
                  {{ t("reports.quarterly.fulfillmentRate") }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="q in quarterlyData" :key="q.quarter">
                <td>
                  <strong>{{ q.quarter }}</strong>
                </td>
                <td class="num">{{ q.total_orders }}</td>
                <td class="num">{{ formatMoney(q.total_revenue) }}</td>
                <td class="num">{{ formatMoney(q.avg_order_value) }}</td>
                <td class="num">
                  <span
                    :class="['badge', getFulfillmentClass(q.fulfillment_rate)]"
                  >
                    {{ q.fulfillment_rate }}%
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Monthly Trends Chart -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t("reports.monthlyTrend.title") }}</h3>
        </div>
        <div class="chart-container">
          <div
            class="bar-chart"
            role="img"
            :aria-label="t('reports.monthlyTrend.title')"
          >
            <div
              v-for="row in monthlyRows"
              :key="row.month"
              class="bar-wrapper"
            >
              <div class="bar-container">
                <div
                  class="bar"
                  :style="{ height: row.barHeight + '%' }"
                  :title="row.label + ': ' + formatMoney(row.revenue)"
                ></div>
              </div>
              <div class="bar-label">{{ row.label }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Month-over-Month Comparison -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t("reports.mom.title") }}</h3>
        </div>
        <div class="table-container">
          <table class="reports-table">
            <thead>
              <tr>
                <th>{{ t("reports.mom.month") }}</th>
                <th class="num">{{ t("reports.mom.orders") }}</th>
                <th class="num">{{ t("reports.mom.revenue") }}</th>
                <th class="num">{{ t("reports.mom.change") }}</th>
                <th class="num">{{ t("reports.mom.growthRate") }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in monthlyRows" :key="row.month">
                <td>
                  <strong>{{ row.label }}</strong>
                </td>
                <td class="num">{{ row.order_count }}</td>
                <td class="num">{{ formatMoney(row.revenue) }}</td>
                <td class="num">
                  <span
                    v-if="row.change !== null"
                    :class="changeClass(row.change)"
                  >
                    {{ formatChange(row.change) }}
                  </span>
                  <span v-else>-</span>
                </td>
                <td class="num">
                  <span
                    v-if="row.growthRate !== null"
                    :class="changeClass(row.change)"
                  >
                    {{ formatGrowth(row.growthRate) }}
                  </span>
                  <span v-else>-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Summary Stats -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">{{ t("reports.summary.totalRevenue") }}</div>
          <div class="stat-value">{{ formatMoney(totalRevenue) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">
            {{ t("reports.summary.avgMonthlyRevenue") }}
          </div>
          <div class="stat-value">{{ formatMoney(avgMonthlyRevenue) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t("reports.summary.totalOrders") }}</div>
          <div class="stat-value">{{ totalOrders }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t("reports.summary.bestQuarter") }}</div>
          <div class="stat-value">{{ bestQuarter || "-" }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from "vue";
import { api } from "../api";
import { useFilters } from "../composables/useFilters";
import { useI18n } from "../composables/useI18n";
import { formatCurrencyWithDecimals } from "../utils/currency";

const MONTH_KEYS = [
  "jan",
  "feb",
  "mar",
  "apr",
  "may",
  "jun",
  "jul",
  "aug",
  "sep",
  "oct",
  "nov",
  "dec",
];

export default {
  name: "Reports",
  setup() {
    const { t, currentLocale, currentCurrency } = useI18n();
    const {
      selectedPeriod,
      selectedLocation,
      selectedCategory,
      selectedStatus,
      getCurrentFilters,
    } = useFilters();

    const loading = ref(true);
    const error = ref(null);
    const quarterlyData = ref([]);
    const monthlyData = ref([]);

    const loadData = async () => {
      try {
        loading.value = true;
        error.value = null;
        const filters = getCurrentFilters();
        // Both reports are independent, so fetch them in parallel
        const [quarterly, monthly] = await Promise.all([
          api.getQuarterlyReports(filters),
          api.getMonthlyTrends(filters),
        ]);
        quarterlyData.value = quarterly;
        monthlyData.value = monthly;
      } catch (err) {
        error.value = t("reports.loadError") + ": " + err.message;
        console.error("Reports load error:", err);
      } finally {
        loading.value = false;
      }
    };

    // Converts YYYY-MM to a localized label; falls back to the raw string if malformed
    const formatMonth = (monthStr) => {
      const [year, month] = (monthStr || "").split("-");
      const key = MONTH_KEYS[parseInt(month, 10) - 1];
      if (!year || !key) return monthStr;
      return currentLocale.value === "ja"
        ? `${year}年${t(`months.${key}`)}`
        : `${t(`months.${key}`)} ${year}`;
    };

    // Derived rows for the chart and MoM table, computed once per data/locale change
    const monthlyRows = computed(() => {
      const maxRevenue = Math.max(
        0,
        ...monthlyData.value.map((m) => m.revenue),
      );
      return monthlyData.value.map((m, i) => {
        const prev = i > 0 ? monthlyData.value[i - 1].revenue : null;
        return {
          ...m,
          label: formatMonth(m.month),
          barHeight: maxRevenue > 0 ? (m.revenue / maxRevenue) * 100 : 0,
          change: prev === null ? null : m.revenue - prev,
          growthRate: prev ? ((m.revenue - prev) / prev) * 100 : null,
        };
      });
    });

    const totalRevenue = computed(() =>
      monthlyData.value.reduce((sum, m) => sum + m.revenue, 0),
    );
    const totalOrders = computed(() =>
      monthlyData.value.reduce((sum, m) => sum + m.order_count, 0),
    );
    const avgMonthlyRevenue = computed(() =>
      monthlyData.value.length
        ? totalRevenue.value / monthlyData.value.length
        : 0,
    );
    const bestQuarter = computed(() => {
      const best = quarterlyData.value.reduce(
        (top, q) => (!top || q.total_revenue > top.total_revenue ? q : top),
        null,
      );
      return best ? best.quarter : "";
    });

    const formatMoney = (amount) =>
      formatCurrencyWithDecimals(amount, currentCurrency.value, 2);

    const formatChange = (change) => {
      if (change === 0) return formatMoney(0);
      return (change > 0 ? "+" : "-") + formatMoney(Math.abs(change));
    };

    const formatGrowth = (rate) =>
      (rate > 0 ? "+" : "") + rate.toFixed(1) + "%";

    const changeClass = (change) => {
      if (change > 0) return "positive-change";
      if (change < 0) return "negative-change";
      return "";
    };

    const getFulfillmentClass = (rate) => {
      if (rate >= 90) return "success";
      if (rate >= 75) return "warning";
      return "danger";
    };

    // Reload when the global filter bar changes
    watch(
      [selectedPeriod, selectedLocation, selectedCategory, selectedStatus],
      () => {
        loadData();
      },
    );

    onMounted(loadData);

    return {
      t,
      loading,
      error,
      quarterlyData,
      monthlyData,
      monthlyRows,
      totalRevenue,
      totalOrders,
      avgMonthlyRevenue,
      bestQuarter,
      formatMoney,
      formatChange,
      formatGrowth,
      changeClass,
      getFulfillmentClass,
    };
  },
};
</script>

<style scoped>
.reports-table {
  width: 100%;
  border-collapse: collapse;
}

.reports-table th {
  background: var(--color-surface-muted);
  padding: var(--space-3);
  text-align: left;
}

.reports-table td {
  padding: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.reports-table tr:hover {
  background: var(--color-surface-muted);
}

.reports-table .num {
  text-align: right;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.chart-container {
  padding: var(--space-8) var(--space-4);
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  gap: var(--space-2);
}

.bar-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  max-width: 80px;
}

.bar-container {
  height: 200px;
  display: flex;
  align-items: flex-end;
  width: 100%;
}

.bar {
  width: 100%;
  background: var(--color-primary);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  transition:
    height 0.3s,
    background 0.3s;
  cursor: pointer;
}

.bar:hover {
  background: var(--color-primary-hover);
}

.bar-label {
  margin-top: var(--space-6);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  text-align: center;
  transform: rotate(-45deg);
  white-space: nowrap;
}

.positive-change {
  color: var(--color-success);
  font-weight: var(--weight-medium);
}

.negative-change {
  color: var(--color-danger);
  font-weight: var(--weight-medium);
}

.reports :deep(.stats-grid) {
  margin-top: var(--space-6);
  margin-bottom: 0;
}
</style>
