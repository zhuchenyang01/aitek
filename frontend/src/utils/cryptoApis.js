/**
 * 需要 AES 加解密的接口路径白名单
 * 后续新增加密接口：把路径追加到这个数组即可（需与后端 CRYPTO_API_PATHS 保持一致）
 *
 * 示例：
 *   '/api/system/login/',
 *   '/api/system/register/',
 *   '/api/project-config/',   // 若整条路径前缀都要加密，也可写前缀并在匹配时用 startsWith
 */
export const CRYPTO_API_PATHS = [
  '/api/system/login/',
  '/api/system/register/'
]

/**
 * 判断某个请求 URL 是否需要加解密
 * @param {string} url axios config.url，如 '/api/system/login/'
 */
export function needCrypto(url = '') {
  const path = url.split('?')[0]
  return CRYPTO_API_PATHS.some(item => path === item || path.startsWith(item))
}
