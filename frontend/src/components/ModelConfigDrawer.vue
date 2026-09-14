<template>
  <el-drawer
    :title="isEdit ? '编辑模型' : '添加模型'"
    :visible="visible"
    size="480px"
    :wrapper-closable="false"
    custom-class="model-config-drawer"
    @close="handleClose"
    @closed="resetForm"
  >
    <div class="drawer-shell">
      <div class="drawer-body">
      <div class="drawer-intro">
        <i class="el-icon-chat-dot-round intro-icon" />
        <div>
          <strong>{{ typeIntroTitle }}</strong>
          <p>{{ typeIntroDesc }}</p>
        </div>
      </div>

      <div class="section">
        <div class="section-label">模型类型</div>
        <div class="type-grid">
          <button
            v-for="item in modelTypes"
            :key="item.value"
            type="button"
            class="type-btn"
            :class="{ active: form.model_type === item.value }"
            :disabled="isEdit"
            @click="setModelType(item.value)"
          >
            <i :class="item.icon" />
            <span>{{ item.label }}</span>
          </button>
        </div>
      </div>

      <div class="section">
        <div class="section-label">模型来源</div>
        <div class="source-row">
          <button
            v-for="item in modelSources"
            :key="item.value"
            type="button"
            class="source-btn"
            :class="{ active: form.source === item.value }"
            @click="setSource(item.value)"
          >
            <i :class="item.icon" />
            <span>{{ item.label }}</span>
          </button>
        </div>
      </div>

      <div class="section">
        <div class="section-label">接入配置</div>
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="config-form">
          <el-form-item v-if="form.source === 'api'" label="服务商" prop="provider">
            <el-select v-model="form.provider" placeholder="请选择服务商" style="width: 100%" @change="handleProviderChange">
              <el-option v-for="item in providerOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="模型名称" prop="model" required>
            <div v-if="form.source === 'ollama'" class="ollama-model-row">
              <el-select
                v-model="form.model"
                filterable
                placeholder="请选择本地模型"
                :loading="ollamaLoading"
                style="width: 100%"
                @visible-change="onOllamaDropdown"
              >
                <el-option
                  v-for="item in ollamaModels"
                  :key="item.name"
                  :label="item.name"
                  :value="item.name"
                />
              </el-select>
              <el-button class="refresh-btn" :loading="ollamaLoading" @click="fetchOllamaModels">刷新</el-button>
            </div>
            <el-input v-else v-model="form.model" :placeholder="modelPlaceholder" maxlength="128" />
            <div v-if="form.source === 'ollama' && ollamaError" class="field-hint error">{{ ollamaError }}</div>
            <div
              v-else-if="form.source === 'ollama' && !ollamaLoading && !ollamaModels.length"
              class="field-hint"
            >
              未检测到本地模型，请先执行 <code>ollama pull bge-m3</code> 等命令下载模型
            </div>
          </el-form-item>
          <el-form-item label="显示名称（可选）" prop="name">
            <el-input v-model="form.name" placeholder="例如：客服问答模型" maxlength="128" />
            <div class="field-hint">仅用于界面展示，实际调用仍使用上面的模型名称</div>
          </el-form-item>
          <el-form-item label="Base URL" prop="base_url" required>
            <el-input
              v-model="form.base_url"
              placeholder="例如：https://api.openai.com/v1"
              maxlength="512"
              @blur="handleBaseUrlBlur"
            />
          </el-form-item>
          <el-form-item v-if="form.source !== 'ollama'" label="API Key（可选）" prop="api_key">
            <el-input
              v-model="form.api_key"
              type="password"
              show-password
              :placeholder="apiKeyPlaceholder"
              maxlength="512"
            />
          </el-form-item>
          <el-form-item v-if="form.model_type === 'embedding'" label="向量维度">
            <el-input :value="form.dimension || '保存后通过测试连接自动检测'" disabled />
          </el-form-item>
          <el-form-item label="设为默认">
            <el-switch v-model="form.is_default" />
          </el-form-item>
        </el-form>
      </div>
      </div>

      <div class="drawer-footer">
        <el-button :loading="testing" @click="handleTest">测试连接</el-button>
        <div class="footer-right">
          <el-button @click="handleClose">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script>
