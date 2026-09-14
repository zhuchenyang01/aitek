import request from './request'

export function getCiHealth() {
  return request({ url: '/api/ci/health/', method: 'get' })
}
