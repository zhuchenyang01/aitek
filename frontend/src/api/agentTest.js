import request from './request'

export function listAgentProjects() {
  return request({ url: '/api/agent-test/projects/', method: 'get' })
}

export function createAgentProject(data) {
  return request({ url: '/api/agent-test/projects/', method: 'post', data })
}

export function getAgentProject(id) {
  return request({ url: `/api/agent-test/projects/${id}/`, method: 'get' })
}

export function understandAgentProject(id, data = {}) {
  return request({
    url: `/api/agent-test/projects/${id}/understand/`,
    method: 'post',
    data,
    timeout: 180000
  })
}

export function updateAgentProjectProfile(id, data) {
  return request({ url: `/api/agent-test/projects/${id}/profile/`, method: 'put', data })
}

export function generateAgentCases(id, data = {}) {
  return request({
    url: `/api/agent-test/projects/${id}/generate-cases/`,
    method: 'post',
    data,
    timeout: 180000
  })
}

export function listAgentCases(params = {}) {
  return request({ url: '/api/agent-test/cases/', method: 'get', params })
}

export function runAgentCase(id) {
  return request({ url: `/api/agent-test/cases/${id}/run/`, method: 'post', timeout: 180000 })
}

export function getAgentCaseLastRun(id) {
  return request({ url: `/api/agent-test/cases/${id}/last-run/`, method: 'get' })
}

export function listAgentReports(params = {}) {
  return request({ url: '/api/agent-test/reports/', method: 'get', params })
}

export function getAgentReport(id) {
  return request({ url: `/api/agent-test/reports/${id}/`, method: 'get' })
}
