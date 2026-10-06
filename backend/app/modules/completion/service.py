from statistics import mean

from app.core.access import lead_id, project_role
from app.core.db import new_id, now, transaction
from app.core.errors import AppError
from app.core.notify import log_event, notify_many

from . import formulas

_PROJECT_SQL = (
    "SELECT p.id, p.problem_id, p.status, p.completed_at, pr.budget, pr.student_pct, pr.researcher_pct, "
    "pr.project_pct, pr.sponsor_id FROM projects p JOIN problems pr ON pr.id = p.problem_id WHERE p.id=?"
)


def _get_project(conn, project_id):
    proj = conn.execute(_PROJECT_SQL, (project_id,)).fetchone()
    if proj is None:
        raise AppError(404, "NOT_FOUND", "Project not found")
    return proj


def _pools(proj):
    budget = round(float(proj["budget"]), 2)
    student_pool = round(budget * proj["student_pct"] / 100, 2)
    researcher_pool = round(budget * proj["researcher_pct"] / 100, 2)
    project_fund = round(budget - student_pool - researcher_pool, 2)
    return budget, student_pool, researcher_pool, project_fund


def _eligible_members(conn, project_id):
    return conn.execute(
        "SELECT pm.student_id, pm.status, u.name FROM project_members pm JOIN users u ON u.id = pm.student_id "
        "WHERE pm.project_id=? AND pm.status IN ('active','removed') ORDER BY u.name, pm.student_id",
        (project_id,),
    ).fetchall()


def _subs_by_student(conn, project_id):
    """Only ORIGINAL submissions count (copied ones count for nothing)."""
    out = {}
    for r in conn.execute(
        "SELECT student_id, status, ai_quality_score FROM work_submissions "
        "WHERE project_id=? AND originality='original'", (project_id,),
    ).fetchall():
        out.setdefault(r["student_id"], []).append({"status": r["status"], "ai_quality_score": r["ai_quality_score"]})
    return out


def _files_count(conn, project_id):
    return {
        r["student_id"]: r["n"]
        for r in conn.execute(
            "SELECT s.student_id, COUNT(*) AS n FROM submission_files f JOIN work_submissions s "
            "ON s.id = f.submission_id WHERE f.project_id=? AND s.status='approved' AND s.originality='original' "
            "GROUP BY s.student_id", (project_id,),
        ).fetchall()
    }


def _researcher_rows(conn, project_id):
    return conn.execute(
        "SELECT pr.researcher_id, pr.role, pr.share_pct, u.name FROM project_researchers pr "
        "JOIN users u ON u.id = pr.researcher_id WHERE pr.project_id=? "
        "ORDER BY CASE pr.role WHEN 'lead' THEN 0 ELSE 1 END, pr.joined_at, pr.researcher_id",
        (project_id,),
    ).fetchall()


def _credit(conn, user_id, amount, entry_type, problem_id, project_id):
    if amount <= 0:
        return
    conn.execute(
        "INSERT INTO wallets(user_id, balance) VALUES(?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET balance = balance + excluded.balance",
        (user_id, amount),
    )
    conn.execute(
        "INSERT INTO ledger_entries(id, user_id, problem_id, project_id, amount, type, created_at) "
        "VALUES(?,?,?,?,?,?,?)",
        (new_id(), user_id, problem_id, project_id, amount, entry_type, now()),
    )


def _researchers_out(conn, project_id, problem_id):
    rows = _researcher_rows(conn, project_id)
    pcts = formulas.effective_researcher_pcts([(r["researcher_id"], r["share_pct"]) for r in rows])
    paid = {
        r["user_id"]: r["s"]
        for r in conn.execute(
            "SELECT user_id, SUM(amount) AS s FROM ledger_entries WHERE problem_id=? AND type='payout' "
            "GROUP BY user_id", (problem_id,),
        ).fetchall()
    }
    return [
        {"researcher_id": r["researcher_id"], "name": r["name"], "role": r["role"],
         "share_pct": pcts[r["researcher_id"]], "amount": round(float(paid.get(r["researcher_id"], 0.0)), 2)}
        for r in rows
    ]


