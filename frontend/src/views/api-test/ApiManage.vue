<template>
  <div class="page">
    <p class="hint">维护 HTTP 接口。列表只展示名称与地址等关键字段；完整信息请点「查看详情」。支持手动新建，或上传 OpenAPI / Postman JSON。</p>

    <div class="toolbar">
      <el-select v-model="filterProjectId" placeholder="全部项目" clearable filterable class="filter-item" @change="handleFilterChange">
        <el-option v-for="item in projects" :key="item.id" :label="item.name" :value="item.id" />
      </el-select>
      <el-input v-model="keyword" clearable placeholder="搜索名称或地址" class="filter-item" @keyup.enter.native="handleFilterChange" />
      <el-button type="primary" plain icon="el-icon-plus" @click="openCreate">新建接口</el-button>
      <el-button type="primary" plain icon="el-icon-upload2" @click="openImport">上传接口文档</el-button>
      <el-button icon="el-icon-refresh" :loading="loading" @click="fetchList">刷新</el-button>
    </div>

    <el-table v-loading="loading" :data="tableData" border stripe empty-text="暂无接口，请先新建或上传文档">
      <el-table-column prop="id" label="接口ID" width="90" />
      <el-table-column prop="name" label="接口名称" min-width="160" show-overflow-tooltip />
      <el-table-column prop="method" label="方法" width="90" />
      <el-table-column label="地址" min-width="240" show-overflow-tooltip>
        <template slot-scope="scope">{{ scope.row.url || scope.row.path }}</template>
      </el-table-column>
      <el-table-column prop="project_name" label="项目" width="140" show-overflow-tooltip />
      <el-table-column prop="version" label="版本" width="90" show-overflow-tooltip />
      <el-table-column label="操作" width="320" align="center">
        <template slot-scope="scope">
          <button type="button" class="link-btn" @click.stop="openEdit(scope.row)">编辑</button>
          <button type="button" class="link-btn" @click.stop="openDetail(scope.row)">查看详情</button>
          <button type="button" class="link-btn" :disabled="generatingId === scope.row.id" @click.stop="handleGenerate(scope.row)">生成测试用例</button>
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

    <el-dialog :title="formTitle" :visible.sync="createVisible" width="960px" append-to-body :close-on-click-modal="false" @closed="resetCreate">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="96px">
        <el-form-item label="所属项目" prop="project_id">
          <el-select v-model="createForm.project_id" placeholder="请选择功能测试项目" filterable style="width: 100%">
            <el-option v-for="item in projects" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="版本号" prop="version">
          <el-input v-model="createForm.version" placeholder="例如 v1.0.0" />
        </el-form-item>
        <el-form-item label="接口名称" prop="name">
          <el-input v-model="createForm.name" placeholder="例如：查询订单详情" />
        </el-form-item>
        <el-form-item label="方法" prop="method">
          <el-select v-model="createForm.method" style="width: 140px">
            <el-option v-for="item in httpMethods" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="请求地址" prop="url">
          <el-input v-model="createForm.url" placeholder="http://127.0.0.1:8000/single/login/" />
        </el-form-item>
        <el-form-item label="超时(ms)">
          <el-input-number v-model="createForm.timeout_ms" :min="1" :step="1000" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-tabs v-model="createTab">
          <el-tab-pane label="Header" name="headers">
            <p class="tab-hint">公共参数（header），参数名可从枚举选择或自定义，逻辑同 Postman</p>
            <param-editor v-model="createForm.headers" :key-options="headerNames" />
          </el-tab-pane>
          <el-tab-pane label="Query" name="query">
            <param-editor v-model="createForm.query_params" />
          </el-tab-pane>
          <el-tab-pane label="Path" name="path">
            <p class="tab-hint">对应 URL 路径占位符，例如 id</p>
            <param-editor v-model="createForm.path_params" />
          </el-tab-pane>
          <el-tab-pane label="Body" name="body">
            <el-select v-model="createForm.body_mode" style="width: 180px; margin-bottom: 8px">
              <el-option label="none" value="none" />
              <el-option label="json" value="json" />
              <el-option label="raw" value="raw" />
              <el-option label="form-data" value="form-data" />
              <el-option label="urlencoded" value="urlencoded" />
            </el-select>
            <el-input v-model="createForm.content_type" placeholder="Content-Type，可空" style="width: 280px; margin-left: 8px; margin-bottom: 8px" />
            <el-input
              v-if="createForm.body_mode === 'json' || createForm.body_mode === 'raw'"
              v-model="createForm.body_raw"
              type="textarea"
              :rows="8"
              placeholder="请求体内容"
            />
            <param-editor v-else-if="createForm.body_mode !== 'none'" v-model="createForm.body_form" />
          </el-tab-pane>
          <el-tab-pane label="认证" name="auth">
            <el-select v-model="createForm.auth_type" style="width: 180px; margin-bottom: 8px">
              <el-option label="No Auth" value="none" />
              <el-option label="Bearer Token" value="bearer" />
              <el-option label="Basic Auth" value="basic" />
              <el-option label="API Key" value="apikey" />
            </el-select>
            <el-input
              v-if="createForm.auth_type !== 'none'"
              v-model="createForm.auth_token"
              placeholder="Token / 用户名:密码 / Key"
            />
          </el-tab-pane>
          <el-tab-pane label="Cookie" name="cookie">
            <param-editor v-model="createForm.cookies" />
          </el-tab-pane>
          <el-tab-pane label="前置操作" name="setup">
            <p class="tab-hint">请求发出前执行。可用 api.set_header / api.set_query / api.set_cookie / api.set_body</p>
            <el-input
              v-model="createForm.setup_script"
              type="textarea"
              :rows="10"
              placeholder='api.set_header("Authorization", "Bearer xxx")'
            />
          </el-tab-pane>
          <el-tab-pane label="后置操作" name="teardown">
            <p class="tab-hint">收到响应后执行。可用 api.assert_in("ok")、api.assert_status(200)、api.response</p>
            <el-input
              v-model="createForm.teardown_script"
              type="textarea"
              :rows="10"
              placeholder='api.assert_status(200)'
            />
          </el-tab-pane>
          <el-tab-pane label="响应示例" name="response">
            <el-input v-model="createForm.response_status" placeholder="状态码，如 200" style="width: 160px; margin-bottom: 8px" />
            <el-input v-model="createForm.response_body" type="textarea" :rows="8" placeholder="响应 JSON / 文本" />
          </el-tab-pane>
        </el-tabs>
      </el-form>
      <div slot="footer">
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
      </div>
    </el-dialog>

    <el-dialog title="上传接口文档" :visible.sync="importVisible" width="520px" :close-on-click-modal="false" @closed="resetImport">
      <el-form ref="importFormRef" :model="importForm" :rules="importRules" label-width="96px">
        <el-form-item label="所属项目" prop="project_id">
          <el-select v-model="importForm.project_id" placeholder="导入到哪个项目" filterable style="width: 100%">
            <el-option v-for="item in projects" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="版本号">
          <el-input v-model="importForm.version" placeholder="不填则使用文档内版本" />
        </el-form-item>
        <el-form-item label="文档" prop="file">
          <el-upload
            action="#"
            :auto-upload="false"
            :limit="1"
            accept=".json,.txt,.docx"
            :on-change="onImportFileChange"
            :on-remove="onImportFileRemove"
            :file-list="importFileList"
          >
            <el-button size="small">选择文件</el-button>
            <div slot="tip" class="el-upload__tip">支持 OpenAPI / Postman JSON，以及 Word（.docx，将调用大模型按原文抽取全部接口）</div>
          </el-upload>
        </el-form-item>
      </el-form>
      <div slot="footer">
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="submitImport">导入</el-button>
      </div>
    </el-dialog>

    <el-drawer title="接口详情" :visible.sync="detailVisible" size="560px" append-to-body>
      <div v-loading="detailLoading" class="detail-wrap">
        <el-descriptions v-if="detail" :column="1" border size="small">
          <el-descriptions-item label="接口ID">{{ detail.id }}</el-descriptions-item>
          <el-descriptions-item label="UID">{{ detail.uid }}</el-descriptions-item>
          <el-descriptions-item label="项目">{{ detail.project_name }}</el-descriptions-item>
          <el-descriptions-item label="版本号">{{ detail.version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="接口名称">{{ detail.name }}</el-descriptions-item>
          <el-descriptions-item label="方法">{{ detail.method }}</el-descriptions-item>
          <el-descriptions-item label="请求地址">{{ detail.url || '-' }}</el-descriptions-item>
          <el-descriptions-item label="路径">{{ detail.path || '-' }}</el-descriptions-item>
          <el-descriptions-item label="协议">{{ detail.protocol || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Host">{{ detail.host || '-' }}</el-descriptions-item>
          <el-descriptions-item label="描述">{{ detail.description || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Headers">
            <pre class="json-block">{{ pretty(detail.headers) }}</pre>
          </el-descriptions-item>
          <el-descriptions-item label="Query">
            <pre class="json-block">{{ pretty(detail.query_params) }}</pre>
          </el-descriptions-item>
          <el-descriptions-item label="Path 参数">
            <pre class="json-block">{{ pretty(detail.path_params) }}</pre>
          </el-descriptions-item>
          <el-descriptions-item label="请求体类型">{{ detail.body_mode }}</el-descriptions-item>
          <el-descriptions-item label="Content-Type">{{ detail.content_type || '-' }}</el-descriptions-item>
          <el-descriptions-item label="请求体">
            <pre class="json-block">{{ detail.body_raw || pretty(detail.body_form) }}</pre>
          </el-descriptions-item>
          <el-descriptions-item label="鉴权">{{ detail.auth_type }} {{ pretty(detail.auth_config) }}</el-descriptions-item>
          <el-descriptions-item label="超时(ms)">{{ detail.timeout_ms }}</el-descriptions-item>
          <el-descriptions-item label="请求示例">
            <pre class="json-block">{{ detail.request_example || '-' }}</pre>
          </el-descriptions-item>
          <el-descriptions-item label="响应状态码">{{ detail.response_status || '-' }}</el-descriptions-item>
          <el-descriptions-item label="响应头">
            <pre class="json-block">{{ pretty(detail.response_headers) }}</pre>
          </el-descriptions-item>
          <el-descriptions-item label="响应体">
            <pre class="json-block">{{ detail.response_body || '-' }}</pre>
          </el-descriptions-item>
          <el-descriptions-item label="Cookie">
            <pre class="json-block">{{ pretty(detail.cookies) }}</pre>
          </el-descriptions-item>
          <el-descriptions-item label="前置操作">
            <pre class="json-block">{{ detail.setup_script || '-' }}</pre>
          </el-descriptions-item>
          <el-descriptions-item label="后置操作">
            <pre class="json-block">{{ detail.teardown_script || '-' }}</pre>
          </el-descriptions-item>
          <el-descriptions-item label="来源">{{ detail.source_type }} {{ detail.source_filename }}</el-descriptions-item>
          <el-descriptions-item label="创建人">{{ detail.creator_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ detail.created_at }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ detail.updated_at }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-drawer>

    <generate-process-dialog
      :visible.sync="generateDialogVisible"
      :title="generateDialogTitle"
      :generating="generating"
      :error="generateError"
      :thinking="generateThinking"
      :answer="generateAnswer"
      :steps="generateSteps"
      :current-step="generateCurrentStep"
      :result-items="generatedNames"
      :result-hint="generatedCount ? `已生成 ${generatedCount} 条测试用例` : ''"
      :can-view="!!generatedCount"
      @abort="abortGenerate"
      @view="goGeneratedCases"
      @closed="resetGenerateDialog"
    />
  </div>
</template>

<script>
import { Message, MessageBox } from 'element-ui'
import { listFunctionalProjects } from '@/api/functionalTest'
import GenerateProcessDialog from '@/components/GenerateProcessDialog.vue'
import { createApiInterface, deleteApiInterface, generateApiCasesStream, getApiInterface, importApiDocument, listApiInterfaces, updateApiInterface } from '@/api/aiApiTest'
import ParamEditor from './ParamEditor.vue'

const methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']

const HEADER_NAMES = [
  'Accept', 'Accept-Charset', 'Accept-Encoding', 'Accept-Language',
  'Access-Control-Request-Headers', 'Access-Control-Request-Method',
  'Authorization', 'Cache-Control', 'Connection', 'Content-Length', 'Content-Type',
  'Cookie', 'Date', 'Expect', 'Forwarded', 'From', 'Host', 'If-Match',
  'If-Modified-Since', 'If-None-Match', 'If-Range', 'If-Unmodified-Since',
  'Max-Forwards', 'Origin', 'Pragma', 'Proxy-Authorization', 'Range', 'Referer',
  'TE', 'Trailer', 'Transfer-Encoding', 'Upgrade', 'User-Agent', 'Via', 'Warning',
  'X-Requested-With', 'X-CSRF-Token', 'X-API-Key', 'Content-Disposition'
]

function emptyKv() {
  return [{ key: '', value: '', type: 'string', required: false, description: '', enabled: true }]
}

function cleanKv(rows) {
  return (rows || [])
    .filter(item => (item.key || '').trim())
    .map(item => ({
      key: item.key.trim(),
      value: item.value || '',
      type: item.type || 'string',
      required: !!item.required,
      description: item.description || '',
      enabled: item.enabled !== false
    }))
}

function fillKv(rows) {
  const cleaned = cleanKv(rows)
  return cleaned.length ? cleaned : emptyKv()
}

function authTokenFromConfig(authType, config) {
  const data = config || {}
  if (authType === 'bearer') return data.token || ''
  if (authType === 'basic') return data.credential || ''
  if (authType === 'apikey') return data.key || ''
  return ''
}

function emptyCreateForm() {
  return {
    project_id: '',
    version: '',
    name: '',
    method: 'GET',
    url: '',
    description: '',
    query_params: emptyKv(),
    path_params: emptyKv(),
    headers: emptyKv(),
    cookies: emptyKv(),
    body_mode: 'none',
    body_raw: '',
    body_form: emptyKv(),
    content_type: '',
    timeout_ms: 30000,
    auth_type: 'none',
    auth_token: '',
    setup_script: '',
    teardown_script: '',
    response_status: '',
    response_body: ''
  }
}

export default {
  name: 'ApiManage',
  components: { ParamEditor, GenerateProcessDialog },
  data() {
    return {
      httpMethods: methods,
      headerNames: HEADER_NAMES,
      loading: false,
      submitting: false,
      importing: false,
      generatingId: null,
      generateDialogVisible: false,
      generating: false,
      generateTarget: null,
      generateSteps: [],
      generateThinking: '',
      generateAnswer: '',
      generateError: '',
      generatedCount: 0,
      generatedNames: [],
      generateAbort: null,
      detailLoading: false,
      projects: [],
      tableData: [],
      page: 1,
      pageSize: 20,
      total: 0,
      filterProjectId: '',
      keyword: '',
      createVisible: false,
      editingId: null,
      createTab: 'headers',
      createForm: emptyCreateForm(),
      createRules: {
        project_id: [{ required: true, message: '请选择项目', trigger: 'change' }],
        name: [{ required: true, message: '请输入接口名称', trigger: 'blur' }],
        method: [{ required: true, message: '请选择方法', trigger: 'change' }],
        url: [{ required: true, message: '请输入请求地址', trigger: 'blur' }]
      },
      importVisible: false,
      importForm: { project_id: '', version: '', file: null },
      importFileList: [],
      importRules: {
        project_id: [{ required: true, message: '请选择项目', trigger: 'change' }],
        file: [{ required: true, message: '请选择文档', trigger: 'change' }]
      },
      detailVisible: false,
      detail: null
    }
  },
  computed: {
    formTitle() {
      return this.editingId ? '编辑接口' : '新建接口'
    },
    generateDialogTitle() {
      const name = this.generateTarget && this.generateTarget.name
      return name ? `生成测试用例 · ${name}` : '生成测试用例'
    },
    generateCurrentStep() {
      if (!this.generateSteps.length) return this.generating ? '正在调用大模型…' : ''
      return this.generateSteps[this.generateSteps.length - 1]
    }
  },
  created() {
    this.fetchProjects()
    this.fetchList()
  },
  methods: {
    pretty(value) {
      if (value == null || value === '') return '-'
      if (typeof value === 'string') return value
      try {
        return JSON.stringify(value, null, 2)
      } catch (e) {
        return String(value)
      }
    },
    async fetchProjects() {
      try {
        const res = await listFunctionalProjects()
        this.projects = (res && res.data) || []
      } catch (e) {
        this.projects = []
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
    async fetchList() {
      this.loading = true
      try {
        const res = await listApiInterfaces({
          project_id: this.filterProjectId || undefined,
          keyword: this.keyword || undefined,
          page: this.page,
          page_size: this.pageSize
        })
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
      await this.fetchList()
      if (!this.tableData.length && this.page > 1) {
        this.page -= 1
        await this.fetchList()
      }
    },
    openCreate() {
      this.editingId = null
      this.createForm = emptyCreateForm()
      this.createTab = 'headers'
      this.createVisible = true
    },
    resetCreate() {
      this.editingId = null
      this.createForm = emptyCreateForm()
      if (this.$refs.createFormRef) this.$refs.createFormRef.clearValidate()
    },
    formPayload() {
      const authConfig = {}
      if (this.createForm.auth_type === 'bearer') authConfig.token = this.createForm.auth_token
      if (this.createForm.auth_type === 'basic') authConfig.credential = this.createForm.auth_token
      if (this.createForm.auth_type === 'apikey') authConfig.key = this.createForm.auth_token
      return {
        project_id: this.createForm.project_id,
        version: this.createForm.version,
        name: this.createForm.name.trim(),
        method: this.createForm.method,
        url: this.createForm.url.trim(),
        path: this.createForm.url.trim(),
        description: this.createForm.description,
        query_params: cleanKv(this.createForm.query_params),
        path_params: cleanKv(this.createForm.path_params),
        headers: cleanKv(this.createForm.headers),
        cookies: cleanKv(this.createForm.cookies),
        body_mode: this.createForm.body_mode,
        body_raw: this.createForm.body_raw,
        body_form: cleanKv(this.createForm.body_form),
        content_type: this.createForm.content_type,
        timeout_ms: this.createForm.timeout_ms || 30000,
        auth_type: this.createForm.auth_type,
        auth_config: authConfig,
        setup_script: this.createForm.setup_script,
        teardown_script: this.createForm.teardown_script,
        request_example: this.createForm.body_raw,
        response_status: this.createForm.response_status,
        response_body: this.createForm.response_body
      }
    },
    async openEdit(row) {
      this.createTab = 'headers'
      this.editingId = row && row.id
      this.createVisible = true
      if (!this.editingId) return
      try {
        const res = await getApiInterface(this.editingId)
        const data = (res && res.data) || {}
        this.createForm = {
          project_id: data.project_id,
          version: data.version || '',
          name: data.name || '',
          method: data.method || 'GET',
          url: data.url || data.path || '',
          description: data.description || '',
          query_params: fillKv(data.query_params),
          path_params: fillKv(data.path_params),
          headers: fillKv(data.headers),
          cookies: fillKv(data.cookies),
          body_mode: data.body_mode || 'none',
          body_raw: data.body_raw || '',
          body_form: fillKv(data.body_form),
          content_type: data.content_type || '',
          timeout_ms: data.timeout_ms || 30000,
          auth_type: data.auth_type || 'none',
          auth_token: authTokenFromConfig(data.auth_type, data.auth_config),
          setup_script: data.setup_script || '',
          teardown_script: data.teardown_script || '',
          response_status: data.response_status || '',
          response_body: data.response_body || ''
        }
      } catch (e) {
        Message.error((e && e.msg) || '加载接口详情失败')
      }
    },
    submitForm() {
      this.$refs.createFormRef.validate(async valid => {
        if (!valid) return
        this.submitting = true
        try {
          const payload = this.formPayload()
          const res = this.editingId
            ? await updateApiInterface(this.editingId, payload)
            : await createApiInterface(payload)
          Message.success((res && res.msg) || (this.editingId ? '接口已保存' : '接口创建成功'))
          this.createVisible = false
          this.fetchList()
        } catch (e) {
          // interceptor
        } finally {
          this.submitting = false
        }
      })
    },
    openImport() {
      this.importForm = { project_id: this.filterProjectId || '', version: '', file: null }
      this.importFileList = []
      this.importVisible = true
    },
    resetImport() {
      this.importForm = { project_id: '', version: '', file: null }
      this.importFileList = []
      if (this.$refs.importFormRef) this.$refs.importFormRef.clearValidate()
    },
    onImportFileChange(file) {
      this.importForm.file = file.raw
      this.importFileList = [file]
    },
    onImportFileRemove() {
      this.importForm.file = null
      this.importFileList = []
    },
    submitImport() {
      this.$refs.importFormRef.validate(async valid => {
        if (!valid) return
        if (!this.importForm.file) {
          Message.warning('请选择文档')
          return
        }
        const form = new FormData()
        form.append('project_id', this.importForm.project_id)
        if (this.importForm.version) form.append('version', this.importForm.version)
        form.append('file', this.importForm.file)
        this.importing = true
        try {
          const res = await importApiDocument(form)
          Message.success((res && res.msg) || '导入成功')
          this.importVisible = false
          this.fetchList()
        } catch (e) {
          // interceptor
        } finally {
          this.importing = false
        }
      })
    },
    async openDetail(row) {
      if (!row || !row.id) return
      this.detailVisible = true
      this.detail = null
      this.detailLoading = true
      try {
        const res = await getApiInterface(row.id)
        this.detail = (res && res.data) || null
      } catch (e) {
        Message.error((e && e.msg) || '加载接口详情失败')
      } finally {
        this.detailLoading = false
      }
    },
    handleDelete(row) {
      if (!row || !row.id) return
      const name = row.name || `接口#${row.id}`
      MessageBox.confirm(`确定删除接口「${name}」吗？删除后不可恢复。`, '提示', {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消'
      }).then(async () => {
        await deleteApiInterface(row.id)
        if (this.detail && this.detail.id === row.id) {
          this.detailVisible = false
          this.detail = null
        }
        Message.success('接口已删除')
        this.refreshAfterDelete()
      }).catch(() => {})
    },
    handleGenerate(row) {
      if (!row || !row.id) return
      this.resetGenerateDialog()
      this.generateTarget = row
      this.generateDialogVisible = true
      this.generating = true
      this.generatingId = row.id
      const { promise, abort } = generateApiCasesStream(row.id, event => {
        const type = event.response_type
        if (type === 'step' && event.content) {
          this.generateSteps = this.generateSteps.concat([event.content])
        } else if (type === 'thinking' && event.content) {
          this.generateThinking += event.content
        } else if (type === 'answer' && event.content) {
          this.generateAnswer += event.content
        } else if (type === 'parsed' && event.content) {
          this.generateSteps = this.generateSteps.concat([event.content])
        } else if (type === 'saved') {
          this.generatedCount = event.count || 0
          this.generatedNames = (event.items || []).map(item => item.name).filter(Boolean)
          this.generating = false
          this.generatingId = null
          Message.success(event.content || `已生成 ${this.generatedCount} 条测试用例`)
        } else if (type === 'error') {
          this.generateError = event.content || '生成测试用例失败'
          this.generating = false
          this.generatingId = null
          Message.error(this.generateError)
        }
      })
      this.generateAbort = abort
      promise.catch(err => {
        if (err && err.name === 'AbortError') return
        this.generateError = (err && err.msg) || '生成测试用例失败'
        this.generating = false
        this.generatingId = null
      })
    },
    abortGenerate() {
      if (this.generateAbort) {
        this.generateAbort()
      }
      this.generating = false
      this.generatingId = null
      this.generateError = this.generateError || '已停止生成'
    },
    resetGenerateDialog() {
      if (this.generateAbort) {
        this.generateAbort()
        this.generateAbort = null
      }
      this.generating = false
      this.generatingId = null
      this.generateSteps = []
      this.generateThinking = ''
      this.generateAnswer = ''
      this.generateError = ''
      this.generatedCount = 0
      this.generatedNames = []
      this.generateTarget = null
    },
    goGeneratedCases() {
      const id = this.generateTarget && this.generateTarget.id
      this.generateDialogVisible = false
      this.$router.push({ path: '/api-test/cases', query: id ? { interface_id: String(id) } : {} })
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

.pager {
  margin-top: 16px;
  text-align: right;
}

.filter-item {
  width: 200px;
  margin-right: 8px;
  vertical-align: middle;
}

.btn-edit {
  color: #0f766e;
}

.link-btn {
  border: none;
  background: none;
  padding: 0 6px;
  color: #0f766e;
  cursor: pointer;
  font-size: 14px;
}

.link-btn:disabled {
  color: #9ca3af;
  cursor: not-allowed;
  text-decoration: none;
}

.link-btn.is-danger {
  color: #c45656;
}

.tab-hint {
  margin: 8px 0 6px;
  color: #6b7280;
  font-size: 12px;
}

.detail-wrap {
  padding: 0 8px 24px;
}

.json-block {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 12px;
  line-height: 1.45;
}

</style>

<style>
.param-head,
.param-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.param-head {
  color: #6b7280;
  font-size: 12px;
}

.col-check {
  width: 18px;
}

.col-key {
  width: 220px;
}

.col-type {
  width: 110px;
}

.col-value,
.col-desc {
  flex: 1;
}

.col-op {
  width: 48px;
}
</style>
