<template>
  <div class="page">
    <p class="hint">按顺序串联已有接口用例。同一套件共用 Cookie；步骤里可用 ${变量名}，从上一步 JSON 路径提取。失败会中断后续步骤，结果写入「测试报告」。</p>

    <div class="toolbar">
      <el-select v-model="filterProjectId" placeholder="全部项目" clearable filterable class="filter-item" @change="handleFilterChange">
        <el-option v-for="item in projects" :key="item.id" :label="item.name" :value="item.id" />
      </el-select>
      <el-input v-model="keyword" clearable placeholder="搜索套件名称" class="filter-item" @keyup.enter.native="handleFilterChange" />
      <el-button type="primary" plain icon="el-icon-plus" @click="openCreate">新建套件</el-button>
      <el-button icon="el-icon-refresh" :loading="loading" @click="fetchList">刷新</el-button>
    </div>

    <el-table v-loading="loading" :data="tableData" border stripe empty-text="暂无执行套件">
      <el-table-column prop="id" label="id" width="70" />
      <el-table-column prop="name" label="套件名称" min-width="180" show-overflow-tooltip />
      <el-table-column prop="project_name" label="项目" width="140" show-overflow-tooltip />
      <el-table-column label="步骤数" width="90">
        <template slot-scope="scope">{{ (scope.row.steps || []).length }}</template>
      </el-table-column>
      <el-table-column prop="updated_at" label="更新时间" width="180" />
      <el-table-column label="操作" width="280" align="center">
        <template slot-scope="scope">
          <button type="button" class="link-btn" :disabled="runningId === scope.row.id" @click.stop="handleRun(scope.row)">开始执行</button>
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

    <el-dialog :title="formTitle" :visible.sync="dialogVisible" width="820px" append-to-body :close-on-click-modal="false">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="所属项目" prop="project_id">
          <el-select v-model="form.project_id" placeholder="请选择项目" filterable style="width: 100%">
            <el-option v-for="item in projects" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="套件名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="步骤">
          <div v-for="(step, index) in form.steps" :key="index" class="step-row">
            <span class="step-index">{{ index + 1 }}</span>
            <el-select v-model="step.case_id" filterable placeholder="选择用例" class="step-case">
              <el-option
                v-for="item in cases"
                :key="item.id"
                :label="`[${item.id}] ${item.name}`"
                :value="item.id"
              />
            </el-select>
            <el-input v-model="step.extractorsText" placeholder='提取 [{"name":"token","path":"data.token"}]' />
            <el-button type="text" @click="removeStep(index)">删除</el-button>
          </div>
          <el-button type="text" icon="el-icon-plus" @click="addStep">添加步骤</el-button>
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">保存</el-button>
      </span>
    </el-dialog>

    <el-drawer :title="resultTitle" :visible.sync="resultVisible" size="720px" append-to-body>
      <div v-if="runResult" class="result-wrap">
        <p class="result-status" :class="runResult.passed ? 'is-ok' : 'is-fail'">
          {{ runResult.passed ? '套件执行成功' : '套件执行失败' }}
          通过 {{ runResult.passed_count }}/{{ runResult.total }}
          <span v-if="runResult.skipped_count">，跳过 {{ runResult.skipped_count }}</span>
        </p>
        <p v-if="runResult.report_id" class="muted">
          报告 ID {{ runResult.report_id }}
          <el-button type="text" @click="goReport(runResult.report_id)">查看测试报告</el-button>
        </p>
        <el-collapse v-model="openSteps">
          <el-collapse-item
            v-for="step in (runResult.steps || [])"
            :key="step.step_index"
            :name="String(step.step_index)"
            :title="`第 ${step.step_index} 步 ${step.case_name} ${step.passed ? '通过' : '失败'}`"
          >
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
            <p v-if="(step.failures || []).length" class="result-status is-fail">{{ humanizeUserMessage(step.failures[0]) }}</p>
          </el-collapse-item>
        </el-collapse>
      </div>
    </el-drawer>
  </div>
</template>

<script>
import { listFunctionalProjects } from '@/api/functionalTest'
import {
  createApiSuite,
  deleteApiSuite,
  listApiCases,
  listApiSuites,
  runApiSuite,
  updateApiSuite
} from '@/api/aiApiTest'
import { humanizeAssertion, humanizeUserMessage } from '@/utils/userError'

