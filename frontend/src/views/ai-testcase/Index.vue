<template>
  <div class="chat-page">
    <aside class="session-rail">
      <button class="new-chat-btn" type="button" :disabled="creatingSession" @click="handleNewChat">
        <i class="el-icon-plus" />
        新对话
      </button>
      <div class="session-label">对话</div>
      <div v-if="!sessions.length" class="session-empty">暂无对话</div>
      <ul class="session-list">
        <li
          v-for="item in sessions"
          :key="item.id"
          class="session-item"
          :class="{ active: item.id === sessionId }"
          @click="handleSelectSession(item)"
        >
          <i class="el-icon-chat-dot-round" />
          <span>{{ sessionTitle(item) }}</span>
        </li>
      </ul>
    </aside>

    <section class="chat-main">
      <div ref="threadRef" class="chat-thread">
        <div v-if="!messages.length && !generating" class="welcome">
          <h2>Hi，我是 AITEK，让测试用例触手可及</h2>
          <p>选择需求库和用例库后提问，也可以用回形针把 Word / PDF 入库后再生成。</p>
        </div>

        <div
          v-for="(item, index) in messages"
          :key="item.id || `${item.role}-${index}`"
          class="bubble-row"
          :class="item.role"
        >
          <div class="bubble">
            <div v-if="item.thinking" class="thinking">{{ item.thinking }}</div>
            <pre class="bubble-text">{{ item.content || (item.pending ? '正在生成…' : '') }}</pre>
            <div v-if="item.references && item.references.length" class="refs">
              <div class="refs-title">检索引用</div>
              <div v-for="(ref, refIndex) in item.references" :key="refIndex" class="ref-item">
                <div class="ref-meta">
                  {{ refIndex + 1 }}. [{{ ref.kb_type === 'requirement' ? '需求' : '用例' }}]
                  {{ ref.knowledge_title || ref.kb_name }}
                  <span class="ref-score">score={{ formatScore(ref) }}</span>
                </div>
                <p class="ref-content">{{ ref.content }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="composer">
        <div class="composer-box">
          <textarea
            v-model="query"
            class="composer-input"
            rows="3"
            placeholder="直接向模型提问，例如：根据登录需求生成测试用例"
            :disabled="generating"
            @keydown.enter.exact.prevent="handleSend"
          />
          <div class="composer-bar">
            <div class="composer-left">
              <el-popover
                placement="top-start"
                width="360"
                trigger="click"
                popper-class="kb-popper"
              >
                <div class="kb-picker">
                  <div class="kb-picker-title">知识库</div>
                  <div class="kb-field">
                    <span>需求文档库</span>
                    <el-select v-model="requirementKbId" filterable placeholder="请选择" size="small">
                      <el-option
                        v-for="item in requirementKbs"
                        :key="item.id"
                        :label="`${item.name}（${item.chunk_count || 0} 分块）`"
                        :value="item.id"
                      />
                    </el-select>
                  </div>
                  <div class="kb-field">
                    <span>测试用例库</span>
                    <el-select v-model="testcaseKbId" filterable placeholder="请选择" size="small">
                      <el-option
                        v-for="item in testcaseKbs"
                        :key="item.id"
                        :label="`${item.name}（${item.chunk_count || 0} 分块）`"
                        :value="item.id"
                      />
                    </el-select>
                  </div>
                </div>
                <button slot="reference" class="icon-btn" type="button" title="选择知识库">
                  @
                </button>
              </el-popover>

              <el-popover ref="uploadPop" placement="top-start" width="200" trigger="click">
                <div class="upload-picker">
                  <button type="button" :disabled="!requirementKbId || uploading" @click="pickFile('requirement')">
                    上传到需求库
                  </button>
                  <button type="button" :disabled="!testcaseKbId || uploading" @click="pickFile('testcase')">
                    上传到用例库
                  </button>
                </div>
                <button slot="reference" class="icon-btn" type="button" title="选择文件" :disabled="uploading">
                  <i class="el-icon-paperclip" />
                </button>
              </el-popover>

              <span v-if="requirementKb" class="kb-chip">需求 · {{ requirementKb.name }}</span>
              <span v-if="testcaseKb" class="kb-chip">用例 · {{ testcaseKb.name }}</span>
            </div>
            <div class="composer-right">
              <el-popover ref="modelPop" placement="top-end" width="280" trigger="click" popper-class="model-popper">
                <div class="model-picker">
                  <div class="model-picker-head">
                    <span>思考 / 对话模型</span>
                    <span>
                      <button type="button" class="add-model-link" @click="openLlmDialog()">+ 添加模型</button>
                      <button type="button" class="add-model-link" @click="goLlmManage">管理</button>
                    </span>
                  </div>
                  <div v-if="!llmConfigs.length" class="model-empty">
                    <p>还没有可用的大模型</p>
                    <button type="button" class="goto-config" @click="openLlmDialog()">点击去配置大模型</button>
                  </div>
                  <ul v-else class="model-options">
                    <li
                      v-for="item in llmConfigs"
                      :key="item.id"
                      :class="{ active: item.id === selectedLlmId }"
                      @click="selectLlm(item)"
                    >
                      <i class="el-icon-chat-dot-round" />
                      <span>{{ item.name }}</span>
                    </li>
                  </ul>
                </div>
                <button slot="reference" class="model-btn" type="button" :class="{ unset: !selectedLlm }">
                  {{ selectedLlm ? selectedLlm.name : '未配置' }}
                </button>
              </el-popover>
              <el-button v-if="generating" size="mini" @click="handleAbort">停止</el-button>
              <button
                class="send-btn"
                type="button"
                :disabled="!canSend"
                :title="generating ? '生成中' : '发送'"
                @click="handleSend"
              >
                <i class="el-icon-s-promotion" />
              </button>
            </div>
          </div>
        </div>
        <input
          ref="fileInput"
          class="hidden-file"
          type="file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          @change="handleFileChange"
        >
        <ModelConfigDrawer :visible.sync="llmDialogVisible" :initial-type="'chat'" @saved="onLlmSaved" />
      </div>
    </section>
  </div>
</template>

<script>
import { Message } from 'element-ui'
import { humanizeUserMessage } from '@/utils/userError'
import {
  addAiTestcaseKnowledgeDocument,
  askAiTestcaseStream,
  createAiTestcaseQA,
  createAiTestcaseSession,
  listAiTestcaseKnowledgeBases,
  listAiTestcaseMessages,
  listAiTestcaseQA,
  listAiTestcaseSessions
} from '@/api/aiTestcase'
import { listLlmConfigs, setDefaultLlmConfig } from '@/api/llmConfig'
import ModelConfigDrawer from '@/components/ModelConfigDrawer.vue'

const LLM_STORAGE_KEY = 'aitek.selectedLlmConfigId'

export default {
  name: 'AiTestcase',
  components: { ModelConfigDrawer },
  data() {
    return {
      knowledgeBases: [],
      sessions: [],
      messages: [],
      sessionId: null,
      qaId: null,
      qaKey: '',
      requirementKbId: null,
      testcaseKbId: null,
      query: '',
      generating: false,
      creatingSession: false,
      uploading: false,
      abortFn: null,
      uploadTarget: 'requirement',
      llmConfigs: [],
      selectedLlmId: null,
      llmDialogVisible: false
    }
  },
  computed: {
    requirementKbs() {
      return this.knowledgeBases.filter(item => item.kb_type === 'requirement')
    },
    testcaseKbs() {
      return this.knowledgeBases.filter(item => item.kb_type === 'testcase')
    },
    requirementKb() {
      return this.requirementKbs.find(item => item.id === this.requirementKbId) || null
    },
    testcaseKb() {
      return this.testcaseKbs.find(item => item.id === this.testcaseKbId) || null
    },
    selectedLlm() {
      return this.llmConfigs.find(item => item.id === this.selectedLlmId) || null
    },
    canSend() {
      return !this.generating && !!(this.query || '').trim()
    }
  },
  created() {
    this.bootstrap()
  },
  beforeDestroy() {
    this.handleAbort()
  },
  methods: {
    sessionTitle(item) {
      return (item && item.title && item.title.trim()) || '新对话'
    },
    formatScore(item) {
      const value = item.rerank_score != null ? item.rerank_score : item.score
      if (value == null || value === '') return '-'
      return Number(value).toFixed(4)
    },
    async bootstrap() {
      await Promise.all([this.fetchKnowledgeBases(), this.fetchSessions(), this.fetchLlmConfigs()])
      if (this.sessions.length) {
        await this.handleSelectSession(this.sessions[0])
      }
    },
    async fetchKnowledgeBases() {
      try {
        const res = await listAiTestcaseKnowledgeBases()
        this.knowledgeBases = (res && res.data) || []
      } catch (e) {
        this.knowledgeBases = []
      }
    },
    async fetchSessions() {
      try {
        const res = await listAiTestcaseSessions()
        this.sessions = (res && res.data) || []
      } catch (e) {
        this.sessions = []
      }
    },
    async fetchLlmConfigs(preferId) {
      try {
        const res = await listLlmConfigs({ model_type: 'chat' })
        this.llmConfigs = (res && res.data) || []
      } catch (e) {
        this.llmConfigs = []
      }
      const stored = Number(localStorage.getItem(LLM_STORAGE_KEY) || 0)
      const preferred = preferId || stored
      const found = this.llmConfigs.find(item => item.id === preferred)
      const fallback = this.llmConfigs.find(item => item.is_default) || this.llmConfigs[0]
      this.selectedLlmId = (found || fallback || {}).id || null
      if (this.selectedLlmId) {
        localStorage.setItem(LLM_STORAGE_KEY, String(this.selectedLlmId))
      } else {
        localStorage.removeItem(LLM_STORAGE_KEY)
      }
    },
    openLlmDialog() {
      if (this.$refs.modelPop && this.$refs.modelPop.doClose) {
        this.$refs.modelPop.doClose()
      }
      this.llmDialogVisible = true
    },
    goLlmManage() {
      if (this.$refs.modelPop && this.$refs.modelPop.doClose) {
        this.$refs.modelPop.doClose()
      }
      this.$router.push('/llm-config')
    },
    async onLlmSaved(config) {
      await this.fetchLlmConfigs(config && config.id)
    },
    async selectLlm(item) {
      if (!item) return
      this.selectedLlmId = item.id
      localStorage.setItem(LLM_STORAGE_KEY, String(item.id))
      if (this.$refs.modelPop && this.$refs.modelPop.doClose) {
        this.$refs.modelPop.doClose()
      }
      try {
        await setDefaultLlmConfig(item.id)
        await this.fetchLlmConfigs(item.id)
      } catch (e) {
        // 拦截器已提示
      }
    },
    async handleNewChat() {
      if (this.creatingSession) return
      this.handleAbort()
      this.creatingSession = true
      try {
        const res = await createAiTestcaseSession({ title: '' })
        const session = res && res.data
        if (!session) return
        this.sessions = [session, ...this.sessions.filter(item => item.id !== session.id)]
        this.resetChatState(session.id)
      } catch (e) {
        // 拦截器已提示
      } finally {
        this.creatingSession = false
      }
    },
    async handleSelectSession(item) {
      if (!item || item.id === this.sessionId) return
      this.handleAbort()
      this.resetChatState(item.id)
      await this.loadSessionContext(item.id)
    },
    resetChatState(sessionId) {
      this.sessionId = sessionId
      this.qaId = null
      this.qaKey = ''
      this.messages = []
      this.query = ''
      this.generating = false
      this.abortFn = null
    },
    async loadSessionContext(sessionId) {
      try {
        const [msgRes, qaRes] = await Promise.all([
          listAiTestcaseMessages(sessionId),
          listAiTestcaseQA({ session_id: sessionId })
        ])
        this.messages = ((msgRes && msgRes.data) || []).map(item => ({
          id: item.id,
          role: item.role,
          content: item.content || '',
          thinking: item.thinking || '',
          references: item.references || []
        }))
        const qas = (qaRes && qaRes.data) || []
        if (qas.length) {
          const latest = qas[0]
          this.qaId = latest.id
          this.requirementKbId = latest.requirement_kb_id
          this.testcaseKbId = latest.testcase_kb_id
          this.qaKey = `${latest.requirement_kb_id}:${latest.testcase_kb_id}`
        }
        this.scrollToBottom()
      } catch (e) {
        this.messages = []
      }
    },
    pickFile(target) {
      this.uploadTarget = target
      const kbId = target === 'requirement' ? this.requirementKbId : this.testcaseKbId
      if (!kbId) {
        Message.error(target === 'requirement' ? '请先选择需求文档知识库' : '请先选择测试用例知识库')
        return
      }
      if (this.$refs.uploadPop && this.$refs.uploadPop.doClose) {
        this.$refs.uploadPop.doClose()
      }
      this.$nextTick(() => {
        this.$refs.fileInput && this.$refs.fileInput.click()
      })
    },
    async handleFileChange(event) {
      const file = event.target.files && event.target.files[0]
      event.target.value = ''
      if (!file) return
      const kbId = this.uploadTarget === 'requirement' ? this.requirementKbId : this.testcaseKbId
      if (!kbId) {
        Message.error('请先通过 @ 选择知识库')
        return
      }
      this.uploading = true
      try {
        const res = await addAiTestcaseKnowledgeDocument(kbId, { file, title: file.name })
        const data = (res && res.data) || {}
        Message.success((res && res.msg) || `已入库 ${file.name}`)
        await this.fetchKnowledgeBases()
        this.messages.push({
          role: 'system',
          content: `已将「${file.name}」上传到${this.uploadTarget === 'requirement' ? '需求库' : '用例库'}，共 ${data.chunk_count || 0} 个分块。`
        })
        this.scrollToBottom()
      } catch (e) {
        // 拦截器已提示
      } finally {
        this.uploading = false
      }
    },
    async ensureSession() {
      if (this.sessionId) return this.sessionId
      const res = await createAiTestcaseSession({ title: (this.query || '新对话').slice(0, 80) })
      const session = res && res.data
      this.sessionId = session.id
      this.sessions = [session, ...this.sessions.filter(item => item.id !== session.id)]
      return this.sessionId
    },
    async ensureKnowledgeBases() {
      if (this.requirementKbId && this.testcaseKbId) {
        if (this.requirementKbId === this.testcaseKbId) {
          Message.error('需求文档知识库与测试用例知识库不能相同')
          return false
        }
        return true
      }
      if (!this.knowledgeBases.length) {
        await this.fetchKnowledgeBases()
      }
      const requirementKb = this.requirementKbs[0]
      const testcaseKb = this.testcaseKbs[0]
      if (!requirementKb || !testcaseKb) {
        Message.error('请先在「项目管理」中创建需求文档库和测试用例库')
        return false
      }
      if (requirementKb.id === testcaseKb.id) {
        Message.error('需求文档知识库与测试用例知识库不能相同')
        return false
      }
      this.requirementKbId = requirementKb.id
      this.testcaseKbId = testcaseKb.id
      return true
    },
    async ensureQa() {
      const ready = await this.ensureKnowledgeBases()
      if (!ready) {
        throw new Error('knowledge_base_missing')
      }
      const key = `${this.requirementKbId}:${this.testcaseKbId}`
      if (this.qaId && this.qaKey === key) return this.qaId
      const sessionId = await this.ensureSession()
      const qaRes = await createAiTestcaseQA({
        session_id: sessionId,
        requirement_kb_id: this.requirementKbId,
        testcase_kb_id: this.testcaseKbId
      })
      this.qaId = qaRes.data.id
      this.qaKey = key
      return this.qaId
    },
    async handleSend() {
      const query = (this.query || '').trim()
      if (!query || this.generating) return
      if (!this.selectedLlmId) {
        Message.warning('请先配置大模型')
        this.openLlmDialog()
        return
      }

      this.generating = true
      this.query = ''
      const userMsg = { role: 'user', content: query }
      const assistantMsg = { role: 'assistant', content: '', thinking: '', references: [], pending: true }
      this.messages.push(userMsg, assistantMsg)
      this.scrollToBottom()

      try {
        const qaId = await this.ensureQa()
        await this.runStream(qaId, query, assistantMsg)
        this.patchSessionTitle(query)
      } catch (e) {
        if (e && e.message === 'knowledge_base_missing') {
          this.messages.splice(-2, 2)
          this.query = query
        } else if (!(e && e.name === 'AbortError')) {
          assistantMsg.content = assistantMsg.content || '生成失败，请稍后重试'
        }
      } finally {
        assistantMsg.pending = false
        this.generating = false
        this.abortFn = null
        this.scrollToBottom()
      }
    },
    patchSessionTitle(query) {
      const session = this.sessions.find(item => item.id === this.sessionId)
      if (session && !(session.title || '').trim()) {
        this.$set(session, 'title', query.slice(0, 80))
      }
    },
    runStream(qaId, query, assistantMsg) {
      return new Promise((resolve, reject) => {
        const { promise, abort } = askAiTestcaseStream(qaId, { query, llm_config_id: this.selectedLlmId }, event => {
          const type = event.response_type
          if (type === 'thinking') {
            assistantMsg.thinking = event.content || assistantMsg.thinking
          } else if (type === 'references') {
            assistantMsg.references = event.knowledge_references || []
          } else if (type === 'answer') {
            if (event.content) assistantMsg.content += event.content
          } else if (type === 'error') {
            Message.error(humanizeUserMessage(event.content || '生成失败'))
          }
          this.scrollToBottom()
        })
        this.abortFn = abort
        promise.then(resolve).catch(err => {
          if (err && err.name === 'AbortError') {
            resolve()
            return
          }
          if (err && err.msg) Message.error(humanizeUserMessage(err.msg))
          reject(err)
        })
      })
    },
    handleAbort() {
      if (this.abortFn) this.abortFn()
    },
    scrollToBottom() {
      this.$nextTick(() => {
        const el = this.$refs.threadRef
        if (el) el.scrollTop = el.scrollHeight
      })
    }
  }
}
</script>

<style scoped>
.chat-page {
  display: flex;
  flex: 1;
  min-height: 0;
  height: 100%;
  background: #fff;
  text-align: left;
}

.session-rail {
  width: 236px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 16px 12px;
  border-right: 1px solid #eef2f6;
  background: #fbfcfe;
}

.new-chat-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 40px;
  padding: 0 12px;
  border: none;
  border-radius: 10px;
  background: #e6f7f4;
  color: #0f766e;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.new-chat-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.session-label {
  margin: 16px 8px 8px;
  color: #9ca3af;
  font-size: 12px;
}

