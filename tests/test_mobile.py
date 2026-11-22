"""手机号应用层加密与 HMAC 检索（密钥只从环境变量读取）。"""
import os

import pytest

from app.services.mobile import decrypt_mobile, encrypt_mobile, hash_mobile


def test_hash_is_stable_and_key_dependent():
    os.environ["LEAD_MOBILE_HASH_KEY"] = "k1"
    a = hash_mobile("13800001111")
    b = hash_mobile("13800001111")
    assert a == b and len(a) == 64
    os.environ["LEAD_MOBILE_HASH_KEY"] = "k2"
    assert hash_mobile("13800001111") != a


def test_encrypt_roundtrip_and_randomness():
    os.environ["LEAD_MOBILE_ENC_KEY"] = "0" * 32
    blob = encrypt_mobile("13800001111")
    assert blob != "13800001111"
    assert decrypt_mobile(blob) == "13800001111"
    assert encrypt_mobile("13800001111") != blob     # 每次 nonce 不同


def test_missing_env_key_raises():
    old = os.environ.pop("LEAD_MOBILE_HASH_KEY", None)
    try:
        with pytest.raises(RuntimeError):
            hash_mobile("13800001111")
    finally:
        if old is not None:
            os.environ["LEAD_MOBILE_HASH_KEY"] = old
