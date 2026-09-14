<template>
  <div class="page">
    <p class="hint">
      选择知识库后，可在线添加评测问题，或下载 Excel 模板填好后上传。评测结果只展示在本页，需要时再下载到本地。
    </p>

    <el-form :inline="true" class="toolbar">
      <el-form-item label="知识库">
        <el-select
          v-model="kbId"
          filterable
          placeholder="请选择知识库"
          style="width: 320px"
          @change="onKbChange"
        >
          <el-option
            v-for="item in knowledgeBases"
            :key="item.id"
            :label="`${item.name}（ID ${item.id} · ${kbTypeLabel(item.kb_type)}）`"
            :value="item.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-checkbox v-model="rerank">使用 rerank</el-checkbox>
      </el-form-item>
    </el-form>
    <div class="action-row">
      <el-button @click="downloadTemplate">下载评测模板</el-button>
      <el-upload
        class="inline-upload"
        action="#"
        :show-file-list="false"
        :auto-upload="false"
        accept=".xlsx"
        :on-change="onExcelChange"
      >
        <el-button>上传 Excel</el-button>
      </el-upload>
      <el-button type="primary" :loading="running" :disabled="!kbId" @click="runEval">开始评测</el-button>
    </div>

    <div class="layout-grid">
      <div class="panel">
        <div class="panel-head">
          <span>评测问题</span>
          <el-button type="text" class="btn-primary" @click="addQuery">添加问题</el-button>
        </div>
        <el-table :data="queries" border stripe empty-text="请添加问题或上传 Excel">
          <el-table-column label="问题" min-width="220">
            <template slot-scope="scope">
              <el-input v-model="scope.row.query" type="textarea" :rows="2" placeholder="真实会问的问题" />
            </template>
          </el-table-column>
          <el-table-column label="相关分块" min-width="180">
            <template slot-scope="scope">
              <el-select
                v-model="scope.row.relevant_chunk_ids"
                multiple
                filterable
                placeholder="选择相关分块 ID"
                style="width: 100%"
              >
                <el-option
                  v-for="chunk in chunks"
                  :key="chunk.id"
                  :label="`#${chunk.id} ${preview(chunk.content)}`"
                  :value="chunk.id"
                />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="相关文档 ID" width="150">
            <template slot-scope="scope">
              <el-select
                v-model="scope.row.relevant_doc_ids"
                multiple
                filterable
                placeholder="可选"
                style="width: 100%"
              >
                <el-option
                  v-for="docId in documentIds"
                  :key="docId"
                  :label="String(docId)"
                  :value="docId"
                />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="备注" min-width="110">
            <template slot-scope="scope">
              <el-input v-model="scope.row.note" placeholder="可选" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="70" align="center">
            <template slot-scope="scope">
              <el-button type="text" class="btn-delete" @click="removeQuery(scope.$index)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <aside class="chunk-panel">
        <div class="chunk-head">
          <div>
            <div class="chunk-title">对照标注</div>
            <div class="chunk-sub">对照分块 ID 与正文进行标注</div>
          </div>
          <span class="chunk-count">{{ chunks.length }} 个分块</span>
        </div>
        <div v-if="chunks.length" class="chunk-list">
          <button
            v-for="chunk in chunks"
            :key="chunk.id"
            type="button"
            class="chunk-item"
            @click="openChunk(chunk)"
          >
            <div class="chunk-meta">
              <span class="chunk-id">分块 {{ chunk.id }}</span>
              <span class="chunk-doc">文档 {{ chunk.document_id }} · {{ chunk.document_title || '未命名' }}</span>
            </div>
            <p class="chunk-text">{{ preview(chunk.content, 120) }}</p>
          </button>
        </div>
        <div v-else class="chunk-empty">请先选择知识库</div>
      </aside>
    </div>

    <el-dialog
      :title="activeChunk ? `分块 ${activeChunk.id}` : '分块内容'"
      :visible.sync="chunkDialogVisible"
      width="640px"
    >
      <p v-if="activeChunk" class="chunk-dialog-meta">
        文档 {{ activeChunk.document_id }} · {{ activeChunk.document_title || '未命名' }}
      </p>
      <pre class="chunk-dialog-content">{{ activeChunk && activeChunk.content }}</pre>
    </el-dialog>

    <div v-if="result" class="result">
      <div class="panel-head">
        <span>评测结果 · {{ result.knowledge_base_name }}（{{ result.query_count }} 条）</span>
        <el-button type="primary" plain @click="downloadResult">下载评测结果（JSON）</el-button>
      </div>
      <el-descriptions :column="2" border class="summary">
        <el-descriptions-item label="分块 Precision@3">{{ fmt(result.chunk && result.chunk['precision@3']) }}</el-descriptions-item>
        <el-descriptions-item label="分块 Recall@3">{{ fmt(result.chunk && result.chunk['recall@3']) }}</el-descriptions-item>
        <el-descriptions-item label="分块 Precision@5">{{ fmt(result.chunk && result.chunk['precision@5']) }}</el-descriptions-item>
        <el-descriptions-item label="分块 Recall@5">{{ fmt(result.chunk && result.chunk['recall@5']) }}</el-descriptions-item>
        <el-descriptions-item label="分块 MRR">{{ fmt(result.chunk && result.chunk.mrr) }}</el-descriptions-item>
        <el-descriptions-item label="文档 MRR">{{ fmt(result.doc && result.doc.mrr) }}</el-descriptions-item>
      </el-descriptions>
      <el-table :data="result.details || []" border stripe class="detail-table">
        <el-table-column prop="query" label="问题" min-width="200" show-overflow-tooltip />
        <el-table-column label="相关分块" min-width="120" show-overflow-tooltip>
          <template slot-scope="scope">{{ (scope.row.relevant_chunk_ids || []).join(', ') }}</template>
        </el-table-column>
        <el-table-column label="命中分块" min-width="120" show-overflow-tooltip>
          <template slot-scope="scope">{{ (scope.row.retrieved_chunk_ids || []).join(', ') }}</template>
        </el-table-column>
        <el-table-column label="P@3" width="80">
          <template slot-scope="scope">{{ fmt(scope.row.chunk && scope.row.chunk['p@3']) }}</template>
        </el-table-column>
        <el-table-column label="R@3" width="80">
          <template slot-scope="scope">{{ fmt(scope.row.chunk && scope.row.chunk['r@3']) }}</template>
        </el-table-column>
        <el-table-column label="P@5" width="80">
          <template slot-scope="scope">{{ fmt(scope.row.chunk && scope.row.chunk['p@5']) }}</template>
        </el-table-column>
        <el-table-column label="R@5" width="80">
          <template slot-scope="scope">{{ fmt(scope.row.chunk && scope.row.chunk['r@5']) }}</template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script>
