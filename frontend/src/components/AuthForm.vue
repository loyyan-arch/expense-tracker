<script setup lang="ts">
import WalletDoodle from './WalletDoodle.vue'
import { computed, onBeforeUnmount, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import {
  authErrorMessage,
  authNotice,
  login,
  register,
} from '@/auth'

const props = defineProps<{
  mode: 'login' | 'register'
}>()

const router = useRouter()
const isRegister = computed(() => props.mode === 'register')
const username = ref('')
const password = ref('')
const loading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

let controller: AbortController | undefined

onBeforeUnmount(() => {
  controller?.abort()
})

async function submit() {
  if (loading.value) return

  loading.value = true
  errorMessage.value = ''
  successMessage.value = ''

  const request = new AbortController()
  controller = request

  try {
    if (isRegister.value) {
      await register(username.value, password.value, request.signal)

      if (request.signal.aborted) return

      successMessage.value = '注册成功，请前往登录'
    } else {
      await login(username.value, password.value, request.signal)

      if (request.signal.aborted) return

      await router.replace('/transactions')
    }
  } catch (error) {
    if (!request.signal.aborted) {
      errorMessage.value = authErrorMessage(error)
    }
  } finally {
    password.value = ''
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-layout">
    <div class="auth-intro">
      <span class="eyebrow">A LITTLE NOTE, A BETTER DAY</span>
      <h1>生活的小账，<br />慢慢记，好好过。</h1>
      <p>一杯咖啡，一次出发，一份小小的快乐。<br />让每一笔收支，都有迹可循。</p>
      <WalletDoodle class="auth-mascot" />
      <div class="intro-note">✳ 每一笔小记录，都是生活的足迹</div>
    </div>
    <section class="auth-card paper-card">
      <span class="eyebrow">{{ isRegister ? 'YOUR STORY STARTS HERE' : 'HELLO, GOOD TO SEE YOU' }}</span>
      <h2>{{ isRegister ? '注册账号' : '欢迎回到账本' }}</h2>
      <p class="muted">{{ isRegister ? '拥有自己的小账本，从今天开始。' : '登录一下，接着记录今天的小日常。' }}</p>
      <p v-if="!isRegister && authNotice" role="status">
        {{ authNotice }}
      </p>

      <form @submit.prevent="submit">
        <label for="username">用户名</label>
        <input
          id="username"
          v-model="username"
          name="username"
          placeholder="你的用户名"
          autocomplete="username"
          required
          minlength="3"
          maxlength="32"
          :pattern="isRegister ? '[a-z0-9_]+' : undefined"
          :disabled="loading"
          aria-describedby="username-help"
        />

        <small id="username-help">
          {{ isRegister
            ? '3～32 位，只能包含小写字母、数字和下划线'
            : '请输入注册时使用的用户名'
          }}
        </small>

        <label for="password">密码</label>
        <input
          id="password"
          v-model="password"
          name="password"
          placeholder="输入你的密码"
          type="password"
          :autocomplete="isRegister ? 'new-password' : 'current-password'"
          required
          :minlength="isRegister ? 7 : 1"
          maxlength="128"
          :disabled="loading"
        />

        <small v-if="isRegister">密码长度为 7～128 位</small>

        <button type="submit" :disabled="loading">
          {{ loading ? '提交中…' : isRegister ? '注册' : '登录' }}
        </button>
      </form>

      <p v-if="errorMessage" role="alert" class="error-message">
        {{ errorMessage }}
      </p>

      <p role="status">{{ successMessage }}</p>

      <RouterLink :to="isRegister ? '/login' : '/register'">
        {{ isRegister ? '已有账号，前往登录' : '没有账号，前往注册' }}
      </RouterLink>
    </section>
  </div>
</template>
