<script setup lang="ts">
import { watch } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { clearSession, user } from '@/auth'

const router = useRouter()

// 请求发现登录失效时，即使没有手动切换页面，也能回到登录页。
watch(user, (currentUser) => {
  if (!currentUser && router.currentRoute.value.meta.requiresAuth) {
    void router.replace('/login')
  }
})

async function logout() {
  clearSession()
  await router.replace('/login')
}
</script>

<template>
  <header class="site-header">
    <RouterLink class="brand" :to="user ? '/transactions' : '/login'">
      <span class="brand-mark" aria-hidden="true">▤</span>
      <span>口袋账本<small>把生活，一笔一笔记下来。</small></span>
    </RouterLink>
    <nav aria-label="主导航">
      <template v-if="user">
        <RouterLink to="/transactions">账单</RouterLink>
        <span class="user-chip">☺ {{ user.username }}</span>
        <button type="button" @click="logout">退出登录</button>
      </template>
      <template v-else>
        <RouterLink to="/login">登录</RouterLink>
        <RouterLink to="/register">注册</RouterLink>
      </template>
    </nav>
  </header>
  <main class="page">
    <RouterView />
  </main>
  <footer class="site-footer">
    <span>POCKET NOTES / 口袋账本</span>
    <span>认真记账，好好生活 ✳</span>
  </footer>
</template>
