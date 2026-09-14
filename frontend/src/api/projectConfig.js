import request from './request'

export function listConfigs() {
  return request({ url: '/api/project-config/', method: 'get' })
}

export function createConfig(data) {
  return request({ url: '/api/project-config/', method: 'post', data })
}

export function updateConfig(id, data) {
  return request({ url: `/api/project-config/${id}/`, method: 'put', data })
}

export function deleteConfig(id) {
  return request({ url: `/api/project-config/${id}/`, method: 'delete' })
}
