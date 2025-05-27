<template>
  <el-alert
      title="编译进度"
      type="info"
      :closable="false"
      class="status-alert">
    <div class="status-scroll-container">
      <div class="status-text-container">
        <div v-for="(line, index) in logs" :key="'compile-' + index">{{ line }}</div>
        <div v-if="logs.length === 0" class="empty-log">暂无编译日志</div>
      </div>
    </div>
  </el-alert>
</template>

<script>
export default {
  name: 'CompileLogDisplay',
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
