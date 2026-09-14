import { login as loginApi, register as registerApi, logout as logoutApi } from '@/api/system'

const savedUser = (() => {
  try {
    return JSON.parse(localStorage.getItem('user') || 'null')
  } catch (e) {
    return null
  }
})()

export default {
  namespaced: true,
  state: {
    token: localStorage.getItem('token') || '',
    user: savedUser
  },
  mutations: {
    SET_TOKEN(state, token) {
      state.token = token || ''
      if (token) {
        localStorage.setItem('token', token)
      } else {
        localStorage.removeItem('token')
      }
    },
    SET_USER(state, user) {
      state.user = user
      if (user) {
        localStorage.setItem('user', JSON.stringify(user))
      } else {
        localStorage.removeItem('user')
      }
    }
  },
  actions: {
    async login({ commit }, form) {
      const res = await loginApi(form)
      const data = res.data || {}
      commit('SET_TOKEN', data.token)
      commit('SET_USER', { id: data.id, username: data.username })
      return res
    },
    async register(_, form) {
      return registerApi(form)
    },
    async logout({ commit, state }) {
      try {
        if (state.token) {
          await logoutApi()
        }
      } catch (e) {
        // 即使后端失败也清理本地登录态
      } finally {
        commit('SET_TOKEN', '')
        commit('SET_USER', null)
      }
    }
  }
}
