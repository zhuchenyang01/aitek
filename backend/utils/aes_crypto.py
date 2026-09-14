import base64
import json
import os

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from django.conf import settings


BLOCK_SIZE = 16


def _get_key() -> bytes:
    secret = getattr(settings, 'AES_SECRET_KEY', 'aitek-dev-aes-key16')
    key = secret.encode('utf-8')
    if len(key) >= 16:
        return key[:16]
    return key.ljust(16, b'0')


def encrypt_text(plain_text: str) -> str:
    """AES-CBC 加密，返回 Base64(IV + CipherText)"""
    iv = os.urandom(BLOCK_SIZE)
    cipher = AES.new(_get_key(), AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(plain_text.encode('utf-8'), BLOCK_SIZE))
    return base64.b64encode(iv + encrypted).decode('utf-8')


def decrypt_text(cipher_text: str) -> str:
    """解密 Base64(IV + CipherText)"""
    raw = base64.b64decode(cipher_text)
    iv = raw[:BLOCK_SIZE]
    encrypted = raw[BLOCK_SIZE:]
    cipher = AES.new(_get_key(), AES.MODE_CBC, iv)
    decrypted = unpad(cipher.decrypt(encrypted), BLOCK_SIZE)
    return decrypted.decode('utf-8')


def encrypt_obj(data) -> str:
    return encrypt_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')))


def decrypt_obj(cipher_text: str):
    return json.loads(decrypt_text(cipher_text))