import { Message } from 'element-ui'
import {
  MODEL_SOURCES,
  MODEL_TYPES,
  PROVIDER_OPTIONS,
  TYPE_DEFAULTS,
  createLlmConfig,
  listOllamaModels,
  testLlmConfig,
  updateLlmConfig
} from '@/api/llmConfig'

const emptyForm = (modelType = 'chat') => {
  const defaults = TYPE_DEFAULTS[modelType] || TYPE_DEFAULTS.chat
  return {
    id: null,
    model_type: modelType,
    source: defaults.source || 'api',
    provider: defaults.provider || 'custom',
    name: '',
    model: defaults.model || '',
    base_url: defaults.base_url || '',
    api_key: '',
    dimension: null,
    is_default: false
  }
}

const OLLAMA_PREFERRED = {
  embedding: ['bge-m3:latest', 'bge-m3', 'nomic-embed-text:latest'],
  chat: ['qwen2.5:latest', 'qwen2.5', 'deepseek-r1:latest', 'llama3.2:latest'],
  rerank: ['bge-reranker-base:latest', 'bge-reranker-base'],
  vision: ['llava:latest', 'llava', 'minicpm-v:latest'],
  voice: ['whisper:latest', 'whisper']
}

const TYPE_INTRO = {
  chat: { title: '配置用于对话的大语言模型', desc: '用于生成测试用例、问答等对话场景。' },
  embedding: { title: '配置用于向量化的 Embedding 模型', desc: '用于文档入库与知识检索，建议 bge-m3。' },
  rerank: { title: '配置用于重排序的 ReRank 模型', desc: '提升检索结果相关性，未配置时使用本地余弦重排。' },
  vision: { title: '配置用于视觉理解的模型', desc: '用于图片、文档视觉解析等场景。' },
  voice: { title: '配置用于语音处理的模型', desc: '用于语音识别与合成等场景。' }
}