import { Message } from 'element-ui'
import {
  downloadEvalTemplate,
  listAiTestcaseChunks,
  listAiTestcaseKnowledgeBases,
  parseEvalExcel,
  runRetrievalEval
} from '@/api/aiTestcase'

const KB_TYPE_LABEL = {
  requirement: '需求文档知识库',
  testcase: '测试用例知识库'
}

const emptyQuery = () => ({
  query: '',
  relevant_chunk_ids: [],
  relevant_doc_ids: [],
  note: ''
})

function saveBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

export default {
  name: 'RetrievalEval',
  data() {
    return {
      knowledgeBases: [],
      kbId: null,
      chunks: [],
      queries: [emptyQuery()],
      rerank: true,
      running: false,
      result: null,
      activeChunk: null,
      chunkDialogVisible: false
    }
  },
  computed: {
    documentIds() {
      const ids = new Set()
      this.chunks.forEach(item => {
        if (item.document_id != null) ids.add(item.document_id)
      })
      return Array.from(ids)
    }
  },
  created() {
    this.fetchKnowledgeBases()
  },
  methods: {
    kbTypeLabel(type) {
      return KB_TYPE_LABEL[type] || type
    },
    preview(text, max = 48) {
      const value = (text || '').replace(/\s+/g, ' ')
      return value.length > max ? `${value.slice(0, max)}…` : value
    },
    openChunk(chunk) {
      this.activeChunk = chunk
      this.chunkDialogVisible = true
    },
    fmt(value) {
      if (value === null || value === undefined || value === '') return '-'
      return Number(value).toFixed(4)
    },
    async fetchKnowledgeBases() {
      try {
        const res = await listAiTestcaseKnowledgeBases()
        this.knowledgeBases = (res && res.data) || []
      } catch (e) {
        this.knowledgeBases = []
      }
    },
    async onKbChange(kbId) {
      this.result = null
      this.chunks = []
      if (!kbId) return
      try {
        const res = await listAiTestcaseChunks(kbId)
        this.chunks = (res && res.data) || []
      } catch (e) {
        this.chunks = []
      }
    },
    addQuery() {
      this.queries.push(emptyQuery())
    },
    removeQuery(index) {
      this.queries.splice(index, 1)
      if (!this.queries.length) {
        this.queries.push(emptyQuery())
      }
    },
    async downloadTemplate() {
      try {
        const blob = await downloadEvalTemplate()
        if (blob && blob.type && blob.type.indexOf('application/json') !== -1) {
          Message.error('模板下载失败，请重新登录后再试')
          return
        }
        saveBlob(blob, 'retrieval_eval_template.xlsx')
        Message.success('模板已开始下载')
      } catch (e) {
        // 错误提示已由拦截器处理
      }
    },
    async onExcelChange(file) {
      const raw = file.raw
      if (!raw) return
      if (!/\.xlsx$/i.test(raw.name || '')) {
        Message.error('请上传 .xlsx 模板文件')
        return
      }
      try {
        const res = await parseEvalExcel(raw)
        const queries = (res && res.data && res.data.queries) || []
        this.queries = queries.map(item => ({
          query: item.query || '',
          relevant_chunk_ids: item.relevant_chunk_ids || [],
          relevant_doc_ids: item.relevant_doc_ids || [],
          note: item.note || ''
        }))
        if (!this.queries.length) {
          this.queries = [emptyQuery()]
        }
        Message.success(`已导入 ${this.queries.length} 条评测问题，可继续编辑`)
      } catch (e) {
        // 错误提示已由拦截器处理
      }
    },
    async runEval() {
      const queries = this.queries
        .map(item => ({
          query: (item.query || '').trim(),
          relevant_chunk_ids: item.relevant_chunk_ids || [],
          relevant_doc_ids: item.relevant_doc_ids || [],
          note: item.note || ''
        }))
        .filter(item => item.query)
      if (!this.kbId) {
        Message.error('请选择知识库')
        return
      }
      if (!queries.length) {
        Message.error('请至少填写一条评测问题')
        return
      }
      this.running = true
      this.result = null
      try {
        const res = await runRetrievalEval({
          knowledge_base_id: this.kbId,
          queries,
          ks: [3, 5],
          rerank: this.rerank
        })
        this.result = (res && res.data) || null
        Message.success((res && res.msg) || '评测完成')
      } catch (e) {
        // 错误提示已由拦截器处理
      } finally {
        this.running = false
      }
    },
    downloadResult() {
      if (!this.result) return
      const blob = new Blob([JSON.stringify(this.result, null, 2)], { type: 'application/json;charset=utf-8' })
      saveBlob(blob, `retrieval_eval_result_kb${this.result.knowledge_base_id || this.kbId}.json`)
      Message.success('评测结果已保存到本地')
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
  margin-bottom: 0;
}

.toolbar >>> .el-form-item {
  margin-bottom: 12px;
}

.action-row {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  margin: 0 0 16px;
}

.inline-upload {
  display: inline-block;
}

.layout-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 16px;
  align-items: stretch;
}

.panel {
  min-width: 0;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 40px;
  margin-bottom: 10px;
  font-weight: 600;
  color: #1f2937;
}

.chunk-panel {
  min-width: 0;
  min-height: 560px;
  display: flex;
  flex-direction: column;
  border: 1px solid #e8edf3;
  border-radius: 10px;
  background: #f8fafc;
  overflow: hidden;
}

.chunk-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 12px 14px 10px;
  border-bottom: 1px solid #e8edf3;
  background: #fff;
}

