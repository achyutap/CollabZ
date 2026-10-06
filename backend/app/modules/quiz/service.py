import json
import random
from pathlib import Path

from app.core.db import new_id, now, transaction
from app.core.errors import AppError
from app.core.security import sign_payload, verify_payload
from app.core.skills import SKILL_IDS, skill_label

BANK_PATH = Path(__file__).parent / "quiz_bank.json"
QUESTIONS_PER_SKILL = 5
PASS_RATIO = 0.6


def ensure_bank(conn) -> None:
    if conn.execute("SELECT COUNT(*) AS c FROM quiz_questions").fetchone()["c"] > 0:
        return
    items = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    with transaction(conn):
        for it in items:
            conn.execute(
                "INSERT OR IGNORE INTO quiz_questions(id, skill, question, options, answer_index) VALUES(?,?,?,?,?)",
                (new_id(), it["skill"], it["question"], json.dumps(it["options"]), int(it["answer_index"])),
            )


def _student(conn, user_id: str):
    row = conn.execute("SELECT * FROM students WHERE user_id=?", (user_id,)).fetchone()
    if row is None:
        raise AppError(404, "NOT_FOUND", "Student profile not found")
    return row


def list_skills(conn, user) -> list[dict]:
    if user.role == "student":
        pending = set(json.loads(_student(conn, user.id)["pending_skills"] or "[]"))
        return [{"id": s, "label": skill_label(s)} for s in SKILL_IDS if s in pending]
    return [{"id": s, "label": skill_label(s)} for s in SKILL_IDS]


def start(conn, user, skills: list[str]) -> dict:
    if not (1 <= len(skills) <= 5):
        raise AppError(422, "VALIDATION_ERROR", "Choose between 1 and 5 skills")
    if len(set(skills)) != len(skills):
        raise AppError(422, "VALIDATION_ERROR", "Skills must be unique")
    for s in skills:
        if s not in SKILL_IDS:
            raise AppError(422, "VALIDATION_ERROR", f"Unknown skill: {s}")
    pending = set(json.loads(_student(conn, user.id)["pending_skills"] or "[]"))
    for s in skills:
        if s not in pending:
            raise AppError(400, "BAD_STATE", "Skill is not waiting for verification")
    ensure_bank(conn)
    questions, answers = [], {}
    for s in skills:
        rows = conn.execute("SELECT * FROM quiz_questions WHERE skill=?", (s,)).fetchall()
        for r in random.sample(rows, min(QUESTIONS_PER_SKILL, len(rows))):
            questions.append({"id": r["id"], "skill": s, "question": r["question"], "options": json.loads(r["options"])})
            answers[r["id"]] = r["answer_index"]
    token = sign_payload({"sub": user.id, "answers": answers, "skills": skills, "jti": new_id()}, minutes=30)
    return {"attempt_token": token, "questions": questions}


def submit(conn, user, token: str, given: list[dict]) -> dict:
    payload = verify_payload(token)
    if payload.get("sub") != user.id:
        raise AppError(400, "INVALID_TOKEN", "Attempt token does not belong to this user")
    jti = payload.get("jti")
    answers = payload.get("answers")
    if not jti or not isinstance(answers, dict) or not answers:
        raise AppError(400, "INVALID_TOKEN", "Malformed attempt token")
    if conn.execute("SELECT 1 FROM quiz_attempts WHERE id=?", (jti,)).fetchone():
        raise AppError(400, "BAD_STATE", "Attempt already submitted")

    ids = list(answers.keys())
    marks = ",".join("?" * len(ids))
    skill_of = {r["id"]: r["skill"] for r in conn.execute(f"SELECT id, skill FROM quiz_questions WHERE id IN ({marks})", ids)}
    chosen = {}
    for a in given:
        if a["question_id"] in answers:
            chosen[a["question_id"]] = a["selected_index"]

    order = [s for s in payload.get("skills", []) if s in SKILL_IDS]
    stats = {s: {"skill": s, "correct": 0, "total": 0, "passed": False} for s in order}
    for qid, correct_idx in answers.items():
        sk = skill_of.get(qid)
        if sk is None:
            continue
        st = stats.setdefault(sk, {"skill": sk, "correct": 0, "total": 0, "passed": False})
        st["total"] += 1
        if chosen.get(qid) == correct_idx:
            st["correct"] += 1
    per_skill = list(stats.values())
    for st in per_skill:
        st["passed"] = st["total"] > 0 and st["correct"] / st["total"] >= PASS_RATIO
    total = sum(s["total"] for s in per_skill)
    total_correct = sum(s["correct"] for s in per_skill)

    with transaction(conn):
        if conn.execute("SELECT 1 FROM quiz_attempts WHERE id=?", (jti,)).fetchone():
            raise AppError(400, "BAD_STATE", "Attempt already submitted")
        stu = _student(conn, user.id)
        skills = json.loads(stu["skills"] or "[]")
        pending = json.loads(stu["pending_skills"] or "[]")
        added = []
        for st in per_skill:
            if st["passed"]:
                if st["skill"] not in skills:
                    skills.append(st["skill"])
                    added.append(st["skill"])
                if st["skill"] in pending:
                    pending.remove(st["skill"])
        temp = None
        if stu["projects_done"] == 0 and total > 0:
            temp = max(1.0, round(total_correct / total * 5, 1))
        if temp is not None:
            conn.execute(
                "UPDATE students SET skills=?, pending_skills=?, temp_rating=? WHERE user_id=?",
                (json.dumps(skills), json.dumps(pending), temp, user.id),
            )
        else:
            conn.execute(
                "UPDATE students SET skills=?, pending_skills=? WHERE user_id=?",
                (json.dumps(skills), json.dumps(pending), user.id),
            )
        conn.execute(
            "INSERT INTO quiz_attempts(id, student_id, skills, score, total, created_at) VALUES(?,?,?,?,?,?)",
            (jti, user.id, json.dumps(order), total_correct, total, now()),
        )
    return {"per_skill": per_skill, "added_skills": added, "temp_rating": temp, "total_correct": total_correct, "total": total}
