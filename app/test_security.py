from datetime import UTC, datetime, timedelta

import jwt

from app.config import settings
from app.security import (
    ALGORITHM,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_produces_a_verifiable_hash():
    hashed = hash_password("supersecret123")
    assert verify_password(plain_password="supersecret123", hashed_password=hashed)


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("supersecret123")
    assert not verify_password(plain_password="wrongpassword", hashed_password=hashed)


def test_hash_password_salts_so_the_same_password_hashes_differently():
    assert hash_password("supersecret123") != hash_password("supersecret123")


def test_create_access_token_embeds_subject_and_timestamps():
    token = create_access_token(subject=42)
    payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])

    assert payload["sub"] == "42"
    assert "iat" in payload
    assert "exp" in payload


def test_decode_access_token_round_trips_a_valid_token():
    token = create_access_token(subject=42)
    decoded = decode_access_token(token)

    assert decoded is not None
    assert decoded.user_id == 42


def test_decode_access_token_returns_none_for_malformed_token():
    assert decode_access_token("not-a-real-token") is None


def test_decode_access_token_returns_none_for_wrong_signature():
    payload = {"sub": "42", "exp": datetime.now(UTC) + timedelta(minutes=5), "iat": datetime.now(UTC).timestamp()}
    token = jwt.encode(payload, "a-different-secret-key", algorithm=ALGORITHM)

    assert decode_access_token(token) is None


def test_decode_access_token_returns_none_for_expired_token():
    payload = {"sub": "42", "exp": datetime.now(UTC) - timedelta(minutes=1), "iat": datetime.now(UTC).timestamp()}
    token = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)

    assert decode_access_token(token) is None


def test_decode_access_token_returns_none_when_iat_missing():
    payload = {"sub": "42", "exp": datetime.now(UTC) + timedelta(minutes=5)}
    token = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)

    assert decode_access_token(token) is None


def test_decode_access_token_returns_none_when_exp_missing():
    payload = {"sub": "42", "iat": datetime.now(UTC).timestamp()}
    token = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)

    assert decode_access_token(token) is None


def test_decode_access_token_returns_none_for_non_integer_subject():
    payload = {
        "sub": "not-an-integer",
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "iat": datetime.now(UTC).timestamp(),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)

    assert decode_access_token(token) is None