.chunk-title {
  font-size: 14px;
  font-weight: 650;
  color: #1f2937;
  line-height: 1.3;
}

.chunk-sub {
  margin-top: 2px;
  font-size: 12px;
  font-weight: 400;
  color: #6b7280;
}

.chunk-count {
  flex-shrink: 0;
  font-size: 12px;
  color: #0f766e;
  background: #e6f7f4;
  border-radius: 999px;
  padding: 2px 8px;
  line-height: 20px;
}

.chunk-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  min-height: 480px;
}

.chunk-item {
  display: block;
  width: 100%;
  text-align: left;
  font: inherit;
  background: #fff;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  padding: 10px 12px;
  margin: 0 0 8px;
  cursor: pointer;
}

.chunk-item:last-child {
  margin-bottom: 0;
}

.chunk-item:hover {
  border-color: #99f6e4;
  box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.08);
}

.chunk-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 10px;
  margin-bottom: 6px;
}

.chunk-id {
  font-size: 12px;
  font-weight: 650;
  color: #0f766e;
  background: #e6f7f4;
  border-radius: 4px;
  padding: 1px 6px;
}

.chunk-doc {
  font-size: 12px;
  color: #6b7280;
}

.chunk-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
  color: #374151;
  word-break: break-word;
}

.chunk-empty {
  flex: 1;
  min-height: 480px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  font-size: 13px;
}

.chunk-dialog-meta {
  margin: 0 0 8px;
  color: #6b7280;
  font-size: 13px;
}

.chunk-dialog-content {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  background: #f8fafc;
  border: 1px solid #e8edf3;
  border-radius: 8px;
  padding: 12px;
  max-height: 360px;
  overflow: auto;
  font-size: 13px;
  line-height: 1.55;
  color: #374151;
}

.btn-primary {
  color: #0f766e;
}

.btn-delete {
  color: #dc2626;
}

.result {
  margin-top: 24px;
}

.summary {
  margin-bottom: 16px;
}

.detail-table {
  width: 100%;
}

@media (max-width: 1200px) {
  .layout-grid {
    grid-template-columns: 1fr;
  }

  .chunk-panel {
    min-height: 420px;
  }

  .chunk-list,
  .chunk-empty {
    min-height: 320px;
  }
}
</style>
