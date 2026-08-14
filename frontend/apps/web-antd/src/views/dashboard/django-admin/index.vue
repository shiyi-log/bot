<script lang="ts" setup>
import { onMounted } from 'vue';

import { Page } from '@vben/common-ui';
import { openWindow } from '@vben/utils';

import { Alert, Button, Card } from 'ant-design-vue';

const adminUrl = 'http://127.0.0.1:8000/admin/';

onMounted(() => {
  openWindow(adminUrl, { target: '_blank' });
});

function openAdmin() {
  openWindow(adminUrl, { target: '_blank' });
}
</script>

<template>
  <Page description="打开 Django 原生后台" title="Django Admin">
    <Card>
      <Alert
        message="已为你打开 Django Admin"
        description="如果浏览器拦截了新窗口，请点击下方按钮手动打开。"
        show-icon
        type="info"
      />
      <div class="mt-4">
        <Button type="primary" @click="openAdmin">打开 Django Admin</Button>
      </div>
    </Card>
  </Page>
</template>
