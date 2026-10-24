<template>
  <div class="page">
    <p class="hint">查看 Agent 安全相关检测报告，例如越权、注入与敏感信息泄露。</p>
    <el-table :data="[]" border stripe empty-text="暂无安全报告">
      <el-table-column prop="name" label="报告名称" min-width="180" />
      <el-table-column prop="level" label="风险等级" width="110" />
      <el-table-column prop="created_at" label="时间" width="180" />
    </el-table>
  </div>
</template>

<script>
export default {
  name: 'AgentTestSecurityReport'
}
</script>

<style scoped>
.page {
  text-align: left;
}

.hint {
  margin: 0 0 16px !important;
}
</style>
