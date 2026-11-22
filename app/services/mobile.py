"""
手机号的应用层加密与检索用 HMAC。

约定（统一技术约定）：
  - 密钥**只从环境变量读取**：`LEAD_MOBILE_HASH_KEY`（HMAC-SHA256）、`LEAD_MOBILE_ENC_KEY`（AES-GCM）；
  - `contact_mobile_enc` 存密文（base64(nonce ‖ ciphertext)），应用层加解密；
  - `contact_mobile_hash` 存 HMAC-SHA256 十六进制摘要，用于等值检索（不可逆）。
"""

import base64
import hashlib
import hmac
import inspect
import os

HASH_KEY_ENV = "LEAD_MOBILE_HASH_KEY"
ENC_KEY_ENV = "LEAD_MOBILE_ENC_KEY"


def _key(env_name: str) -> bytes:
    value = os.environ.get(env_name)
    if not value:
        raise RuntimeError(f"缺少环境变量 {env_name}（密钥只从环境变量读取）")
    return value.encode("utf-8")


def hash_mobile(mobile: str, key: bytes | None = None) -> str:
    """HMAC-SHA256 十六进制摘要（等值检索用）。"""
    k = key if key is not None else _key(HASH_KEY_ENV)
    return hmac.new(k, (mobile or "").encode("utf-8"), hashlib.sha256).hexdigest()


def _aesgcm_new_api(cipher) -> bool:
    """cryptography 新版把 nonce 提到 encrypt/decrypt 的显式参数里（老版不是）。"""
    try:
        return len(inspect.signature(cipher.encrypt).parameters) >= 3
    except (TypeError, ValueError):
        return False


def encrypt_mobile(mobile: str, key: bytes | None = None) -> str:
    """AES-GCM 加密，返回 base64(nonce ‖ ciphertext)。"""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    k = key if key is not None else _key(ENC_KEY_ENV)
    nonce = os.urandom(12)
    cipher = AESGCM(k)
    data = (mobile or "").encode("utf-8")
    if _aesgcm_new_api(cipher):
        # 新签名：encrypt(nonce, data, aad) **只返回密文** ⇒ nonce 要自己拼在前面
        blob = nonce + cipher.encrypt(nonce, data, b"")
    else:
        blob = nonce + cipher.encrypt(data, None)
    return base64.b64encode(blob).decode("ascii")


def decrypt_mobile(blob_b64: str, key: bytes | None = None) -> str:
    """解密 `encrypt_mobile` 的输出。"""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    k = key if key is not None else _key(ENC_KEY_ENV)
    raw = base64.b64decode(blob_b64)
    nonce, blob = raw[:12], raw[12:]
    cipher = AESGCM(k)
    if _aesgcm_new_api(cipher):
        return cipher.decrypt(nonce, blob, b"").decode("utf-8")
    return cipher.decrypt(blob, None).decode("utf-8")