.session-empty {
  margin: 8px;
  color: #9ca3af;
  font-size: 13px;
}

.session-list {
  margin: 0;
  padding: 0;
  list-style: none;
  overflow-y: auto;
  flex: 1;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 40px;
  padding: 0 10px;
  border-radius: 10px;
  color: #374151;
  font-size: 13px;
  cursor: pointer;
}

.session-item span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-item i {
  color: #9ca3af;
}

.session-item:hover,
.session-item.active {
  background: #e6f7f4;
  color: #0f766e;
}

.session-item.active i {
  color: #0f766e;
}

.chat-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.chat-thread {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 32px 48px 16px;
}

.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 42%;
  text-align: center;
}

.welcome h2 {
  margin: 0 0 10px !important;
  color: #111827 !important;
  font-size: 28px !important;
  font-weight: 650;
}

.welcome p {
  max-width: 520px;
  color: #6b7280;
  font-size: 14px;
  line-height: 1.6;
}

.bubble-row {
  display: flex;
  margin-bottom: 18px;
}

.bubble-row.user {
  justify-content: flex-end;
}

.bubble-row.assistant,
.bubble-row.system {
  justify-content: flex-start;
}

.bubble {
  max-width: 78%;
  padding: 12px 16px;
  border-radius: 16px;
  background: #f8fafc;
  border: 1px solid #e8edf3;
}

