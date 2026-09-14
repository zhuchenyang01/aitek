import request from './request'

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

function readSseStream(response, onEvent) {
  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  let sawTerminal = false
  return (async () => {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const chunks = buffer.split('\n\n')
      buffer = chunks.pop() || ''
      for (const chunk of chunks) {
        parseSseChunk(chunk, event => {
          onEvent(event)
          const type = event.response_type
          if (type === 'error' || type === 'saved' || (type === 'answer' && event.done)) {
            sawTerminal = true
          }
        })
      }
    }
    if (buffer.trim()) {
      parseSseChunk(buffer, event => {
        onEvent(event)
        const type = event.response_type
        if (type === 'error' || type === 'saved' || (type === 'answer' && event.done)) {
          sawTerminal = true
        }
      })
    }
    if (!sawTerminal) {
      throw { msg: '生成流程中断，服务端未返回完成信号，请稍后重试' }
    }
  })()
}

export function listFunctionalProjects() {
  return request({ url: '/api/functional-test/projects/', method: 'get' })
}

export function createFunctionalProject(data) {
  return request({ url: '/api/functional-test/projects/', method: 'post', data })
}

export function updateFunctionalProject(id, data) {
  return request({ url: `/api/functional-test/projects/${id}/`, method: 'put', data })
}

export function listProjectRequirements(projectId) {
  return request({ url: `/api/functional-test/projects/${projectId}/requirements/`, method: 'get' })
}

export function uploadProjectRequirement(projectId, { file, title }) {
  const form = new FormData()
  form.append('file', file)
  if (title) {
    form.append('title', title)
  }
  return request({
    url: `/api/functional-test/projects/${projectId}/requirements/`,
    method: 'post',
    data: form,
    timeout: 120000
  })
}

export function deleteProjectRequirement(projectId, docId) {
  return request({
    url: `/api/functional-test/projects/${projectId}/requirements/${docId}/`,
    method: 'delete'
  })
}

export function updateProjectRequirement(projectId, docId, data) {
  return request({
    url: `/api/functional-test/projects/${projectId}/requirements/${docId}/`,
    method: 'put',
    data
  })
}

export function generateProjectRequirement(projectId, docId, data = {}) {
  return request({
    url: `/api/functional-test/projects/${projectId}/requirements/${docId}/generate/`,
    method: 'post',
    data,
    timeout: 180000
  })
}

export function generateProjectRequirementStream(projectId, docId, data = {}, onEvent) {
  const controller = new AbortController()
  const token = localStorage.getItem('token')
  const baseURL = request.defaults.baseURL || ''

  const promise = fetch(
    `${baseURL}/api/functional-test/projects/${projectId}/requirements/${docId}/generate/`,
    {
      method: 'POST',
      headers: {
        Authorization: token ? `Bearer ${token}` : '',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ ...data, stream: true }),
      signal: controller.signal
    }
  ).then(async res => {
    if (!res.ok) {
      let payload = null
      try {
        payload = await res.json()
      } catch (e) {
        payload = { msg: `请求失败（HTTP ${res.status}）` }
      }
      throw payload
    }
    await readSseStream(res, onEvent)
  })

  return { promise, abort: () => controller.abort() }
}

export function listFunctionalTestCases(params = {}) {
  return request({
    url: '/api/functional-test/testcases/',
    method: 'get',
    params,
    timeout: 60000
  })
}

export function getFunctionalTestCase(id) {
  return request({
    url: `/api/functional-test/testcases/${id}/`,
    method: 'get',
    timeout: 30000
  })
}

export function exportFunctionalTestCases(params = {}) {
  return request({
    url: '/api/functional-test/testcases/export/',
    method: 'get',
    params,
    responseType: 'blob',
    timeout: 120000
  })
}

export function deleteFunctionalTestCase(id) {
  return request({
    url: `/api/functional-test/testcases/${id}/`,
    method: 'delete'
  })
}

export function batchDeleteFunctionalTestCases(ids) {
  return request({
    url: '/api/functional-test/testcases/batch-delete/',
    method: 'post',
    data: { ids }
  })
}
