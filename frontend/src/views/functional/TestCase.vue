<template>
  <div class="page">
    <p class="hint">查看 AI 生成的结构化测试用例，可按项目或需求筛选，支持导出与删除。</p>

    <div class="toolbar">
      <el-select
        v-model="filterProjectId"
        placeholder="全部项目"
        filterable
        clearable
        class="filter-select"
        @change="handleProjectChange"
      >
        <el-option label="全部" value="" />
        <el-option
          v-for="item in projects"
          :key="item.id"
          :label="item.name"
          :value="item.id"
        />
      </el-select>
      <el-select
        v-model="filterRequirementId"
        placeholder="全部需求"
        filterable
        clearable
        class="filter-select"
      >
        <el-option label="全部" value="" />
        <el-option
          v-for="item in requirementOptions"
          :key="item.id"
          :label="item.label"
          :value="item.id"
        />
      </el-select>
      <el-button type="primary" plain icon="el-icon-download" :loading="exporting" @click="handleExport">
        导出 Excel
      </el-button>
      <el-button
        type="danger"
        plain
        icon="el-icon-delete"
        :disabled="!selectedRows.length"
        :loading="deleting"
        @click="handleBatchDelete"
      >
        批量删除{{ selectedRows.length ? `（${selectedRows.length}）` : '' }}
      </el-button>
      <el-button icon="el-icon-refresh" :loading="loading" @click="fetchList">刷新</el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="tableData"
      border
      stripe
      class="case-table"
      empty-text="暂无测试用例，请先在需求管理中生成"
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="46" align="center" />
      <el-table-column prop="case_no" label="编号" width="150" show-overflow-tooltip />
      <el-table-column prop="module" label="模块" width="140" show-overflow-tooltip />
      <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
      <el-table-column prop="precondition" label="前置条件" min-width="160" show-overflow-tooltip />
      <el-table-column prop="steps" label="测试步骤" min-width="220" show-overflow-tooltip />
      <el-table-column prop="expected_result" label="预期结果" min-width="180" show-overflow-tooltip />
      <el-table-column prop="priority" label="优先级" width="90" />
      <el-table-column prop="creator_name" label="创建人" width="120" show-overflow-tooltip />
      <el-table-column prop="project_name" label="所属项目" min-width="120" show-overflow-tooltip />
      <el-table-column prop="requirement_title" label="关联需求" min-width="160" show-overflow-tooltip />
      <el-table-column label="生成时间" width="170">
        <template slot-scope="scope">
          {{ formatTime(scope.row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right" align="center">
        <template slot-scope="scope">
          <el-button type="text" class="btn-view" @click="openDetail(scope.row)">详情</el-button>
          <el-button type="text" class="btn-delete" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <el-pagination
        background
        :current-page="page"
        :page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="handlePageChange"
        @size-change="handlePageSizeChange"
      />
    </div>

    <el-dialog
      title="用例详情"
      :visible.sync="detailVisible"
      width="720px"
      top="8vh"
    >
      <div v-if="detailRow" class="detail-body">
        <div class="detail-item"><span class="label">编号</span>{{ detailRow.case_no || '-' }}</div>
        <div class="detail-item"><span class="label">模块</span>{{ detailRow.module || '-' }}</div>
        <div class="detail-item"><span class="label">标题</span>{{ detailRow.title || '-' }}</div>
        <div class="detail-item"><span class="label">优先级</span>{{ detailRow.priority || '-' }}</div>
        <div class="detail-item"><span class="label">创建人</span>{{ detailRow.creator_name || '-' }}</div>
        <div class="detail-item"><span class="label">所属项目</span>{{ detailRow.project_name || '-' }}</div>
        <div class="detail-item"><span class="label">关联需求</span>{{ detailRow.requirement_title || '-' }}</div>
        <div class="detail-block">
          <div class="label">前置条件</div>
          <pre>{{ detailRow.precondition || '无' }}</pre>
        </div>
        <div class="detail-block">
          <div class="label">测试步骤</div>
          <pre>{{ detailRow.steps || '无' }}</pre>
        </div>
        <div class="detail-block">
          <div class="label">预期结果</div>
          <pre>{{ detailRow.expected_result || '无' }}</pre>
        </div>
      </div>
      <div slot="footer">
        <el-button @click="detailVisible = false">关闭</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { Message, MessageBox } from 'element-ui'
import {
  batchDeleteFunctionalTestCases,
  deleteFunctionalTestCase,
  exportFunctionalTestCases,
  listFunctionalProjects,
  listFunctionalTestCases,
  getFunctionalTestCase
} from '@/api/functionalTest'

function saveBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

function stemFilename(name) {
  const text = String(name || '').trim()
  if (!text) return ''
  return text.replace(/\.[^.\\/]+$/, '')
}

export default {
  name: 'FunctionalTestCase',
  data() {
    return {
      loading: false,
      exporting: false,
      deleting: false,
      selectedRows: [],
      projects: [],
      tableData: [],
      page: 1,
      pageSize: 20,
      total: 0,
      filterProjectId: '',
      filterRequirementId: '',
      detailVisible: false,
      detailRow: null
    }
  },
  computed: {
    requirementOptions() {
      const rows = []
      ;(this.projects || []).forEach(project => {
        if (this.filterProjectId && project.id !== this.filterProjectId) return
        ;(project.requirements || []).forEach(item => {
          rows.push({
            id: item.id,
            title: item.title || '',
            source_filename: item.source_filename || '',
            label: `${project.name} / ${item.title || item.source_filename || `文档#${item.id}`}`
          })
        })
      })
      return rows
    },
    exportFilename() {
      let name = ''
      if (this.filterRequirementId) {
        const selected = this.requirementOptions.find(item => item.id === this.filterRequirementId)
        name = stemFilename((selected && (selected.title || selected.source_filename)) || '')
      }
      if (!name) {
        const titles = [...new Set((this.tableData || []).map(item => stemFilename(item.requirement_title)).filter(Boolean))]
        if (titles.length === 1) name = titles[0]
      }
      return `${name || '测试用例'}.xlsx`
    }
  },
  watch: {
    '$route.query': {
      immediate: true,
      handler(query) {
        this.filterProjectId = query.project_id ? Number(query.project_id) : ''
        this.filterRequirementId = query.requirement_id ? Number(query.requirement_id) : ''
      }
    },
    filterProjectId() {
      if (this.filterRequirementId && !this.requirementOptions.some(item => item.id === this.filterRequirementId)) {
        this.filterRequirementId = ''
      }
    },
    filterRequirementId: 'handleFilterChange',
    filterProjectId: 'handleFilterChange'
  },
  created() {
    this.bootstrap()
  },
  methods: {
    formatTime(value) {
      if (!value) return ''
      return String(value).replace('T', ' ').slice(0, 19)
    },
    async bootstrap() {
      await this.fetchProjects()
      await this.fetchList()
    },
    async fetchProjects() {
      try {
        const res = await listFunctionalProjects()
        this.projects = (res && res.data) || []
      } catch (e) {
        this.projects = []
      }
    },
    handleProjectChange() {
      if (this.filterRequirementId && !this.requirementOptions.some(item => item.id === this.filterRequirementId)) {
        this.filterRequirementId = ''
      }
    },
    handleFilterChange() {
      this.page = 1
      this.fetchList()
    },
    handlePageChange(page) {
      this.page = page
      this.fetchList()
    },
    handlePageSizeChange(size) {
      this.pageSize = size
      this.page = 1
      this.fetchList()
    },
    handleSelectionChange(rows) {
      this.selectedRows = rows || []
    },
    buildQueryParams(includePage = false) {
      const params = {}
      if (this.filterProjectId) params.project_id = this.filterProjectId
      if (this.filterRequirementId) params.requirement_id = this.filterRequirementId
      if (includePage) {
        params.page = this.page
        params.page_size = this.pageSize
      }
      return params
    },
    async fetchList() {
      this.loading = true
      try {
        const res = await listFunctionalTestCases(this.buildQueryParams(true))
        const payload = (res && res.data) || {}
        this.tableData = payload.items || []
        this.total = payload.total || 0
        this.page = payload.page || this.page
        this.pageSize = payload.page_size || this.pageSize
      } catch (e) {
        this.tableData = []
        this.total = 0
      } finally {
        this.loading = false
      }
    },
    async refreshAfterDelete() {
      this.selectedRows = []
      await this.fetchList()
      if (!this.tableData.length && this.page > 1) {
        this.page -= 1
        await this.fetchList()
      }
    },
    handleDelete(row) {
      const name = row.case_no || row.title || `用例#${row.id}`
      MessageBox.confirm(`确定删除用例「${name}」吗？删除后不可恢复。`, '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          const res = await deleteFunctionalTestCase(row.id)
          Message.success((res && res.msg) || '删除成功')
          if (this.detailRow && this.detailRow.id === row.id) {
            this.detailVisible = false
            this.detailRow = null
          }
          await this.refreshAfterDelete()
        } catch (e) {
          // 错误提示已由拦截器处理
        }
      }).catch(() => {})
    },
    handleBatchDelete() {
      const ids = this.selectedRows.map(item => item.id).filter(Boolean)
      if (!ids.length) {
        Message.warning('请先选择要删除的用例')
        return
      }
      MessageBox.confirm(`确定删除选中的 ${ids.length} 条用例吗？删除后不可恢复。`, '批量删除', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        this.deleting = true
        try {
          const res = await batchDeleteFunctionalTestCases(ids)
          Message.success((res && res.msg) || '删除成功')
          await this.refreshAfterDelete()
        } catch (e) {
          // 错误提示已由拦截器处理
        } finally {
          this.deleting = false
        }
      }).catch(() => {})
    },
    async handleExport() {
      this.exporting = true
      try {
        const blob = await exportFunctionalTestCases(this.buildQueryParams())
        saveBlob(blob, this.exportFilename)
        Message.success('导出成功')
      } catch (e) {
        // 错误提示已由拦截器处理
      } finally {
        this.exporting = false
      }
    },
    async openDetail(row) {
      this.detailRow = row
      this.detailVisible = true
      try {
        const res = await getFunctionalTestCase(row.id)
        if (res && res.data) {
          this.detailRow = res.data
        }
      } catch (e) {
        // 列表摘要仍可展示
      }
    }
  }
}
</script>

<style scoped>
.page {
  text-align: left;
}

.hint {
  margin: 0 0 16px !important;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.filter-select {
  width: 220px;
}

.case-table {
  width: 100%;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.btn-view {
  color: #0f766e;
}

.btn-delete {
  color: #dc2626;
}

.detail-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-item {
  font-size: 14px;
  color: #374151;
}

.detail-item .label,
.detail-block .label {
  display: inline-block;
  min-width: 72px;
  margin-right: 8px;
  color: #6b7280;
}

.detail-block pre {
  margin: 8px 0 0;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.55;
}
</style>