.bubble-row.user .bubble {
  background: #e6f7f4;
  border-color: #ccfbf1;
}

.bubble-row.system .bubble {
  background: #fff;
  color: #0f766e;
  border-color: #ccfbf1;
}

.bubble-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.65;
  color: #1f2937;
}

.thinking {
  margin-bottom: 10px;
  padding: 8px 10px;
  background: rgba(15, 118, 110, 0.08);
  border-radius: 8px;
  color: #0f766e;
  font-size: 13px;
  white-space: pre-wrap;
}

.refs {
  margin-top: 12px;
}

.refs-title {
  margin-bottom: 8px;
  font-weight: 650;
  color: #1f2937;
  font-size: 13px;
}

.ref-item {
  border: 1px solid #e8edf3;
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 8px;
  background: #fff;
}

.ref-meta {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 4px;
}

.ref-score {
  margin-left: 8px;
  font-weight: 400;
  color: #9ca3af;
}

.ref-content {
  margin: 0;
  font-size: 12px;
  line-height: 1.55;
  color: #6b7280;
  white-space: pre-wrap;
  word-break: break-word;
}

.composer {
  padding: 0 48px 24px;
}

.composer-box {
  border: 1px solid #e5e7eb;
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
  padding: 12px 14px 10px;
}

.composer-input {
  width: 100%;
  border: none;
  outline: none;
  resize: none;
  font-size: 14px;
  line-height: 1.6;
  color: #111827;
  font-family: inherit;
  background: transparent;
}

