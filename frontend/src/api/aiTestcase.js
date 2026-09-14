import request from './request'

const ASK_TIMEOUT = 180000

export function getAiTestcaseHealth() {
  return request({ url: '/api/ai-testcase/health/', method: 'get' })
}

export function listAiTestcaseSessions() {
  return request({ url: '/api/ai-testcase/sessions/', method: 'get' })
}

export function createAiTestcaseSession(data) {
  return request({ url: '/api/ai-testcase/sessions/', method: 'post', data })
}

export function getAiTestcaseSession(id) {
  return request({ url: `/api/ai-testcase/sessions/${id}/`, method: 'get' })
}

export function listAiTestcaseMessages(sessionId) {
  return request({ url: `/api/ai-testcase/sessions/${sessionId}/messages/`, method: 'get' })
}

export function listAiTestcaseKnowledgeBases(params) {
  return request({ url: '/api/ai-testcase/knowledge-bases/', method: 'get', params })
}

export function createAiTestcaseKnowledgeBase(data) {
  return request({ url: '/api/ai-testcase/knowledge-bases/', method: 'post', data })
}

export function getAiTestcaseKnowledgeBase(kbId) {
  return request({ url: `/api/ai-testcase/knowledge-bases/${kbId}/`, method: 'get' })
}

export function addAiTestcaseKnowledgeDocument(kbId, { file, title }) {
  const form = new FormData()
  form.append('file', file)
  if (title) {
    form.append('title', title)
  }
  return request({
    url: `/api/ai-testcase/knowledge-bases/${kbId}/documents/`,
    method: 'post',
    data: form,
    timeout: ASK_TIMEOUT
  })
}

export function listAiTestcaseDocuments(kbId) {
  return request({ url: `/api/ai-testcase/knowledge-bases/${kbId}/documents/`, method: 'get' })
}

export function getAiTestcaseDocument(kbId, docId) {
  return request({ url: `/api/ai-testcase/knowledge-bases/${kbId}/documents/${docId}/`, method: 'get' })
}

export function deleteAiTestcaseDocument(kbId, docId) {
  return request({ url: `/api/ai-testcase/knowledge-bases/${kbId}/documents/${docId}/`, method: 'delete' })
}

export function listAiTestcaseChunks(kbId) {
  return request({ url: `/api/ai-testcase/knowledge-bases/${kbId}/chunks/`, method: 'get' })
}

export function downloadEvalTemplate() {
  return request({
    url: '/api/ai-testcase/eval/template.xlsx',
    method: 'get',
    responseType: 'blob'
  })
}

export function parseEvalExcel(file) {
  const form = new FormData()
  form.append('file', file)
  return request({
    url: '/api/ai-testcase/eval/parse/',
    method: 'post',
    data: form
  })
}

export function runRetrievalEval(data) {
  return request({
    url: '/api/ai-testcase/eval/run/',
    method: 'post',
    data,
    timeout: ASK_TIMEOUT
  })
}

export function listAiTestcaseQA(params) {
  return request({ url: '/api/ai-testcase/qa/', method: 'get', params })
}

export function createAiTestcaseQA(data) {
  return request({
    url: '/api/ai-testcase/qa/',
    method: 'post',
    data
  })
}

export function getAiTestcaseQA(id) {
  return request({ url: `/api/ai-testcase/qa/${id}/`, method: 'get' })
}

/** 非流式提问，一次返回完整测试用例 */
export function askAiTestcase(qaId, data) {
  return request({
    url: `/api/ai-testcase/qa/${qaId}/ask/`,
    method: 'post',
    data: { ...data, stream: false },
    timeout: ASK_TIMEOUT
  })
}

/**
 * 流式提问。onEvent(event) 收到 SSE 解析后的 JSON。
 * 返回 { abort } 用于中止。
 */
export function askAiTestcaseStream(qaId, data, onEvent) {
  const controller = new AbortController()
  const token = localStorage.getItem('token')
  const baseURL = request.defaults.baseURL || ''

  const promise = fetch(`${baseURL}/api/ai-testcase/qa/${qaId}/ask/`, {
    method: 'POST',
    headers: {
      Authorization: token ? `Bearer ${token}` : '',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ ...data, stream: true }),
    signal: controller.signal
  }).then(async res => {
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
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const chunks = buffer.split('\n\n')
      buffer = chunks.pop() || ''
      for (const chunk of chunks) {
        const dataLines = chunk
          .split('\n')
          .filter(line => line.startsWith('data:'))
          .map(line => line.slice(5).trim())
        if (!dataLines.length) continue
        try {
          onEvent(JSON.parse(dataLines.join('\n')))
        } catch (e) {
          onEvent({ response_type: 'raw', content: dataLines.join('\n'), done: false })
        }
      }
    }
  })

  return { promise, abort: () => controller.abort() }
}
