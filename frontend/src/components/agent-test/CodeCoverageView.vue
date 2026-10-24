<template>
  <div class="coverage-root">
    <div v-if="!traces.length" class="empty">暂无代码覆盖率数据</div>
    <div v-for="(trace, tIdx) in traces" :key="tIdx" class="trace-block">
      <div class="trace-header">
        <span class="fn">{{ trace.function_name || '未知函数' }}</span>
        <span class="meta">
          覆盖率 {{ formatCoverage(trace.coverage_percentage) }}%
          （{{ trace.executed_lines || 0 }}/{{ trace.total_lines || 0 }} 行）
        </span>
      </div>
      <div v-if="trace.filename" class="filename" :title="trace.filename">{{ shortPath(trace.filename) }}</div>
      <div class="legend">
        <span class="lg executed">已执行</span>
        <span class="lg not-executed">未执行</span>
        <span class="lg blank">空行</span>
      </div>
      <div class="code-panel">
        <div
          v-for="(line, lIdx) in lineList(trace)"
          :key="lIdx"
          class="code-line"
          :class="lineClass(line)"
        >
          <span class="ln">{{ line.line_num }}</span>
          <span class="mark">{{ markSymbol(line) }}</span>
          <span class="code">{{ line.content === '' ? ' ' : line.content }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CodeCoverageView',
  props: {
    /** traces 数组，或 { traces: [] }，或单条带 execution_details 的对象 */
    source: {
      type: [Array, Object],
      default: null
    }
  },
  computed: {
    traces() {
      const src = this.source
      if (!src) return []
      if (Array.isArray(src)) {
        return src.filter(t => t && (t.execution_details || t.function_name))
      }
      if (Array.isArray(src.traces)) {
        return src.traces.filter(t => t && (t.execution_details || t.function_name))
      }
      if (src.execution_details) return [src]
      return []
    }
  },
  methods: {
    lineList(trace) {
      const details = (trace && trace.execution_details) || []
      return Array.isArray(details) ? details : []
    },
    formatCoverage(v) {
      if (v == null || v === '') return '-'
      const n = Number(v)
      return Number.isNaN(n) ? v : n.toFixed(1)
    },
    shortPath(path) {
      if (!path) return ''
      const parts = String(path).split(/[/\\]/)
      return parts.slice(-3).join('/')
    },
    lineClass(line) {
      const status = (line && line.status) || ''
      if (status === 'executed') return 'is-executed'
      if (status === 'not_executed') return 'is-not-executed'
      return 'is-blank'
    },
    markSymbol(line) {
      const status = (line && line.status) || ''
      if (status === 'executed') return '✓'
      if (status === 'not_executed') return '✗'
      return ' '
    }
  }
}
</script>

<style scoped>
.coverage-root {
  text-align: left;
}

.empty {
  color: #94a3b8;
  font-size: 13px;
}

.trace-block + .trace-block {
  margin-top: 16px;
}

.trace-header {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 4px;
}

.fn {
  font-weight: 600;
  color: #0f172a;
}

.meta {
  font-size: 12px;
  color: #64748b;
}

.filename {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 6px;
  word-break: break-all;
}

.legend {
  display: flex;
  gap: 10px;
  margin-bottom: 8px;
  font-size: 12px;
}

.lg {
  padding: 2px 8px;
  border-radius: 4px;
}

.lg.executed {
  background: #bbf7d0;
  color: #166534;
}

.lg.not-executed {
  background: #fecaca;
  color: #991b1b;
}

.lg.blank {
  background: #f1f5f9;
  color: #64748b;
}

.code-panel {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: auto;
  max-height: 420px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  line-height: 1.55;
  background: #fff;
}

.code-line {
  display: flex;
  align-items: stretch;
  min-height: 22px;
  white-space: pre;
}

.code-line .ln {
  flex: 0 0 52px;
  padding: 0 8px;
  text-align: right;
  color: #64748b;
  background: rgba(15, 23, 42, 0.04);
  user-select: none;
  border-right: 1px solid rgba(148, 163, 184, 0.35);
}

.code-line .mark {
  flex: 0 0 22px;
  text-align: center;
  user-select: none;
}

.code-line .code {
  flex: 1;
  padding: 0 10px;
  min-width: 0;
}

.is-executed {
  background: #bbf7d0;
}

.is-executed .mark {
  color: #15803d;
}

.is-not-executed {
  background: #fecaca;
}

.is-not-executed .mark {
  color: #b91c1c;
}

.is-blank {
  background: #f8fafc;
}

.is-blank .mark {
  color: #cbd5e1;
}
</style>