.composer-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 8px;
}

.composer-left,
.composer-right {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex-shrink: 0;
}

.model-btn {
  max-width: 180px;
  height: 32px;
  padding: 0 10px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  color: #374151;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.model-btn.unset {
  color: #0f766e;
  border-color: #99f6e4;
  background: #f0fdfa;
}

.model-picker-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  color: #111827;
  font-size: 13px;
  font-weight: 650;
}

.add-model-link,
.goto-config {
  border: none;
  background: none;
  color: #0f766e;
  cursor: pointer;
  font-size: 13px;
  padding: 0;
  margin-left: 8px;
}

.model-empty {
  color: #6b7280;
  font-size: 13px;
  line-height: 1.6;
}

.model-empty p {
  margin: 0 0 8px !important;
}

.model-options {
  margin: 0;
  padding: 0;
  list-style: none;
}

.model-options li {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 8px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  color: #374151;
}

.model-options li span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.model-options li:hover,
.model-options li.active {
  background: #e6f7f4;
  color: #0f766e;
}

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  color: #4b5563;
  cursor: pointer;
  font-size: 15px;
  font-weight: 650;
}

.icon-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.kb-chip {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 2px 8px;
  border-radius: 999px;
  background: #e6f7f4;
  color: #0f766e;
  font-size: 12px;
}

.send-btn {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 10px;
  background: #0f766e;
  color: #fff;
  cursor: pointer;
}

.send-btn:disabled {
  background: #d1d5db;
  cursor: not-allowed;
}

.hidden-file {
  display: none;
}

.kb-picker-title,
.upload-picker button {
  font-size: 13px;
}

.kb-picker-title {
  margin-bottom: 10px;
  font-weight: 650;
  color: #111827;
}

.kb-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 10px;
}

.kb-field span {
  color: #6b7280;
  font-size: 12px;
}

.upload-picker {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.upload-picker button {
  height: 32px;
  border: none;
  border-radius: 8px;
  background: #f3f4f6;
  color: #111827;
  cursor: pointer;
}

.upload-picker button:disabled {
  color: #9ca3af;
  cursor: not-allowed;
}
</style>
