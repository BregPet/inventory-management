<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="card budget-card">
        <div class="budget-header">
          <label for="budget-slider" class="budget-label">{{ t('restocking.budget') }}</label>
          <span class="budget-value">{{ money(budget) }}</span>
        </div>
        <input
          id="budget-slider"
          v-model.number="budget"
          type="range"
          min="0"
          :max="maxBudget"
          :step="BUDGET_STEP"
          class="budget-slider"
          @input="onBudgetInput"
        />
        <div class="budget-hint">{{ t('restocking.budgetHint', { max: money(maxBudget) }) }}</div>
      </div>

      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.budget') }}</div>
          <div class="stat-value">{{ money(recommendation.budget) }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.plannedSpend') }}</div>
          <div class="stat-value">{{ money(recommendation.total_cost) }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.remainingBudget') }}</div>
          <div class="stat-value">{{ money(recommendation.remaining_budget) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('restocking.itemsToOrder') }}</div>
          <div class="stat-value">{{ recommendation.items.length }}</div>
        </div>
      </div>

      <div v-if="orderError" class="alert alert-error">{{ orderError }}</div>
      <div v-if="placedOrder" class="alert alert-success">
        <div>
          <strong>{{ t('restocking.orderPlaced', { orderNumber: placedOrder.order_number }) }}</strong>
          <span class="alert-detail">{{ t('restocking.expectedDelivery', { date: formatDate(placedOrder.expected_delivery) }) }}</span>
        </div>
        <router-link to="/orders" class="alert-link">{{ t('restocking.viewOrders') }}</router-link>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendations') }} ({{ recommendation.items.length }})</h3>
          <button
            class="btn-primary"
            :disabled="recommendation.items.length === 0 || submitting || refreshing"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.placing') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="recommendation.items.length === 0" class="empty">{{ t('restocking.empty') }}</div>
        <div v-else :class="['table-container', { stale: refreshing }]">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.name') }}</th>
                <th>{{ t('restocking.table.category') }}</th>
                <th>{{ t('restocking.table.warehouse') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th class="num">{{ t('restocking.table.onHand') }}</th>
                <th class="num">{{ t('restocking.table.forecast') }}</th>
                <th class="num">{{ t('restocking.table.shortfall') }}</th>
                <th class="num">{{ t('restocking.table.recommendedQty') }}</th>
                <th class="num">{{ t('restocking.table.unitCost') }}</th>
                <th class="num">{{ t('restocking.table.lineTotal') }}</th>
                <th class="num">{{ t('restocking.table.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in recommendation.items" :key="item.sku">
                <td><strong>{{ item.sku }}</strong></td>
                <td>{{ translateProductName(item.name) }}</td>
                <td>{{ translateCategory(item.category) }}</td>
                <td>{{ translateWarehouse(item.warehouse) }}</td>
                <td>
                  <span :class="['badge', item.trend]">{{ t(`trends.${item.trend}`) }}</span>
                </td>
                <td class="num">{{ item.quantity_on_hand.toLocaleString() }}</td>
                <td class="num">{{ item.forecasted_demand.toLocaleString() }}</td>
                <td class="num">{{ item.shortfall.toLocaleString() }}</td>
                <td class="num"><strong>{{ item.recommended_quantity.toLocaleString() }}</strong></td>
                <td class="num">{{ money(item.unit_cost, 2) }}</td>
                <td class="num"><strong>{{ money(item.line_total, 2) }}</strong></td>
                <td class="num">{{ item.lead_time_days }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

const BUDGET_STEP = 100
const DEBOUNCE_MS = 250

export default {
  name: 'Restocking',
  setup() {
    const { t, currentLocale, currentCurrency, translateProductName, translateWarehouse } = useI18n()

    const loading = ref(true)
    const error = ref(null)
    const refreshing = ref(false)
    const maxBudget = ref(0)
    const budget = ref(0)
    const recommendation = ref({ budget: 0, total_cost: 0, remaining_budget: 0, items: [] })

    const submitting = ref(false)
    const orderError = ref(null)
    const placedOrder = ref(null)

    let debounceTimer = null
    // Guards against out-of-order responses while the slider is moving
    let requestSeq = 0

    const money = (amount, decimals = 0) =>
      formatCurrencyWithDecimals(amount ?? 0, currentCurrency.value, decimals)

    const translateCategory = (category) => {
      const categoryMap = {
        'Circuit Boards': t('categories.circuitBoards'),
        'Sensors': t('categories.sensors'),
        'Actuators': t('categories.actuators'),
        'Controllers': t('categories.controllers'),
        'Power Supplies': t('categories.powerSupplies')
      }
      return categoryMap[category] || category
    }

    const formatDate = (dateString) => {
      const date = new Date(dateString)
      if (isNaN(date.getTime())) return dateString
      return date.toLocaleDateString(currentLocale.value === 'ja' ? 'ja-JP' : 'en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    const loadRecommendations = async () => {
      const seq = ++requestSeq
      try {
        refreshing.value = true
        const data = await api.getRestockRecommendations(budget.value)
        if (seq !== requestSeq) return
        recommendation.value = data
        error.value = null
      } catch (err) {
        if (seq !== requestSeq) return
        error.value = t('restocking.loadFailed', { message: err.message })
      } finally {
        if (seq === requestSeq) refreshing.value = false
      }
    }

    const onBudgetInput = () => {
      placedOrder.value = null
      orderError.value = null
      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(loadRecommendations, DEBOUNCE_MS)
    }

    const init = async () => {
      try {
        loading.value = true
        // Budget 0 returns no items but still reports the total shortfall cost, which sets the slider range
        const baseline = await api.getRestockRecommendations(0)
        maxBudget.value = Math.max(500, Math.ceil(baseline.total_shortfall_cost / 500) * 500)
        budget.value = Math.round(maxBudget.value / 2 / BUDGET_STEP) * BUDGET_STEP
        await loadRecommendations()
      } catch (err) {
        error.value = t('restocking.loadFailed', { message: err.message })
      } finally {
        loading.value = false
      }
    }

    const placeOrder = async () => {
      if (submitting.value || recommendation.value.items.length === 0) return
      submitting.value = true
      orderError.value = null
      placedOrder.value = null
      try {
        placedOrder.value = await api.createRestockOrder(
          recommendation.value.items.map(item => ({
            sku: item.sku,
            quantity: item.recommended_quantity
          }))
        )
      } catch (err) {
        const detail = err.response?.data?.detail
        orderError.value = t('restocking.orderFailed', {
          message: typeof detail === 'string' ? detail : err.message
        })
      } finally {
        submitting.value = false
      }
    }

    onMounted(init)
    onBeforeUnmount(() => clearTimeout(debounceTimer))

    return {
      t,
      BUDGET_STEP,
      loading,
      error,
      refreshing,
      maxBudget,
      budget,
      recommendation,
      submitting,
      orderError,
      placedOrder,
      money,
      translateProductName,
      translateWarehouse,
      translateCategory,
      formatDate,
      onBudgetInput,
      placeOrder
    }
  }
}
</script>

<style scoped>

.budget-card {
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.5rem;
}

.budget-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.75rem;
}

.budget-label {
  color: var(--color-text-muted);
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.budget-value {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-size: var(--text-xl);
  font-weight: var(--weight-medium);
  color: var(--color-text);
}

.budget-slider {
  width: 100%;
  accent-color: var(--color-primary);
  cursor: pointer;
}

.budget-hint {
  margin-top: 0.5rem;
  color: var(--color-text-subtle);
  font-size: 0.813rem;
}

.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.table-container.stale {
  opacity: 0.6;
  transition: opacity 0.15s;
}

.alert {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 0.875rem 1.25rem;
  margin-bottom: 1.5rem;
  border-radius: var(--radius-md);
  border: 1px solid;
  font-size: 0.875rem;
}

.alert-success {
  background: var(--color-success-soft);
  border-color: var(--color-success);
  color: var(--color-success-text);
}

.alert-error {
  background: var(--color-danger-soft);
  border-color: var(--color-danger);
  color: var(--color-danger-text);
}

.alert-detail {
  margin-left: 0.75rem;
}

.alert-link {
  color: var(--color-primary);
  font-weight: var(--weight-medium);
  text-decoration: none;
  white-space: nowrap;
}

.alert-link:hover {
  text-decoration: underline;
}

.empty {
  padding: 2rem;
  text-align: center;
  color: var(--color-text-muted);
}


tbody td:first-child {
  white-space: nowrap;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}

.loading,
.error {
  padding: var(--space-8);
}
</style>
