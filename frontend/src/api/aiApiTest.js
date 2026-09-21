import request from './request'

export function getAiApiTestHealth() {
  return request({ url: '/api/ai-api-test/health/', method: 'get' })
}

export function listApiInterfaces(params = {}) {
  return request({
    url: '/api/ai-api-test/interfaces/',
    method: 'get',
    params
  })
}

export function createApiInterface(data) {
  return request({
    url: '/api/ai-api-test/interfaces/',
    method: 'post',
    data
  })
}

export function getApiInterface(id) {
  return request({
    url: `/api/ai-api-test/interfaces/${id}/`,
    method: 'get'
  })
}

export function updateApiInterface(id, data) {
  return request({
    url: `/api/ai-api-test/interfaces/${id}/`,
    method: 'put',
    data
  })
}

export function deleteApiInterface(id) {
  return request({
    url: `/api/ai-api-test/interfaces/${id}/`,
    method: 'delete'
  })
}

export function importApiDocument(formData) {
  return request({
    url: '/api/ai-api-test/interfaces/import/',
    method: 'post',
    data: formData,
    timeout: 300000
  })
}

export function listApiDatasets(params = {}) {
  return request({
    url: '/api/ai-api-test/datasets/',
    method: 'get',
    params
  })
}

export function createApiDataset(data) {
  return request({
    url: '/api/ai-api-test/datasets/',
    method: 'post',
    data
  })
}

export function updateApiDataset(id, data) {
  return request({
    url: `/api/ai-api-test/datasets/${id}/`,
    method: 'put',
    data
  })
}

export function deleteApiDataset(id) {
  return request({
    url: `/api/ai-api-test/datasets/${id}/`,
    method: 'delete'
  })
}

export function generateApiCases(interfaceId) {
  return request({
    url: `/api/ai-api-test/interfaces/${interfaceId}/generate-cases/`,
    method: 'post',
    timeout: 300000
  })
}

function parseSseChunk(chunk, onEvent) {
  const dataLines = chunk
    .split('\n')
    .filter(line => line.startsWith('data:'))
    .map(line => line.slice(5).trim())
  if (!dataLines.length) return
  try {
    onEvent(JSON.parse(dataLines.join('\n')))
  } catch (e) {
    onEvent({ response_type: 'raw', content: dataLines.join('\n'), done: false })
  }
}

export function generateApiCasesStream(interfaceId, onEvent) {
  const controller = new AbortController()
  const token = localStorage.getItem('token')
  const baseURL = request.defaults.baseURL || ''
  const promise = fetch(
    `${baseURL}/api/ai-api-test/interfaces/${interfaceId}/generate-cases/stream/`,
    {
      method: 'POST',
      headers: {
        Authorization: token ? `Bearer ${token}` : '',
        'Content-Type': 'application/json'
      },
      body: '{}',
      signal: controller.signal
    }
  ).then(async (res) => {
    if (!res.ok) {
      let payload = null
      try {
        payload = await res.json()
      } catch (e) {
        payload = { msg: `请求失败（HTTP ${res.status}）` }
      }
      throw payload
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    let finished = false
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const chunks = buffer.split('\n\n')
      buffer = chunks.pop() || ''
      chunks.forEach(chunk => {
        parseSseChunk(chunk, event => {
          onEvent(event)
          if (event.response_type === 'error' || event.response_type === 'saved') {
            finished = true
          }
        })
      })
    }
    if (buffer.trim()) {
      parseSseChunk(buffer, event => {
        onEvent(event)
        if (event.response_type === 'error' || event.response_type === 'saved') {
          finished = true
        }
      })
    }
    if (!finished) {
      throw { msg: '生成流程中断，请稍后重试' }
    }
  })
  return { promise, abort: () => controller.abort() }
}

export function listApiCases(params = {}) {
  return request({
    url: '/api/ai-api-test/cases/',
    method: 'get',
    params
  })
}

export function createApiCase(data) {
  return request({
    url: '/api/ai-api-test/cases/',
    method: 'post',
    data
  })
}

export function updateApiCase(id, data) {
  return request({
    url: `/api/ai-api-test/cases/${id}/`,
    method: 'put',
    data
  })
}

export function deleteApiCase(id) {
  return request({
    url: `/api/ai-api-test/cases/${id}/`,
    method: 'delete'
  })
}

export function runApiCase(id) {
  return request({
    url: `/api/ai-api-test/cases/${id}/run/`,
    method: 'post',
    timeout: 60000
  })
}

export function listApiCaseLogs(id, params = {}) {
  return request({
    url: `/api/ai-api-test/cases/${id}/logs/`,
    method: 'get',
    params
  })
}

export function listApiSuites(params = {}) {
  return request({
    url: '/api/ai-api-test/suites/',
    method: 'get',
    params
  })
}

export function createApiSuite(data) {
  return request({
    url: '/api/ai-api-test/suites/',
    method: 'post',
    data
  })
}

export function updateApiSuite(id, data) {
  return request({
    url: `/api/ai-api-test/suites/${id}/`,
    method: 'put',
    data
  })
}

export function deleteApiSuite(id) {
  return request({
    url: `/api/ai-api-test/suites/${id}/`,
    method: 'delete'
  })
}

export function runApiSuite(id) {
  return request({
    url: `/api/ai-api-test/suites/${id}/run/`,
    method: 'post',
    timeout: 180000
  })
}

export function listApiRuns(params = {}) {
  return request({
    url: '/api/ai-api-test/runs/',
    method: 'get',
    params
  })
}

export function getApiRun(id) {
  return request({
    url: `/api/ai-api-test/runs/${id}/`,
    method: 'get'
  })
}
