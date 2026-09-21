<template>
  <el-container class="layout">
    <el-aside :width="asideWidth" class="layout-aside" :class="{ 'is-collapsed': sidebarCollapsed }">
      <div class="brand">
        <img class="brand-logo" src="@/assets/logo.png" alt="AItek">
        <div v-show="!sidebarCollapsed" class="brand-text">
          <strong>AITEK</strong>
          <span>AI 测试开发平台</span>
        </div>
      </div>

      <el-menu
        class="side-menu"
        :default-active="activeMenu"
        :unique-opened="true"
        :collapse="sidebarCollapsed"
        :collapse-transition="false"
        router
      >
        <el-submenu index="functional">
          <template slot="title">
            <i class="el-icon-s-grid" />
            <span>功能测试</span>
          </template>
          <el-menu-item index="/functional/projects">项目管理</el-menu-item>
          <el-menu-item index="/functional/requirements">需求管理</el-menu-item>
          <el-menu-item index="/functional/testcases">测试用例</el-menu-item>
        </el-submenu>

        <el-submenu index="api-test">
          <template slot="title">
            <i class="el-icon-connection" />
            <span>接口测试</span>
          </template>
          <el-menu-item index="/api-test/apis">接口管理</el-menu-item>
          <el-menu-item index="/api-test/cases">接口用例</el-menu-item>
          <el-menu-item index="/api-test/data">数据配置</el-menu-item>
          <el-menu-item index="/api-test/runs">用例执行</el-menu-item>
          <el-menu-item index="/api-test/reports">测试报告</el-menu-item>
        </el-submenu>

        <el-menu-item index="/web-auto">
          <i class="el-icon-monitor" />
          <span slot="title">Web 自动化测试</span>
        </el-menu-item>
        <el-menu-item index="/app-auto">
          <i class="el-icon-mobile-phone" />
          <span slot="title">APP 自动化测试</span>
        </el-menu-item>
        <el-menu-item index="/project-config">
          <i class="el-icon-setting" />
          <span slot="title">项目配置</span>
        </el-menu-item>
        <el-menu-item index="/llm-config">
          <i class="el-icon-cpu" />
          <span slot="title">模型配置</span>
        </el-menu-item>
        <!-- AI 生成测试用例（聊天页）暂时下线，后续从功能测试-需求管理触发生成 -->
        <!-- <el-menu-item index="/ai-testcase">
          <i class="el-icon-document-copy" />
          <span slot="title">AI 生成测试用例</span>
        </el-menu-item> -->
        <el-menu-item index="/retrieval-eval">
          <i class="el-icon-data-analysis" />
          <span slot="title">检索评测</span>
        </el-menu-item>
      </el-menu>

      <button
        type="button"
        class="aside-toggle"
        :title="sidebarCollapsed ? '展开导航' : '收起导航'"
        @click="toggleSidebar"
      >
        <i :class="sidebarCollapsed ? 'el-icon-s-unfold' : 'el-icon-s-fold'" />
        <span v-show="!sidebarCollapsed">收起</span>
      </button>
    </el-aside>

    <el-container class="layout-right">
      <el-header class="layout-header" height="60px">
        <div class="header-title">{{ pageTitle }}</div>
        <div class="header-actions">
          <span class="username">{{ username }}</span>
          <el-button type="text" class="logout-btn" @click="handleLogout">退出</el-button>
        </div>
      </el-header>
      <el-main class="layout-main">
        <div class="main-panel">
          <router-view />
        </div>
      </el-main>
    </el-container>
  </el-container>
</template>

<script>
import { Message } from 'element-ui'
import { mapActions, mapState } from 'vuex'

const TITLE_MAP = {
  '/functional/projects': '项目管理',
  '/functional/requirements': '需求管理',
  '/functional/testcases': '测试用例',
  '/api-test/apis': '接口管理',
  '/api-test/cases': '接口用例',
  '/api-test/data': '数据配置',
  '/api-test/runs': '用例执行',
  '/api-test/reports': '测试报告',
  '/web-auto': 'Web 自动化测试',
  '/app-auto': 'APP 自动化测试',
  '/project-config': '项目配置',
  '/llm-config': '模型配置',
  '/retrieval-eval': '检索评测'
}

const SIDEBAR_STORAGE_KEY = 'aitek_sidebar_collapsed'
const SIDEBAR_EXPANDED_WIDTH = '200px'
const SIDEBAR_COLLAPSED_WIDTH = '64px'

export default {
  name: 'AppLayout',
  data() {
    return {
      sidebarCollapsed: localStorage.getItem(SIDEBAR_STORAGE_KEY) === '1'
    }
  },
  computed: {
    ...mapState('system', ['user']),
    asideWidth() {
      return this.sidebarCollapsed ? SIDEBAR_COLLAPSED_WIDTH : SIDEBAR_EXPANDED_WIDTH
    },
    activeMenu() {
      return this.$route.path
    },
    pageTitle() {
      return TITLE_MAP[this.$route.path] || 'AI 测试开发平台'
    },
    username() {
      return (this.user && this.user.username) || '未登录'
    }
  },
  methods: {
    ...mapActions('system', ['logout']),
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed
      localStorage.setItem(SIDEBAR_STORAGE_KEY, this.sidebarCollapsed ? '1' : '0')
    },
    async handleLogout() {
      await this.logout()
      Message.success('已退出登录')
      this.$router.replace('/login')
    }
  }
}
</script>

