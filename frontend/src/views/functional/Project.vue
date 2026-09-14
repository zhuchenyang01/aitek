<template>
  <div class="page">
    <p class="hint">创建并管理功能测试项目，需求文件请在「需求管理」中上传。</p>

    <div class="toolbar">
      <el-button type="primary" plain icon="el-icon-plus" @click="openCreate">新建项目</el-button>
      <el-button icon="el-icon-refresh" :loading="loading" @click="fetchList">刷新</el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="tableData"
      border
      stripe
      class="project-table"
      empty-text="暂无项目，请先新建"
    >
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="项目名称" min-width="180" show-overflow-tooltip />
      <el-table-column prop="description" label="描述" min-width="220" show-overflow-tooltip />
      <el-table-column prop="requirement_count" label="需求数" width="90" />
      <el-table-column prop="creator_name" label="创建人" width="120" show-overflow-tooltip />
      <el-table-column label="创建时间" width="180">
        <template slot-scope="scope">
          {{ formatTime(scope.row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template slot-scope="scope">
          <el-button type="text" class="btn-edit" @click="openEdit(scope.row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      :title="dialogTitle"
      :visible.sync="dialogVisible"
      width="480px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="form.name" placeholder="例如：登录模块" maxlength="255" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="可选" />
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
import { Message } from 'element-ui'
import { createFunctionalProject, listFunctionalProjects, updateFunctionalProject } from '@/api/functionalTest'

const emptyForm = () => ({
  id: null,
  name: '',
  description: ''
})

export default {
  name: 'FunctionalProject',
  data() {
    return {
      loading: false,
      submitting: false,
      tableData: [],
      dialogVisible: false,
      isEdit: false,
      form: emptyForm(),
      rules: {
        name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }]
      }
    }
  },
  computed: {
    dialogTitle() {
      return this.isEdit ? '编辑项目' : '新建项目'
    }
  },
  created() {
    this.fetchList()
  },
  methods: {
    formatTime(value) {
      if (!value) return ''
      return String(value).replace('T', ' ').slice(0, 19)
    },
    async fetchList() {
      this.loading = true
      try {
        const res = await listFunctionalProjects()
        this.tableData = (res && res.data) || []
      } catch (e) {
        this.tableData = []
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
        name: row.name,
        description: row.description || ''
      }
      this.dialogVisible = true
    },
    resetForm() {
      this.isEdit = false
      this.form = emptyForm()
      if (this.$refs.formRef) {
        this.$refs.formRef.clearValidate()
      }
    },
    submitForm() {
      this.$refs.formRef.validate(async valid => {
        if (!valid) return
        this.submitting = true
        try {
          const payload = {
            name: this.form.name.trim(),
            description: (this.form.description || '').trim()
          }
          const res = this.isEdit
            ? await updateFunctionalProject(this.form.id, payload)
            : await createFunctionalProject(payload)
          Message.success((res && res.msg) || (this.isEdit ? '项目修改成功' : '项目创建成功'))
          this.dialogVisible = false
          this.fetchList()
        } catch (e) {
          // 错误提示已由拦截器处理
        } finally {
          this.submitting = false
        }
      })
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

.project-table {
  width: 100%;
}

.btn-edit {
  color: #0f766e;
}
</style>
