<template>
  <div class="page">
    <p class="hint">仅展示「用例执行」套件跑出来的报告。点开明细可分别查看每步请求、响应、断言与提取变量。</p>

    <div class="toolbar">
      <el-input v-model="keyword" clearable placeholder="搜索名称" class="filter-item" @keyup.enter.native="handleFilterChange" />
      <el-button icon="el-icon-refresh" :loading="loading" @click="fetchList">刷新</el-button>
    </div>

    <el-table v-loading="loading" :data="tableData" border stripe empty-text="暂无测试报告">
      <el-table-column prop="id" label="id" width="70" />
      <el-table-column prop="name" label="名称" min-width="180" show-overflow-tooltip />
      <el-table-column prop="status" label="状态" width="90">
        <template slot-scope="scope">{{ statusText(scope.row.status) }}</template>
      </el-table-column>
      <el-table-column prop="pass_rate" label="通过率" width="90" />
      <el-table-column prop="total" label="总数" width="80" />
      <el-table-column prop="passed" label="通过" width="80" />
      <el-table-column prop="failed" label="失败" width="80" />
      <el-table-column prop="started_at" label="开始时间" width="180" />
      <el-table-column label="操作" width="120" align="center">
        <template slot-scope="scope">
          <button type="button" class="link-btn" @click.stop="openDetail(scope.row)">查看明细</button>
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

    <el-drawer :title="detailTitle" :visible.sync="detailVisible" size="780px" append-to-body>
      <div v-loading="detailLoading" class="result-wrap">
        <template v-if="detail">
          <div class="chart-panel">
            <svg class="pie" viewBox="0 0 160 160" aria-label="成功失败占比">
              <circle class="pie-track" cx="80" cy="80" r="54" />
              <circle
                class="pie-pass"
                cx="80"
                cy="80"
                r="54"
                :stroke-dasharray="passDash"
                stroke-dashoffset="0"
              />
              <circle
                class="pie-fail"
                cx="80"
                cy="80"
                r="54"
                :stroke-dasharray="failDash"
                :stroke-dashoffset="failOffset"
              />
              <text x="80" y="76" text-anchor="middle" class="pie-rate">{{ detail.pass_rate || '0%' }}</text>
              <text x="80" y="96" text-anchor="middle" class="pie-label">通过率</text>
            </svg>
            <div class="chart-legend">
              <p class="result-status" :class="detail.status === 'success' ? 'is-ok' : 'is-fail'">
                {{ statusText(detail.status) }}　{{ detail.summary }}
              </p>
              <ul>
                <li><span class="dot is-ok" />成功 {{ chartPassed }}</li>
                <li><span class="dot is-fail" />失败 {{ chartFailed }}</li>
                <li v-if="chartSkipped"><span class="dot is-skip" />跳过 {{ chartSkipped }}</li>
              </ul>
            </div>
          </div>

          <el-collapse v-model="openSteps" accordion class="step-list">
            <el-collapse-item
              v-for="step in (detail.steps || [])"
              :key="step.id"
              :name="String(step.step_index)"
            >
              <template slot="title">
                <span class="step-title">
                  <span class="dot" :class="step.passed ? 'is-ok' : 'is-fail'" />
                  第 {{ step.step_index }} 步　{{ step.case_name }}
                  <em :class="step.passed ? 'is-ok' : 'is-fail'">{{ step.passed ? '通过' : '失败' }}</em>
                </span>
              </template>
              <p v-if="step.extracts && Object.keys(step.extracts).length" class="muted">提取：{{ pretty(step.extracts) }}</p>
              <h4>请求</h4>
              <pre class="json-block">{{ pretty(step.request || {}) }}</pre>
              <h4>响应</h4>
              <pre class="json-block">{{ pretty(step.response || {}) }}</pre>
              <h4>断言</h4>
              <ul>
                <li v-for="(item, idx) in (step.assertion_logs || []).map(humanizeAssertion)" :key="idx">{{ item }}</li>
                <li v-if="!(step.assertion_logs || []).length">无</li>
              </ul>
              <h4>执行过程</h4>
              <el-timeline>
                <el-timeline-item
                  v-for="(item, idx) in (step.result_logs || [])"
                  :key="idx"
                  :type="timelineType(item.outcome)"
                >
                  {{ humanizeEvent(item.event, item.outcome) }}
                  <div v-if="item.message && !looksLikeCodeDump(item.message)" class="muted">{{ humanizeUserMessage(item.message) }}</div>
                </el-timeline-item>
              </el-timeline>
              <p v-if="(step.failures || []).length" class="result-status is-fail">{{ humanizeUserMessage(step.failures[0]) }}</p>
            </el-collapse-item>
          </el-collapse>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script>
import { getApiRun, listApiRuns } from '@/api/aiApiTest'
import { humanizeAssertion, humanizeEvent, humanizeUserMessage, looksLikeCodeDump } from '@/utils/userError'

