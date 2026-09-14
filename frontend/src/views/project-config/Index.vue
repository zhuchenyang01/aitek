<template>
  <div class="page">
    <div class="toolbar">
      <el-button type="primary" plain icon="el-icon-plus" @click="openCreate">新增</el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="tableData"
      border
      stripe
      class="config-table"
      empty-text="暂无项目配置"
    >
      <el-table-column prop="key" label="KEY" min-width="140" show-overflow-tooltip />
      <el-table-column prop="value" label="VALUE" min-width="220" show-overflow-tooltip />
      <el-table-column prop="create_time" label="CREATE_TIME" width="160" />
      <el-table-column prop="remark" label="备注" min-width="180" show-overflow-tooltip />
      <el-table-column label="操作" width="160" fixed="right">
        <template slot-scope="scope">
          <el-button type="text" class="btn-edit" @click="openEdit(scope.row)">编辑</el-button>
          <el-button type="text" class="btn-delete" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      :title="dialogTitle"
      :visible.sync="dialogVisible"
      width="520px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="KEY" prop="key">
          <el-input v-model="form.key" placeholder="请输入配置 KEY" maxlength="64" />
        </el-form-item>
        <el-form-item label="VALUE" prop="value">
          <el-input
            v-model="form.value"
            type="textarea"
            :rows="3"
            placeholder="请输入配置 VALUE"
          />
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" placeholder="描述配置的作用（可选）" maxlength="255" />
        </el-form-item>
      </el-form>
      <div slot="footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">确定</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { Message, MessageBox } from 'element-ui'
import { listConfigs, createConfig, updateConfig, deleteConfig } from '@/api/projectConfig'

const emptyForm = () => ({
  id: null,
  key: '',
  value: '',
  remark: ''
})

export default {
  name: 'ProjectConfig',
  data() {
    return {
      loading: false,
      submitting: false,
      tableData: [],
      dialogVisible: false,
      isEdit: false,
      form: emptyForm(),
      rules: {
        key: [{ required: true, message: '请输入 KEY', trigger: 'blur' }],
        value: [{ required: true, message: '请输入 VALUE', trigger: 'blur' }]
      }
    }
  },
  computed: {
    dialogTitle() {
      return this.isEdit ? '编辑项目配置' : '新增项目配置'
    }
  },
  created() {
    this.fetchList()
  },
  methods: {
    async fetchList() {
      this.loading = true
      try {
        const res = await listConfigs()
        this.tableData = (res && res.data) || []
      } catch (e) {
        // 错误提示已由拦截器处理
      } finally {
        this.loading = false
      }
    },
    openCreate() {
      this.isEdit = false
      this.form = emptyForm()
      this.dialogVisible = true
    },
    openEdit(row) {
      this.isEdit = true
      this.form = {
        id: row.id,
        key: row.key,
        value: row.value,
        remark: row.remark || ''
      }
      this.dialogVisible = true
    },
    resetForm() {
      this.form = emptyForm()
      if (this.$refs.formRef) {
        this.$refs.formRef.clearValidate()
      }
    },
    submitForm() {
      this.$refs.formRef.validate(async valid => {
        if (!valid) return
        this.submitting = true
        const payload = {
          key: this.form.key.trim(),
          value: this.form.value.trim(),
          remark: (this.form.remark || '').trim()
        }
        try {
          const res = this.isEdit
            ? await updateConfig(this.form.id, payload)
            : await createConfig(payload)
          Message.success((res && res.msg) || (this.isEdit ? '修改成功' : '新增成功'))
          this.dialogVisible = false
          this.fetchList()
        } catch (e) {
          // 错误提示已由拦截器处理
        } finally {
          this.submitting = false
        }
      })
    },
    handleDelete(row) {
      MessageBox.confirm(`确定删除配置「${row.key}」吗？`, '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          const res = await deleteConfig(row.id)
          Message.success((res && res.msg) || '删除成功')
          this.fetchList()
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

.toolbar {
  margin-bottom: 16px;
}

.config-table {
  width: 100%;
}

.btn-edit {
  color: #0f766e;
}

.btn-delete {
  color: #dc2626;
}
</style>
