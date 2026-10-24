<template>
  <div class="page">
    <p class="hint">管理 Agent 测试用例。执行测试将调用项目配置的 JSON-RPC Agent，并从埋点服务拉取完整调用流。</p>

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
      <el-input
        v-model="keyword"
        clearable
        placeholder="搜索任务名称"
        class="filter-item"
        @keyup.enter.native="handleFilterChange"
      />
      <el-button type="primary" plain icon="el-icon-search" @click="handleFilterChange">查询</el-button>
      <el-button icon="el-icon-refresh" :loading="loading" @click="fetchList">刷新</el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="tableData"
      border
      stripe
      class="case-table"
      empty-text="暂无用例，请先在添加项目中生成"
    >
      <el-table-column prop="id" label="用例id" width="72" />
      <el-table-column prop="task_name" label="任务名称" min-width="120" show-overflow-tooltip />
      <el-table-column label="用户输入" min-width="240">
        <template slot-scope="scope">
          <div class="io-cell" :title="scope.row.user_input || ''">
            {{ scope.row.user_input || '-' }}
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="tool_chain" label="工具链" min-width="120" show-overflow-tooltip />
      <el-table-column prop="expected_result" label="预期结果" min-width="120" show-overflow-tooltip />
      <el-table-column label="校验状态" width="90">
        <template slot-scope="scope">
          <el-tag size="small" :type="verifyType(scope.row.verify_status)">
            {{ scope.row.verify_status_label || '未校验' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="score" label="评分" width="70" />
      <el-table-column prop="last_run_at" label="最近执行" width="160" />
      <el-table-column label="操作" width="160" fixed="right" align="center">
        <template slot-scope="scope">
          <el-button
            type="text"
            class="btn-action"
            :loading="runningId === scope.row.id"
            @click="handleRun(scope.row)"
          >
            执行测试
          </el-button>
          <el-button type="text" class="btn-action" @click="openResult(scope.row)">
            执行结果
          </el-button>
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
        @current-change="handlePageChange"
        @size-change="handlePageSizeChange"
      />
    </div>

    <el-dialog
      title="执行结果"
      :visible.sync="resultVisible"
      width="820px"
      top="6vh"
      @closed="onResultClosed"
    >
      <div v-if="resultRow" class="result-body" v-loading="detailLoading">
        <div class="result-item"><span class="label">用例</span>{{ resultRow.task_name }}</div>
        <div class="result-item"><span class="label">校验状态</span>{{ resultRow.verify_status_label || resultMeta.verify_status_label || '-' }}</div>
        <div class="result-item"><span class="label">评分</span>{{ displayScore }}</div>
        <div class="result-item"><span class="label">执行时间</span>{{ resultRow.last_run_at || '-' }}</div>
        <div class="result-item" v-if="detail.request_id"><span class="label">request_id</span>{{ detail.request_id }}</div>
        <div class="result-item" v-if="detail.elapsed_ms != null"><span class="label">整轮耗时</span>{{ detail.elapsed_ms }} ms</div>
        <div class="result-block">
          <div class="label">对话明细（每轮输入 / 输出）</div>
          <dialogue-turns
            :turns="resultDialogueTurns"
            :pending-text="'暂无输出，请先执行测试'"
          />
        </div>
        <div class="result-block">
          <div class="label">结果摘要</div>
          <pre>{{ resultRow.last_run_result || resultMeta.last_run_result || '暂无执行结果' }}</pre>
        </div>
        <div class="result-block">
          <div class="label">代码覆盖率</div>
          <code-coverage-view v-if="hasCoverage" :source="coverageSource" />
          <div v-else class="empty-detail">暂无覆盖率数据（执行后展示）</div>
        </div>

        <el-collapse v-model="activePanels" class="flow-collapse" @change="onCollapseChange">
          <el-collapse-item title="点击展开埋点调用流（arrive / invoke / response 等，不含重复的对话与覆盖率）" name="flow">
            <div v-if="!hasDetail" class="empty-detail">暂无详情，请先执行测试</div>
            <template v-else>
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
                  <pre v-if="stepPreview(step)" class="flow-pre">{{ stepPreview(step) }}</pre>
                </el-timeline-item>
              </el-timeline>
              <div class="section-title">埋点 summary</div>
              <pre class="flow-pre">{{ pretty(detail.buried && detail.buried.summary) }}</pre>
              <div class="section-title">埋点 logs</div>
              <pre class="flow-pre">{{ pretty(detail.buried && detail.buried.logs) }}</pre>
              <div class="section-title">Agent 原始响应</div>
              <pre class="flow-pre">{{ pretty(detail.chat_rpc || detail.chat_result) }}</pre>
            </template>
          </el-collapse-item>
        </el-collapse>
      </div>
      <div slot="footer">
        <el-button @click="resultVisible = false">关闭</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { Message } from 'element-ui'
import CodeCoverageView from '@/components/agent-test/CodeCoverageView.vue'
import DialogueTurns from '@/components/agent-test/DialogueTurns.vue'
import {
  getAgentCaseLastRun,
  listAgentCases,
  listAgentProjects,
  runAgentCase
} from '@/api/agentTest'

export default {
  name: 'AgentTestCase',
  components: { CodeCoverageView, DialogueTurns },
  data() {
    return {
      loading: false,
      runningId: null,
      detailLoading: false,
      projects: [],
      tableData: [],
      filterProjectId: '',
      keyword: '',
      page: 1,
      pageSize: 20,
      total: 0,
      resultVisible: false,
      resultRow: null,
      resultMeta: {},
      detail: {},
      activePanels: []
    }
  },
  computed: {
    displayScore() {
      const s = this.resultRow && this.resultRow.score
      if (s == null && this.resultMeta.score == null) return '-'
      return s != null ? s : this.resultMeta.score
    },
    resultDialogueTurns() {
      // 优先用执行落库的按轮 turns（含每轮 answer）
      if (this.detail && this.detail.turns && this.detail.turns.length) {
        return this.detail.turns
      }
      if (this.resultMeta && this.resultMeta.dialogue_turns && this.resultMeta.dialogue_turns.length) {
        return this.resultMeta.dialogue_turns
      }
      if (this.resultRow && this.resultRow.dialogue_turns && this.resultRow.dialogue_turns.length) {
        return this.resultRow.dialogue_turns
      }
      return [{
        turn: 1,
        user_input: (this.resultRow && this.resultRow.user_input) || (this.detail && this.detail.user_input) || '',
        answer: (this.detail && this.detail.actual_answer) || (this.resultRow && this.resultRow.last_run_output) || '',
        executed: !!(this.detail && this.detail.request_id)
      }]
    },
    hasDetail() {
      return this.detail && Object.keys(this.detail).length > 0
    },
    flowSteps() {
      return (this.detail && this.detail.flow) || []
    },
    // 时间线去掉对话/覆盖率，避免与上方专区重复
    timelineSteps() {
      return this.flowSteps.filter(
        s => s && s.step !== 'dialogue' && s.step !== 'trace_detail'
      )
    },
    coverageSource() {
      const buried = (this.detail && this.detail.buried) || {}
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
    }
  },
  created() {
    this.applyRouteQuery(this.$route.query)
    this.bootstrap()
  },
  watch: {
    '$route.query'(query) {
      if (this.applyRouteQuery(query)) {
        this.page = 1
        this.fetchList()
      }
    }
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
    stepPreview(step) {
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
    applyRouteQuery(query) {
      const projectId = query && query.project_id ? Number(query.project_id) : ''
      const changed = projectId !== this.filterProjectId
      this.filterProjectId = projectId
      return changed
    },
    verifyType(status) {
      if (status === 'passed') return 'success'
      if (status === 'failed') return 'danger'
      if (status === 'skipped') return 'info'
      return 'warning'
    },
    async bootstrap() {
      await Promise.all([this.fetchProjects(), this.fetchList()])
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
        const res = await listAgentCases({
          project_id: this.filterProjectId || undefined,
          keyword: this.keyword || undefined,
          page: this.page,
          page_size: this.pageSize
        })
        const data = (res && res.data) || {}
        this.tableData = data.items || []
        this.total = data.total || 0
        this.page = data.page || this.page
        this.pageSize = data.page_size || this.pageSize
      } catch (e) {
        this.tableData = []
        this.total = 0
      } finally {
        this.loading = false
      }
    },
    handleFilterChange() {
      this.page = 1
      const query = {}
      if (this.filterProjectId) query.project_id = this.filterProjectId
      this.$router.replace({ path: '/agent-test/cases', query }).catch(() => {})
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
    async handleRun(row) {
      if (!row || !row.id) return
      this.runningId = row.id
      try {
        const res = await runAgentCase(row.id)
        Message.success((res && res.msg) || '执行完成')
        await this.fetchList()
        const latest = this.tableData.find(item => item.id === row.id) || (res && res.data)
        if (latest) this.openResult(latest, res && res.data)
      } catch (e) {
        // interceptor
      } finally {
        this.runningId = null
      }
    },
    async openResult(row, runPayload) {
      this.resultRow = row
      this.resultMeta = {}
      this.detail = (runPayload && runPayload.last_run_detail) || {}
      this.activePanels = []
      this.resultVisible = true
      if (!this.hasDetail && row && row.id) {
        await this.loadDetail(row.id)
      }
    },
    async loadDetail(caseId) {
      this.detailLoading = true
      try {
        const res = await getAgentCaseLastRun(caseId)
        const data = (res && res.data) || {}
        this.resultMeta = data
        this.detail = data.last_run_detail || {}
        if (data.last_run_result) {
          this.resultRow = { ...this.resultRow, last_run_result: data.last_run_result, last_run_at: data.last_run_at, score: data.score, verify_status_label: data.verify_status_label }
        }
      } catch (e) {
        this.detail = {}
      } finally {
        this.detailLoading = false
      }
    },
    onCollapseChange(names) {
      if (names && names.indexOf('flow') >= 0 && !this.hasDetail && this.resultRow) {
        this.loadDetail(this.resultRow.id)
      }
    },
    onResultClosed() {
      this.activePanels = []
      this.detail = {}
      this.resultMeta = {}
      this.resultRow = null
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

.case-table {
  width: 100%;
}


.pager {
  margin-top: 16px;
  text-align: right;
}

.btn-action {
  color: #0f766e;
}

.result-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.result-item {
  font-size: 14px;
  color: #374151;
}

.result-item .label,
.result-block .label {
  display: inline-block;
  min-width: 88px;
  margin-right: 8px;
  color: #6b7280;
}

.result-block pre,
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

.flow-collapse {
  margin-top: 8px;
}

.section-title {
  margin: 14px 0 6px;
  font-weight: 600;
  color: #334155;
}

.flow-title {
  font-weight: 600;
  color: #0f172a;
}

.flow-meta {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.empty-detail {
  color: #94a3b8;
  font-size: 13px;
}

.io-cell {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
  overflow: hidden;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.45;
  font-size: 13px;
  color: #1e293b;
  max-height: 5.8em;
}

</style>
