<template>
  <div class="page model-page">
    <div class="page-head">
      <h2>模型配置</h2>
      <p>管理不同类型的 AI 模型，支持 Ollama 本地模型与远程 API。</p>
    </div>

    <div class="type-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        type="button"
        class="type-tab"
        :class="{ active: activeType === tab.value }"
        @click="activeType = tab.value"
      >
        {{ tab.label }}<span v-if="tab.count != null"> ({{ tab.count }})</span>
      </button>
    </div>

    <div v-loading="loading" class="model-grid">
      <div
        v-for="item in filteredList"
        :key="item.id"
        class="model-card"
        @click="openEdit(item)"
      >
        <div class="card-top">
          <div class="card-icon">
            <i :class="typeIcon(item.model_type)" />
          </div>
          <div class="card-actions" @click.stop>
            <el-dropdown trigger="click" @command="cmd => handleCardAction(cmd, item)">
              <span class="card-more"><i class="el-icon-more" /></span>
              <el-dropdown-menu slot="dropdown">
                <el-dropdown-item v-if="!item.is_default" command="default">设为默认</el-dropdown-item>
                <el-dropdown-item command="edit">编辑</el-dropdown-item>
                <el-dropdown-item command="delete">删除</el-dropdown-item>
              </el-dropdown-menu>
            </el-dropdown>
          </div>
        </div>
        <div class="card-title">{{ item.name }}</div>
        <div class="card-model">{{ item.model }}</div>
        <div class="card-meta">
          <span class="meta-tag">{{ sourceLabel(item) }}</span>
          <span class="meta-tag">{{ item.model_type_label }}</span>
          <span v-if="item.dimension" class="meta-tag">向量维度 {{ item.dimension }}</span>
          <span v-if="item.is_default" class="meta-tag default">默认</span>
        </div>
      </div>

      <button type="button" class="model-card add-card" @click="openCreate">
        <i class="el-icon-plus" />
        <span>添加模型</span>
      </button>
    </div>

    <ModelConfigDrawer
      :visible.sync="drawerVisible"
      :value="editing"
      :initial-type="createType"
      @saved="fetchList"
    />
  </div>
</template>

<script>
import { Message, MessageBox } from 'element-ui'
import { MODEL_TYPES, deleteLlmConfig, listLlmConfigs, setDefaultLlmConfig } from '@/api/llmConfig'
import ModelConfigDrawer from '@/components/ModelConfigDrawer.vue'

const TAB_ALL = 'all'

export default {
  name: 'LlmConfig',
  components: { ModelConfigDrawer },
  data() {
    return {
      loading: false,
      tableData: [],
      activeType: TAB_ALL,
      drawerVisible: false,
      editing: null,
      createType: 'chat'
    }
  },
  computed: {
    tabs() {
      const counts = {}
      this.tableData.forEach(item => {
        counts[item.model_type] = (counts[item.model_type] || 0) + 1
      })
      return [
        { value: TAB_ALL, label: '全部', count: this.tableData.length },
        ...MODEL_TYPES.map(item => ({
          value: item.value,
          label: item.label,
          count: counts[item.value] || 0
        }))
      ]
    },
    filteredList() {
      if (this.activeType === TAB_ALL) return this.tableData
      return this.tableData.filter(item => item.model_type === this.activeType)
    }
  },
  created() {
    this.fetchList()
  },
  methods: {
    typeIcon(modelType) {
      const item = MODEL_TYPES.find(row => row.value === modelType)
      return (item && item.icon) || 'el-icon-cpu'
    },
    sourceLabel(item) {
      if (item.source === 'ollama' || item.provider === 'ollama') return 'Ollama'
      return item.provider_label || 'API'
    },
    async fetchList() {
      this.loading = true
      try {
        const res = await listLlmConfigs()
        this.tableData = (res && res.data) || []
      } catch (e) {
        this.tableData = []
      } finally {
        this.loading = false
      }
    },
    openCreate() {
      this.editing = null
      this.createType = this.activeType === TAB_ALL ? 'chat' : this.activeType
      this.drawerVisible = true
    },
    openEdit(row) {
      this.editing = row
      this.drawerVisible = true
    },
    async handleCardAction(command, row) {
      if (command === 'edit') {
        this.openEdit(row)
        return
      }
      if (command === 'default') {
        try {
          const res = await setDefaultLlmConfig(row.id)
          Message.success((res && res.msg) || '已设为默认模型')
          await this.fetchList()
        } catch (e) {
          // 拦截器已提示
        }
        return
      }
      if (command === 'delete') {
        MessageBox.confirm(`确定删除「${row.name}」吗？`, '删除模型', {
          type: 'warning',
          confirmButtonText: '删除',
          cancelButtonText: '取消'
        })
          .then(async () => {
            const res = await deleteLlmConfig(row.id)
            Message.success((res && res.msg) || '已删除')
            await this.fetchList()
          })
          .catch(() => {})
      }
    }
  }
}
</script>

<style scoped>
.model-page {
  text-align: left;
}

.page-head h2 {
  margin: 0 0 6px !important;
  font-size: 22px;
  font-weight: 650;
  color: #111827;
}

.page-head p {
  margin: 0 0 18px !important;
  color: #6b7280;
  font-size: 14px;
}

.type-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 18px;
}

.type-tab {
  height: 34px;
  padding: 0 14px;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  background: #fff;
  color: #374151;
  font-size: 13px;
  cursor: pointer;
}

.type-tab.active {
  border-color: #0f766e;
  background: #ecfdf5;
  color: #0f766e;
  font-weight: 600;
}

.model-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
  min-height: 180px;
}

.model-card {
  position: relative;
  min-height: 148px;
  padding: 16px;
  border: 1px solid #e8edf3;
  border-radius: 14px;
  background: #fff;
  cursor: pointer;
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
}

.model-card:hover {
  border-color: #99f6e4;
  box-shadow: 0 8px 24px rgba(15, 118, 110, 0.08);
}

.card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 12px;
}

.card-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: #ecfdf5;
  color: #0f766e;
  font-size: 18px;
}

.card-more {
  color: #9ca3af;
  cursor: pointer;
  padding: 4px;
}

.card-title {
  font-size: 15px;
  font-weight: 650;
  color: #111827;
  margin-bottom: 4px;
}

.card-model {
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 12px;
  word-break: break-all;
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.meta-tag {
  padding: 2px 8px;
  border-radius: 999px;
  background: #f3f4f6;
  color: #4b5563;
  font-size: 12px;
}

.meta-tag.default {
  background: #ecfdf5;
  color: #0f766e;
}

.add-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-style: dashed;
  color: #6b7280;
  background: #fbfcfe;
}

.add-card i {
  font-size: 22px;
  color: #0f766e;
}

.add-card span {
  font-size: 14px;
  font-weight: 600;
}
</style>