export default {
  name: 'ApiRun',
  data() {
    return {
      loading: false,
      saving: false,
      runningId: null,
      tableData: [],
      projects: [],
      cases: [],
      filterProjectId: '',
      keyword: '',
      page: 1,
      pageSize: 20,
      total: 0,
      dialogVisible: false,
      editingId: null,
      form: this.emptyForm(),
      rules: {
        project_id: [{ required: true, message: '请选择项目', trigger: 'change' }],
        name: [{ required: true, message: '请填写套件名称', trigger: 'blur' }]
      },
      resultVisible: false,
      runResult: null,
      resultTitle: '执行结果',
      openSteps: []
    }
  },
  computed: {
    formTitle() {
      return this.editingId ? '编辑套件' : '新建套件'
    }
  },
  created() {
    this.fetchProjects()
    this.fetchCases()
    this.fetchList()
  },
  methods: {
    emptyForm() {
      return {
        project_id: '',
        name: '',
        description: '',
        steps: [{ case_id: '', extractorsText: '[]' }]
      }
    },
    pretty(value) {
      try {
        return JSON.stringify(value, null, 2)
      } catch (e) {
        return String(value)
      }
    },
    humanizeAssertion,
    humanizeUserMessage,
    parseExtractors(text) {
      const raw = (text || '').trim() || '[]'
      const parsed = JSON.parse(raw)
      if (!Array.isArray(parsed)) {
        throw new Error('提取规则必须是 JSON 数组')
      }
      return parsed
    },
    async fetchProjects() {
      try {
        const res = await listFunctionalProjects()
        this.projects = res.data || []
      } catch (e) {
        this.projects = []
      }
    },
    async fetchCases() {
      try {
        const res = await listApiCases({ page: 1, page_size: 50 })
        this.cases = (res.data && res.data.items) || []
      } catch (e) {
        this.cases = []
      }
    },
    async fetchList() {
      this.loading = true
      try {
        const res = await listApiSuites({
          project_id: this.filterProjectId || undefined,
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
    addStep() {
      this.form.steps.push({ case_id: '', extractorsText: '[]' })
    },
    removeStep(index) {
      this.form.steps.splice(index, 1)
      if (!this.form.steps.length) {
        this.addStep()
      }
    },
    openCreate() {
      this.editingId = null
      this.form = this.emptyForm()
      this.form.project_id = this.filterProjectId || ''
      this.dialogVisible = true
    },
    openEdit(row) {
      this.editingId = row.id
      this.form = {
        project_id: row.project_id,
        name: row.name,
        description: row.description,
        steps: (row.steps || []).length
          ? row.steps.map(item => ({
            case_id: item.case_id,
            extractorsText: JSON.stringify(item.extractors || [], null, 0)
          }))
          : [{ case_id: '', extractorsText: '[]' }]
      }
      this.dialogVisible = true
    },
    submitForm() {
      this.$refs.formRef.validate(async (valid) => {
        if (!valid) return
        let steps
        try {
          steps = this.form.steps.map((item, index) => ({
            order: index + 1,
            case_id: item.case_id,
            extractors: this.parseExtractors(item.extractorsText)
          })).filter(item => item.case_id)
        } catch (e) {
          this.$message.error('提取规则必须是合法 JSON 数组')
          return
        }
        if (!steps.length) {
          this.$message.error('请至少选择一个用例步骤')
          return
        }
        this.saving = true
        const payload = {
          project_id: this.form.project_id,
          name: this.form.name,
          description: this.form.description,
          steps
        }
        try {
          if (this.editingId) {
            await updateApiSuite(this.editingId, payload)
            this.$message.success('套件已更新')
          } else {
            await createApiSuite(payload)
            this.$message.success('套件已创建')
          }
          this.dialogVisible = false
          this.fetchList()
        } finally {
          this.saving = false
        }
      })
    },
    async handleRun(row) {
      this.runningId = row.id
      try {
        const res = await runApiSuite(row.id)
        const data = (res && res.data) || {}
        this.runResult = data
        this.resultTitle = `执行结果 - ${row.name}`
        this.openSteps = (data.steps || []).map(item => String(item.step_index))
        this.resultVisible = true
        if (data.passed) {
          this.$message.success(res.msg || '套件执行成功')
        } else {
          this.$message.error(res.msg || '套件执行失败')
        }
      } catch (e) {
        // interceptor
      } finally {
        this.runningId = null
      }
    },
    goReport(id) {
      this.$router.push({ path: '/api-test/reports', query: { run_id: id } })
    },
    handleDelete(row) {
      this.$confirm(`确定删除套件「${row.name}」？`, '提示', { type: 'warning' }).then(async () => {
        await deleteApiSuite(row.id)
        this.$message.success('已删除')
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
  padding: 0 6px;
}

.link-btn.is-danger {
  color: #f56c6c;
}

.link-btn:disabled {
  color: #c0c4cc;
  cursor: not-allowed;
}

.step-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.step-index {
  width: 24px;
}

.step-case {
  width: 260px;
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
</style>
