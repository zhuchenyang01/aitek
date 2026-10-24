import Vue from 'vue'
import VueRouter from 'vue-router'
import Layout from '../layout/Layout.vue'
import store from '../store'

Vue.use(VueRouter)

const routes = [
  {
    path: '/',
    component: Layout,
    redirect: '/functional/projects',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'functional/projects',
        name: 'FunctionalProjects',
        meta: { requiresAuth: true },
        component: () => import(/* webpackChunkName: "functional" */ '../views/functional/Project.vue')
      },
      {
        path: 'functional/testcases',
        name: 'FunctionalTestcases',
        meta: { requiresAuth: true },
        component: () => import(/* webpackChunkName: "functional" */ '../views/functional/TestCase.vue')
      },
      {
        path: 'functional/requirements',
        name: 'FunctionalRequirements',
        meta: { requiresAuth: true },
        component: () => import(/* webpackChunkName: "functional" */ '../views/functional/Requirement.vue')
      },
      {
        path: 'api-test/apis',
        name: 'ApiManage',
        meta: { requiresAuth: true },
        component: () => import(/* webpackChunkName: "api-test" */ '../views/api-test/ApiManage.vue')
      },
      {
        path: 'api-test/cases',
        name: 'ApiCase',
        meta: { requiresAuth: true },
        component: () => import(/* webpackChunkName: "api-test" */ '../views/api-test/ApiCase.vue')
      },
      {
        path: 'api-test/data',
        name: 'ApiData',
        meta: { requiresAuth: true },
        component: () => import(/* webpackChunkName: "api-test" */ '../views/api-test/ApiData.vue')
      },
      {
        path: 'api-test/runs',
        name: 'ApiRun',
        meta: { requiresAuth: true },
        component: () => import(/* webpackChunkName: "api-test" */ '../views/api-test/ApiRun.vue')
      },
      {
        path: 'api-test/reports',
        name: 'ApiReport',
        meta: { requiresAuth: true },
        component: () => import(/* webpackChunkName: "api-test" */ '../views/api-test/ApiReport.vue')
      },
      {
        path: 'agent-test/projects',
        name: 'AgentTestProjects',
        meta: { requiresAuth: true },
        component: () => import(/* webpackChunkName: "agent-test" */ '../views/agent-test/Project.vue')
      },
      {
        path: 'agent-test/cases',
        name: 'AgentTestCases',
        meta: { requiresAuth: true },
        component: () => import(/* webpackChunkName: "agent-test" */ '../views/agent-test/Case.vue')
      },
      {
        path: 'agent-test/reports',
        name: 'AgentTestReports',
        meta: { requiresAuth: true },
        component: () => import(/* webpackChunkName: "agent-test" */ '../views/agent-test/Report.vue')
      },
      {
        path: 'agent-test/security-reports',
        name: 'AgentTestSecurityReports',
        meta: { requiresAuth: true },
        component: () => import(/* webpackChunkName: "agent-test" */ '../views/agent-test/SecurityReport.vue')
      },
      {
        path: 'api-test/project-link',
        redirect: '/api-test/apis'
      },
      {
        path: 'api-test/docs',
        redirect: '/api-test/apis'
      },
      {
        path: 'api-test/test',
        redirect: '/api-test/cases'
      },
      // Web / APP 自动化暂无实际内容，路由先下线（直链也回到首页）
      {
        path: 'web-auto',
        redirect: '/'
      },
      {
        path: 'app-auto',
        redirect: '/'
      },
      {
        path: 'project-config',
        name: 'ProjectConfig',
        meta: { requiresAuth: true },
        component: () => import(/* webpackChunkName: "project-config" */ '../views/project-config/Index.vue')
      },
      {
        path: 'llm-config',
        name: 'LlmConfig',
        meta: { requiresAuth: true },
        component: () => import(/* webpackChunkName: "llm-config" */ '../views/llm-config/Index.vue')
      },
      {
        path: 'knowledge-base',
        redirect: '/functional/projects'
      },
      {
        path: 'ai-testcase',
        redirect: '/functional/requirements'
      },
      // 聊天式 AI 生成测试用例页暂时下线，后续从功能测试-需求管理触发生成
      // {
      //   path: 'ai-testcase',
      //   name: 'AiTestcase',
      //   meta: { requiresAuth: true },
      //   component: () => import(/* webpackChunkName: "ai-testcase" */ '../views/ai-testcase/Index.vue')
      // },
      {
        path: 'retrieval-eval',
        name: 'RetrievalEval',
        meta: { requiresAuth: true },
        component: () => import(/* webpackChunkName: "retrieval-eval" */ '../views/retrieval-eval/Index.vue')
      }
    ]
  },
  {
    path: '/login',
    name: 'Login',
    meta: { guest: true },
    component: () => import(/* webpackChunkName: "system" */ '../views/system/Login.vue')
  }
]

const router = new VueRouter({
  mode: 'history',
  base: process.env.BASE_URL,
  routes
})

router.beforeEach((to, from, next) => {
  const token = store.state.system.token || localStorage.getItem('token')
  const needAuth = to.matched.some(record => record.meta.requiresAuth)
  const isGuest = to.matched.some(record => record.meta.guest)

  if (needAuth && !token) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }
  if (isGuest && token) {
    next('/functional/projects')
    return
  }
  next()
})

export default router
