<template>
  <div v-if="scrimVisible" class="sidebar-scrim" :class="{ 'is-tablet': mode === 'tablet' }" @click="closeTransient"></div>
  <aside
    class="sidebar"
    :class="{
      'is-rail': isRail,
      'is-overlay': mode === 'tablet' && tabletExpanded,
      'is-offcanvas': mode === 'mobile',
      'is-open': mobileOpen
    }"
    :aria-label="t('nav.mainNavigation')"
  >
    <div class="sidebar-brand">
      <span class="brand-mark" aria-hidden="true">C</span>
      <div class="brand-text">
        <span class="brand-name">{{ t('nav.companyName') }}</span>
        <span class="brand-subtitle">{{ t('nav.subtitle') }}</span>
      </div>
    </div>

    <nav class="sidebar-nav">
      <div v-for="group in groups" :key="group.label" class="nav-group">
        <div class="nav-group-label">{{ t(group.label) }}</div>
        <router-link
          v-for="item in group.items"
          :key="item.path"
          :to="item.path"
          custom
          v-slot="{ href, navigate, isActive, isExactActive }"
        >
          <a
            :href="href"
            class="nav-item"
            :class="{ 'is-active': item.exact ? isExactActive : isActive }"
            :aria-current="(item.exact ? isExactActive : isActive) ? 'page' : undefined"
            :title="isRail ? t(item.label) : undefined"
            :aria-label="isRail ? t(item.label) : undefined"
            @click="navigate"
          >
            <NavIcon :name="item.icon" />
            <span class="nav-label">{{ t(item.label) }}</span>
          </a>
        </router-link>
      </div>
    </nav>

    <div class="sidebar-footer">
      <ProfileMenu
        @show-profile-details="$emit('show-profile-details')"
        @show-tasks="$emit('show-tasks')"
      />
      <button
        v-if="mode !== 'mobile'"
        type="button"
        class="collapse-toggle"
        :aria-expanded="String(!isRail)"
        :aria-label="isRail ? t('nav.expandSidebar') : t('nav.collapseSidebar')"
        :title="isRail ? t('nav.expandSidebar') : t('nav.collapseSidebar')"
        @click="toggleSidebar"
      >
        <NavIcon :name="isRail ? 'chevrons-right' : 'chevrons-left'" />
        <span class="toggle-label">{{ t('nav.collapseSidebar') }}</span>
      </button>
    </div>
  </aside>
</template>

<script>
import { computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import NavIcon from './NavIcon.vue'
import ProfileMenu from './ProfileMenu.vue'
import { useI18n } from '../composables/useI18n'
import { useLayout } from '../composables/useLayout'
import { navItems } from '../navItems'

export default {
  name: 'AppSidebar',
  components: { NavIcon, ProfileMenu },
  emits: ['show-profile-details', 'show-tasks'],
  setup() {
    const { t } = useI18n()
    const route = useRoute()
    const { mode, isRail, tabletExpanded, mobileOpen, toggleSidebar, closeTransient } = useLayout()

    const groups = computed(() => {
      const result = []
      navItems.forEach(item => {
        let group = result.find(g => g.label === item.group)
        if (!group) {
          group = { label: item.group, items: [] }
          result.push(group)
        }
        group.items.push(item)
      })
      return result
    })

    const scrimVisible = computed(() => mobileOpen.value || (mode.value === 'tablet' && tabletExpanded.value))

    watch(() => route.fullPath, closeTransient)

    const onKeydown = (event) => {
      if (event.key === 'Escape') closeTransient()
    }
    onMounted(() => document.addEventListener('keydown', onKeydown))
    onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))

    return { t, mode, groups, isRail, tabletExpanded, mobileOpen, scrimVisible, toggleSidebar, closeTransient }
  }
}
</script>

<style scoped>
.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 50;
  width: var(--sidebar-width);
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  transition: width var(--duration-base) var(--ease-out);
}

.sidebar.is-rail {
  width: var(--sidebar-width-rail);
}

.sidebar.is-overlay {
  box-shadow: var(--shadow-lg);
}

.sidebar-brand {
  height: var(--header-height);
  flex: none;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 0 var(--space-4);
  border-bottom: 1px solid var(--color-border);
  overflow: hidden;
}

.brand-mark {
  flex: none;
  width: 30px;
  height: 30px;
  border-radius: var(--radius-md);
  display: grid;
  place-items: center;
  background: var(--color-text);
  color: var(--color-surface);
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  font-family: var(--font-sans);
}

.brand-text {
  min-width: 0;
  display: flex;
  flex-direction: column;
  line-height: var(--leading-tight);
}

.brand-name {
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.brand-subtitle {
  margin-top: 2px;
  font-size: var(--text-2xs);
  color: var(--color-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-nav {
  flex: 1;
  overflow-x: hidden;
  overflow-y: auto;
  padding: var(--space-4) var(--space-3);
}

.nav-group + .nav-group {
  margin-top: var(--space-5);
}

.nav-group-label {
  padding: 0 var(--space-3) var(--space-2);
  font-size: var(--text-2xs);
  font-weight: var(--weight-medium);
  text-transform: uppercase;
  letter-spacing: var(--tracking-label);
  color: var(--color-text-muted);
  white-space: nowrap;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 36px;
  padding: 0 var(--space-3);
  margin-bottom: 2px;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: var(--text-base);
  font-weight: var(--weight-medium);
  white-space: nowrap;
  transition: background var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out);
}

.nav-item:hover {
  background: var(--color-surface-muted);
  color: var(--color-text);
}

.nav-item.is-active {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.sidebar-footer {
  flex: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3);
  border-top: 1px solid var(--color-border);
}

.collapse-toggle {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 32px;
  padding: 0 var(--space-3);
  border: 0;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-text-muted);
  font-family: inherit;
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  white-space: nowrap;
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out);
}

.collapse-toggle:hover {
  background: var(--color-surface-muted);
  color: var(--color-text);
}

/* Rail: icons only */
.is-rail .brand-text,
.is-rail .nav-label,
.is-rail .toggle-label {
  display: none;
}

.is-rail .nav-group-label {
  height: 1px;
  padding: 0;
  margin: 0 var(--space-3) var(--space-2);
  background: var(--color-border);
  font-size: 0;
}

.is-rail .nav-item,
.is-rail .collapse-toggle {
  justify-content: center;
  padding: 0;
}

.is-rail :deep(.profile-name),
.is-rail :deep(.chevron) {
  display: none;
}

.is-rail :deep(.profile-button) {
  justify-content: center;
  padding: var(--space-1) 0;
}

.sidebar-scrim {
  position: fixed;
  inset: 0;
  z-index: 40;
  background: rgb(15 23 42 / 0.4);
}

.sidebar-scrim.is-tablet {
  background: transparent;
}

@media (max-width: 767px) {
  .sidebar.is-offcanvas {
    width: var(--sidebar-width);
    transform: translateX(-100%);
    visibility: hidden;
    box-shadow: none;
    transition: transform var(--duration-base) var(--ease-out), visibility 0s linear var(--duration-base);
  }

  .sidebar.is-offcanvas.is-open {
    transform: none;
    visibility: visible;
    box-shadow: var(--shadow-lg);
    transition: transform var(--duration-base) var(--ease-out);
  }
}
</style>
