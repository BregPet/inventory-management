import { ref, computed } from 'vue'

const STORAGE_KEY = 'sidebar-collapsed'
const DESKTOP_QUERY = '(min-width: 1280px)'
const TABLET_QUERY = '(min-width: 768px)'

const readCollapsed = () => {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

// Remembered desktop preference only; the tablet rail default never touches it
const collapsed = ref(readCollapsed())
const tabletExpanded = ref(false)
const mobileOpen = ref(false)
const mode = ref('desktop')

const updateMode = () => {
  if (window.matchMedia(DESKTOP_QUERY).matches) mode.value = 'desktop'
  else if (window.matchMedia(TABLET_QUERY).matches) mode.value = 'tablet'
  else mode.value = 'mobile'
  tabletExpanded.value = false
  mobileOpen.value = false
}

let listening = false
const listen = () => {
  if (listening || typeof window === 'undefined' || !window.matchMedia) return
  listening = true
  updateMode()
  window.matchMedia(DESKTOP_QUERY).addEventListener('change', updateMode)
  window.matchMedia(TABLET_QUERY).addEventListener('change', updateMode)
}

export function useLayout() {
  listen()

  // Icons-only presentation: the desktop choice, or the tablet default
  const isRail = computed(() => {
    if (mode.value === 'desktop') return collapsed.value
    if (mode.value === 'tablet') return !tabletExpanded.value
    return false
  })

  const toggleSidebar = () => {
    if (mode.value === 'desktop') {
      collapsed.value = !collapsed.value
      try {
        localStorage.setItem(STORAGE_KEY, collapsed.value ? '1' : '0')
      } catch {
        // storage unavailable: the choice just won't persist
      }
    } else if (mode.value === 'tablet') {
      tabletExpanded.value = !tabletExpanded.value
    }
  }

  const openMobile = () => { mobileOpen.value = true }
  const closeTransient = () => {
    tabletExpanded.value = false
    mobileOpen.value = false
  }

  return { mode, isRail, collapsed, tabletExpanded, mobileOpen, toggleSidebar, openMobile, closeTransient }
}
