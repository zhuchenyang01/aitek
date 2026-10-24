<template>
  <div class="page">
    <p class="hint">添加 Agent 项目 → 理解项目 → 生成测试用例（覆盖安全/对话/知识源/泛化/失败错误等维度）；生成后可跳转用例管理查看。</p>

    <div class="toolbar">
      <el-button type="primary" plain icon="el-icon-plus" @click="openCreate">添加项目</el-button>
      <el-button icon="el-icon-refresh" :loading="loading" @click="fetchList">刷新</el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="tableData"
      border
      stripe
      class="project-table"
      empty-text="暂无项目，请先添加"
    >
      <el-table-column prop="id" label="id" width="80" />
      <el-table-column prop="name" label="项目名称" min-width="160" show-overflow-tooltip />
      <el-table-column prop="path" label="项目路径" min-width="200" show-overflow-tooltip />
      <el-table-column prop="agent_url" label="Agent地址" min-width="160" show-overflow-tooltip />
      <el-table-column prop="buried_point_url" label="埋点地址" min-width="150" show-overflow-tooltip />
      <el-table-column label="创建时间" width="180">
        <template slot-scope="scope">{{ scope.row.created_at || '-' }}</template>
      </el-table-column>
      <el-table-column label="更新时间" width="180">
        <template slot-scope="scope">{{ scope.row.updated_at || '-' }}</template>
      </el-table-column>
      <el-table-column label="理解状态" width="110">
        <template slot-scope="scope">
          <el-tag size="small" :type="statusType(scope.row.understand_status)">
            {{ scope.row.understand_status_label || '未理解' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right" align="center">
        <template slot-scope="scope">
          <el-button
            type="text"
            class="btn-action"
            :loading="understandingId === scope.row.id"
            :disabled="scope.row.understand_status === 'running'"
            @click="handleUnderstand(scope.row)"
          >
            理解项目
          </el-button>
          <el-button
            type="text"
            class="btn-action"
            :disabled="!scope.row.profile"
            @click="openProfile(scope.row)"
          >
            查看/编辑
          </el-button>
          <el-button
            type="text"
            class="btn-action"
            :loading="generatingId === scope.row.id"
            :disabled="scope.row.understand_status !== 'done'"
            @click="handleGenerateCases(scope.row)"
          >
            生成测试用例
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      title="添加项目"
      :visible.sync="dialogVisible"
      width="520px"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="form.name" placeholder="例如：智能日程助手" maxlength="255" />
        </el-form-item>
        <el-form-item label="项目路径" prop="path">
          <el-input v-model="form.path" placeholder="Agent 代码目录，例如 /Users/me/AITEK_艾泰克/运动健康Agent" />
        </el-form-item>
        <el-form-item label="Agent地址" prop="agent_url">
          <el-input v-model="form.agent_url" placeholder="JSON-RPC 地址，默认 http://127.0.0.1:3001" />
        </el-form-item>
        <el-form-item label="埋点地址" prop="buried_point_url">
          <el-input v-model="form.buried_point_url" placeholder="埋点服务，默认 http://127.0.0.1:5000" />
        </el-form-item>
      </el-form>
      <div slot="footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">确定</el-button>
      </div>
    </el-dialog>

    <el-dialog
      :title="profileTitle"
      :visible.sync="profileVisible"
      width="720px"
      top="6vh"
      :close-on-click-modal="false"
      @closed="resetProfile"
    >
      <div v-if="profileRow" class="profile-meta">
        <span>项目：{{ profileRow.name }}</span>
        <span>来源：{{ (profileRow.profile && profileRow.profile.source_label) || '-' }}</span>
        <span>版本：{{ (profileRow.profile && profileRow.profile.content_version) || 1 }}</span>
      </div>
      <el-input
        v-model="profileContent"
        type="textarea"
        :rows="18"
        placeholder="项目理解文案"
      />
      <div slot="footer">
        <el-button @click="profileVisible = false">关闭</el-button>
        <el-button type="primary" :loading="profileSaving" @click="saveProfile">保存修改</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { Message, MessageBox } from 'element-ui'
import {
  createAgentProject,
  generateAgentCases,
  listAgentProjects,
  understandAgentProject,
  updateAgentProjectProfile
} from '@/api/agentTest'

const emptyForm = () => ({
  name: '',
  path: '',
  agent_url: 'http://127.0.0.1:3001',
  buried_point_url: 'http://127.0.0.1:5000'
})

export default {
  name: 'AgentTestProject',
  data() {
    return {
      loading: false,
      submitting: false,
      understandingId: null,
      generatingId: null,
      tableData: [],
      dialogVisible: false,
      form: emptyForm(),
      rules: {
        name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
        path: [{ required: true, message: '请输入项目路径', trigger: 'blur' }]
      },
      profileVisible: false,
      profileSaving: false,
      profileRow: null,
      profileContent: ''
    }
  },
  computed: {
    profileTitle() {
      const name = this.profileRow && this.profileRow.name
      return name ? `项目理解 - ${name}` : '项目理解'
    }
  },
  created() {
    this.fetchList()
  },
  methods: {
    statusType(status) {
      if (status === 'done') return 'success'
      if (status === 'failed') return 'danger'
      if (status === 'running') return 'warning'
      return 'info'
    },
    async fetchList() {
      this.loading = true
      try {
        const res = await listAgentProjects()
        this.tableData = (res && res.data) || []
      } catch (e) {
        this.tableData = []
      } finally {
        this.loading = false
      }
    },
    openCreate() {
      this.form = emptyForm()
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
        try {
          const res = await createAgentProject({
            name: this.form.name.trim(),
            path: this.form.path.trim(),
            agent_url: (this.form.agent_url || '').trim() || 'http://127.0.0.1:3001',
            buried_point_url: (this.form.buried_point_url || '').trim() || 'http://127.0.0.1:5000'
          })
          Message.success((res && res.msg) || '项目创建成功')
          this.dialogVisible = false
          this.fetchList()
        } catch (e) {
          // 错误提示已由拦截器处理
        } finally {
          this.submitting = false
        }
      })
    },
    async handleUnderstand(row) {
      if (!row || !row.id) return
      this.understandingId = row.id
      try {
        const res = await understandAgentProject(row.id)
        Message.success((res && res.msg) || '项目理解已生成')
        await this.fetchList()
        const latest = this.tableData.find(item => item.id === row.id) || (res && res.data)
        if (latest) {
          this.openProfile(latest)
        }
      } catch (e) {
        this.fetchList()
      } finally {
        this.understandingId = null
      }
    },
    async handleGenerateCases(row) {
      if (!row || !row.id) return
      if (row.understand_status !== 'done') {
        Message.warning('请先完成项目理解')
        return
      }
      this.generatingId = row.id
      try {
        const res = await generateAgentCases(row.id)
        const count = (res && res.data && res.data.count) || 0
        await this.fetchList()
        MessageBox.confirm(
          `已生成 ${count} 条测试用例（覆盖越权/提示词攻击/正常异常/单多轮/知识库与 search/泛化/失败错误等维度）。是否前往用例管理查看？`,
          '生成完成',
          {
            confirmButtonText: '查看',
            cancelButtonText: '关闭',
            type: 'success'
          }
        ).then(() => {
          this.$router.push({ path: '/agent-test/cases', query: { project_id: row.id } })
        }).catch(() => {})
      } catch (e) {
        // 错误提示已由拦截器处理
      } finally {
        this.generatingId = null
      }
    },
    openProfile(row) {
      this.profileRow = row
      this.profileContent = (row.profile && row.profile.content) || ''
      this.profileVisible = true
    },
    resetProfile() {
      this.profileRow = null
      this.profileContent = ''
      this.profileSaving = false
    },
    async saveProfile() {
      if (!this.profileRow) return
      const content = (this.profileContent || '').trim()
      if (!content) {
        Message.warning('请填写项目理解文案')
        return
      }
      this.profileSaving = true
      try {
        const res = await updateAgentProjectProfile(this.profileRow.id, { content })
        Message.success((res && res.msg) || '项目理解已保存')
        this.profileVisible = false
        this.fetchList()
      } catch (e) {
        // 错误提示已由拦截器处理
      } finally {
        this.profileSaving = false
      }
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

.btn-action {
  color: #0f766e;
}

.profile-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 12px;
  color: #6b7280;
  font-size: 13px;
}
</style>
