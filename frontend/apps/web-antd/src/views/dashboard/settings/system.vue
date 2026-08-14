<script lang="ts" setup>
import SiteConfigGroup from './components/site-config-group.vue';
</script>

<template>
  <SiteConfigGroup
    group-key="system"
    title="系统设置"
    description="后台密码、Google 验证器、机器人基础配置与 Telegram API。"
    :show-password-card="true"
  />
</template>