export default {
  name: 'ModelConfigDrawer',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    value: {
      type: Object,
      default: null
    },
    initialType: {
      type: String,
      default: 'chat'
    }
  },
  data() {
    return {
      submitting: false,
      testing: false,
      modelTypes: MODEL_TYPES,
      modelSources: MODEL_SOURCES,
      providerOptions: PROVIDER_OPTIONS,
      form: emptyForm(),
      ollamaModels: [],
      ollamaLoading: false,
      ollamaError: '',
      rules: {
        model: [{ required: true, message: '请选择或填写模型名称', trigger: 'change' }],
        base_url: [{ required: true, message: '请填写 Base URL', trigger: 'blur' }]
      }
    }
  },
  computed: {
    isEdit() {
      return !!(this.form && this.form.id)
    },
    typeIntroTitle() {
      return (TYPE_INTRO[this.form.model_type] || TYPE_INTRO.chat).title
    },
    typeIntroDesc() {
      return (TYPE_INTRO[this.form.model_type] || TYPE_INTRO.chat).desc
    },
    modelPlaceholder() {
      const map = {
        chat: '例如：gpt-4、deepseek-chat',
        embedding: '例如：bge-m3:latest',
        rerank: '例如：rerank',
        vision: '例如：gpt-4o',
        voice: '例如：whisper-1'
      }
      return map[this.form.model_type] || '请输入模型名称'
    },
    apiKeyPlaceholder() {
      if (this.form.source === 'ollama') return 'Ollama 本地通常无需填写'
      return this.isEdit ? '不修改请留空' : '请输入 API Key'
    }
  },
  watch: {
    visible(val) {
      if (val) this.hydrate()
    }
  },
  methods: {
    hydrate() {
      if (this.value && this.value.id) {
        this.form = {
          id: this.value.id,
          model_type: this.value.model_type || 'chat',
          source: this.value.source || 'api',
          provider: this.value.provider || 'custom',
          name: this.value.name || '',
          model: this.value.model || '',
          base_url: this.value.base_url || '',
          api_key: '',
          dimension: this.value.dimension || null,
          is_default: !!this.value.is_default
        }
      } else {
        this.form = emptyForm(this.initialType || 'chat')
      }
      this.$nextTick(() => {
        if (this.$refs.formRef) this.$refs.formRef.clearValidate()
        if (this.form.source === 'ollama') {
          this.fetchOllamaModels()
        }
      })
    },
    preferredOllamaModel(names) {
      const prefs = OLLAMA_PREFERRED[this.form.model_type] || []
      for (const item of prefs) {
        if (names.includes(item)) return item
      }
      for (const item of prefs) {
        const prefix = item.split(':')[0]
        const hit = names.find(name => name === prefix || name.startsWith(`${prefix}:`))
        if (hit) return hit
      }
      return null
    },
    applyOllamaDefaultModel() {
      if (!this.ollamaModels.length) return
      const names = this.ollamaModels.map(item => item.name)
      if (this.form.model && names.includes(this.form.model)) return
      const preferred = this.preferredOllamaModel(names)
      this.form.model = preferred || names[0]
    },
    async fetchOllamaModels() {
      if (this.form.source !== 'ollama') return
      this.ollamaLoading = true
      this.ollamaError = ''
      try {
        const res = await listOllamaModels({ base_url: this.form.base_url })
        this.ollamaModels = ((res && res.data) || {}).models || []
        this.applyOllamaDefaultModel()
      } catch (e) {
        this.ollamaModels = []
        this.ollamaError = (e && e.msg) || '无法连接 Ollama，请确认服务已启动'
      } finally {
        this.ollamaLoading = false
      }
    },
    onOllamaDropdown(visible) {
      if (visible && !this.ollamaModels.length && !this.ollamaLoading) {
        this.fetchOllamaModels()
      }
    },
    handleBaseUrlBlur() {
      if (this.form.source === 'ollama') {
        this.fetchOllamaModels()
      }
    },
    setModelType(type) {
      if (this.isEdit) return
      this.form.model_type = type
      const defaults = TYPE_DEFAULTS[type] || TYPE_DEFAULTS.chat
      this.form.source = defaults.source || 'api'
      this.form.provider = defaults.provider || 'custom'
      this.form.model = defaults.model || ''
      this.form.base_url = defaults.base_url || ''
      if (this.form.source === 'ollama') {
        this.fetchOllamaModels()
      }
    },
    setSource(source) {
      this.form.source = source
      if (source === 'ollama') {
        this.form.provider = 'ollama'
        this.form.base_url = 'http://127.0.0.1:11434/v1'
        this.ollamaModels = []
        this.ollamaError = ''
        this.fetchOllamaModels()
      } else {
        this.ollamaModels = []
        this.ollamaError = ''
      }
    },
    handleProviderChange(provider) {
      const preset = TYPE_DEFAULTS[this.form.model_type] || {}
      if (provider === 'ollama') {
        this.form.source = 'ollama'
        this.form.base_url = 'http://127.0.0.1:11434/v1'
        this.fetchOllamaModels()
        return
      }
      const map = {
        deepseek: { model: 'deepseek-chat', base_url: 'https://api.deepseek.com/v1' },
        openai: { model: preset.model || 'gpt-4o-mini', base_url: 'https://api.openai.com/v1' },
        qwen: { model: 'qwen-plus', base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1' },
        moonshot: { model: 'moonshot-v1-8k', base_url: 'https://api.moonshot.cn/v1' },
        zhipu: { model: 'glm-4', base_url: 'https://open.bigmodel.cn/api/paas/v4' },
        custom: { model: preset.model || '', base_url: preset.base_url || '' }
      }
      const item = map[provider] || map.custom
      if (item.model) this.form.model = item.model
      if (item.base_url) this.form.base_url = item.base_url
    },
    buildPayload() {
      const payload = {
        model_type: this.form.model_type,
        source: this.form.source,
        provider: this.form.source === 'ollama' ? 'ollama' : this.form.provider,
        name: (this.form.name || '').trim(),
        model: (this.form.model || '').trim(),
        base_url: (this.form.base_url || '').trim(),
        is_default: this.form.is_default
      }
      if ((this.form.api_key || '').trim()) {
        payload.api_key = this.form.api_key.trim()
      }
      return payload
    },
    handleClose() {
      this.$emit('update:visible', false)
    },
    resetForm() {
      this.form = emptyForm()
      this.ollamaModels = []
      this.ollamaError = ''
      this.submitting = false
      this.testing = false
    },
    handleTest() {
      this.$refs.formRef.validate(async valid => {
        if (!valid) return
        const payload = this.buildPayload()
        if (this.isEdit) payload.id = this.form.id
        if (!payload.api_key && payload.source !== 'ollama' && !this.isEdit) {
          Message.error('请先填写 API Key')
          return
        }
        this.testing = true
        try {
          const res = await testLlmConfig(payload)
          const data = (res && res.data) || {}
          if (data.dimension) {
            this.form.dimension = data.dimension
          }
          Message.success((res && res.msg) || '连接成功')
        } catch (e) {
          // 拦截器已提示
        } finally {
          this.testing = false
        }
      })
    },
    submit() {
      this.$refs.formRef.validate(async valid => {
        if (!valid) return
        const payload = this.buildPayload()
        if (!payload.api_key && payload.source !== 'ollama' && !this.isEdit) {
          Message.error('请填写 API Key')
          return
        }
        this.submitting = true
        try {
          let res
          if (this.isEdit) {
            res = await updateLlmConfig(this.form.id, payload)
          } else {
            res = await createLlmConfig(payload)
          }
          Message.success((res && res.msg) || '已保存')
          this.$emit('saved', (res && res.data) || null)
          this.handleClose()
        } catch (e) {
          // 拦截器已提示
        } finally {
          this.submitting = false
        }
      })
    }
  }
}
</script>

