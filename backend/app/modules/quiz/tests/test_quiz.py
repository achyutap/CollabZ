import json
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(_tmp, "quiz_test.db")
os.environ["UPLOAD_DIR"] = os.path.join(_tmp, "uploads")
os.environ["LLM_MOCK"] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.db import get_conn, init_db, new_id, now  # noqa: E402
from app.core.security import create_access_token, sign_payload  # noqa: E402
from app.main import app  # noqa: E402

init_db()
client = TestClient(app)


def make_student(pending=("python",), skills=(), projects_done=0, temp=None):
    conn = get_conn()
    uid = new_id()
    conn.execute(
        "INSERT INTO users(id, role, name, email, password_hash, created_at) VALUES(?,?,?,?,?,?)",
        (uid, "student", "Stu", f"{uid}@t.com", "x", now()),
    )
    conn.execute(
        "INSERT INTO students(user_id, skills, pending_skills, temp_rating, projects_done, last_active_at) VALUES(?,?,?,?,?,?)",
        (uid, json.dumps(list(skills)), json.dumps(list(pending)), temp, projects_done, now()),
    )
    conn.close()
    return uid, {"Authorization": "Bearer " + create_access_token(uid, "student")}


def student_row(uid):
    conn = get_conn()
    r = conn.execute("SELECT * FROM students WHERE user_id=?", (uid,)).fetchone()
    conn.close()
    return r


def correct_map(questions):
    conn = get_conn()
    m = {q["id"]: conn.execute("SELECT answer_index FROM quiz_questions WHERE id=?", (q["id"],)).fetchone()[0] for q in questions}
    conn.close()
    return m


