import request from './request'

export function listLlmConfigs(params) {
  return request({ url: '/api/system/llm-configs/', method: 'get', params })
}

export function createLlmConfig(data) {
  return request({ url: '/api/system/llm-configs/', method: 'post', data })
}

export function updateLlmConfig(id, data) {
  return request({ url: `/api/system/llm-configs/${id}/`, method: 'patch', data })
}

export function deleteLlmConfig(id) {
  return request({ url: `/api/system/llm-configs/${id}/`, method: 'delete' })
}

export function setDefaultLlmConfig(id) {
  return request({ url: `/api/system/llm-configs/${id}/default/`, method: 'post' })
}

export function testLlmConfig(data) {
  return request({ url: '/api/system/llm-configs/test/', method: 'post', data, timeout: 60000 })
}

export function listOllamaModels(params) {
  return request({ url: '/api/system/ollama/models/', method: 'get', params, timeout: 15000 })
}

export const MODEL_TYPES = [
  { value: 'chat', label: '对话', icon: 'el-icon-chat-dot-round' },
  { value: 'embedding', label: 'Embedding', icon: 'el-icon-connection' },
  { value: 'rerank', label: 'ReRank', icon: 'el-icon-sort' },
  { value: 'vision', label: '视觉', icon: 'el-icon-view' },
  { value: 'voice', label: '语音', icon: 'el-icon-microphone' }
]

export const MODEL_SOURCES = [
  { value: 'api', label: 'API', icon: 'el-icon-cloudy' },
  { value: 'ollama', label: 'Ollama', icon: 'el-icon-cpu' }
]

export const PROVIDER_OPTIONS = [
  { value: 'custom', label: '自定义（OpenAI 兼容接口）' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'qwen', label: '通义千问' },
  { value: 'moonshot', label: 'Moonshot' },
  { value: 'zhipu', label: '智谱 GLM' },
  { value: 'ollama', label: 'Ollama' }
]

export const TYPE_DEFAULTS = {
  chat: { provider: 'deepseek', model: 'deepseek-chat', base_url: 'https://api.deepseek.com/v1' },
  embedding: { provider: 'ollama', model: 'bge-m3:latest', base_url: 'http://127.0.0.1:11434/v1', source: 'ollama' },
  rerank: { provider: 'custom', model: 'rerank', base_url: '' },
  vision: { provider: 'openai', model: 'gpt-4o', base_url: 'https://api.openai.com/v1' },
  voice: { provider: 'openai', model: 'whisper-1', base_url: 'https://api.openai.com/v1' }
}
