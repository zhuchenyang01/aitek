import request from './request'

export function getAiWebTestHealth() {
  return request({ url: '/api/ai-web-test/health/', method: 'get' })
}
