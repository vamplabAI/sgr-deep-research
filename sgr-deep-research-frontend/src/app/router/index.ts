import { createRouter, createWebHistory } from 'vue-router'

const ROUTES = [
  {
    path: '/',
    name: 'Workspace',
    component: () => import('../../pages/WorkspacePage.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: ROUTES,
})

export default router
