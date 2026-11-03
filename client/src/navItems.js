// Single source of truth for the sidebar and the header title
export const navItems = [
  { path: '/', label: 'nav.overview', icon: 'home', group: 'nav.groupOperations', exact: true },
  { path: '/inventory', label: 'nav.inventory', icon: 'package', group: 'nav.groupOperations' },
  { path: '/orders', label: 'nav.orders', icon: 'clipboard-list', group: 'nav.groupOperations' },
  { path: '/restocking', label: 'nav.restocking', icon: 'truck', group: 'nav.groupOperations' },
  { path: '/spending', label: 'nav.finance', icon: 'wallet', group: 'nav.groupAnalytics' },
  { path: '/demand', label: 'nav.demandForecast', icon: 'trending-up', group: 'nav.groupAnalytics' },
  { path: '/reports', label: 'nav.reports', icon: 'file-text', group: 'nav.groupAnalytics' }
]
