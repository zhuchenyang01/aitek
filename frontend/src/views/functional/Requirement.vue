<template>
  <div class="page">
    <p class="hint">默认展示全部需求文档，可按项目筛选；支持 Word / PDF 上传后生成测试用例。</p>

    <div class="toolbar">
      <el-select
        v-model="filterProjectId"
        placeholder="全部项目"
        filterable
        clearable
        class="project-select"
      >
        <el-option label="全部" value="" />
        <el-option
          v-for="item in projects"
          :key="item.id"
          :label="item.name"
          :value="item.id"
        />
      </el-select>
      <el-button
        type="primary"
        plain
        icon="el-icon-plus"
        :disabled="!projects.length"
        @click="openUpload"
      >
        添加需求
      </el-button>
      <el-button icon="el-icon-refresh" :loading="loading" @click="refreshAll">刷新</el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="tableData"
      border
      stripe
      class="req-table"
      empty-text="暂无需求文件"
    >
      <el-table-column prop="project_name" label="所属项目" min-width="140" show-overflow-tooltip />
      <el-table-column prop="source_filename" label="文件名" min-width="200" show-overflow-tooltip />
      <el-table-column prop="title" label="标题" min-width="160" show-overflow-tooltip />
      <el-table-column prop="creator_name" label="创建人" width="120" show-overflow-tooltip />
      <el-table-column label="上传时间" width="180">
        <template slot-scope="scope">
          {{ formatTime(scope.row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="260" fixed="right" align="center">
        <template slot-scope="scope">
          <el-button
            type="text"
            class="btn-primary"
            :loading="generatingId === scope.row.id"
            @click="handleGenerateTestcase(scope.row)"
          >
            生成测试用例
          </el-button>
          <el-button type="text" class="btn-edit" @click="openEdit(scope.row)">编辑</el-button>
          <el-button type="text" class="btn-delete" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      :title="uploadDialogTitle"
      :visible.sync="uploadDialogVisible"
      width="560px"
      :close-on-click-modal="false"
      @closed="resetUploadForm"
    >
      <el-form ref="uploadFormRef" :model="uploadForm" :rules="uploadRules" label-width="80px">
        <el-form-item label="所属项目" prop="projectId">
          <el-select v-model="uploadForm.projectId" placeholder="请选择项目" style="width: 100%">
            <el-option
              v-for="item in projects"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="标题" prop="title">
          <el-input v-model="uploadForm.title" placeholder="不填则使用文件名" maxlength="255" />
        </el-form-item>
        <el-form-item label="文件" prop="file">
          <el-upload
            action="#"
            :auto-upload="false"
            :limit="1"
            accept=".pdf,.docx"
            :on-change="onFileChange"
            :on-remove="onFileRemove"
            :file-list="fileList"
          >
            <el-button size="small">选择文件</el-button>
            <div slot="tip" class="el-upload__tip">仅支持 .pdf / .docx，单文件不超过 20MB</div>
          </el-upload>
        </el-form-item>
      </el-form>
      <div slot="footer">
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submittingUpload" @click="submitUpload">上传</el-button>
      </div>
    </el-dialog>

    <el-dialog
      title="编辑需求"
      :visible.sync="editDialogVisible"
      width="480px"
      :close-on-click-modal="false"
      @closed="resetEditForm"
    >
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-width="90px">
        <el-form-item label="文档名称" prop="title">
          <el-input v-model="editForm.title" placeholder="请输入文档名称" maxlength="255" />
        </el-form-item>
      </el-form>
      <div slot="footer">
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submittingEdit" @click="submitEdit">确定</el-button>
      </div>
    </el-dialog>

    <generate-process-dialog
      :visible.sync="generateDialogVisible"
      :title="generateDialogTitle"
      :generating="generating"
      :error="generateError"
      :thinking="generateResult.thinking"
      :answer="generateResult.answer"
      :steps="generateSteps"
      :current-step="currentStep"
      :result-hint="savedResultHint"
      :can-view="!!savedGeneration"
      @abort="handleAbortGenerate"
      @view="goToTestcases"
      @closed="resetGenerateResult"
    />
  </div>
</template>

<script>
import { Message, MessageBox } from 'element-ui'
import GenerateProcessDialog from '@/components/GenerateProcessDialog.vue'
import {
  deleteProjectRequirement,
  generateProjectRequirementStream,
  listFunctionalProjects,
  updateProjectRequirement,
  uploadProjectRequirement
} from '@/api/functionalTest'

const emptyUploadForm = () => ({
  projectId: null,
  title: '',
  file: null
})

const emptyEditForm = () => ({
  id: null,
  projectId: null,
  title: ''
})

export default {
  name: 'FunctionalRequirement',
  components: { GenerateProcessDialog },
  data() {
    return {
      loading: false,
      submittingUpload: false,
      submittingEdit: false,
      projects: [],
      allRequirements: [],
      filterProjectId: '',
      uploadDialogVisible: false,
      editDialogVisible: false,
      generateDialogVisible: false,
      generating: false,
      generatingId: null,
      generateLogs: [],
      generateSteps: [],
      generateLineBuffer: '',
      generateStreamPrefix: '',
      generateThinkingLogged: false,
      processingTime: '',
      generateResult: {
        answer: '',
        thinking: '',
        references: []
      },
      generateTarget: null,
      generateAbortFn: null,
      savedGeneration: null,
      generateError: '',
      generateStatus: 'idle',
      currentStep: '',
      lastEventAt: 0,
      stallTimer: null,
      stallWarned: false,
      fileList: [],
      uploadForm: emptyUploadForm(),
      editForm: emptyEditForm(),
      uploadRules: {
        projectId: [{ required: true, message: '请选择项目', trigger: 'change' }],
        file: [{ required: true, message: '请选择 pdf 或 docx 文件', trigger: 'change' }]
      },
      editRules: {
        title: [{ required: true, message: '请输入文档名称', trigger: 'blur' }]
      }
    }
  },
  computed: {
    tableData() {
      if (!this.filterProjectId) {
        return this.allRequirements
      }
      return this.allRequirements.filter(item => item.project_id === this.filterProjectId)
    },
    uploadDialogTitle() {
      const project = this.projects.find(item => item.id === this.uploadForm.projectId)
      if (!project) return '添加需求'
      return `添加需求 · ${project.name}`
    },
    generateDialogTitle() {
      if (!this.generateTarget) return '生成测试用例'
      const name = this.generateTarget.title || this.generateTarget.source_filename || '需求文档'
      return `生成测试用例 · ${name}`
    },
    savedResultHint() {
      if (!this.savedGeneration) return ''
      const count = this.savedGeneration.case_count || 0
      return `已保存 ${count} 条测试用例`
    }
  },
  created() {
    this.refreshAll()
  },
  methods: {
    formatTime(value) {
      if (!value) return ''
      return String(value).replace('T', ' ').slice(0, 19)
    },
    formatLogTime(date = new Date()) {
      const hours = String(date.getHours()).padStart(2, '0')
      const minutes = String(date.getMinutes()).padStart(2, '0')
      const seconds = String(date.getSeconds()).padStart(2, '0')
      return `${hours}:${minutes}:${seconds}`
    },
    resolveLogPrefix(text) {
      if (/不符合|无效|错误|失败/.test(text)) return '不符合要求：'
      if (/^(TC-|用例|测试用例)/i.test(text)) return '测试用例：'
      return '用例生成：'
    },
    pushGenerateLog(prefix, text, level = 'info') {
      const content = (text || '').trim()
      if (!content) return
      if (/^[-=#*]{2,}$/.test(content)) return
      this.generateLogs.push({
        prefix,
        text: content.replace(/^#{1,6}\s*/, ''),
        time: this.formatLogTime(new Date()),
        level
      })
      const stepText = `${prefix}${content}`.replace(/\s+/g, ' ').trim()
      if (stepText && (level === 'error' || level === 'warn' || /完成|开始|保存/.test(prefix))) {
        this.generateSteps = this.generateSteps.concat([stepText])
      }
      this.processingTime = this.formatLogTime(new Date())
      this.lastEventAt = Date.now()
      this.stallWarned = false
    },
    touchGenerateActivity(step) {
      this.currentStep = step || this.currentStep
      this.lastEventAt = Date.now()
      this.processingTime = this.formatLogTime(new Date())
      this.stallWarned = false
    },
    startStallWatchdog() {
      this.clearStallWatchdog()
      this.lastEventAt = Date.now()
      this.stallTimer = setInterval(() => {
        if (!this.generating || this.generateError) return
        const idleSeconds = Math.floor((Date.now() - this.lastEventAt) / 1000)
        if (idleSeconds >= 120) {
          this.handleGenerateFailure(
            `当前步骤「${this.currentStep || '未知'}」已超过 2 分钟无响应，生成可能已中断，请关闭后重试`
          )
          this.clearStallWatchdog()
        } else if (idleSeconds >= 60 && !this.stallWarned) {
          this.stallWarned = true
          this.pushGenerateLog(
            '等待中：',
            `当前步骤「${this.currentStep || '处理中'}」已等待 ${idleSeconds} 秒，仍在执行…`,
            'warn'
          )
        }
      }, 5000)
    },
    clearStallWatchdog() {
      if (this.stallTimer) {
        clearInterval(this.stallTimer)
        this.stallTimer = null
      }
    },
    handleGenerateFailure(message) {
      const text = (message || '').trim()
      if (!text || this.generateError) return
      this.generateError = text
      this.generateStatus = 'failed'
      this.pushGenerateLog('生成失败：', text, 'error')
      Message.error(text)
    },
    mergeThinking(chunk) {
      if (!chunk) return
      const prev = this.generateResult.thinking || ''
      if (!prev || chunk.startsWith(prev)) {
        this.generateResult.thinking = chunk
        return
      }
      this.generateResult.thinking = prev + chunk
    },
    appendAnswerChunk(chunk, prefix) {
      if (!chunk) return
      if (prefix && prefix !== this.generateStreamPrefix) {
        this.flushGenerateLineBuffer()
        this.generateStreamPrefix = prefix
      }
      if (prefix === '用例生成：') {
        this.generateResult.answer += chunk
      }
      this.generateLineBuffer += chunk
      const parts = this.generateLineBuffer.split('\n')
      this.generateLineBuffer = parts.pop() || ''
      parts.forEach(line => {
        const trimmed = line.trim()
        if (trimmed) {
          this.commitGenerateLine(trimmed)
        }
      })
      this.upsertLiveGenerateLine(this.generateLineBuffer)
    },
    upsertLiveGenerateLine(text) {
      const trimmed = (text || '').replace(/\s+/g, ' ').trim()
      if (!trimmed) return
      const last = this.generateLogs[this.generateLogs.length - 1]
      if (last && last.live) {
        last.text = trimmed
        last.time = this.formatLogTime(new Date())
      } else {
        this.generateLogs.push({
          prefix: this.generateStreamPrefix || '',
          text: trimmed,
          time: this.formatLogTime(new Date()),
          level: 'info',
          live: true
        })
      }
      this.processingTime = this.formatLogTime(new Date())
      this.lastEventAt = Date.now()
      this.stallWarned = false
    },
    commitGenerateLine(text) {
      const last = this.generateLogs[this.generateLogs.length - 1]
      if (last && last.live) {
        last.text = text
        last.live = false
        last.time = this.formatLogTime(new Date())
        return
      }
      this.pushGenerateLog(this.generateStreamPrefix || this.resolveLogPrefix(text), text)
    },
    flushGenerateLineBuffer() {
      const trimmed = (this.generateLineBuffer || '').trim()
      if (trimmed) {
        this.commitGenerateLine(trimmed)
      }
      this.generateLineBuffer = ''
    },
    buildRequirements(projects) {
      const rows = []
      ;(projects || []).forEach(project => {
        ;(project.requirements || []).forEach(item => {
          rows.push({
            ...item,
            project_id: item.project_id || project.id,
            project_name: project.name
          })
        })
      })
      return rows.sort((a, b) => {
        const left = new Date(a.created_at || 0).getTime()
        const right = new Date(b.created_at || 0).getTime()
        return right - left
      })
    },
    async fetchProjects() {
      const res = await listFunctionalProjects()
      this.projects = (res && res.data) || []
      this.allRequirements = this.buildRequirements(this.projects)
      if (this.filterProjectId && !this.projects.some(item => item.id === this.filterProjectId)) {
        this.filterProjectId = ''
      }
    },
    async refreshAll() {
      this.loading = true
      try {
        await this.fetchProjects()
      } catch (e) {
        this.projects = []
        this.allRequirements = []
      } finally {
        this.loading = false
      }
    },
    openUpload() {
      if (!this.projects.length) {
        Message.warning('请先在项目管理中创建项目')
        return
      }
      this.uploadForm = {
        ...emptyUploadForm(),
        projectId: this.filterProjectId || this.projects[0].id
      }
      this.fileList = []
      this.uploadDialogVisible = true
    },
    resetUploadForm() {
      this.uploadForm = emptyUploadForm()
      this.fileList = []
      if (this.$refs.uploadFormRef) {
        this.$refs.uploadFormRef.clearValidate()
      }
    },
    onFileChange(file, fileList) {
      const raw = file.raw
      const name = (raw && raw.name) || ''
      if (!/\.(pdf|docx)$/i.test(name)) {
        Message.error('仅支持 pdf 或 docx 文件')
        this.fileList = []
        this.uploadForm.file = null
        return
      }
      this.uploadForm.file = raw
      this.fileList = fileList.slice(-1)
      if (this.$refs.uploadFormRef) {
        this.$refs.uploadFormRef.clearValidate('file')
      }
    },
    onFileRemove() {
      this.uploadForm.file = null
      this.fileList = []
    },
    submitUpload() {
      this.$refs.uploadFormRef.validate(async valid => {
        if (!valid || !this.uploadForm.projectId || !this.uploadForm.file) return
        this.submittingUpload = true
        try {
          const res = await uploadProjectRequirement(this.uploadForm.projectId, {
            file: this.uploadForm.file,
            title: (this.uploadForm.title || '').trim()
          })
          Message.success((res && res.msg) || '需求上传成功')
          this.uploadDialogVisible = false
          await this.refreshAll()
        } catch (e) {
          // 错误提示已由拦截器处理
        } finally {
          this.submittingUpload = false
        }
      })
    },
    handleGenerateTestcase(row) {
      if (this.generateAbortFn) {
        this.generateAbortFn()
        this.generateAbortFn = null
      }
      this.generateTarget = row
      this.generateLogs = []
      this.generateSteps = []
      this.generateLineBuffer = ''
      this.generateStreamPrefix = ''
      this.generateThinkingLogged = false
      this.savedGeneration = null
      this.generateError = ''
      this.generateStatus = 'running'
      this.currentStep = '准备启动'
      this.stallWarned = false
      this.processingTime = this.formatLogTime(new Date())
      this.generateResult = { answer: '', thinking: '', references: [] }
      this.generateDialogVisible = true
      this.generating = true
      this.generatingId = row.id
      this.pushGenerateLog('开始生成：', '正在解析需求并准备生成测试用例…')
      this.startStallWatchdog()

      const { promise, abort } = generateProjectRequirementStream(
        row.project_id,
        row.id,
        {},
        event => this.handleGenerateStreamEvent(event)
      )
      this.generateAbortFn = abort

      promise
        .then(() => {
          if (this.generateStatus !== 'failed' && (this.generateResult.answer || this.savedGeneration)) {
            this.generateStatus = 'success'
            Message.success('生成成功，用例已保存到测试用例模块')
          }
        })
        .catch(err => {
          if (err && err.name === 'AbortError') return
          if (this.generateStatus === 'aborted') return
          const message = (err && err.msg) || (err && err.message) || '生成失败，请稍后重试'
          this.handleGenerateFailure(message)
        })
        .finally(() => {
          this.clearStallWatchdog()
          this.flushGenerateLineBuffer()
          if (
            this.generateStatus === 'running' &&
            !this.savedGeneration &&
            !this.generateError &&
            !this.generateResult.answer
          ) {
            this.handleGenerateFailure('生成流程意外结束，未收到完成信号')
          }
          this.generating = false
          this.generatingId = null
          this.generateAbortFn = null
        })
    },
    handleGenerateStreamEvent(event) {
      const type = event.response_type
      this.touchGenerateActivity(this.currentStep)
      if (type === 'thinking') {
        this.mergeThinking(event.content || '')
      } else if (type === 'references') {
        this.generateResult.references = event.knowledge_references || []
      } else if (type === 'pipeline') {
        const label = event.step_label || event.step || '进度'
        const content = event.content || ''
        this.currentStep = content ? `${label}（${content}）` : label
        this.touchGenerateActivity(this.currentStep)
        if (event.status === 'done' || event.status === 'error' || event.status === 'start') {
          const last = this.generateSteps[this.generateSteps.length - 1]
          if (this.currentStep && last !== this.currentStep) {
            this.generateSteps = this.generateSteps.concat([this.currentStep])
          }
        }
        if (event.status === 'error') {
          this.handleGenerateFailure(content || `${label}失败`)
        } else if (event.status === 'done' && content) {
          this.pushGenerateLog(`${label}完成：`, content)
        }
      } else if (type === 'llm_chunk') {
        const step = event.step || ''
        const label = event.step_label || event.step || '模型输出'
        this.currentStep = label
        if (step === 'testcase_generate') {
          this.appendAnswerChunk(event.content || '', '用例生成：')
        } else {
          this.mergeThinking(event.content || '')
        }
      } else if (type === 'answer') {
        this.currentStep = '用例生成'
        this.appendAnswerChunk(event.content || '', '用例生成：')
      } else if (type === 'error') {
        this.handleGenerateFailure(event.content || '生成失败，请稍后重试')
      } else if (type === 'saved') {
        this.savedGeneration = {
          generation_id: event.generation_id,
          case_count: event.case_count || 0,
          project_id: event.project_id,
          requirement_id: event.requirement_id
        }
        if (event.failed) {
          this.pushGenerateLog('保存完成：', `共保存 ${event.case_count || 0} 条测试用例（过程中存在错误）`, 'warn')
        } else {
          this.generateStatus = 'success'
          this.pushGenerateLog('保存完成：', `共保存 ${event.case_count || 0} 条测试用例`)
        }
      }
    },
    goToTestcases() {
      const query = {}
      const saved = this.savedGeneration || {}
      const target = this.generateTarget || {}
      if (saved.project_id || target.project_id) {
        query.project_id = saved.project_id || target.project_id
      }
      if (saved.requirement_id || target.id) {
        query.requirement_id = saved.requirement_id || target.id
      }
      this.generateDialogVisible = false
      this.$router.push({ path: '/functional/testcases', query })
    },
    handleAbortGenerate() {
      this.generateStatus = 'aborted'
      this.generating = false
      this.generatingId = null
      if (this.generateAbortFn) {
        this.generateAbortFn()
      }
    },
    resetGenerateResult() {
      this.clearStallWatchdog()
      if (this.generateAbortFn) {
        this.generateAbortFn()
        this.generateAbortFn = null
      }
      this.generating = false
      this.generatingId = null
      this.generateTarget = null
      this.generateLogs = []
      this.generateSteps = []
      this.generateLineBuffer = ''
      this.generateStreamPrefix = ''
      this.generateThinkingLogged = false
      this.savedGeneration = null
      this.generateError = ''
      this.generateStatus = 'idle'
      this.currentStep = ''
      this.stallWarned = false
      this.processingTime = ''
      this.generateResult = { answer: '', thinking: '', references: [] }
    },
    openEdit(row) {
      this.editForm = {
        id: row.id,
        projectId: row.project_id,
        title: row.title || row.source_filename || ''
      }
      this.editDialogVisible = true
    },
    resetEditForm() {
      this.editForm = emptyEditForm()
      if (this.$refs.editFormRef) {
        this.$refs.editFormRef.clearValidate()
      }
    },
    submitEdit() {
      this.$refs.editFormRef.validate(async valid => {
        if (!valid || !this.editForm.projectId || !this.editForm.id) return
        this.submittingEdit = true
        try {
          const res = await updateProjectRequirement(this.editForm.projectId, this.editForm.id, {
            title: this.editForm.title.trim()
          })
          Message.success((res && res.msg) || '修改成功')
          this.editDialogVisible = false
          await this.refreshAll()
        } catch (e) {
          // 错误提示已由拦截器处理
        } finally {
          this.submittingEdit = false
        }
      })
    },
    handleDelete(row) {
      const name = row.title || row.source_filename || `文档#${row.id}`
      MessageBox.confirm(`确定删除需求「${name}」吗？`, '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          const res = await deleteProjectRequirement(row.project_id, row.id)
          Message.success((res && res.msg) || '删除成功')
          await this.refreshAll()
        } catch (e) {
          // 错误提示已由拦截器处理
        }
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
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.project-select {
  width: 240px;
}

.req-table {
  width: 100%;
}

.btn-primary {
  color: #0f766e;
}

.btn-edit {
  color: #0f766e;
}

.btn-delete {
  color: #dc2626;
}
</style>
