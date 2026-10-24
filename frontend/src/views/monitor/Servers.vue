<template>
  <div class="page">
    <p class="hint">配置远程 Linux 服务器的 SSH 信息，测试连通后可在监控看板查看实时指标与历史曲线。</p>

    <div class="toolbar">
      <el-button type="primary" plain icon="el-icon-plus" @click="openCreate">新增服务器</el-button>
      <el-button icon="el-icon-refresh" :loading="loading" @click="fetchList">刷新</el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="tableData"
      border
      stripe
      empty-text="暂无服务器，请先新增"
    >
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="名称" min-width="120" show-overflow-tooltip />
      <el-table-column label="地址" min-width="160" show-overflow-tooltip>
        <template slot-scope="scope">{{ scope.row.host }}:{{ scope.row.port }}</template>
      </el-table-column>
      <el-table-column prop="username" label="用户名" width="110" show-overflow-tooltip />
      <el-table-column label="持续采集" width="100" align="center">
        <template slot-scope="scope">
          <el-tag size="mini" :type="scope.row.enabled ? 'success' : 'info'">
            {{ scope.row.enabled ? '开' : '关' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100" align="center">
        <template slot-scope="scope">
          <el-tag size="mini" :type="statusType(scope.row.last_status)">
            {{ statusLabel(scope.row.last_status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="last_collect_at" label="最近采集" width="170" />
      <el-table-column prop="last_error" label="最近错误" min-width="160" show-overflow-tooltip />
      <el-table-column label="操作" width="280" fixed="right" align="center">
        <template slot-scope="scope">
          <el-button
            type="text"
            :loading="testingId === scope.row.id"
            @click="handleTest(scope.row)"
          >测试连接</el-button>
          <el-button type="text" @click="openEdit(scope.row)">编辑</el-button>
          <el-button type="text" class="btn-delete" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      :title="isEdit ? '编辑服务器' : '新增服务器'"
      :visible.sync="dialogVisible"
      width="520px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="例如：压测机-1" maxlength="128" />
        </el-form-item>
        <el-form-item label="主机" prop="host">
          <el-input v-model="form.host" placeholder="IP 或域名" maxlength="255" />
        </el-form-item>
        <el-form-item label="端口" prop="port">
          <el-input-number v-model="form.port" :min="1" :max="65535" controls-position="right" />
        </el-form-item>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="SSH 用户名" maxlength="128" />
        </el-form-item>
        <el-form-item label="密码" :prop="isEdit ? '' : 'password'">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="isEdit ? '留空则不修改密码' : 'SSH 密码'"
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item label="持续采集">
          <el-switch v-model="form.enabled" />
          <span class="form-tip">开启后可用管理命令定时补采</span>
        </el-form-item>
        <el-form-item label="采集间隔(秒)" prop="collect_interval">
          <el-input-number v-model="form.collect_interval" :min="3" :max="3600" controls-position="right" />
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
import {
  listMonitorServers,
  createMonitorServer,
  updateMonitorServer,
  deleteMonitorServer,
  testMonitorServer
} from '@/api/monitor'

const emptyForm = () => ({
  id: null,
  name: '',
  host: '',
  port: 22,
  username: '',
  password: '',
  enabled: false,
  collect_interval: 5
})

export default {
  name: 'MonitorServers',
  data() {
    return {
      loading: false,
      submitting: false,
      testingId: null,
      tableData: [],
      dialogVisible: false,
      isEdit: false,
      form: emptyForm(),
      rules: {
        name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
        host: [{ required: true, message: '请输入主机', trigger: 'blur' }],
        port: [{ required: true, message: '请输入端口', trigger: 'change' }],
        username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
        password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
      }
    }
  },
  created() {
    this.fetchList()
  },
  methods: {
    statusType(s) {
      if (s === 'ok') return 'success'
      if (s === 'error') return 'danger'
      return 'info'
    },
    statusLabel(s) {
      if (s === 'ok') return '正常'
      if (s === 'error') return '异常'
      return '未知'
    },
    async fetchList() {
      this.loading = true
      try {
        const res = await listMonitorServers()
        this.tableData = (res && res.data) || []
      } catch (e) {
        // interceptor
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
        host: row.host,
        port: row.port || 22,
        username: row.username,
        password: '',
        enabled: !!row.enabled,
        collect_interval: row.collect_interval || 5
      }
      this.dialogVisible = true
    },
    resetForm() {
      this.form = emptyForm()
      if (this.$refs.formRef) this.$refs.formRef.clearValidate()
    },
    submitForm() {
      this.$refs.formRef.validate(async (valid) => {
        if (!valid) return
        this.submitting = true
        try {
          const payload = {
            name: this.form.name,
            host: this.form.host,
            port: this.form.port,
            username: this.form.username,
            enabled: this.form.enabled,
            collect_interval: this.form.collect_interval
          }
          if (this.form.password) payload.password = this.form.password
          if (this.isEdit) {
            await updateMonitorServer(this.form.id, payload)
            Message.success('更新成功')
          } else {
            await createMonitorServer({ ...payload, password: this.form.password })
            Message.success('创建成功')
          }
          this.dialogVisible = false
          this.fetchList()
        } catch (e) {
          // interceptor
        } finally {
          this.submitting = false
        }
      })
    },
    async handleTest(row) {
      this.testingId = row.id
      try {
        const res = await testMonitorServer(row.id)
        const uname = (res && res.data && res.data.uname) || ''
        Message.success(uname ? `连接成功：${uname}` : '连接成功')
        this.fetchList()
      } catch (e) {
        this.fetchList()
      } finally {
        this.testingId = null
      }
    },
    handleDelete(row) {
      MessageBox.confirm(`确定删除服务器「${row.name}」？历史指标也会删除。`, '提示', {
        type: 'warning'
      })
        .then(async () => {
          await deleteMonitorServer(row.id)
          Message.success('已删除')
          this.fetchList()
        })
        .catch(() => {})
    }
  }
}
</script>

<style scoped>
.page {
  padding: 4px 0;
}
.hint {
  margin: 0 0 12px;
  color: #606266;
  font-size: 13px;
  line-height: 1.5;
}
.toolbar {
  margin-bottom: 12px;
}
.btn-delete {
  color: #f56c6c;
}
.form-tip {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}
</style>
