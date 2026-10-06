import os
import tempfile

os.environ["LLM_MOCK"] = "true"
os.environ["AUTO_SEED"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.core.db import init_db
from app.core.deps import CurrentUser, require_role
from app.core.embeddings import chunk_text, cosine, embed_texts
from app.core.errors import AppError
from app.core.llm import LLMUnavailable, complete, complete_json
from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    sign_payload,
    verify_password,
    verify_payload,
)


def test_token_roundtrip():
    claims = decode_token(create_access_token("u1", "student"))
    assert claims["sub"] == "u1" and claims["role"] == "student" and "exp" in claims


def test_token_expired_and_garbage():
    expired = sign_payload({"sub": "u1", "role": "student"}, -1)
    with pytest.raises(AppError) as e:
        decode_token(expired)
    assert e.value.status_code == 401 and e.value.code == "UNAUTHORIZED"
    with pytest.raises(AppError) as e:
        verify_payload(expired)
    assert e.value.status_code == 400 and e.value.code == "INVALID_TOKEN"
    with pytest.raises(AppError):
        decode_token("garbage")
    assert verify_payload(sign_payload({"a": 1}, 5))["a"] == 1


def test_password_hash():
    h = hash_password("demo1234")
    assert verify_password("demo1234", h) and not verify_password("nope", h)


def test_require_role_403():
    dep = require_role("sponsor")
    with pytest.raises(AppError) as e:
        dep(CurrentUser(id="1", role="student", name="n", email="e"))
    assert e.value.status_code == 403 and e.value.code == "FORBIDDEN"
    u = CurrentUser(id="1", role="sponsor", name="n", email="e")
    assert dep(u) is u


def test_error_format_on_422():
    os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "core_test.db")
    init_db()
    from app.main import app

    c = TestClient(app)
    r = c.post("/auth/register", json={"email": "bad", "password": "x"})
    assert r.status_code == 422
    body = r.json()
    assert set(body) == {"detail", "code"} and body["code"] == "VALIDATION_ERROR" and isinstance(body["detail"], str)
    assert c.get("/health").json() == {"status": "ok"}
    assert c.get("/nope").json()["code"] == "NOT_FOUND"


def test_chunk_text_counts():
    assert chunk_text("") == []
    assert len(chunk_text("a b c")) == 1
    assert len(chunk_text(" ".join(["w"] * 200))) == 1
    assert len(chunk_text(" ".join(["w"] * 250))) == 2
    assert len(chunk_text(" ".join(["w"] * 400))) == 3
    assert len(chunk_text(" ".join(str(i) for i in range(10)), size=4, overlap=1)) == 3


def test_embeddings_cosine_ordering():
    base = "the quick brown fox jumps over the lazy dog near the river bank today"
    near = "the quick brown fox jumps over the lazy dog near the river bank"
    far = "quantum chromodynamics describes gluon interactions inside protons"
    a, b, c = embed_texts([base, near, far])
    assert len(a) == 256
    assert abs(cosine(a, a) - 1.0) < 1e-9
    assert cosine(a, b) > 0.8 > cosine(a, c)
    assert cosine(a, c) < 0.3
    assert cosine([0.0] * 256, a) == 0.0
    assert embed_texts([base])[0] == a


def test_llm_mock_behaviour():
    assert complete("sys", "hello world") == "[mock] hello world"
    with pytest.raises(LLMUnavailable):
        complete_json("sys", "hello")