<style scoped>
.layout {
  --aside-bg: #f7f9fc;
  --aside-border: #e6ebf2;
  --brand: #0f766e;
  --brand-soft: #ccfbf1;
  --text: #1f2937;
  --text-muted: #6b7280;
  --hover: #eef2f7;
  --active-bg: #e6f7f4;
  --surface: #ffffff;
  --page-bg: #eef2f6;
  --radius: 12px;

  height: 100vh;
  background: var(--page-bg);
  font-family: "Plus Jakarta Sans", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}

.layout-aside {
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #fbfcfe 0%, var(--aside-bg) 100%);
  border-right: 1px solid var(--aside-border);
  overflow: hidden;
  transition: width 0.2s ease;
}

.layout-aside.is-collapsed .brand {
  justify-content: center;
  padding: 0 8px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 64px;
  padding: 0 14px;
  border-bottom: 1px solid var(--aside-border);
  flex-shrink: 0;
}

.brand-logo {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  object-fit: contain;
  flex-shrink: 0;
  background: #fff;
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
  text-align: left;
}

.brand-text strong {
  color: var(--text);
  font-size: 15px;
  font-weight: 700;
}

.brand-text strong em {
  margin-left: 4px;
  font-style: normal;
  font-size: 13px;
  font-weight: 600;
  color: var(--brand);
}

.brand-text span {
  color: var(--text-muted);
  font-size: 12px;
}

.side-menu {
  flex: 1;
  border-right: none !important;
  background: transparent !important;
  padding: 10px 8px 12px;
  overflow-y: auto;
  overflow-x: hidden;
}

.side-menu.el-menu--collapse {
  width: 100%;
}

.layout-aside.is-collapsed .side-menu {
  padding: 8px 0 12px;
}

.layout-aside.is-collapsed .side-menu >>> .el-menu-item,
.layout-aside.is-collapsed .side-menu >>> .el-submenu__title {
  padding: 0 20px !important;
  margin: 2px 4px;
}

.aside-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 44px;
  margin: 0 8px 10px;
  border: 1px solid var(--aside-border);
  border-radius: 10px;
  background: #fff;
  color: var(--text-muted);
  font-size: 13px;
  cursor: pointer;
  flex-shrink: 0;
}

.layout-aside.is-collapsed .aside-toggle {
  margin: 0 8px 10px;
  padding: 0;
}

.aside-toggle:hover {
  color: var(--brand);
  border-color: #99f6e4;
  background: var(--active-bg);
}

.side-menu >>> .el-menu-item,
.side-menu >>> .el-submenu__title {
  height: 44px;
  line-height: 44px;
  margin: 2px 0;
  border-radius: 10px;
  color: var(--text) !important;
  font-size: 14px;
  font-weight: 500;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.side-menu >>> .el-menu-item i,
.side-menu >>> .el-submenu__title i {
  color: var(--text-muted);
  margin-right: 8px;
  width: 18px;
  text-align: center;
}

.side-menu >>> .el-menu-item:hover,
.side-menu >>> .el-submenu__title:hover {
  background: var(--hover) !important;
  color: var(--text) !important;
}

.side-menu >>> .el-menu-item.is-active {
  background: var(--active-bg) !important;
  color: var(--brand) !important;
  font-weight: 600;
  box-shadow: inset 3px 0 0 var(--brand);
}

.side-menu >>> .el-menu-item.is-active i {
  color: var(--brand);
}

.side-menu >>> .el-submenu .el-menu-item {
  min-width: auto;
  height: 40px;
  line-height: 40px;
  padding-left: 40px !important;
  color: var(--text-muted) !important;
  font-weight: 400;
}

.side-menu >>> .el-submenu .el-menu-item.is-active {
  color: var(--brand) !important;
  background: var(--active-bg) !important;
}

.side-menu >>> .el-submenu.is-opened > .el-submenu__title {
  color: var(--text) !important;
}

.side-menu >>> .el-submenu__icon-arrow {
  color: #9ca3af;
}

.layout-right {
  min-width: 0;
}

.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.86);
  border-bottom: 1px solid var(--aside-border);
  backdrop-filter: blur(8px);
  padding: 0 28px;
}

.header-title {
  color: var(--text);
  font-size: 18px;
  font-weight: 650;
  letter-spacing: -0.01em;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.username {
  color: var(--text-muted);
  font-size: 14px;
}

.logout-btn {
  color: var(--brand);
  font-weight: 600;
  padding: 0;
}

.layout-main {
  padding: 20px 24px 24px;
  overflow-y: auto;
  background:
    radial-gradient(circle at top right, rgba(20, 184, 166, 0.08), transparent 28%),
    var(--page-bg);
}

.main-panel {
  min-height: calc(100vh - 124px);
  background: var(--surface);
  border: 1px solid #e8edf3;
  border-radius: var(--radius);
  padding: 24px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.layout-main.is-chat {
  overflow: hidden;
  height: calc(100vh - 60px);
}

.main-panel.is-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
  overflow: hidden;
}

.main-panel.is-chat >>> .chat-page {
  flex: 1;
  min-height: 0;
}

.main-panel >>> .page {
  background: transparent;
  padding: 0;
  border-radius: 0;
}

.main-panel >>> .page h2 {
  margin: 0 0 8px;
  color: var(--text);
  font-size: 20px;
  font-weight: 650;
}

.main-panel >>> .page p {
  margin: 0;
  color: var(--text-muted);
  font-size: 14px;
}
</style>