def start(h, skills):
    r = client.post("/quiz/start", json={"skills": skills}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def answers_for(questions, n_correct_per_skill):
    cm = correct_map(questions)
    seen, out = {}, []
    for q in questions:
        k = seen.get(q["skill"], 0)
        seen[q["skill"]] = k + 1
        idx = cm[q["id"]] if k < n_correct_per_skill else (cm[q["id"]] + 1) % 4
        out.append({"question_id": q["id"], "selected_index": idx})
    return out


def test_bank_integrity():
    items = json.load(open(os.path.join(os.path.dirname(__file__), "..", "quiz_bank.json"), encoding="utf-8"))
    assert len(items) == 72
    by = {}
    for it in items:
        assert len(it["options"]) == 4 and len(set(it["options"])) == 4 and 0 <= it["answer_index"] <= 3
        by[it["skill"]] = by.get(it["skill"], 0) + 1
    assert len(by) == 12 and set(by.values()) == {6}
    assert len({it["answer_index"] for it in items}) == 4


def test_skills_endpoint_pending_only_for_students():
    _, h = make_student(pending=("sql", "ml"))
    r = client.get("/quiz/skills", headers=h)
    assert {s["id"] for s in r.json()} == {"sql", "ml"}


def test_start_requires_pending_and_hides_answers():
    _, h = make_student(pending=("python",))
    r = client.post("/quiz/start", json={"skills": ["sql"]}, headers=h)
    assert r.status_code == 400 and r.json()["code"] == "BAD_STATE"
    assert client.post("/quiz/start", json={"skills": ["nope"]}, headers=h).status_code == 422
    assert client.post("/quiz/start", json={"skills": []}, headers=h).status_code == 422
    data = start(h, ["python"])
    assert len(data["questions"]) == 5
    assert "answer_index" not in json.dumps(data["questions"])
    assert all(len(q["options"]) == 4 for q in data["questions"])


def test_pass_moves_skill_from_pending_to_skills():
    uid, h = make_student(pending=("python", "sql"))
    d = start(h, ["python"])
    r = client.post("/quiz/submit", json={"attempt_token": d["attempt_token"], "answers": answers_for(d["questions"], 3)}, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["per_skill"] == [{"skill": "python", "correct": 3, "total": 5, "passed": True}]
    assert body["added_skills"] == ["python"]
    row = student_row(uid)
    assert json.loads(row["skills"]) == ["python"] and json.loads(row["pending_skills"]) == ["sql"]


def test_fail_keeps_skill_pending_and_59_percent_boundary():
    uid, h = make_student(pending=("python",))
    d = start(h, ["python"])
    r = client.post("/quiz/submit", json={"attempt_token": d["attempt_token"], "answers": answers_for(d["questions"], 2)}, headers=h).json()
    assert r["per_skill"][0]["passed"] is False and r["added_skills"] == []
    row = student_row(uid)
    assert json.loads(row["pending_skills"]) == ["python"] and json.loads(row["skills"]) == []


def test_rating_minimum_is_one():
    uid, h = make_student(pending=("python",))
    d = start(h, ["python"])
    r = client.post("/quiz/submit", json={"attempt_token": d["attempt_token"], "answers": []}, headers=h).json()
    assert r["total_correct"] == 0 and r["temp_rating"] == 1.0
    assert student_row(uid)["temp_rating"] == 1.0


def test_no_temp_rating_when_projects_done():
    uid, h = make_student(pending=("python",), projects_done=2)
    d = start(h, ["python"])
    r = client.post("/quiz/submit", json={"attempt_token": d["attempt_token"], "answers": answers_for(d["questions"], 5)}, headers=h).json()
    assert r["temp_rating"] is None and student_row(uid)["temp_rating"] is None


def test_retake_replaces_temp_rating():
    uid, h = make_student(pending=("python", "sql"))
    d1 = start(h, ["python"])
    client.post("/quiz/submit", json={"attempt_token": d1["attempt_token"], "answers": answers_for(d1["questions"], 5)}, headers=h)
    assert student_row(uid)["temp_rating"] == 5.0
    d2 = start(h, ["sql"])
    client.post("/quiz/submit", json={"attempt_token": d2["attempt_token"], "answers": answers_for(d2["questions"], 3)}, headers=h)
    assert student_row(uid)["temp_rating"] == 3.0


def test_token_tamper_expired_wrong_user_and_reuse():
    uid, h = make_student(pending=("python",))
    d = start(h, ["python"])
    tok = d["attempt_token"]
    bad = tok[:-3] + ("AAA" if tok[-3:] != "AAA" else "BBB")
    r = client.post("/quiz/submit", json={"attempt_token": bad, "answers": []}, headers=h)
    assert r.status_code == 400 and r.json()["code"] == "INVALID_TOKEN"

    expired = sign_payload({"sub": uid, "answers": {"x": 0}, "skills": ["python"], "jti": new_id()}, minutes=-5)
    r = client.post("/quiz/submit", json={"attempt_token": expired, "answers": []}, headers=h)
    assert r.status_code == 400 and r.json()["code"] == "INVALID_TOKEN"

    _, h2 = make_student(pending=("python",))
    r = client.post("/quiz/submit", json={"attempt_token": tok, "answers": []}, headers=h2)
    assert r.status_code == 400 and r.json()["code"] == "INVALID_TOKEN"

    ok = client.post("/quiz/submit", json={"attempt_token": tok, "answers": answers_for(d["questions"], 5)}, headers=h)
    assert ok.status_code == 200
    again = client.post("/quiz/submit", json={"attempt_token": tok, "answers": []}, headers=h)
    assert again.status_code == 400 and again.json()["code"] == "BAD_STATE"
    assert again.json()["detail"] == "Attempt already submitted"


def test_unknown_question_ids_ignored():
    uid, h = make_student(pending=("python",))
    d = start(h, ["python"])
    ans = answers_for(d["questions"], 5) + [{"question_id": "not-in-token", "selected_index": 0}]
    r = client.post("/quiz/submit", json={"attempt_token": d["attempt_token"], "answers": ans}, headers=h).json()
    assert r["total"] == 5 and r["total_correct"] == 5