export default {
  name: 'ApiReport',
  data() {
    return {
      loading: false,
      tableData: [],
      keyword: '',
      page: 1,
      pageSize: 20,
      total: 0,
      detailVisible: false,
      detailLoading: false,
      detail: null,
      openSteps: ''
    }
  },
  computed: {
    detailTitle() {
      return this.detail ? `报告 - ${this.detail.name}` : '报告明细'
    },
    chartPassed() {
      return Number((this.detail && this.detail.passed) || 0)
    },
    chartFailed() {
      return Number((this.detail && this.detail.failed) || 0)
    },
    chartSkipped() {
      return Number((this.detail && this.detail.skipped) || 0)
    },
    chartTotal() {
      const total = this.chartPassed + this.chartFailed + this.chartSkipped
      return total || Number((this.detail && this.detail.total) || 0)
    },
    pieCircumference() {
      return 2 * Math.PI * 54
    },
    passDash() {
      if (!this.chartTotal) return `0 ${this.pieCircumference}`
      const len = (this.chartPassed / this.chartTotal) * this.pieCircumference
      return `${len} ${this.pieCircumference}`
    },
    failDash() {
      if (!this.chartTotal) return `0 ${this.pieCircumference}`
      const len = (this.chartFailed / this.chartTotal) * this.pieCircumference
      return `${len} ${this.pieCircumference}`
    },
    failOffset() {
      if (!this.chartTotal) return 0
      return -((this.chartPassed / this.chartTotal) * this.pieCircumference)
    }
  },
  created() {
    this.fetchList().then(() => {
      const runId = this.$route.query.run_id
      if (runId) {
        this.openDetail({ id: Number(runId) })
      }
    })
  },
  methods: {
    statusText(status) {
      return ({ success: '成功', fail: '失败', running: '执行中' })[status] || status || '-'
    },
    humanizeAssertion,
    humanizeEvent,
    humanizeUserMessage,
    looksLikeCodeDump,
    pretty(value) {
      try {
        return JSON.stringify(value, null, 2)
      } catch (e) {
        return String(value)
      }
    },
    timelineType(outcome) {
      if (outcome === 'success') return 'success'
      if (outcome === 'failure' || outcome === 'error') return 'danger'
      if (outcome === 'skip') return 'warning'
      return 'primary'
    },
    async fetchList() {
      this.loading = true
      try {
        const res = await listApiRuns({
          keyword: this.keyword || undefined,
          page: this.page,
          page_size: this.pageSize
        })
        const data = res.data || {}
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
    async openDetail(row) {
      if (!row || !row.id) return
      this.detailVisible = true
      this.detailLoading = true
      this.detail = null
      try {
        const res = await getApiRun(row.id)
        this.detail = res.data || null
        this.openSteps = ''
      } finally {
        this.detailLoading = false
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
  margin-bottom: 16px;
}

.filter-item {
  width: 220px;
  margin-right: 8px;
}

.pager {
  margin-top: 16px;
  text-align: right;
}

.link-btn {
  background: none;
  border: none;
  color: #409eff;
  cursor: pointer;
}

.result-wrap {
  padding: 0 16px 24px;
}

.result-status.is-ok {
  color: #67c23a;
}

.result-status.is-fail {
  color: #f56c6c;
}

.muted {
  color: #909399;
}

.json-block {
  background: #f5f7fa;
  padding: 8px;
  white-space: pre-wrap;
  word-break: break-all;
}

.chart-panel {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 20px;
  padding: 12px 16px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fafafa;
}

.pie {
  width: 160px;
  height: 160px;
  flex-shrink: 0;
}

.pie-track {
  fill: none;
  stroke: #ebeef5;
  stroke-width: 18;
}

.pie-pass,
.pie-fail {
  fill: none;
  stroke-width: 18;
  stroke-linecap: butt;
  transform: rotate(-90deg);
  transform-origin: 80px 80px;
}

.pie-pass {
  stroke: #67c23a;
}

.pie-fail {
  stroke: #f56c6c;
}

.pie-rate {
  font-size: 18px;
  font-weight: 600;
  fill: #303133;
}

.pie-label {
  font-size: 12px;
  fill: #909399;
}

.chart-legend ul {
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
  color: #606266;
  line-height: 1.8;
}

.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 8px;
  vertical-align: middle;
}

.dot.is-ok {
  background: #67c23a;
}

.dot.is-fail {
  background: #f56c6c;
}

.dot.is-skip {
  background: #e6a23c;
}

.step-list {
  border-top: 1px solid #ebeef5;
}

.step-title {
  display: flex;
  align-items: center;
  min-width: 0;
  font-weight: 500;
}

.step-title em {
  margin-left: 8px;
  font-style: normal;
  font-size: 12px;
}

.step-title em.is-ok {
  color: #67c23a;
}

.step-title em.is-fail {
  color: #f56c6c;
}
</style>
