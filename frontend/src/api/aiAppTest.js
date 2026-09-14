import request from './request'

export function getAiAppTestHealth() {
  return request({ url: '/api/ai-app-test/health/', method: 'get' })
}
