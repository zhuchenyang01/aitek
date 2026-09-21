<template>
  <div class="page">
    <p class="hint">展示由接口管理生成或手动维护的接口测试用例。单条「运行」会写入「测试报告」；多接口串联请到「用例执行」。</p>

    <div class="toolbar">
      <el-select v-model="filterInterfaceId" placeholder="全部接口" clearable filterable class="filter-item" @change="handleFilterChange">
        <el-option
          v-for="item in interfaces"
          :key="item.id"
          :label="interfaceLabel(item)"
          :value="item.id"
        />
      </el-select>
      <el-input v-model="keyword" clearable placeholder="搜索用例名称" class="filter-item" @keyup.enter.native="handleFilterChange" />
      <el-button type="primary" plain icon="el-icon-plus" @click="openCreate">新建用例</el-button>
      <el-button icon="el-icon-refresh" :loading="loading" @click="fetchList">刷新</el-button>
    </div>

    <el-table v-loading="loading" :data="tableData" border stripe empty-text="暂无接口用例，请先在接口管理中生成">
      <el-table-column prop="id" label="id" width="80" />
      <el-table-column prop="name" label="用例名称" min-width="180" show-overflow-tooltip />
      <el-table-column label="关联接口" min-width="180" show-overflow-tooltip>
        <template slot-scope="scope">[{{ scope.row.interface_id }}] {{ scope.row.interface_method }} {{ scope.row.interface_name }}</template>
      </el-table-column>
      <el-table-column prop="priority" label="优先级" width="90" />
      <el-table-column prop="case_type" label="类型" width="90" />
      <el-table-column prop="expected_status" label="期望状态码" width="110" />
      <el-table-column prop="source_type" label="来源" width="110">
        <template slot-scope="scope">{{ scope.row.source_type === 'llm' ? '大模型生成' : '手动创建' }}</template>
      </el-table-column>
      <el-table-column prop="updated_at" label="更新时间" width="180" />
      <el-table-column label="操作" width="280" align="center">
        <template slot-scope="scope">
          <button type="button" class="link-btn" :disabled="runningId === scope.row.id" @click.stop="handleRun(scope.row)">运行</button>
          <button type="button" class="link-btn" @click.stop="openResult(scope.row)">查看结果</button>
          <button type="button" class="link-btn" @click.stop="openEdit(scope.row)">编辑</button>
          <button type="button" class="link-btn is-danger" @click.stop="handleDelete(scope.row)">删除</button>
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

    <el-dialog :title="formTitle" :visible.sync="dialogVisible" width="720px" append-to-body :close-on-click-modal="false" @closed="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="关联接口" prop="interface_id">
          <el-select v-model="form.interface_id" placeholder="请选择接口" filterable style="width: 100%">
            <el-option
              v-for="item in interfaces"
              :key="item.id"
              :label="interfaceLabel(item)"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="用例名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-select v-model="form.priority" style="width: 140px">
            <el-option label="P0" value="P0" />
            <el-option label="P1" value="P1" />
            <el-option label="P2" value="P2" />
            <el-option label="P3" value="P3" />
          </el-select>
        </el-form-item>
        <el-form-item label="用例类型">
          <el-input v-model="form.case_type" placeholder="正向 / 反向 / 边界 / 异常" />
        </el-form-item>
        <el-form-item label="前置条件">
          <el-input v-model="form.preconditions" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="用例描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="请求体">
          <el-input v-model="form.request_body" type="textarea" :rows="6" placeholder="JSON 请求体" />
        </el-form-item>
        <el-form-item label="期望状态码">
          <el-input v-model="form.expected_status" style="width: 160px" />
        </el-form-item>
        <el-form-item label="期望响应">
          <el-input v-model="form.expected_body" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="断言 JSON">
          <el-input v-model="form.assertionsText" type="textarea" :rows="4" placeholder='[{"name":"status","expected":"200"}]' />
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">保存</el-button>
      </span>
    </el-dialog>

    <el-drawer
      :title="resultTitle"
      :visible.sync="resultVisible"
      size="640px"
      append-to-body
    >
      <div v-loading="resultLoading" class="result-wrap">
        <template v-if="runResult">
          <p class="result-status" :class="runResult.passed ? 'is-ok' : 'is-fail'">
            {{ runResult.passed ? '执行成功' : '执行失败' }}
            <span v-if="runHttp.status_code">HTTP {{ runHttp.status_code }}</span>
            <span v-if="runHttp.elapsed_ms">{{ runHttp.elapsed_ms }} ms</span>
          </p>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="用例">{{ runResult.case_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="运行ID">{{ runResult.run_id || '-' }}</el-descriptions-item>
            <el-descriptions-item label="请求">{{ runHttp.method || '-' }} {{ runHttp.url || '-' }}</el-descriptions-item>
            <el-descriptions-item label="完成时间">{{ runResult.finished_at || '-' }}</el-descriptions-item>
          </el-descriptions>

          <h4>请求头</h4>
          <pre class="json-block">{{ pretty(runHttp.request_headers) }}</pre>
          <h4>Query</h4>
          <pre class="json-block">{{ pretty(runHttp.request_params) }}</pre>
          <h4>请求体</h4>
          <pre class="json-block">{{ pretty(runHttp.request_body) }}</pre>
          <h4>响应头</h4>
          <pre class="json-block">{{ pretty(runHttp.response_headers) }}</pre>
          <h4>响应体</h4>
          <pre class="json-block">{{ pretty(runHttp.response_text) }}</pre>

          <h4>断言</h4>
          <ul class="log-list">
            <li v-for="(item, index) in assertionTexts" :key="'a' + index">{{ item }}</li>
            <li v-if="!assertionTexts.length">无</li>
          </ul>

          <h4>执行过程</h4>
          <el-timeline>
            <el-timeline-item
              v-for="(item, index) in (runResult.result_logs || [])"
              :key="'e' + index"
              :type="timelineType(item.outcome)"
            >
              {{ humanizeEvent(item.event, item.outcome) }}
              <div v-if="item.message && !looksLikeCodeDump(item.message)" class="muted">{{ humanizeUserMessage(item.message) }}</div>
            </el-timeline-item>
          </el-timeline>
          <p v-if="failureTexts.length" class="result-status is-fail">{{ failureTexts[0] }}</p>
        </template>
        <p v-else class="muted">暂无运行结果，请先点击运行。</p>
      </div>
    </el-drawer>
  </div>
</template>

<script>
import {
  createApiCase,
  deleteApiCase,
  listApiCaseLogs,
  listApiCases,
  listApiInterfaces,
  runApiCase,
  updateApiCase
} from '@/api/aiApiTest'
import { humanizeAssertion, humanizeEvent, humanizeUserMessage, looksLikeCodeDump, userFacingFailures } from '@/utils/userError'

export default {
  name: 'ApiCase',
  data() {
    return {
      loading: false,
      saving: false,
      runningId: null,
      tableData: [],
      interfaces: [],
      filterInterfaceId: '',
      keyword: '',
      page: 1,
      pageSize: 20,
      total: 0,
      dialogVisible: false,
      resultVisible: false,
      resultLoading: false,
      runResult: null,
      resultCaseName: '',
      lastResults: {},
      editingId: null,
      form: this.emptyForm(),
      rules: {
        interface_id: [{ required: true, message: '请选择关联接口', trigger: 'change' }],
        name: [{ required: true, message: '请填写用例名称', trigger: 'blur' }],
        priority: [{ required: true, message: '请选择优先级', trigger: 'change' }]
      }
    }
  },
  computed: {
    formTitle() {
      return this.editingId ? '编辑用例' : '新建用例'
    },
    resultTitle() {
      return this.resultCaseName ? `运行结果 - ${this.resultCaseName}` : '运行结果'
    },
    runHttp() {
      return (this.runResult && this.runResult.http) || {}
    },
    assertionTexts() {
      return ((this.runResult && this.runResult.assertion_logs) || []).map(item => humanizeAssertion(item))
    },
    failureTexts() {
      return userFacingFailures((this.runResult && this.runResult.failures) || [])
    }
  },
  created() {
    const qid = this.$route.query.interface_id
    if (qid) {
      this.filterInterfaceId = Number(qid) || qid
    }
    this.fetchInterfaces()
    this.fetchList()
  },
  watch: {
    '$route.query.interface_id'(value) {
      this.filterInterfaceId = value ? (Number(value) || value) : ''
      this.page = 1
      this.fetchList()
    }
  },
  methods: {
    emptyForm() {
      return {
        interface_id: '',
        name: '',
        priority: 'P2',
        case_type: '正向',
        preconditions: '',
        description: '',
        request_body: '',
        expected_status: '200',
        expected_body: '',
        assertionsText: '[]'
      }
    },
    interfaceLabel(item) {
      return `[${item.id}] ${item.method} ${item.name}`
    },
    parseAssertions(text) {
      const raw = (text || '').trim() || '[]'
      const parsed = JSON.parse(raw)
      if (!Array.isArray(parsed)) {
        throw new Error('断言必须是 JSON 数组')
      }
      return parsed
    },
    async fetchInterfaces() {
      try {
        const res = await listApiInterfaces({ for_select: 1 })
        this.interfaces = res.data || []
      } catch (e) {
        this.interfaces = []
      }
    },
    async fetchList() {
      this.loading = true
      try {
        const res = await listApiCases({
          interface_id: this.filterInterfaceId || undefined,
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
    openCreate() {
      this.editingId = null
      this.form = this.emptyForm()
      this.form.interface_id = this.filterInterfaceId || ''
      this.dialogVisible = true
    },
    openEdit(row) {
      this.editingId = row.id
      this.form = {
        interface_id: row.interface_id,
        name: row.name,
        priority: row.priority,
        case_type: row.case_type,
        preconditions: row.preconditions,
        description: row.description,
        request_body: row.request_body,
        expected_status: row.expected_status,
        expected_body: row.expected_body,
        assertionsText: JSON.stringify(row.assertions || [], null, 2)
      }
      this.dialogVisible = true
    },
    resetForm() {
      this.editingId = null
      if (this.$refs.formRef) {
        this.$refs.formRef.clearValidate()
      }
    },
    submitForm() {
      this.$refs.formRef.validate(async (valid) => {
        if (!valid) return
        let assertions
        try {
          assertions = this.parseAssertions(this.form.assertionsText)
        } catch (e) {
          this.$message.error('断言必须是合法 JSON 数组')
          return
        }
        this.saving = true
        const payload = {
          interface_id: this.form.interface_id,
          name: this.form.name,
          priority: this.form.priority,
          case_type: this.form.case_type,
          preconditions: this.form.preconditions,
          description: this.form.description,
          request_body: this.form.request_body,
          expected_status: this.form.expected_status,
          expected_body: this.form.expected_body,
          assertions
        }
        try {
          if (this.editingId) {
            await updateApiCase(this.editingId, payload)
            this.$message.success('用例已更新')
          } else {
            await createApiCase(payload)
            this.$message.success('用例创建成功')
          }
          this.dialogVisible = false
          this.fetchList()
        } finally {
          this.saving = false
        }
      })
    },
    pretty(value) {
      if (value == null || value === '') return '-'
      if (typeof value === 'string') {
        const text = value.trim()
        if ((text.startsWith('{') && text.endsWith('}')) || (text.startsWith('[') && text.endsWith(']'))) {
          try {
            return JSON.stringify(JSON.parse(text), null, 2)
          } catch (e) {
            return value
          }
        }
        return value
      }
      try {
        return JSON.stringify(value, null, 2)
      } catch (e) {
        return String(value)
      }
    },
    humanizeEvent,
    humanizeUserMessage,
    looksLikeCodeDump,
    timelineType(outcome) {
      if (outcome === 'success') return 'success'
      if (outcome === 'failure' || outcome === 'error') return 'danger'
      if (outcome === 'skip') return 'warning'
      return 'primary'
    },
    showResult(payload, caseName) {
      this.runResult = payload || null
      this.resultCaseName = caseName || (payload && payload.case_name) || ''
      this.resultVisible = true
    },
    async openResult(row) {
      if (!row || !row.id) return
      this.resultCaseName = row.name || ''
      const cached = this.lastResults[row.id]
      if (cached) {
        this.showResult(cached, row.name)
        return
      }
      this.resultVisible = true
      this.resultLoading = true
      this.runResult = null
      try {
        const res = await listApiCaseLogs(row.id)
        const items = ((res && res.data) || {}).items || []
        if (!items.length) {
          this.runResult = null
          this.$message.info('还没有运行记录，请先点击运行')
          return
        }
        const latestId = items[items.length - 1].run_id
        const logs = items.filter(item => item.run_id === latestId)
        const httpRow = logs.slice().reverse().find(item => item.extra && item.extra.http && Object.keys(item.extra.http).length)
        const http = (httpRow && httpRow.extra && httpRow.extra.http) || {}
        this.showResult({
          case_name: row.name,
          run_id: latestId,
          passed: logs.some(item => item.outcome === 'success'),
          http,
          result_logs: logs,
          assertion_logs: [],
          logs: logs.map(item => `${item.created_at} ${item.event} ${item.outcome} ${item.message || ''}`),
          unittest_output: '',
          screenshots: logs.map(item => item.screenshot_path).filter(Boolean),
          finished_at: (logs[logs.length - 1] || {}).created_at
        }, row.name)
      } finally {
        this.resultLoading = false
      }
    },
    async handleRun(row) {
      if (!row || !row.id) return
      this.runningId = row.id
      try {
        const res = await runApiCase(row.id)
        const data = (res && res.data) || {}
        this.lastResults = { ...this.lastResults, [row.id]: data }
        this.showResult(data, row.name)
        const extra = (data.http && data.http.status_code) ? `（HTTP ${data.http.status_code}）` : ''
        if (data.passed) {
          this.$message.success((res && res.msg) || `执行成功${extra}`)
        } else {
          const reason = humanizeUserMessage((data.failures && data.failures[0]) || res.msg || '执行失败')
          this.$message.error(`${reason}${extra}`)
        }
      } catch (e) {
        // interceptor
      } finally {
        this.runningId = null
      }
    },
    handleDelete(row) {
      this.$confirm(`确定删除用例「${row.name}」？`, '提示', {
        type: 'warning'
      }).then(async () => {
        await deleteApiCase(row.id)
        this.$message.success('已删除')
        if (this.tableData.length <= 1 && this.page > 1) {
          this.page -= 1
        }
        this.fetchList()
      }).catch(() => {})
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
  width: 240px;
  margin-right: 12px;
}

.pager {
  margin-top: 16px;
  text-align: right;
}

.link-btn {
  margin: 0 8px;
  padding: 0;
  border: none;
  background: none;
  color: #0f766e;
  cursor: pointer;
  font-size: 14px;
}

.link-btn:disabled {
  color: #9ca3af;
  cursor: not-allowed;
}

.link-btn.is-danger {
  color: #c45656;
}

.result-wrap {
  padding: 0 8px 24px;
  text-align: left;
}

.result-status {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
}

.result-status.is-ok {
  color: #0f766e;
}

.result-status.is-fail {
  color: #c45656;
}

.result-wrap h4 {
  margin: 16px 0 8px;
}

.json-block {
  margin: 0;
  padding: 8px;
  background: #f8fafc;
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 12px;
  line-height: 1.45;
}

.log-list {
  padding-left: 18px;
  margin: 0;
}

.muted {
  color: #6b7280;
  font-size: 12px;
}
</style>