def _transactions(conn, problem_id):
    out = []
    for r in conn.execute(
        "SELECT l.user_id, u.name, u.role, l.type, l.amount FROM ledger_entries l JOIN users u ON u.id = l.user_id "
        "WHERE l.problem_id=? AND l.type IN ('payout','refund','project_fund') ORDER BY l.created_at, l.rowid",
        (problem_id,),
    ).fetchall():
        if r["type"] == "refund":
            kind = "refund"
        elif r["type"] == "project_fund":
            kind = "project_fund"
        else:
            kind = "student_reward" if r["role"] == "student" else "researcher_share"
        out.append({"user_id": r["user_id"], "name": r["name"], "role": r["role"], "kind": kind,
                    "amount": round(float(r["amount"]), 2)})
    return out


def complete_project(conn, user, project_id):
    with transaction(conn):
        proj = _get_project(conn, project_id)
        if lead_id(conn, project_id) != user.id:
            raise AppError(403, "FORBIDDEN", "Only the lead researcher can complete the project")
        if proj["status"] != "active":
            raise AppError(409, "CONFLICT", "Project is not active")
        pending = conn.execute(
            "SELECT COUNT(*) AS n FROM work_submissions WHERE project_id=? AND status='pending' "
            "AND student_id NOT IN (SELECT student_id FROM project_members WHERE project_id=? "
            "AND status='blacklisted')", (project_id, project_id),
        ).fetchone()["n"]
        if pending:
            raise AppError(400, "BAD_STATE", f"{pending} submissions still pending")

        problem_id = proj["problem_id"]
        budget, student_pool, researcher_pool, project_fund = _pools(proj)
        members = _eligible_members(conn, project_id)
        subs = _subs_by_student(conn, project_id)
        fcounts = _files_count(conn, project_id)
        stats = {m["student_id"]: formulas.member_stats(subs.get(m["student_id"], [])) for m in members}
        raws = {sid: s["raw"] for sid, s in stats.items()}
        max_raw = max(raws.values()) if raws else 0.0

        refunded = 0.0
        if sum(raws.values()) == 0:
            shares = {sid: 0.0 for sid in raws}
            amounts = {sid: 0.0 for sid in raws}
            if student_pool > 0:
                _credit(conn, proj["sponsor_id"], student_pool, "refund", problem_id, project_id)
            refunded = student_pool
        else:
            shares = formulas.compute_shares(raws)
            amounts = formulas.split_amounts(shares, student_pool)
            for sid in raws:
                conn.execute(
                    "INSERT INTO rewards(project_id, student_id, share_pct, amount) VALUES(?,?,?,?)",
                    (project_id, sid, round(shares[sid] * 100, 2), amounts[sid]),
                )
                _credit(conn, sid, amounts[sid], "payout", problem_id, project_id)

        res_rows = _researcher_rows(conn, project_id)
        res_amounts = formulas.split_researcher_pool(
            researcher_pool, {r["researcher_id"]: r["share_pct"] for r in res_rows}, user.id
        )
        for rid, amt in res_amounts.items():
            _credit(conn, rid, amt, "payout", problem_id, project_id)
        _credit(conn, user.id, project_fund, "project_fund", problem_id, project_id)

        ts = now()
        students_out = []
        for m in members:
            sid = m["student_id"]
            st = stats[sid]
            score = formulas.project_score(st["raw"], max_raw, st["approval_ratio"])
            row = conn.execute(
                "SELECT temp_rating, final_rating, projects_done FROM students WHERE user_id=?", (sid,)
            ).fetchone()
            previous = [r["score"] for r in conn.execute(
                "SELECT score FROM project_ratings WHERE student_id=?", (sid,)).fetchall()]
            conn.execute("INSERT INTO project_ratings(project_id, student_id, score) VALUES(?,?,?)",
                         (project_id, sid, score))
            old_rating = None
            if row is not None:
                done = row["projects_done"]
                old_rating = row["final_rating"] if done > 0 else row["temp_rating"]
                if len(previous) < done and row["final_rating"] is not None:
                    previous += [row["final_rating"]] * (done - len(previous))
                final = formulas.new_final_rating(previous, score)
                conn.execute(
                    "UPDATE students SET final_rating=?, projects_done=projects_done+1, temp_rating=NULL, "
                    "last_active_at=? WHERE user_id=?", (final, ts, sid),
                )
            else:
                final = formulas.new_final_rating(previous, score)
            students_out.append({
                "student_id": sid, "name": m["name"], "status": m["status"],
                "submitted": st["submitted"], "approved": st["approved"], "files_count": fcounts.get(sid, 0),
                "approval_ratio": round(st["approval_ratio"], 4), "impact": round(st["impact"], 4),
                "share_pct": round(shares[sid] * 100, 2), "amount": amounts[sid],
                "project_score": score, "old_rating": old_rating, "new_final_rating": final,
            })

        conn.execute("UPDATE projects SET status='completed', completed_at=? WHERE id=?", (ts, project_id))
        conn.execute("UPDATE problems SET status='completed' WHERE id=?", (problem_id,))
        notify_many(
            conn, [proj["sponsor_id"]] + [r["researcher_id"] for r in res_rows] + [m["student_id"] for m in members],
            "project_completed", "Project completed", "The project has been completed and funds were distributed.",
            f"/projects/{project_id}?tab=budget",
        )
        log_event(conn, project_id, user.id, "project_completed", f"{user.name} completed the project",
                  project_id, {"budget": budget})

        return {
            "project_id": project_id, "budget": budget, "student_pool": student_pool,
            "researcher_pool": researcher_pool, "project_fund": project_fund, "refunded": refunded,
            "completed_at": ts, "researchers": _researchers_out(conn, project_id, problem_id),
            "students": students_out, "transactions": _transactions(conn, problem_id),
        }


