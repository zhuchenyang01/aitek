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
        path: 'api-test/project-link',
        name: 'ApiTestProjectLink',
        meta: { requiresAuth: true },
        component: () => import(/* webpackChunkName: "api-test" */ '../views/api-test/ProjectLink.vue')
      },
      {
        path: 'api-test/docs',
        name: 'ApiTestDocs',
        meta: { requiresAuth: true },
        component: () => import(/* webpackChunkName: "api-test" */ '../views/api-test/DocManage.vue')
      },
      {
        path: 'api-test/test',
        name: 'ApiTest',
        meta: { requiresAuth: true },
        component: () => import(/* webpackChunkName: "api-test" */ '../views/ai-api-test/Index.vue')
      },
      {
        path: 'web-auto',
        name: 'WebAuto',
        meta: { requiresAuth: true },
        component: () => import(/* webpackChunkName: "web-auto" */ '../views/ai-web-test/Index.vue')
      },
      {
        path: 'app-auto',
        name: 'AppAuto',
        meta: { requiresAuth: true },
        component: () => import(/* webpackChunkName: "app-auto" */ '../views/ai-app-test/Index.vue')
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
