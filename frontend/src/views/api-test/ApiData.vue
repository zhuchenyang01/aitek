<template>
  <div class="page">
    <p class="hint">保存接口请求/登录等 JSON 数据，关联已解析的接口 ID，供后续用例执行引用。</p>

    <div class="toolbar">
      <el-select v-model="filterInterfaceId" placeholder="全部接口" clearable filterable class="filter-item" @change="handleFilterChange">
        <el-option
          v-for="item in interfaces"
          :key="item.id"
          :label="interfaceLabel(item)"
          :value="item.id"
        />
      </el-select>
      <el-input v-model="keyword" clearable placeholder="搜索数据描述" class="filter-item" @keyup.enter.native="handleFilterChange" />
      <el-button type="primary" plain icon="el-icon-plus" @click="openCreate">新建数据</el-button>
      <el-button icon="el-icon-refresh" :loading="loading" @click="fetchList">刷新</el-button>
    </div>

    <el-table v-loading="loading" :data="tableData" border stripe empty-text="暂无数据配置，请先新建">
      <el-table-column prop="id" label="id" width="80" />
      <el-table-column prop="interface_id" label="关联解析接口的 ID" width="160" />
      <el-table-column prop="description" label="数据描述" min-width="180" show-overflow-tooltip />
      <el-table-column label="数据" min-width="280" show-overflow-tooltip>
        <template slot-scope="scope">
          <span class="json-cell">{{ formatPayload(scope.row.payload) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="日期" width="180" />
      <el-table-column label="操作" width="160" align="center">
        <template slot-scope="scope">
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

    <el-dialog :title="formTitle" :visible.sync="dialogVisible" width="640px" append-to-body :close-on-click-modal="false" @closed="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="140px">
        <el-form-item label="关联解析接口的 ID" prop="interface_id">
          <el-select v-model="form.interface_id" placeholder="请选择接口" filterable style="width: 100%">
            <el-option
              v-for="item in interfaces"
              :key="item.id"
              :label="interfaceLabel(item)"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="数据描述" prop="description">
          <el-input v-model="form.description" placeholder="例如：正确的账号和密码" />
        </el-form-item>
        <el-form-item label="数据" prop="payloadText">
          <el-input
            v-model="form.payloadText"
            type="textarea"
            :rows="8"
            placeholder='例如：{"username":"13800000000","password":"******"}'
          />
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">保存</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import {
  createApiDataset,
  deleteApiDataset,
  listApiDatasets,
  listApiInterfaces,
  updateApiDataset
} from '@/api/aiApiTest'

export default {
  name: 'ApiData',
  data() {
    return {
      loading: false,
      saving: false,
      tableData: [],
      interfaces: [],
      filterInterfaceId: '',
      keyword: '',
      page: 1,
      pageSize: 20,
      total: 0,
      dialogVisible: false,
      editingId: null,
      form: {
        interface_id: '',
        description: '',
        payloadText: '{\n  \n}'
      },
      rules: {
        interface_id: [{ required: true, message: '请选择关联接口', trigger: 'change' }],
        description: [{ required: true, message: '请填写数据描述', trigger: 'blur' }],
        payloadText: [{ required: true, validator: this.validatePayload, trigger: 'blur' }]
      }
    }
  },
  computed: {
    formTitle() {
      return this.editingId ? '编辑数据' : '新建数据'
    }
  },
  created() {
    this.fetchInterfaces()
    this.fetchList()
  },
  methods: {
    interfaceLabel(item) {
      return `[${item.id}] ${item.method} ${item.name}`
    },
    formatPayload(payload) {
      try {
        return JSON.stringify(payload)
      } catch (e) {
        return String(payload)
      }
    },
    validatePayload(rule, value, callback) {
      const text = (value || '').trim()
      if (!text) {
        callback(new Error('请填写 JSON 数据'))
        return
      }
      try {
        const parsed = JSON.parse(text)
        if (parsed === null || typeof parsed !== 'object') {
          callback(new Error('数据必须是 JSON 对象或数组'))
          return
        }
        callback()
      } catch (e) {
        callback(new Error('数据必须是合法 JSON'))
      }
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
        const res = await listApiDatasets({
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
      this.form = {
        interface_id: this.filterInterfaceId || '',
        description: '',
        payloadText: '{\n  \n}'
      }
      this.dialogVisible = true
    },
    openEdit(row) {
      this.editingId = row.id
      this.form = {
        interface_id: row.interface_id,
        description: row.description,
        payloadText: JSON.stringify(row.payload, null, 2)
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
        this.saving = true
        const payload = {
          interface_id: this.form.interface_id,
          description: this.form.description,
          payload: JSON.parse(this.form.payloadText)
        }
        try {
          if (this.editingId) {
            await updateApiDataset(this.editingId, payload)
            this.$message.success('数据已更新')
          } else {
            await createApiDataset(payload)
            this.$message.success('数据保存成功')
          }
          this.dialogVisible = false
          this.fetchList()
        } finally {
          this.saving = false
        }
      })
    },
    handleDelete(row) {
      this.$confirm(`确定删除数据「${row.description}」？`, '提示', {
        type: 'warning'
      }).then(async () => {
        await deleteApiDataset(row.id)
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

.json-cell {
  font-family: Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
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
  color: #409eff;
  cursor: pointer;
  font-size: 14px;
}

.link-btn.is-danger {
  color: #f56c6c;
}
</style>
