import { createRouter, createWebHistory } from 'vue-router'
import { user, restoreSession } from '@/auth'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import TransactionsView from '../views/TransactionsView.vue'
import YearlyStatisticsView from '../views/YearlyStatisticsView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/transactions' },
    { path: '/statistics/yearly', component: YearlyStatisticsView, meta: { requiresAuth: true } },
    {
      path: '/login',
      component: LoginView,
      meta: { guestOnly: true },
    },
    {
      path: '/register',
      component: RegisterView,
      meta: { guestOnly: true },
    },
    {
      path: '/transactions',
      component: TransactionsView,
      meta: { requiresAuth: true },
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  try {
    await restoreSession()
  } catch {
    // 保留目标地址；App 显示恢复失败和重试入口，不把网络故障当退出。
    return
  }
  if (to.meta.requiresAuth && !user.value) {
    return '/login'
  }

  if (to.meta.guestOnly && user.value) {
    return '/transactions'
  }
})

export default router
