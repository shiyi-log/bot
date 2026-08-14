<script lang="ts" setup>
import { reactive, ref } from 'vue';

import { SliderCaptcha } from '@vben/common-ui';

import { Alert, Button, Card, Input, InputPassword } from 'ant-design-vue';

import { useAuthStore } from '#/store';

const authStore = useAuthStore();
const errorMessage = ref('');
const captchaPassed = ref(false);
const form = reactive({
  otp_token: '',
  password: '',
  username: '',
});

async function handleLogin() {
  errorMessage.value = '';
  if (!form.username || !form.password) {
    errorMessage.value = '请输入用户名和密码';
    return;
  }
  if (!captchaPassed.value) {
    errorMessage.value = '请先完成滑动验证';
    return;
  }
  try {
    await authStore.authLogin({
      otp_token: form.otp_token.trim(),
      password: form.password,
      username: form.username.trim(),
    });
  } catch (error: any) {
    errorMessage.value =
      error?.response?.data?.message || error?.message || '登录失败，请重试';
  }
}
</script>

<template>
  <Card class="password-login-card" :bordered="false">
    <div class="password-login-content" @keydown.enter.prevent="handleLogin">
      <h2 class="password-login-title">后台登录</h2>
      <p class="password-login-desc">请输入账号密码和 Google 动态验证码。</p>

      <Alert
        v-if="errorMessage"
        class="mb-4"
        show-icon
        type="error"
        :message="errorMessage"
      />

      <Input
        v-model:value="form.username"
        class="mb-4"
        autocomplete="username"
        placeholder="用户名"
        size="large"
      />
      <InputPassword
        v-model:value="form.password"
        class="mb-4"
        autocomplete="current-password"
        placeholder="密码"
        size="large"
      />
      <Input
        v-model:value="form.otp_token"
        class="mb-4"
        autocomplete="one-time-code"
        inputmode="numeric"
        :maxlength="6"
        placeholder="Google 验证码（6位）"
        size="large"
      />

      <SliderCaptcha
        v-model="captchaPassed"
        class="mb-6"
        success-text="验证通过"
        text="向右滑动完成验证"
      />

      <Button
        block
        size="large"
        type="primary"
        :loading="authStore.loginLoading"
        @click="handleLogin"
      >
        登录
      </Button>
    </div>
  </Card>
</template>

<style scoped>
.password-login-card {
  width: 100%;
}

.password-login-content {
  text-align: center;
}

.password-login-title {
  margin-bottom: 8px;
  font-size: 24px;
  font-weight: 600;
}

.password-login-desc {
  margin-bottom: 24px;
  color: hsl(var(--muted-foreground));
}
</style>
