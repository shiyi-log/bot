<script lang="ts" setup>
import { reactive } from 'vue';

import { Page } from '@vben/common-ui';

import { Button, Card, Form, Input, message } from 'ant-design-vue';

import { changeDashboardMyPasswordApi } from '#/api/admin';

const form = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
});

const loading = reactive({ value: false });

async function submit() {
  loading.value = true;
  try {
    await changeDashboardMyPasswordApi({ ...form });
    message.success('密码修改成功，请重新登录');
    form.old_password = '';
    form.new_password = '';
    form.confirm_password = '';
  } catch (error: any) {
    message.error(error?.message || '密码修改失败');
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <Page description="修改当前登录管理员密码" title="密码修改">
    <Card class="password-card">
      <Form layout="vertical">
        <Form.Item label="旧密码">
          <Input.Password
            v-model:value="form.old_password"
            :visibility-toggle="true"
            placeholder="请输入旧密码"
          />
        </Form.Item>
        <Form.Item label="新密码">
          <Input.Password
            v-model:value="form.new_password"
            :visibility-toggle="true"
            placeholder="请输入新密码"
          />
        </Form.Item>
        <Form.Item label="确认新密码">
          <Input.Password
            v-model:value="form.confirm_password"
            :visibility-toggle="true"
            placeholder="再次输入新密码"
          />
        </Form.Item>
        <Button type="primary" :loading="loading.value" @click="submit"
          >保存新密码</Button
        >
      </Form>
    </Card>
  </Page>
</template>

<style scoped>
.password-card {
  max-width: 560px;
}
</style>
