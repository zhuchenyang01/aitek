"""监控服务器密码加解密（复用平台 AES）。"""
from utils.aes_crypto import decrypt_text, encrypt_text


def encrypt_password(plain: str) -> str:
    if plain is None:
        return ''
    text = str(plain)
    if not text:
        return ''
    return encrypt_text(text)


def decrypt_password(cipher: str) -> str:
    if not cipher:
        return ''
    return decrypt_text(cipher)
