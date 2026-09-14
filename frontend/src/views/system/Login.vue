<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-brand">
        <img class="brand-logo" src="@/assets/logo.png" alt="AItek">
        <div>
          <h1>AITEK</h1>
          <p>AI 测试开发平台</p>
        </div>
      </div>

      <el-tabs v-model="activeTab" stretch>
        <el-tab-pane label="登录" name="login">
          <el-form ref="loginForm" :model="loginForm" :rules="loginRules" @keyup.enter.native="handleLogin">
            <el-form-item prop="username">
              <el-input v-model="loginForm.username" prefix-icon="el-icon-user" placeholder="请输入用户名" />
            </el-form-item>
            <el-form-item prop="password">
              <el-input
                v-model="loginForm.password"
                prefix-icon="el-icon-lock"
                show-password
                placeholder="请输入密码"
              />
            </el-form-item>
            <el-button type="primary" class="submit-btn" :loading="loading" @click="handleLogin">
              登录
            </el-button>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="注册" name="register">
          <el-form ref="registerForm" :model="registerForm" :rules="registerRules" @keyup.enter.native="handleRegister">
            <el-form-item prop="username">
              <el-input v-model="registerForm.username" prefix-icon="el-icon-user" placeholder="请输入用户名" />
            </el-form-item>
            <el-form-item prop="password">
              <el-input
                v-model="registerForm.password"
                prefix-icon="el-icon-lock"
                show-password
                placeholder="请输入密码（至少6位）"
              />
            </el-form-item>
            <el-form-item prop="confirm_password">
              <el-input
                v-model="registerForm.confirm_password"
                prefix-icon="el-icon-lock"
                show-password
                placeholder="请再次确认密码"
              />
            </el-form-item>
            <el-button type="primary" class="submit-btn" :loading="loading" @click="handleRegister">
              注册
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script>
import { Message } from 'element-ui'
import { mapActions } from 'vuex'

export default {
  name: 'SystemLogin',
  data() {
    const validateConfirm = (rule, value, callback) => {
      if (value !== this.registerForm.password) {
        callback(new Error('两次输入的密码不一致'))
      } else {
        callback()
      }
    }
    return {
      activeTab: 'login',
      loading: false,
      loginForm: {
        username: '',
        password: ''
      },
      registerForm: {
        username: '',
        password: '',
        confirm_password: ''
      },
      loginRules: {
        username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
        password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
      },
      registerRules: {
        username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
        password: [
          { required: true, message: '请输入密码', trigger: 'blur' },
          { min: 6, message: '密码至少 6 位', trigger: 'blur' }
        ],
        confirm_password: [
          { required: true, message: '请确认密码', trigger: 'blur' },
          { validator: validateConfirm, trigger: 'blur' }
        ]
      }
    }
  },
  methods: {
    ...mapActions('system', ['login', 'register']),
    handleLogin() {
      this.$refs.loginForm.validate(async valid => {
        if (!valid) return
        this.loading = true
        try {
          const res = await this.login({
            username: this.loginForm.username.trim(),
            password: this.loginForm.password
          })
          Message.success((res && res.msg) || '登录成功')
          const redirect = this.$route.query.redirect || '/functional/projects'
          this.$router.replace(redirect)
        } catch (e) {
          // 错误提示由拦截器处理
        } finally {
          this.loading = false
        }
      })
    },
    handleRegister() {
      this.$refs.registerForm.validate(async valid => {
        if (!valid) return
        this.loading = true
        try {
          const res = await this.register({
            username: this.registerForm.username.trim(),
            password: this.registerForm.password,
            confirm_password: this.registerForm.confirm_password
          })
          Message.success((res && res.msg) || '注册成功，请登录')
          this.activeTab = 'login'
          this.loginForm.username = this.registerForm.username.trim()
          this.loginForm.password = ''
          this.registerForm = { username: '', password: '', confirm_password: '' }
        } catch (e) {
          // 错误提示由拦截器处理
        } finally {
          this.loading = false
        }
      })
    }
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background-color: #0f172a;
  background-image:
    linear-gradient(135deg, rgba(15, 23, 42, 0.62) 0%, rgba(15, 118, 110, 0.42) 55%, rgba(15, 23, 42, 0.55) 100%),
    url("~@/assets/login-bg.png");
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  font-family: "Plus Jakarta Sans", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}

.auth-card {
  width: 420px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(232, 237, 243, 0.9);
  border-radius: 16px;
  padding: 32px 28px 28px;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.18);
  backdrop-filter: blur(10px);
}

.auth-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 22px;
}

.brand-logo {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  object-fit: contain;
  flex-shrink: 0;
  background: #fff;
}

.auth-brand h1 {
  margin: 0;
  font-size: 22px;
  color: #1f2937;
  line-height: 1.2;
}

.auth-brand h1 span {
  margin-left: 6px;
  font-size: 16px;
  font-weight: 600;
  color: #0f766e;
}

.auth-brand p {
  margin: 2px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.submit-btn {
  width: 100%;
  margin-top: 4px;
}

.auth-card >>> .el-tabs__item.is-active {
  color: #0f766e;
}

.auth-card >>> .el-tabs__active-bar {
  background-color: #0f766e;
}
</style>
