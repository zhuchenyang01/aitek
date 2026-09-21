<template>
  <el-dialog
    :title="title"
    :visible.sync="innerVisible"
    custom-class="generate-process-dialog"
    width="920px"
    top="6vh"
    :close-on-click-modal="false"
    append-to-body
    @closed="$emit('closed')"
  >
    <el-alert
      v-if="error"
      class="gpd-alert"
      :title="error"
      type="error"
      show-icon
      :closable="false"
    />

    <div class="gpd-status">
      <span class="gpd-pill" :class="statusClass">
        <i :class="statusIcon" />
        {{ statusText }}
      </span>
      <span v-if="currentStep" class="gpd-current">{{ currentStep }}</span>
      <span v-else class="gpd-current muted">{{ generating ? '正在连接模型…' : '等待开始' }}</span>
    </div>

    <div class="gpd-panes">
      <section class="gpd-pane">
        <header class="gpd-pane-head">
          <span class="gpd-pane-title">
            <i class="el-icon-cpu" />
            模型思考
          </span>
          <span v-if="generating && !thinking" class="gpd-live">思考中</span>
        </header>
        <div ref="thinkRef" class="gpd-scroll gpd-scroll-think">
          <ol v-if="steps.length" class="gpd-steps">
            <li v-for="(line, index) in steps" :key="'s' + index">{{ line }}</li>
          </ol>
          <pre class="gpd-text">{{ thinkingDisplay }}</pre>
        </div>
      </section>

      <section class="gpd-pane">
        <header class="gpd-pane-head">
          <span class="gpd-pane-title">
            <i class="el-icon-document" />
            生成过程
          </span>
          <span v-if="generating && !answer" class="gpd-live">输出中</span>
        </header>
        <div ref="answerRef" class="gpd-scroll gpd-scroll-answer">
          <pre class="gpd-text gpd-mono">{{ answerDisplay }}</pre>
          <div v-if="resultHint || resultItems.length" class="gpd-result">
            <p v-if="resultHint" class="gpd-result-hint">{{ resultHint }}</p>
            <ul v-if="resultItems.length" class="gpd-names">
              <li v-for="name in resultItems" :key="name">{{ name }}</li>
            </ul>
          </div>
        </div>
      </section>
    </div>

    <span slot="footer">
      <el-button v-if="canView" type="primary" plain @click="$emit('view')">查看用例</el-button>
      <el-button v-if="generating" type="warning" plain @click="$emit('abort')">停止生成</el-button>
      <el-button @click="innerVisible = false">关闭</el-button>
    </span>
  </el-dialog>
</template>

<script>
export default {
  name: 'GenerateProcessDialog',
  props: {
    visible: { type: Boolean, default: false },
    title: { type: String, default: '生成测试用例' },
    generating: { type: Boolean, default: false },
    error: { type: String, default: '' },
    thinking: { type: String, default: '' },
    answer: { type: String, default: '' },
    steps: { type: Array, default: () => [] },
    currentStep: { type: String, default: '' },
    resultItems: { type: Array, default: () => [] },
    resultHint: { type: String, default: '' },
    canView: { type: Boolean, default: false }
  },
  computed: {
    innerVisible: {
      get() {
        return this.visible
      },
      set(value) {
        this.$emit('update:visible', value)
      }
    },
    statusClass() {
      if (this.error) return 'is-error'
      if (this.generating) return 'is-running'
      if (this.canView || this.resultHint) return 'is-done'
      return 'is-idle'
    },
    statusText() {
      if (this.error) return '生成失败'
      if (this.generating) return '生成中'
      if (this.canView || this.resultHint) return '已完成'
      return '未开始'
    },
    statusIcon() {
      if (this.error) return 'el-icon-warning'
      if (this.generating) return 'el-icon-loading'
      if (this.canView || this.resultHint) return 'el-icon-success'
      return 'el-icon-time'
    },
    thinkingDisplay() {
      if (this.thinking) return this.thinking
      if (this.generating) return '等待模型思考…'
      return '暂无思考内容'
    },
    answerDisplay() {
      if (this.answer) return this.answer
      if (this.generating) return '等待模型输出用例…'
      return '暂无生成内容'
    }
  },
  watch: {
    thinking() {
      this.scrollPanes()
    },
    answer() {
      this.scrollPanes()
    },
    steps() {
      this.scrollPanes()
    }
  },
  methods: {
    scrollPanes() {
      this.$nextTick(() => {
        ;['thinkRef', 'answerRef'].forEach(name => {
          const el = this.$refs[name]
          if (el) el.scrollTop = el.scrollHeight
        })
      })
    }
  }
}
</script>

<style>
.generate-process-dialog {
  border-radius: 12px;
  overflow: hidden;
}

.generate-process-dialog .el-dialog__header {
  padding: 16px 20px 12px;
  border-bottom: 1px solid #e8edf3;
}

.generate-process-dialog .el-dialog__title {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.generate-process-dialog .el-dialog__body {
  padding: 16px 20px 8px;
}

.generate-process-dialog .el-dialog__footer {
  padding: 12px 20px 16px;
  border-top: 1px solid #e8edf3;
}

.gpd-alert {
  margin-bottom: 12px;
}

.gpd-status {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  min-height: 28px;
}

.gpd-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.2;
}

.gpd-pill.is-running {
  color: #0f766e;
  background: #ccfbf1;
}

.gpd-pill.is-done {
  color: #047857;
  background: #d1fae5;
}

.gpd-pill.is-error {
  color: #b91c1c;
  background: #fee2e2;
}

.gpd-pill.is-idle {
  color: #6b7280;
  background: #f3f4f6;
}

.gpd-current {
  font-size: 13px;
  color: #374151;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gpd-current.muted {
  color: #9ca3af;
}

.gpd-panes {
  display: flex;
  gap: 12px;
  height: 440px;
}

.gpd-pane {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid #e8edf3;
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
}

.gpd-pane-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: #f0fdfa;
  border-bottom: 1px solid #ccfbf1;
}

.gpd-pane-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #0f766e;
}

.gpd-live {
  font-size: 12px;
  color: #0d9488;
}

.gpd-scroll {
  flex: 1;
  overflow: auto;
  padding: 12px;
}

.gpd-scroll-think {
  background: #f8fafc;
}

.gpd-scroll-answer {
  background: #fff;
}

.gpd-steps {
  margin: 0 0 12px;
  padding-left: 18px;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.55;
}

.gpd-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.6;
  color: #111827;
  font-family: inherit;
}

.gpd-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 12px;
  color: #1f2937;
}

.gpd-result {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed #e5e7eb;
}

.gpd-result-hint {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 600;
  color: #0f766e;
}

.gpd-names {
  margin: 0;
  padding-left: 18px;
  color: #0f766e;
  font-size: 13px;
  line-height: 1.6;
}
</style>
