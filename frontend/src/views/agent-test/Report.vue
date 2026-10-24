<template>
  <div class="page">
    <p class="hint">Agent 用例执行报告。列表仅展示摘要；点击「查看详情」展开完整调用流（响应时间、工具链、代码覆盖率及埋点原始数据）。</p>

    <div class="toolbar">
      <el-select
        v-model="filterProjectId"
        placeholder="全部项目"
        filterable
        clearable
        class="filter-item"
        @change="handleFilterChange"
      >
        <el-option label="全部项目" value="" />
        <el-option
          v-for="item in projects"
          :key="item.id"
          :label="item.name"
          :value="item.id"
        />
      </el-select>
      <el-button type="primary" plain icon="el-icon-search" @click="handleFilterChange">查询</el-button>
      <el-button icon="el-icon-refresh" :loading="loading" @click="fetchList">刷新</el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="tableData"
      border
      stripe
      empty-text="暂无报告，请先在用例管理中执行测试"
    >
      <el-table-column prop="id" label="报告id" width="90" />
      <el-table-column prop="task_name" label="用例" min-width="160" show-overflow-tooltip />
      <el-table-column prop="project_name" label="项目" min-width="120" show-overflow-tooltip />
      <el-table-column prop="request_id" label="request_id" min-width="180" show-overflow-tooltip />
      <el-table-column label="结果" width="100">
        <template slot-scope="scope">
          <el-tag size="small" :type="verifyType(scope.row.verify_status)">
            {{ scope.row.verify_status_label || '-' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="score" label="评分" width="80" />
      <el-table-column label="耗时" width="110">
        <template slot-scope="scope">{{ scope.row.elapsed_ms }} ms</template>
      </el-table-column>
      <el-table-column prop="summary" label="摘要" min-width="220" show-overflow-tooltip />
      <el-table-column prop="created_at" label="时间" width="170" />
      <el-table-column label="操作" width="120" fixed="right" align="center">
        <template slot-scope="scope">
          <el-button type="text" class="btn-action" @click="openDetail(scope.row)">查看详情</el-button>
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
        layout="total, sizes, prev, pager, next"
        @current-change="p => { page = p; fetchList() }"
        @size-change="s => { pageSize = s; page = 1; fetchList() }"
      />
    </div>

    <el-dialog
      title="报告详情"
      :visible.sync="detailVisible"
      width="860px"
      top="5vh"
      @closed="onClosed"
    >
      <div v-loading="detailLoading">
        <template v-if="detail">
          <div class="meta">
            <div><span class="label">用例</span>{{ detail.task_name }}</div>
            <div><span class="label">结果</span>{{ detail.verify_status_label }}</div>
            <div><span class="label">评分</span>{{ detail.score }}</div>
            <div><span class="label">耗时</span>{{ detail.elapsed_ms }} ms</div>
            <div><span class="label">request_id</span>{{ detail.request_id }}</div>
            <div><span class="label">摘要</span>{{ detail.summary }}</div>
          </div>

          <div class="section-title">对话明细</div>
          <dialogue-turns :turns="reportDialogueTurns" />
          <div class="section-title">代码覆盖率</div>
          <code-coverage-view v-if="hasCoverage" :source="coverageSource" />
          <div v-else class="empty-detail">暂无覆盖率数据</div>

          <el-collapse v-model="activePanels">
            <el-collapse-item title="点击展开埋点调用流（不含重复的对话与覆盖率）" name="flow">
              <div class="section-title">埋点调用流程</div>
              <el-timeline>
                <el-timeline-item
                  v-for="(step, idx) in timelineSteps"
                  :key="idx"
                  :timestamp="step.created_at || ''"
                  placement="top"
                >
                  <div class="flow-title">{{ step.title || step.step }}</div>
                  <div v-if="step.execution_time_ms != null" class="flow-meta">耗时：{{ step.execution_time_ms }} ms</div>
                  <div v-if="step.tools_name" class="flow-meta">工具：{{ step.tools_name }}</div>
                  <pre v-if="stepBlock(step)" class="flow-pre">{{ stepBlock(step) }}</pre>
                </el-timeline-item>
              </el-timeline>
              <div class="section-title">埋点 summary</div>
              <pre class="flow-pre">{{ pretty(detail.detail && detail.detail.buried && detail.detail.buried.summary) }}</pre>
              <div class="section-title">埋点 logs</div>
              <pre class="flow-pre">{{ pretty(detail.detail && detail.detail.buried && detail.detail.buried.logs) }}</pre>
              <div class="section-title">Agent 原始响应</div>
              <pre class="flow-pre">{{ pretty(detail.detail && (detail.detail.chat_rpc || detail.detail.chat_result)) }}</pre>
            </el-collapse-item>
          </el-collapse>
        </template>
      </div>
      <div slot="footer">
        <el-button @click="detailVisible = false">关闭</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import CodeCoverageView from '@/components/agent-test/CodeCoverageView.vue'
import DialogueTurns from '@/components/agent-test/DialogueTurns.vue'
import { getAgentReport, listAgentProjects, listAgentReports } from '@/api/agentTest'

export default {
  name: 'AgentTestReport',
  components: { CodeCoverageView, DialogueTurns },
  data() {
    return {
      loading: false,
      detailLoading: false,
      projects: [],
      tableData: [],
      filterProjectId: '',
      page: 1,
      pageSize: 20,
      total: 0,
      detailVisible: false,
      detail: null,
      activePanels: []
    }
  },
  computed: {
    flowSteps() {
      return (this.detail && this.detail.detail && this.detail.detail.flow) || []
    },
    timelineSteps() {
      return this.flowSteps.filter(
        s => s && s.step !== 'dialogue' && s.step !== 'trace_detail'
      )
    },
    coverageSource() {
      const buried = (this.detail && this.detail.detail && this.detail.detail.buried) || {}
      if (buried.traces && (buried.traces.traces || Array.isArray(buried.traces))) {
        return buried.traces
      }
      return this.flowSteps.filter(
        s => s && s.step === 'trace_detail' && s.execution_details && s.execution_details.length
      )
    },
    hasCoverage() {
      const src = this.coverageSource
      if (!src) return false
      if (Array.isArray(src)) return src.length > 0
      if (Array.isArray(src.traces)) return src.traces.length > 0
      return !!(src.execution_details && src.execution_details.length)
    },
    reportDialogueTurns() {
      const d = (this.detail && this.detail.detail) || {}
      if (d.turns && d.turns.length) return d.turns
      const dialogue = this.flowSteps.find(s => s && s.step === 'dialogue' && s.turns)
      return (dialogue && dialogue.turns) || []
    }
  },
  created() {
    this.fetchProjects()
    this.fetchList()
  },
  methods: {
    pretty(obj) {
      if (obj == null || obj === '') return '（无）'
      try {
        return JSON.stringify(obj, null, 2)
      } catch (e) {
        return String(obj)
      }
    },
    stepBlock(step) {
      if (!step) return ''
      if (step.step === 'trace_detail' || step.step === 'dialogue') return ''
      if (step.step === 'validation') {
        return this.pretty({
          tool_validation: step.tool_validation,
          result_validation: step.result_validation,
          chat_answer_preview: step.chat_answer_preview
        })
      }
      if (step.data) {
        const text = typeof step.data === 'string' ? step.data : this.pretty(step.data)
        return text.length > 1200 ? `${text.slice(0, 1200)}...` : text
      }
      return ''
    },
    verifyType(status) {
      if (status === 'passed') return 'success'
      if (status === 'failed') return 'danger'
      return 'warning'
    },
    async fetchProjects() {
      try {
        const res = await listAgentProjects()
        this.projects = (res && res.data) || []
      } catch (e) {
        this.projects = []
      }
    },
    async fetchList() {
      this.loading = true
      try {
        const res = await listAgentReports({
          project_id: this.filterProjectId || undefined,
          page: this.page,
          page_size: this.pageSize
        })
        const data = (res && res.data) || {}
        this.tableData = data.items || []
        this.total = data.total || 0
      } catch (e) {
        this.tableData = []
        this.total = 0
      } finally {
        this.loading = false
      }
    },
    handleFilterChange() {
      this.page = 1
      this.fetchList()
    },
    async openDetail(row) {
      this.detailVisible = true
      this.activePanels = []
      this.detail = null
      this.detailLoading = true
      try {
        const res = await getAgentReport(row.id)
        this.detail = (res && res.data) || null
      } catch (e) {
        this.detail = null
      } finally {
        this.detailLoading = false
      }
    },
    onClosed() {
      this.activePanels = []
      this.detail = null
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
  gap: 8px;
  margin-bottom: 16px;
}

.filter-item {
  width: 220px;
}

.pager {
  margin-top: 16px;
  text-align: right;
}

.btn-action {
  color: #0f766e;
}

.meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 16px;
  margin-bottom: 12px;
  font-size: 14px;
  color: #334155;
}

.meta .label {
  display: inline-block;
  min-width: 88px;
  color: #64748b;
}

.section-title {
  margin: 14px 0 6px;
  font-weight: 600;
}

.flow-title {
  font-weight: 600;
}

.flow-meta {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.flow-pre {
  margin: 8px 0 0;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  line-height: 1.5;
  max-height: 280px;
  overflow: auto;
}

.empty-detail {
  color: #94a3b8;
  font-size: 13px;
  margin-bottom: 12px;
}
</style>
