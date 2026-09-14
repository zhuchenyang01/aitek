import request from './request'

export function getAiApiTestHealth() {
  return request({ url: '/api/ai-api-test/health/', method: 'get' })
}
