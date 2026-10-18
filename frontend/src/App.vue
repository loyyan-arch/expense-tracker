<script setup lang="ts">
import { ref, watch } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import {
  user, logout as endSession, authReady, authRestoreError,
  restoreSession, authErrorMessage,
} from '@/auth'

const router = useRouter()
const loggingOut = ref(false)
const logoutError = ref('')
const retrying = ref(false)

// 请求发现登录失效时，即使没有手动切换页面，也能回到登录页。
watch(user, (currentUser) => {
  if (!currentUser && router.currentRoute.value.meta.requiresAuth) {
    void router.replace('/login')
  }
})

async function logout() {
  if (loggingOut.value) return
  loggingOut.value = true
  logoutError.value = ''
  try {
    await endSession()
    await router.replace('/login')
  } catch (error) {
    logoutError.value = `退出未确认：${authErrorMessage(error)}，请重试`
  } finally {
    loggingOut.value = false
  }
}

async function retryRestore() {
  if (retrying.value) return
  retrying.value = true
  try {
    await restoreSession()
    const route = router.currentRoute.value
    if (!user.value && route.meta.requiresAuth) await router.replace('/login')
    else if (user.value && route.meta.guestOnly) await router.replace('/transactions')
  } catch {
    // 错误信息由 restoreSession 保存，继续显示重试入口。
  } finally {
    retrying.value = false
  }
}
</script>

<template>
  <header class="site-header">
    <RouterLink class="brand" :to="user ? '/transactions' : '/login'">
      <span class="brand-mark" aria-hidden="true">▤</span>
      <span>口袋账本<small>把生活，一笔一笔记下来。</small></span>
    </RouterLink>
    <nav v-if="authReady" aria-label="主导航">
      <template v-if="user">
        <RouterLink to="/transactions">账单</RouterLink>
        <RouterLink to="/statistics/yearly">年度统计</RouterLink>
        <span class="user-chip">☺ {{ user.username }}</span>
        <button type="button" :disabled="loggingOut" @click="logout">
          {{ loggingOut ? '退出中…' : '退出登录' }}
        </button>
      </template>
      <template v-else>
        <RouterLink to="/login">登录</RouterLink>
        <RouterLink to="/register">注册</RouterLink>
      </template>
    </nav>
  </header>
  <main class="page">
    <section v-if="!authReady" class="paper-card" aria-live="polite">
      <template v-if="authRestoreError">
        <p role="alert">暂时无法确认登录状态：{{ authRestoreError }}</p>
        <button type="button" :disabled="retrying" @click="retryRestore">
          {{ retrying ? '重试中…' : '重新连接' }}
        </button>
      </template>
      <p v-else>正在恢复登录状态…</p>
    </section>
    <template v-else>
      <p v-if="logoutError" role="alert">{{ logoutError }}</p>
      <RouterView />
    </template>
  </main>
  <footer class="site-footer">
    <span>POCKET NOTES / 口袋账本</span>
    <span>认真记账，好好生活 ✳</span>
  </footer>
</template>
