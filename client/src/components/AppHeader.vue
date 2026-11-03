<template>
  <header class="app-header">
    <button
      v-if="mode === 'mobile'"
      type="button"
      class="menu-button"
      :aria-label="t('nav.openMenu')"
      :aria-expanded="String(mobileOpen)"
      @click="openMobile"
    >
      <NavIcon name="menu" />
    </button>
    <span class="page-title">{{ pageTitle }}</span>
    <div class="header-actions">
      <LanguageSwitcher />
    </div>
  </header>
</template>

<script>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import NavIcon from './NavIcon.vue'
import LanguageSwitcher from './LanguageSwitcher.vue'
import { useI18n } from '../composables/useI18n'
import { useLayout } from '../composables/useLayout'
import { navItems } from '../navItems'

export default {
  name: 'AppHeader',
  components: { NavIcon, LanguageSwitcher },
  setup() {
    const { t } = useI18n()
    const route = useRoute()
    const { mode, mobileOpen, openMobile } = useLayout()

    const pageTitle = computed(() => {
      const item = navItems.find(i => i.path === route.path)
      return item ? t(item.label) : ''
    })

    return { t, mode, mobileOpen, openMobile, pageTitle }
  }
}
</script>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 30;
  height: var(--header-height);
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 0 var(--content-padding);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.page-title {
  font-size: var(--text-md);
  font-weight: var(--weight-semibold);
  color: var(--color-text);
}

.header-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.menu-button {
  display: inline-grid;
  place-items: center;
  width: 36px;
  height: 36px;
  margin-left: calc(var(--space-2) * -1);
  border: 0;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out);
}

.menu-button:hover {
  background: var(--color-surface-muted);
}
</style>
