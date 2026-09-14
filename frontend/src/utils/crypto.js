import CryptoJS from 'crypto-js'

// 开发环境共享密钥，需与后端 AES_SECRET_KEY 保持一致（生产请改为环境变量）
const AES_SECRET_KEY = 'aitek-dev-aes-key16'

function getKey() {
  const key = CryptoJS.enc.Utf8.parse(AES_SECRET_KEY.slice(0, 16).padEnd(16, '0'))
  return key
}

/**
 * AES-CBC 加密，返回 Base64(IV + CipherText)
 */
export function encryptText(plainText) {
  const key = getKey()
  const iv = CryptoJS.lib.WordArray.random(16)
  const encrypted = CryptoJS.AES.encrypt(plainText, key, {
    iv,
    mode: CryptoJS.mode.CBC,
    padding: CryptoJS.pad.Pkcs7
  })
  const combined = iv.concat(encrypted.ciphertext)
  return CryptoJS.enc.Base64.stringify(combined)
}

/**
 * 解密 Base64(IV + CipherText)
 */
export function decryptText(cipherText) {
  const key = getKey()
  const raw = CryptoJS.enc.Base64.parse(cipherText)
  const iv = CryptoJS.lib.WordArray.create(raw.words.slice(0, 4), 16)
  const ciphertext = CryptoJS.lib.WordArray.create(
    raw.words.slice(4),
    raw.sigBytes - 16
  )
  const decrypted = CryptoJS.AES.decrypt({ ciphertext }, key, {
    iv,
    mode: CryptoJS.mode.CBC,
    padding: CryptoJS.pad.Pkcs7
  })
  return decrypted.toString(CryptoJS.enc.Utf8)
}

export function encryptObj(data) {
  return encryptText(JSON.stringify(data))
}

export function decryptObj(cipherText) {
  const text = decryptText(cipherText)
  return JSON.parse(text)
}