<style scoped>
.drawer-shell {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.drawer-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0 4px 8px;
}

.drawer-intro {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  padding: 14px;
  border-radius: 12px;
  background: #f0fdfa;
}

.intro-icon {
  font-size: 22px;
  color: #0f766e;
  margin-top: 2px;
}

.drawer-intro strong {
  display: block;
  color: #111827;
  font-size: 14px;
  margin-bottom: 4px;
}

.drawer-intro p {
  margin: 0 !important;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.5;
}

.section {
  margin-bottom: 18px;
}

.section-label {
  margin-bottom: 10px;
  color: #374151;
  font-size: 13px;
  font-weight: 650;
}

.type-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.type-btn,
.source-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 64px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
  color: #374151;
  cursor: pointer;
  font-size: 12px;
}

.type-btn i,
.source-btn i {
  font-size: 18px;
}

.type-btn.active,
.source-btn.active {
  border-color: #0f766e;
  background: #ecfdf5;
  color: #0f766e;
}

.type-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.source-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.config-form >>> .el-form-item {
  margin-bottom: 18px;
}

.config-form >>> .el-form-item__label {
  padding-bottom: 4px;
  line-height: 1.4;
  color: #374151;
  font-weight: 600;
}

.field-hint {
  margin-top: 4px;
  color: #9ca3af;
  font-size: 12px;
  line-height: 1.4;
}

.field-hint.error {
  color: #dc2626;
}

.field-hint code {
  padding: 1px 4px;
  border-radius: 4px;
  background: #f3f4f6;
  color: #374151;
  font-size: 12px;
}

.ollama-model-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.refresh-btn {
  flex-shrink: 0;
  color: #0f766e;
}

.drawer-footer {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 4px 0;
  margin-top: 8px;
  border-top: 1px solid #eef2f6;
  background: #fff;
}

.footer-right {
  display: flex;
  gap: 8px;
}
</style>

<style>
.model-config-drawer .el-drawer__header {
  margin-bottom: 12px;
  padding-bottom: 16px;
  border-bottom: 1px solid #eef2f6;
}

.model-config-drawer .el-drawer__body {
  display: flex;
  flex-direction: column;
  height: calc(100% - 60px);
  padding: 0 20px 20px;
  overflow: hidden;
}
</style>
