<template>
  <el-alert
      title="量化进度"
      type="warning"
      :closable="false"
      class="status-alert">
    <div class="status-scroll-container">
      <div class="status-text-container">
        <div v-for="(line, index) in logs" :key="'quant-' + index">{{ line }}</div>
        <div v-if="logs.length === 0" class="empty-log">暂无量化日志</div>
      </div>
    </div>
  </el-alert>
</template>

<script>
export default {
  name: 'QuantLogDisplay',
  props: {
    logs: {
      type: Array,
      required: true
    }
  }
}
</script>

<style scoped>
.status-scroll-container {
  max-height: 200px;
  overflow-y: auto;
}
.status-text-container {
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
