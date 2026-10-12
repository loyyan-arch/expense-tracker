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
    <h1>个人记账</h1>

    <nav aria-label="主导航">
      <template v-if="user">
        <RouterLink to="/transactions">账单</RouterLink>
        <span>当前用户：{{ user.username }}</span>
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
</template>