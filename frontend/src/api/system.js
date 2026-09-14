import request from './request'

export function login(data) {
  return request({ url: '/api/system/login/', method: 'post', data })
}

export function register(data) {
  return request({ url: '/api/system/register/', method: 'post', data })
}

export function logout() {
  return request({ url: '/api/system/logout/', method: 'post' })
}