def get_payout(conn, user, project_id):
    proj = _get_project(conn, project_id)
    role = project_role(conn, project_id, user.id)
    if role is None:
        removed = conn.execute(
            "SELECT 1 FROM project_members WHERE project_id=? AND student_id=? AND status='removed'",
            (project_id, user.id),
        ).fetchone()
        if not removed:
            raise AppError(403, "FORBIDDEN", "Not allowed to view this payout")
    if proj["status"] != "completed":
        raise AppError(400, "BAD_STATE", "Project is not completed")

    budget, student_pool, researcher_pool, project_fund = _pools(proj)
    problem_id = proj["problem_id"]
    refunded = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS s FROM ledger_entries WHERE problem_id=? AND type='refund'",
        (problem_id,),
    ).fetchone()["s"]
    subs = _subs_by_student(conn, project_id)
    fcounts = _files_count(conn, project_id)
    rows = conn.execute(
        "SELECT pm.student_id, pm.status, u.name, r.share_pct, r.amount, pr.score, st.final_rating "
        "FROM project_members pm JOIN users u ON u.id = pm.student_id "
        "LEFT JOIN rewards r ON r.project_id = pm.project_id AND r.student_id = pm.student_id "
        "LEFT JOIN project_ratings pr ON pr.project_id = pm.project_id AND pr.student_id = pm.student_id "
        "LEFT JOIN students st ON st.user_id = pm.student_id "
        "WHERE pm.project_id=? AND pm.status IN ('active','removed') ORDER BY u.name, pm.student_id",
        (project_id,),
    ).fetchall()
    students_out = []
    for r in rows:
        sid = r["student_id"]
        st = formulas.member_stats(subs.get(sid, []))
        others = [x["score"] for x in conn.execute(
            "SELECT score FROM project_ratings WHERE student_id=? AND project_id != ?", (sid, project_id)).fetchall()]
        score = r["score"] if r["score"] is not None else 1.0
        students_out.append({
            "student_id": sid, "name": r["name"], "status": r["status"],
            "submitted": st["submitted"], "approved": st["approved"], "files_count": fcounts.get(sid, 0),
            "approval_ratio": round(st["approval_ratio"], 4), "impact": round(st["impact"], 4),
            "share_pct": r["share_pct"] if r["share_pct"] is not None else 0.0,
            "amount": r["amount"] if r["amount"] is not None else 0.0,
            "project_score": score, "old_rating": round(mean(others), 1) if others else None,
            "new_final_rating": r["final_rating"] if r["final_rating"] is not None else score,
        })
    return {
        "project_id": project_id, "budget": budget, "student_pool": student_pool,
        "researcher_pool": researcher_pool, "project_fund": project_fund,
        "refunded": round(float(refunded), 2), "completed_at": proj["completed_at"],
        "researchers": _researchers_out(conn, project_id, problem_id), "students": students_out,
        "transactions": _transactions(conn, problem_id),
    }
