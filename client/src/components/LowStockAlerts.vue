<template>
  <div ref="root" class="low-stock-alerts">
    <button
      type="button"
      class="bell-button"
      :aria-label="
        t('alerts.button') + (items.length ? ` (${items.length})` : '')
      "
      :aria-expanded="String(isOpen)"
      aria-haspopup="dialog"
      @click="toggle"
    >
      <NavIcon name="bell" />
      <span
        v-if="items.length"
        :class="['count-badge', { critical: hasCritical }]"
      >
        {{ items.length }}
      </span>
    </button>

    <div
      v-if="isOpen"
      class="alerts-panel"
      role="dialog"
      :aria-label="t('alerts.title')"
    >
      <div class="panel-header">{{ t("alerts.title") }}</div>

      <div v-if="error" class="panel-message error-text">{{ error }}</div>
      <div v-else-if="items.length === 0" class="panel-message">
        {{ t("alerts.empty") }}
      </div>
      <ul v-else class="alert-list">
        <li v-for="item in items" :key="item.id" class="alert-item">
          <div class="alert-main">
            <span class="alert-name">{{
              translateProductName(item.name)
            }}</span>
            <span
              :class="[
                'badge',
                item.severity === 'critical' ? 'danger' : 'warning',
              ]"
            >
              {{ t(`alerts.${item.severity}`) }}
            </span>
          </div>
          <div class="alert-meta">
            <span class="sku">{{ item.sku }}</span>
            <span>{{ translateWarehouse(item.warehouse) }}</span>
          </div>
          <div class="alert-meta">
            <span>{{
              t("alerts.onHand", {
                qty: item.quantity_on_hand,
                reorder: item.reorder_point,
              })
            }}</span>
            <span class="shortfall">{{
              t("alerts.short", { count: item.shortfall })
            }}</span>
          </div>
        </li>
      </ul>

      <router-link to="/inventory" class="panel-footer" @click="isOpen = false">
        {{ t("alerts.viewInventory") }}
      </router-link>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import NavIcon from "./NavIcon.vue";
import { api } from "../api";
import { useFilters } from "../composables/useFilters";
import { useI18n } from "../composables/useI18n";

export default {
  name: "LowStockAlerts",
  components: { NavIcon },
  setup() {
    const { t, translateProductName, translateWarehouse } = useI18n();
    // Inventory has no time dimension, so only Location and Category apply
    const { selectedLocation, selectedCategory, getCurrentFilters } =
      useFilters();

    const root = ref(null);
    const isOpen = ref(false);
    const items = ref([]);
    const error = ref(null);

    const hasCritical = computed(() =>
      items.value.some((i) => i.severity === "critical"),
    );

    const loadAlerts = async () => {
      try {
        error.value = null;
        items.value = await api.getLowStock(getCurrentFilters());
      } catch (err) {
        error.value = t("alerts.loadError");
        console.error("Low-stock alerts load error:", err);
      }
    };

    const toggle = () => {
      isOpen.value = !isOpen.value;
      // Refresh on open so the list is current even without a filter change
      if (isOpen.value) loadAlerts();
    };

    const onDocumentClick = (event) => {
      if (isOpen.value && root.value && !root.value.contains(event.target)) {
        isOpen.value = false;
      }
    };

    const onKeydown = (event) => {
      if (event.key === "Escape") isOpen.value = false;
    };

    watch([selectedLocation, selectedCategory], loadAlerts);

    onMounted(() => {
      loadAlerts();
      document.addEventListener("click", onDocumentClick);
      document.addEventListener("keydown", onKeydown);
    });

    onBeforeUnmount(() => {
      document.removeEventListener("click", onDocumentClick);
      document.removeEventListener("keydown", onKeydown);
    });

    return {
      t,
      root,
      isOpen,
      items,
      error,
      hasCritical,
      toggle,
      translateProductName,
      translateWarehouse,
    };
  },
};
</script>

<style scoped>
.low-stock-alerts {
  position: relative;
}

.bell-button {
  position: relative;
  display: inline-grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition:
    background var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out);
}

.bell-button:hover {
  background: var(--color-surface-muted);
  border-color: var(--color-border-strong);
}

.bell-button :deep(.nav-icon-svg) {
  width: 18px;
  height: 18px;
}

.count-badge {
  position: absolute;
  top: calc(var(--space-2) * -1);
  right: calc(var(--space-2) * -1);
  min-width: 18px;
  height: 18px;
  padding: 0 var(--space-1);
  border-radius: 9px;
  background: var(--color-warning);
  color: var(--color-surface);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  font-family: var(--font-mono);
  line-height: 18px;
  text-align: center;
}

.count-badge.critical {
  background: var(--color-danger);
}

.alerts-panel {
  position: absolute;
  top: calc(100% + var(--space-2));
  right: 0;
  width: 340px;
  max-width: calc(100vw - var(--space-8));
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  z-index: 1000;
  overflow: hidden;
}

.panel-header {
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
  font-weight: var(--weight-semibold);
  color: var(--color-text);
}

.panel-message {
  padding: var(--space-4);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.error-text {
  color: var(--color-danger);
}

.alert-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 360px;
  overflow-y: auto;
}

.alert-item {
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.alert-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.alert-name {
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--color-text);
}

.alert-meta {
  display: flex;
  justify-content: space-between;
  gap: var(--space-2);
  margin-top: var(--space-1);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.sku,
.shortfall {
  font-family: var(--font-mono);
}

.shortfall {
  color: var(--color-danger);
}

.panel-footer {
  display: block;
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--color-primary);
  text-decoration: none;
  text-align: center;
}

.panel-footer:hover {
  background: var(--color-surface-muted);
}
</style>
