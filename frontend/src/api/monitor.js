import request from './request'

export function listMonitorServers() {
  return request({ url: '/api/monitor/servers/', method: 'get' })
}

export function createMonitorServer(data) {
  return request({ url: '/api/monitor/servers/', method: 'post', data })
}

export function updateMonitorServer(id, data) {
  return request({ url: `/api/monitor/servers/${id}/`, method: 'put', data })
}

export function deleteMonitorServer(id) {
  return request({ url: `/api/monitor/servers/${id}/`, method: 'delete' })
}

export function testMonitorServer(id) {
  return request({
    url: `/api/monitor/servers/${id}/test/`,
    method: 'post',
    timeout: 30000
  })
}

export function collectMonitorServer(id) {
  return request({
    url: `/api/monitor/servers/${id}/collect/`,
    method: 'post',
    timeout: 30000
  })
}

export function getMonitorMetrics(id, params = {}) {
  return request({
    url: `/api/monitor/servers/${id}/metrics/`,
    method: 'get',
    params
  })
}

export function getMonitorLatest(id) {
  return request({
    url: `/api/monitor/servers/${id}/latest/`,
    method: 'get'
  })
}
