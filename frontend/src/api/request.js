import axios from 'axios'
import { Message } from 'element-ui'
import { encryptObj, decryptObj } from '@/utils/crypto'
import { needCrypto } from '@/utils/cryptoApis'

const service = axios.create({
  baseURL: process.env.VUE_APP_API_BASE || '',
  timeout: 10000
})

let redirectingToLogin = false

function clearAuthAndRedirect() {
  localStorage.removeItem('token')
  localStorage.removeItem('user')

  import('@/store').then(({ default: store }) => {
    store.commit('system/SET_TOKEN', '')
    store.commit('system/SET_USER', null)
  }).catch(() => {})

  if (redirectingToLogin) return
  redirectingToLogin = true
  Message.error('未登录或登录已失效，请重新登录')

  import('@/router').then(({ default: router }) => {
    if (router.currentRoute.path !== '/login') {
      router.replace({
        path: '/login',
        query: { redirect: router.currentRoute.fullPath }
      }).finally(() => {
        redirectingToLogin = false
      })
    } else {
      redirectingToLogin = false
    }
  }).catch(() => {
    redirectingToLogin = false
    window.location.href = '/login'
  })
}

function unwrapPayload(data) {
  if (data && typeof data === 'object' && typeof data.payload === 'string') {
    try {
      return decryptObj(data.payload)
    } catch (e) {
      return data
    }
  }
  return data
}

service.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
    if (config.headers) {
      delete config.headers['Content-Type']
    }
    return config
  }

  // 仅白名单接口加密请求体（见 src/utils/cryptoApis.js）
  if (needCrypto(config.url) && config.data !== undefined && config.data !== null) {
    const plain = typeof config.data === 'string' ? JSON.parse(config.data) : config.data
    config.data = { payload: encryptObj(plain) }
    config.headers['Content-Type'] = 'application/json'
  }
  return config
}, error => Promise.reject(error))

function extractErrorMsg(err) {
  let data = err.response && err.response.data
  data = unwrapPayload(data)
  if (!data) return err.message || '请求失败'
  if (typeof data.msg === 'string' && data.msg) return data.msg
  if (typeof data.detail === 'string' && data.detail) return data.detail
  if (typeof data === 'string') return data
  return '请求失败'
}

service.interceptors.response.use(res => {
  if (res.config && res.config.responseType === 'blob') {
    return res.data
  }
  // 有 payload 才解密；其它接口保持明文，方便抓包调试
  const payload = unwrapPayload(res.data)
  if (payload && typeof payload === 'object' && Object.prototype.hasOwnProperty.call(payload, 'code')) {
    if (payload.code === 401) {
      clearAuthAndRedirect()
      return Promise.reject(payload)
    }
    if (payload.code !== 0) {
      Message.error(payload.msg || '操作失败')
      return Promise.reject(payload)
    }
  }
  return payload
}, err => {
  const status = err.response && err.response.status
  if (err.response && err.response.data) {
    err.response.data = unwrapPayload(err.response.data)
  }
  if (status === 401) {
    clearAuthAndRedirect()
    return Promise.reject(err)
  }
  Message.error(extractErrorMsg(err))
  return Promise.reject(err)
})

export default service
