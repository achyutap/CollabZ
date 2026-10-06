"""Demo data seeder (schema v2).

Run from the backend directory:  python -m seed.seed
Idempotent: existing emails / problems / documents are skipped, so it is safe to run repeatedly.
Backdated timestamps are written with plain INSERTs (core.notify helpers always stamp now()).
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.db import get_conn, init_db, new_id, now, transaction
from app.core.embeddings import chunk_text, embed_texts
from app.core.security import hash_password
from app.core.storage import is_text, save_file

PASSWORD = "demo1234"
BANK_PATH = Path(__file__).resolve().parent.parent / "app" / "modules" / "quiz" / "quiz_bank.json"
CORPUS_PATH = Path(__file__).resolve().parent / "demo_corpus.txt"


def ts(days: float = 0, hours: float = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days, hours=hours)).isoformat(timespec="seconds")


def edu(school, degree, field, start, end):
    return {"school": school, "degree": degree, "field": field, "start_year": start, "end_year": end}


# ----------------------------------------------------------------------------- people
SPONSORS = [
    ("Meridian Water Board", "sponsor1@demo.com"),
    ("Greenfield Energy Labs", "sponsor2@demo.com"),
    ("Orion Campus Services", "sponsor3@demo.com"),
]
RESEARCHERS = [
    ("Dr. Ananya Sharma", ["iot", "embedded_c", "python", "data_analysis"], 4.8, 0.8, "IoT systems researcher focused on low-power sensing and edge analytics."),
    ("Dr. Rohan Mehta", ["ml", "python", "data_analysis", "sql"], 4.6, 0.6, "Machine learning researcher working on time-series forecasting for infrastructure."),
    ("Dr. Priya Nair", ["fastapi", "python", "sql", "technical_writing"], 4.4, 0.9, "Software engineering researcher; builds data-backed web platforms and mentors students."),
    ("Dr. Vikram Iyer", ["react", "javascript", "html_css", "ui_design"], 4.2, 0.7, "Human-computer interaction researcher focused on dashboards for civic data."),
    ("Dr. Kavita Rao", ["ml", "data_analysis", "python", "technical_writing"], 4.9, 0.5, "Applied statistician and ML researcher with a passion for reproducible research."),
    ("Dr. Arjun Desai", ["embedded_c", "iot", "python"], 3.9, 1.0, "Firmware and hardware prototyping lead; works on sensor nodes and wireless protocols."),
    ("Dr. Meera Krishnan", ["ui_design", "html_css", "react", "javascript"], 4.1, 0.4, "Design researcher exploring accessible interfaces for data-heavy applications."),
    ("Dr. Sanjay Gupta", ["sql", "fastapi", "data_analysis", "javascript"], 3.6, 0.85, "Database and backend researcher specialising in analytics pipelines."),
]
# name, skills, temp/final rating, projects_done  (rating kind decided by projects_done)
STUDENTS = [
    ("Aarav Patel", ["iot", "python", "embedded_c"], 3.8, 0),
    ("Diya Singh", ["python", "data_analysis", "sql"], 4.2, 0),
    ("Rahul Verma", ["data_analysis", "ml", "python"], 3.5, 0),
    ("Sneha Reddy", ["ui_design", "html_css", "react"], 4.0, 0),
    ("Karthik Menon", ["javascript", "react", "html_css"], 3.2, 0),
    ("Ishita Bose", ["technical_writing", "data_analysis", "python"], 4.4, 0),
    ("Manish Kumar", ["embedded_c", "iot", "python"], 2.9, 0),
    ("Pooja Joshi", ["sql", "fastapi", "python"], 3.6, 0),
    ("Aditya Rao", ["ml", "python", "data_analysis"], 2.6, 0),
    ("Neha Kapoor", ["ui_design", "html_css", "javascript"], 3.1, 0),
    ("Siddharth Jain", ["fastapi", "python", "sql", "javascript"], 4.5, 2),
    ("Tanvi Shah", ["ml", "python", "data_analysis", "technical_writing"], 4.7, 3),
    ("Rohit Agarwal", ["iot", "embedded_c", "python"], 4.1, 1),
    ("Anjali Pillai", ["react", "javascript", "ui_design"], 4.3, 2),
    ("Varun Chopra", ["sql", "data_analysis", "python"], 3.9, 1),
    ("Kritika Malhotra", ["html_css", "javascript", "technical_writing"], 3.4, 1),
    ("Harsh Vardhan", ["fastapi", "sql", "python"], 4.8, 3),
    ("Sana Qureshi", ["ml", "data_analysis", "technical_writing"], 4.0, 2),
    ("Nikhil Bhat", ["react", "javascript", "html_css"], 3.6, 1),
    ("Meghna Das", ["python", "fastapi", "sql"], 3.0, 1),
]
RECENT_STUDENTS = {1: 1, 2: 2, 3: 3, 19: 4, 4: 20}  # student number -> days since last activity

PROFILES = {
    "sponsor1@demo.com": ("Water utility sponsoring open research", "Meridian Water Board manages municipal water supply and funds applied research on monitoring and conservation.", "Pune, India",
        {"website": "https://meridian-water.example.org"}, {"organization": "Meridian Water Board", "industry": "Public utilities", "website": "https://meridian-water.example.org", "focus_areas": ["water quality", "IoT monitoring", "conservation"]}),
    "sponsor2@demo.com": ("Funding practical energy-efficiency research", "Greenfield Energy Labs sponsors student-powered projects that cut campus and industrial energy use.", "Bengaluru, India",
        {"website": "https://greenfield-energy.example.org", "linkedin": "https://www.linkedin.com/company/greenfield-energy-example"}, {"organization": "Greenfield Energy Labs", "industry": "Energy", "website": "https://greenfield-energy.example.org", "focus_areas": ["energy analytics", "smart buildings", "dashboards"]}),
    "sponsor3@demo.com": ("Campus operations and student services", "Orion Campus Services funds software projects that improve everyday campus life.", "Hyderabad, India",
        {"website": "https://orion-campus.example.org"}, {"organization": "Orion Campus Services", "industry": "Education services", "website": "https://orion-campus.example.org", "focus_areas": ["campus software", "student services"]}),
    "researcher1@demo.com": ("IoT & embedded systems researcher", "I lead projects on low-power sensing, LoRa networks and edge analytics. I enjoy mentoring students through their first hardware deployments.", "Pune, India",
        {"github": "https://github.com/ananya-sharma-example", "scholar": "https://scholar.example.org/ananya", "website": "https://ananya.example.org"},
        {"institution": "Pune Institute of Technology", "department": "Electronics & Telecommunication", "designation": "Associate Professor", "research_areas": ["IoT", "embedded systems", "edge analytics"],
         "education": [edu("IIT Bombay", "PhD", "Electrical Engineering", 2010, 2015), edu("VJTI Mumbai", "B.Tech", "Electronics", 2006, 2010)],
         "publications": [{"title": "Low-power LoRa sensing for river monitoring", "venue": "IEEE Sensors Journal", "year": 2022, "url": "https://example.org/pub/lora-river"}, {"title": "Duty cycling strategies for solar nodes", "venue": "IoT Conf.", "year": 2020, "url": "https://example.org/pub/duty-cycle"}],
         "awards": ["Best Paper, IoT Conf. 2020"]}),
    "researcher2@demo.com": ("Machine learning for infrastructure data", "I work on forecasting and anomaly detection for energy and water systems.", "Mumbai, India",
        {"github": "https://github.com/rohan-mehta-example", "scholar": "https://scholar.example.org/rohan"},
        {"institution": "Mumbai Institute of Science", "department": "Computer Science", "designation": "Assistant Professor", "research_areas": ["time-series forecasting", "anomaly detection"],
         "education": [edu("IISc Bangalore", "PhD", "Computer Science", 2012, 2017)], "publications": [{"title": "Forecasting campus energy demand with gradient boosting", "venue": "ACM BuildSys", "year": 2021, "url": "https://example.org/pub/energy-gbm"}], "awards": []}),
    "researcher3@demo.com": ("Backend engineering & research software", "I build robust data-backed web platforms and teach students API design.", "Chennai, India",
        {"github": "https://github.com/priya-nair-example"},
        {"institution": "Chennai College of Engineering", "department": "Information Technology", "designation": "Professor", "research_areas": ["web platforms", "API design", "databases"],
         "education": [edu("Anna University", "PhD", "Information Technology", 2008, 2013)], "publications": [], "awards": ["Excellence in Teaching 2023"]}),
    "researcher4@demo.com": ("Civic data dashboards & HCI", "I design interactive dashboards that make public data understandable.", "Delhi, India",
        {"website": "https://vikram-iyer.example.org"},
        {"institution": "Delhi Design University", "department": "Interaction Design", "designation": "Associate Professor", "research_areas": ["data visualisation", "HCI"],
         "education": [edu("IIT Delhi", "PhD", "Design", 2011, 2016)], "publications": [{"title": "Dashboards for non-expert decision makers", "venue": "CHI Workshops", "year": 2019, "url": "https://example.org/pub/dash"}], "awards": []}),
    "researcher5@demo.com": ("Applied statistics & reproducible ML", "I help teams ship reproducible analyses and write about them clearly.", "Kolkata, India",
        {"scholar": "https://scholar.example.org/kavita"},
        {"institution": "Eastern Institute of Statistics", "department": "Data Science", "designation": "Professor", "research_areas": ["applied statistics", "reproducibility"],
         "education": [edu("ISI Kolkata", "PhD", "Statistics", 2005, 2010)], "publications": [], "awards": ["Women in Data Science Award 2022"]}),
    "researcher6@demo.com": ("Firmware & wireless sensor nodes", "Hands-on prototyping with microcontrollers and radios.", "Hyderabad, India", {}, 
        {"institution": "Hyderabad Tech Institute", "department": "Embedded Systems", "designation": "Assistant Professor", "research_areas": ["firmware", "wireless protocols"],
         "education": [edu("IIIT Hyderabad", "MS", "Embedded Systems", 2012, 2014)], "publications": [], "awards": []}),
    "researcher7@demo.com": ("Accessible interface design", "Research on accessible, inclusive interfaces for data-heavy applications.", "Bengaluru, India", {"website": "https://meera-k.example.org"},
        {"institution": "Bengaluru School of Design", "department": "UX Research", "designation": "Lecturer", "research_areas": ["accessibility", "UX"],
         "education": [edu("NID Ahmedabad", "M.Des", "Interaction Design", 2013, 2015)], "publications": [], "awards": []}),
    "researcher8@demo.com": ("Analytics pipelines & databases", "Backend and database specialist for analytics workloads.", "Noida, India", {},
        {"institution": "Noida Institute of Computing", "department": "Computer Applications", "designation": "Assistant Professor", "research_areas": ["data pipelines", "SQL optimisation"],
         "education": [edu("IIT Kanpur", "M.Tech", "Computer Science", 2009, 2011)], "publications": [], "awards": []}),
    "student1@demo.com": ("IoT and embedded enthusiast", "Final-year ECE student building sensor nodes and data pipelines.", "Pune, India", {"github": "https://github.com/aarav-patel-example"},
        {"education": [edu("Pune Institute of Technology", "B.Tech", "Electronics", 2022, 2026)], "experience": [{"title": "Embedded intern", "org": "SensorWorks", "description": "Wrote ESP32 firmware for temperature loggers.", "start": "2025-05", "end": "2025-07"}], "achievements": ["Smart India Hackathon finalist"], "interests": ["IoT", "LoRa", "robotics"]}),
    "student2@demo.com": ("Python & data analysis", "I like turning messy data into clear answers.", "Delhi, India", {"github": "https://github.com/diya-singh-example", "linkedin": "https://www.linkedin.com/in/diya-singh-example"},
        {"education": [edu("Delhi Technical University", "B.Tech", "Computer Science", 2022, 2026)], "experience": [], "achievements": ["Top 10 in university data challenge"], "interests": ["data analysis", "SQL", "visualisation"]}),
    "student3@demo.com": ("Aspiring ML engineer", "Interested in forecasting and applied machine learning.", "Mumbai, India", {"github": "https://github.com/rahul-verma-example"},
        {"education": [edu("Mumbai Institute of Science", "B.Sc", "Data Science", 2023, 2026)], "experience": [], "achievements": [], "interests": ["machine learning", "time series"]}),
    "student4@demo.com": ("UI designer who codes", "Designing accessible interfaces with React.", "Bengaluru, India", {"website": "https://sneha-reddy.example.org"},
        {"education": [edu("Bengaluru School of Design", "B.Des", "Interaction Design", 2022, 2026)], "experience": [{"title": "UI design intern", "org": "Pixelcraft", "description": "Designed onboarding flows for a fintech app.", "start": "2025-06", "end": "2025-08"}], "achievements": ["Dribbble featured shot"], "interests": ["design systems", "accessibility"]}),
    "student11@demo.com": ("Backend developer", "FastAPI and SQL developer with two completed research projects.", "Jaipur, India", {"github": "https://github.com/siddharth-jain-example"},
        {"education": [edu("Jaipur Engineering College", "B.Tech", "Information Technology", 2021, 2025)], "experience": [{"title": "Backend intern", "org": "ApiForge", "description": "Built REST services in FastAPI.", "start": "2024-06", "end": "2024-09"}], "achievements": ["Open-source contributor"], "interests": ["APIs", "databases"]}),
    "student12@demo.com": ("ML practitioner", "Applied ML, three research projects delivered.", "Hyderabad, India", {"github": "https://github.com/tanvi-shah-example", "scholar": "https://scholar.example.org/tanvi"},
        {"education": [edu("Hyderabad Tech Institute", "B.Tech", "Computer Science", 2021, 2025)], "experience": [], "achievements": ["Kaggle bronze medal"], "interests": ["ML", "technical writing"]}),
    "student14@demo.com": ("Front-end developer", "React developer and UI designer.", "Chennai, India", {"github": "https://github.com/anjali-pillai-example"},
        {"education": [edu("Chennai College of Engineering", "B.E", "Computer Science", 2021, 2025)], "experience": [], "achievements": ["Built the campus lost-and-found portal UI"], "interests": ["React", "UI design"]}),
    "student17@demo.com": ("API engineer", "Top-rated student contributor with three completed projects.", "Pune, India", {"github": "https://github.com/harsh-vardhan-example", "linkedin": "https://www.linkedin.com/in/harsh-vardhan-example"},
        {"education": [edu("Pune Institute of Technology", "B.Tech", "Computer Engineering", 2021, 2025)], "experience": [{"title": "Software intern", "org": "DataBridge", "description": "Designed a reporting API.", "start": "2024-05", "end": "2024-08"}], "achievements": ["Dean's list"], "interests": ["FastAPI", "SQL", "testing"]}),
}

# ----------------------------------------------------------------------------- generated file contents
def file_text(path: str, version: int, topic: str) -> str:
    stem = Path(path).stem
    ext = Path(path).suffix
    if ext == ".py":
        extra = f"\n\ndef summarise_v{version}(items):\n    \"\"\"Return counts per category (added in revision {version}).\"\"\"\n    out = {{}}\n    for it in items:\n        out[it.get('kind', 'unknown')] = out.get(it.get('kind', 'unknown'), 0) + 1\n    return out\n" if version > 1 else "\n"
        return (f'"""{stem}: {topic} (revision {version})."""\nimport logging\n\nlog = logging.getLogger(__name__)\n\n\n'
                f"def run(items):\n    \"\"\"Process items and return the cleaned list.\"\"\"\n    cleaned = [it for it in items if it is not None]\n    log.info('%s processed %d items', '{stem}', len(cleaned))\n    return cleaned\n{extra}")
    if ext == ".jsx":
        return (f"import React from 'react';\n\n// {stem}: {topic} (revision {version})\nexport default function {stem}({{ title = '{topic}', items = [] }}) {{\n"
                f"  return (\n    <section className=\"{stem.lower()}\">\n      <h2>{{title}}</h2>\n      <ul>{{items.map((i) => <li key={{i.id}}>{{i.label}}</li>)}}</ul>\n    </section>\n  );\n}}\n")
    if ext == ".css":
        return f"/* {topic} styles, revision {version} */\n.card {{ border: 1px solid #d0d7de; border-radius: 8px; padding: 12px; }}\n.card h2 {{ margin: 0 0 8px; font-size: 1.1rem; }}\n"
    if ext == ".sql":
        return f"-- {topic} (revision {version})\nCREATE TABLE IF NOT EXISTS readings (\n  id INTEGER PRIMARY KEY,\n  node_id TEXT NOT NULL,\n  value REAL NOT NULL,\n  recorded_at TEXT NOT NULL\n);\nCREATE INDEX IF NOT EXISTS idx_readings_node ON readings(node_id, recorded_at);\n"
    return f"# {stem.replace('_', ' ').title()}\n\n_{topic} — revision {version}_\n\n## Summary\nThis note documents decisions taken so far and open questions for the next iteration.\n\n## Details\n- Inputs: sensor readings in UTC\n- Output: validated records ready for the dashboard\n- Next: review with the research lead\n"


def add_file(conn, project_id, submission_id, author_id, path, version, topic, originality, public, created_at, force_text=None):
    fid = new_id()
    text = file_text(path, version, topic)
    data = text.encode("utf-8")
    storage = save_file(project_id, fid, data)
    ctype = {".py": "text/x-python", ".jsx": "text/javascript", ".css": "text/css", ".sql": "application/sql", ".md": "text/markdown"}.get(Path(path).suffix, "text/plain")
    istext = 1 if is_text(Path(path).name, data) else 0
    conn.execute(
        "INSERT INTO submission_files(id, submission_id, project_id, author_id, path, name, size, content_type, is_text, storage_path, version, originality, is_public, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (fid, submission_id, project_id, author_id, path, Path(path).name, len(data), ctype, istext, storage, version, originality, 1 if public else 0, created_at),
    )
    if istext:
        chunks = chunk_text(text, 200, 40)
        for c, e in zip(chunks, embed_texts(chunks) if chunks else []):
            conn.execute("INSERT INTO file_chunks(id, file_id, user_id, project_id, chunk_text, embedding) VALUES(?,?,?,?,?,?)", (new_id(), fid, author_id, project_id, c, json.dumps(e)))
    return fid


# ----------------------------------------------------------------------------- helpers
def ledger(conn, uid, amount, typ, problem_id=None, project_id=None, created_at=None):
    conn.execute(
        "INSERT INTO ledger_entries(id, user_id, problem_id, project_id, amount, type, created_at) VALUES(?,?,?,?,?,?,?)",
        (new_id(), uid, problem_id, project_id, round(amount, 2), typ, created_at or now()),
    )
    conn.execute("UPDATE wallets SET balance = ROUND(balance + ?, 2) WHERE user_id=?", (round(amount, 2), uid))


def event(conn, project_id, actor_id, typ, message, created_at, ref_id=None, meta=None):
    conn.execute(
        "INSERT INTO project_events(id, project_id, actor_id, type, message, ref_id, meta, created_at) VALUES(?,?,?,?,?,?,?,?)",
        (new_id(), project_id, actor_id, typ, message, ref_id, json.dumps(meta or {}), created_at),
    )


def notif(conn, uid, typ, title, body, link, is_read, created_at):
    conn.execute(
        "INSERT INTO notifications(id, user_id, type, title, body, link, is_read, created_at) VALUES(?,?,?,?,?,?,?,?)",
        (new_id(), uid, typ, title, body, link, 1 if is_read else 0, created_at),
    )


def uid_of(conn, email):
    r = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    return r["id"] if r else None


def name_of(conn, uid):
    return conn.execute("SELECT name FROM users WHERE id=?", (uid,)).fetchone()["name"]


def create_user(conn, pw_hash, role, name, email, created_at):
    if uid_of(conn, email):
        return uid_of(conn, email), False
    uid = new_id()
    conn.execute("INSERT INTO users(id, role, name, email, password_hash, created_at) VALUES(?,?,?,?,?,?)", (uid, role, name, email, pw_hash, created_at))
    conn.execute("INSERT INTO wallets(user_id, balance) VALUES(?,0)", (uid,))
    return uid, True


def put_profile(conn, uid, email):
    p = PROFILES.get(email)
    if not p:
        return
    conn.execute(
        "INSERT OR IGNORE INTO profiles(user_id, headline, about, location, links, details, updated_at) VALUES(?,?,?,?,?,?,?)",
        (uid, p[0], p[1], p[2], json.dumps(p[3]), json.dumps(p[4]), now()),
    )


def quiz_attempt(conn, uid, skills, target_rating, created_at):
    total = 5 * len(skills)
    score = min(total, max(0, round(target_rating / 5 * total)))
    conn.execute("INSERT INTO quiz_attempts(id, student_id, skills, score, total, created_at) VALUES(?,?,?,?,?,?)", (new_id(), uid, json.dumps(skills), score, total, created_at))
    return max(1.0, round(score / total * 5, 1))


def ensure_problem(conn, sponsor_id, title, description, budget, spct, rpct, ppct, skills, status, created_at):
    row = conn.execute("SELECT id FROM problems WHERE sponsor_id=? AND title=?", (sponsor_id, title)).fetchone()
    if row:
        return row["id"], False
    pid = new_id()
    conn.execute(
        "INSERT INTO problems(id, sponsor_id, title, description, budget, student_pct, researcher_pct, project_pct, required_skills, status, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (pid, sponsor_id, title, description, budget, spct, rpct, ppct, json.dumps(skills), status, created_at),
    )
    ledger(conn, sponsor_id, -budget, "escrow", problem_id=pid, created_at=created_at)
    return pid, True


# ----------------------------------------------------------------------------- scenarios
def seed_completed(conn, sponsor_id, lead, co, students):
    """Completed project: lead researcher3 + co-researcher4, 3 students, consistent payout."""
    pid, created = ensure_problem(
        conn, sponsor_id, "Campus lost-and-found web portal",
        "Build a web portal where students report and search for lost items. The platform needs a REST API with a relational database, a searchable React front end and clear documentation for campus staff.",
        60000, 50, 40, 10, ["fastapi", "python", "sql", "react", "ui_design"], "completed", ts(45))
    if not created:
        return
    prj = new_id()
    conn.execute("INSERT INTO projects(id, problem_id, researcher_id, status, created_at, completed_at) VALUES(?,?,?,?,?,?)", (prj, pid, lead, "completed", ts(42), ts(5)))
    conn.execute("INSERT INTO project_researchers(project_id, researcher_id, role, share_pct, joined_at) VALUES(?,?,?,?,?)", (prj, lead, "lead", 60, ts(42)))
    conn.execute("INSERT INTO project_researchers(project_id, researcher_id, role, share_pct, joined_at) VALUES(?,?,?,?,?)", (prj, co, "researcher", 40, ts(41)))
    for rid, sc in ((lead, 0.91), (co, 0.84)):
        conn.execute("INSERT INTO researcher_requests(id, problem_id, researcher_id, match_score, status, created_at) VALUES(?,?,?,?,'accepted',?)", (new_id(), pid, rid, sc, ts(44)))
    event(conn, prj, lead, "project_created", f"{name_of(conn, lead)} started the project", ts(42))
    event(conn, prj, co, "researcher_joined", f"{name_of(conn, co)} joined as co-researcher", ts(41))
    needs = [("fastapi", 1), ("react", 1), ("sql", 1)]
    for sk, c in needs:
        conn.execute("INSERT INTO skill_needs(id, project_id, skill, count) VALUES(?,?,?,?)", (new_id(), prj, sk, c))
    plan = {  # student -> (skill, [(path, status, days_ago)])
        "s17": ("fastapi", [("src/api/main.py", "approved", 36), ("src/api/models.py", "approved", 32), ("sql/schema.sql", "approved", 28), ("tests/test_api.py", "approved", 20)]),
        "s14": ("react", [("src/web/App.jsx", "approved", 35), ("src/web/Search.jsx", "approved", 27), ("src/web/styles.css", "approved", 18)]),
        "s15": ("sql", [("docs/schema.md", "approved", 34), ("sql/queries.sql", "approved", 25), ("sql/report.sql", "rejected", 22)]),
    }
    counts, pub_ids = {}, []
    for key, (skill, items) in plan.items():
        sid = students[key]
        conn.execute("INSERT INTO student_requests(id, project_id, student_id, skill, match_score, status, created_at) VALUES(?,?,?,?,?,'accepted',?)", (new_id(), prj, sid, skill, 0.8, ts(40)))
        conn.execute("INSERT INTO project_members(project_id, student_id, skill, status, joined_at) VALUES(?,?,?,?,?)", (prj, sid, skill, "active", ts(39)))
        event(conn, prj, sid, "student_joined", f"{name_of(conn, sid)} joined as {skill}", ts(39), meta={"student_id": sid})
        n_ok = 0
        for path, status, d in items:
            sub = new_id()
            msg = f"Add {Path(path).name} for the lost-and-found portal"
            conn.execute("INSERT INTO work_submissions(id, project_id, student_id, commit_msg, description, status, ai_quality_score, reviewer_feedback, created_at, reviewed_at, originality) VALUES(?,?,?,?,?,?,?,?,?,?,'original')",
                         (sub, prj, sid, msg, None, status, 0.82 if status == "approved" else 0.4, "Looks good." if status == "approved" else "Needs more work on edge cases.", ts(d), ts(d - 1)))
            fid = add_file(conn, prj, sub, sid, path, 1, "Lost-and-found portal", "original", False, ts(d))
            if path in ("src/api/main.py", "src/web/App.jsx"):
                pub_ids.append(fid)
            meta = {"submission_id": sub, "student_id": sid, "commit_msg": msg, "file_count": 1}
            event(conn, prj, sid, "submission_created", f"{name_of(conn, sid)} submitted: {msg}", ts(d), sub, {**meta, "status": "pending"})
            event(conn, prj, lead, "submission_" + status, f"{name_of(conn, lead)} {status} a submission", ts(d - 1), sub, {**meta, "status": status})
            n_ok += status == "approved"
        counts[key] = (len(items), n_ok)
    conn.executemany("UPDATE submission_files SET is_public=1 WHERE id=?", [(f,) for f in pub_ids])
    event(conn, prj, lead, "files_published", f"{name_of(conn, lead)} published 2 file(s)", ts(6), None, {"file_ids": pub_ids, "count": 2})
    # payout: impact = approved * approval_ratio, share = impact / total_impact (see README: contract gaps)
    budget, student_pool, researcher_pool, project_fund = 60000.0, 30000.0, 24000.0, 6000.0
    impacts = {k: counts[k][1] * (counts[k][1] / counts[k][0]) for k in counts}
    total = sum(impacts.values())
    scores = {"s17": 4.8, "s14": 4.6, "s15": 3.4}
    for key, imp in impacts.items():
        sid = students[key]
        share = round(imp / total * 100, 2)
        amount = round(student_pool * imp / total, 2)
        conn.execute("INSERT INTO rewards(project_id, student_id, share_pct, amount) VALUES(?,?,?,?)", (prj, sid, share, amount))
        conn.execute("INSERT INTO project_ratings(project_id, student_id, score) VALUES(?,?,?)", (prj, sid, scores[key]))
        ledger(conn, sid, amount, "payout", pid, prj, ts(5))
    ledger(conn, lead, researcher_pool * 0.6, "payout", pid, prj, ts(5))
    ledger(conn, co, researcher_pool * 0.4, "payout", pid, prj, ts(5))
    ledger(conn, lead, project_fund, "project_fund", pid, prj, ts(5))
    event(conn, prj, lead, "project_completed", "Project completed and payouts distributed", ts(5))


ACTIVE_SUBS = [  # idx, student key, commit msg, status, days ago, [(path, topic)], originality
    (1, "s1", "Add MQTT sensor publisher for energy meters", "approved", 26, [("src/sensors/mqtt_publisher.py", "MQTT energy meter publisher"), ("docs/sensor_wiring.md", "Sensor wiring guide")], "original"),
    (2, "s2", "Create ingestion pipeline for meter readings", "approved", 24, [("src/ingest/pipeline.py", "Meter reading ingestion"), ("src/ingest/schema.sql", "Readings schema")], "original"),
    (3, "s3", "Exploratory analysis of hourly consumption", "approved", 22, [("analysis/eda_summary.md", "Hourly consumption EDA"), ("src/analysis/stats.py", "Consumption statistics")], "original"),
    (4, "s4", "Draft dashboard wireframe notes for review", "approved", 20, [("docs/wireframe_notes.md", "Dashboard wireframe notes")], "original"),
    (5, "s1", "Improve publisher with retry and backoff", "approved", 15, [("src/sensors/mqtt_publisher.py", "MQTT energy meter publisher")], "original"),
    (6, "s19", "Dashboard layout with energy usage cards", "approved", 14, [("src/dashboard/App.jsx", "Energy dashboard"), ("src/dashboard/styles.css", "Dashboard")], "original"),
    (7, "s2", "Add anomaly flagging for sudden spikes", "pending", 9, [("src/ingest/anomaly.py", "Spike detection")], "original"),
    (8, "s3", "Rolling average forecast baseline", "rejected", 11, [("src/analysis/forecast.py", "Forecast baseline")], "original"),
    (9, "s2", "Fix timezone handling in the pipeline", "approved", 7, [("src/ingest/pipeline.py", "Meter reading ingestion")], "original"),
    (10, "s19", "Add hourly chart component to the dashboard", "pending", 5, [("src/dashboard/Chart.jsx", "Hourly chart"), ("src/dashboard/App.jsx", "Energy dashboard")], "copied"),
    (11, "s1", "Firmware notes for the ESP32 meter node", "pending", 3, [("docs/firmware_notes.md", "ESP32 firmware notes")], "original"),
]


def seed_active(conn, sponsor_id, lead, co, st):
    pid, created = ensure_problem(
        conn, sponsor_id, "Smart campus energy usage dashboard",
        "Instrument campus buildings with smart energy meters, ingest the readings into a clean data pipeline, analyse consumption patterns and present them in an interactive dashboard so facilities teams can spot waste.",
        120000, 40, 50, 10, ["iot", "python", "data_analysis", "react", "ui_design"], "matched", ts(34))
    if not created:
        return None
    prj = new_id()
    conn.execute("INSERT INTO projects(id, problem_id, researcher_id, status, created_at) VALUES(?,?,?,?,?)", (prj, pid, lead, "active", ts(30)))
    conn.execute("INSERT INTO project_researchers(project_id, researcher_id, role, share_pct, joined_at) VALUES(?,?,?,?,?)", (prj, lead, "lead", None, ts(30)))
    conn.execute("INSERT INTO project_researchers(project_id, researcher_id, role, share_pct, joined_at) VALUES(?,?,?,?,?)", (prj, co, "researcher", None, ts(29)))
    for rid, sc in ((lead, 0.88), (co, 0.74)):
        conn.execute("INSERT INTO researcher_requests(id, problem_id, researcher_id, match_score, status, created_at) VALUES(?,?,?,?,'accepted',?)", (new_id(), pid, rid, sc, ts(33)))
    event(conn, prj, lead, "project_created", f"{name_of(conn, lead)} started the project", ts(30))
    event(conn, prj, co, "researcher_joined", f"{name_of(conn, co)} joined as co-researcher", ts(29))
    for sk, c in (("iot", 1), ("python", 2), ("data_analysis", 1), ("react", 1), ("ui_design", 1)):
        conn.execute("INSERT INTO skill_needs(id, project_id, skill, count) VALUES(?,?,?,?)", (new_id(), prj, sk, c))
    members = [("s1", "iot", "active", 28), ("s2", "python", "active", 27), ("s3", "data_analysis", "active", 26), ("s4", "ui_design", "removed", 25), ("s19", "react", "active", 24), ("s20", "python", "blacklisted", 23)]
    for key, skill, status, d in members:
        sid = st[key]
        conn.execute("INSERT INTO student_requests(id, project_id, student_id, skill, match_score, status, created_at) VALUES(?,?,?,?,?,'accepted',?)", (new_id(), prj, sid, skill, 0.78, ts(d + 1)))
        removed_at = ts(12) if status == "removed" else (ts(6) if status == "blacklisted" else None)
        reason = "Left the project" if status == "removed" else ("Blacklisted after repeated copied uploads" if status == "blacklisted" else None)
        conn.execute("INSERT INTO project_members(project_id, student_id, skill, status, joined_at, removed_at, removed_reason) VALUES(?,?,?,?,?,?,?)", (prj, sid, skill, status, ts(d), removed_at, reason))
        event(conn, prj, sid, "student_joined", f"{name_of(conn, sid)} joined as {skill}", ts(d), meta={"student_id": sid})
    conn.execute("INSERT INTO student_requests(id, project_id, student_id, skill, match_score, status, created_at) VALUES(?,?,?,?,?,'pending',?)", (new_id(), prj, st["s8"], "python", 0.7, ts(2)))
    event(conn, prj, lead, "student_removed", f"{name_of(conn, st['s4'])} was removed from the project", ts(12), meta={"student_id": st["s4"]})
    event(conn, prj, lead, "student_removed", f"{name_of(conn, st['s20'])} was blacklisted and removed", ts(6), meta={"student_id": st["s20"]})

    versions, file_ids, sub_ids = {}, {}, {}
    for idx, key, msg, status, d, files, orig in sorted(ACTIVE_SUBS, key=lambda s: -s[4]):
        sid, sub = st[key], new_id()
        sub_ids[idx] = sub
        reviewer = lead if idx % 2 else co
        reviewed = status != "pending"
        conn.execute(
            "INSERT INTO work_submissions(id, project_id, student_id, commit_msg, description, status, ai_quality_score, reviewer_feedback, created_at, reviewed_at, originality) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (sub, prj, sid, msg, "Part of the energy dashboard project.", status, 0.55 + (idx % 4) * 0.1,
             ("Good work, merged." if status == "approved" else "Please add tests and compare against a naive baseline.") if reviewed else None,
             ts(d), ts(d - 1) if reviewed else None, orig))
        ids = []
        for path, topic in files:
            versions[path] = versions.get(path, 0) + 1
            fid = add_file(conn, prj, sub, sid, path, versions[path], topic, orig, False, ts(d))
            file_ids[(idx, path)] = fid
            ids.append(fid)
        meta = {"submission_id": sub, "student_id": sid, "commit_msg": msg, "file_count": len(files)}
        event(conn, prj, sid, "submission_created", f"{name_of(conn, sid)} submitted: {msg}", ts(d), sub, {**meta, "status": "pending"})
        if reviewed:
            event(conn, prj, reviewer, "submission_" + status, f"{name_of(conn, reviewer)} {status} a submission", ts(d - 1), sub, {**meta, "status": status})
    wiring, pub_v2, pipe_v2 = file_ids[(1, "docs/sensor_wiring.md")], file_ids[(5, "src/sensors/mqtt_publisher.py")], file_ids[(9, "src/ingest/pipeline.py")]
    conn.executemany("UPDATE submission_files SET is_public=1 WHERE id=?", [(wiring,), (pub_v2,), (pipe_v2,)])
    event(conn, prj, lead, "files_published", f"{name_of(conn, lead)} published 1 file(s)", ts(15), None, {"file_ids": [wiring], "count": 1})
    event(conn, prj, co, "files_published", f"{name_of(conn, co)} published 2 file(s)", ts(4), None, {"file_ids": [pub_v2, pipe_v2], "count": 2})
    # integrity: student19 warned once (second copy blocks); student20 warned then blocked and blacklisted
    conn.execute("INSERT INTO integrity_events(id, user_id, project_id, submission_id, action, detail, created_at) VALUES(?,?,?,?,?,?,?)",
                 (new_id(), st["s19"], prj, sub_ids[10], "warned", "Uploaded files closely match another student's work (similarity 0.87). Further copying will block the upload.", ts(5)))
    conn.execute("INSERT INTO integrity_events(id, user_id, project_id, submission_id, action, detail, created_at) VALUES(?,?,?,?,?,?,?)",
                 (new_id(), st["s20"], prj, None, "warned", "Uploaded files closely match existing project files (similarity 0.91).", ts(9)))
    conn.execute("INSERT INTO integrity_events(id, user_id, project_id, submission_id, action, detail, created_at) VALUES(?,?,?,?,?,?,?)",
                 (new_id(), st["s20"], prj, None, "blocked", "Second copied upload blocked; account blacklisted.", ts(6)))
    conn.execute("UPDATE users SET is_blacklisted=1, blacklisted_at=? WHERE id=?", (ts(6), st["s20"]))
    return prj


def run() -> None:
    init_db()
    conn = get_conn()
    pw_hash = hash_password(PASSWORD)
    creds: list[tuple[str, str, str, str]] = []
    with transaction(conn):
        # quiz bank
        if conn.execute("SELECT COUNT(*) AS c FROM quiz_questions").fetchone()["c"] == 0:
            for it in json.loads(BANK_PATH.read_text(encoding="utf-8")):
                conn.execute("INSERT OR IGNORE INTO quiz_questions(id, skill, question, options, answer_index) VALUES(?,?,?,?,?)",
                             (new_id(), it["skill"], it["question"], json.dumps(it["options"]), int(it["answer_index"])))
        # sponsors
        sponsors = {}
        for i, (name, email) in enumerate(SPONSORS, 1):
            uid, new = create_user(conn, pw_hash, "sponsor", name, email, ts(60))
            sponsors[i] = uid
            if new:
                conn.execute("UPDATE wallets SET balance=0 WHERE user_id=?", (uid,))
                ledger(conn, uid, 500000, "seed", created_at=ts(60))
                put_profile(conn, uid, email)
            creds.append(("sponsor", name, email, PASSWORD))
        # researchers
        res = {}
        for i, (name, skills, rating, avail, bio) in enumerate(RESEARCHERS, 1):
            email = f"researcher{i}@demo.com"
            uid, new = create_user(conn, pw_hash, "researcher", name, email, ts(90 - i))
            res[i] = uid
            if new:
                conn.execute("INSERT INTO researchers(user_id, skills, rating, bio, availability) VALUES(?,?,?,?,?)", (uid, json.dumps(skills), rating, bio, avail))
                put_profile(conn, uid, email)
            creds.append(("researcher", name, email, PASSWORD))
        # students
        st = {}
        for i, (name, skills, rating, done) in enumerate(STUDENTS, 1):
            email = f"student{i}@demo.com"
            uid, new = create_user(conn, pw_hash, "student", name, email, ts(100 - i))
            st[f"s{i}"] = uid
            if new:
                last_active = ts(RECENT_STUDENTS.get(i, (i * 7) % 121))
                temp = quiz_attempt(conn, uid, skills, rating if done == 0 else 4.0, ts(80 - i))
                pending = ["ml"] if i == 10 else []
                if done == 0:
                    conn.execute("INSERT INTO students(user_id, skills, pending_skills, temp_rating, final_rating, projects_done, last_active_at) VALUES(?,?,?,?,NULL,0,?)", (uid, json.dumps(skills), json.dumps(pending), temp, last_active))
                else:
                    conn.execute("INSERT INTO students(user_id, skills, pending_skills, temp_rating, final_rating, projects_done, last_active_at) VALUES(?,?,?,NULL,?,?,?)", (uid, json.dumps(skills), json.dumps(pending), rating, done, last_active))
                put_profile(conn, uid, email)
            creds.append(("student", name, email, PASSWORD))

        # demo open problem (sponsor1)
        demo_id, _ = ensure_problem(
            conn, sponsors[1], "Water quality monitoring using IoT",
            "Design a low-cost network of IoT sensor nodes that measure pH, turbidity and temperature in a river system. Build the firmware, a Python data pipeline that cleans and stores the readings, and a dashboard that shows live values, trends and alerts for water authorities.",
            100000, 30, 60, 10, ["iot", "python", "embedded_c", "data_analysis"], "open", ts(3))
        # completed + active projects
        seed_completed(conn, sponsors[3], res[3], res[4], {"s17": st["s17"], "s14": st["s14"], "s15": st["s15"]})
        prj = seed_active(conn, sponsors[2], res[1], res[2], st)

        # corpus document for the plagiarism demo
        text = CORPUS_PATH.read_text(encoding="utf-8").strip()
        if not conn.execute("SELECT 1 FROM documents WHERE user_id=? AND filename=?", (st["s1"], "iot_water_quality_notes.txt")).fetchone():
            did = new_id()
            conn.execute("INSERT INTO documents(id, project_id, user_id, filename, text, plagiarism_score, created_at) VALUES(?,?,?,?,?,0,?)", (did, None, st["s1"], "iot_water_quality_notes.txt", text, ts(50)))
            chunks = chunk_text(text, 200, 40)
            for c, e in zip(chunks, embed_texts(chunks)):
                conn.execute("INSERT INTO document_chunks(id, document_id, chunk_text, embedding) VALUES(?,?,?,?)", (new_id(), did, c, json.dumps(e)))

        # likes + notifications (only on first seed of the active project)
        for a, b in (("sponsor1", "researcher1"), ("student1", "researcher1"), ("student2", "researcher1"), ("researcher1", "student1"), ("researcher2", "student1"), ("student4", "student14"), ("sponsor2", "student17")):
            ua, ub = uid_of(conn, a + "@demo.com"), uid_of(conn, b + "@demo.com")
            conn.execute("INSERT OR IGNORE INTO profile_likes(liker_id, user_id, created_at) VALUES(?,?,?)", (ua, ub, ts(10)))
        if prj:
            notif(conn, sponsors[1], "profile_like", "Someone liked your profile", "A researcher liked your profile.", f"/profile/{res[1]}", False, ts(2))
            notif(conn, res[1], "submission_pending", "New submission to review", "Dr. Ananya's project has a new submission: Firmware notes for the ESP32 meter node", f"/projects/{prj}?tab=work", False, ts(3))
            notif(conn, res[1], "submission_pending", "New submission to review", "A new dashboard chart component is waiting for review.", f"/projects/{prj}?tab=work", False, ts(5))
            notif(conn, st["s1"], "submission_approved", "Your submission was approved", "Improve publisher with retry and backoff was approved.", f"/projects/{prj}?tab=work", True, ts(14))
            notif(conn, st["s1"], "profile_like", "Someone liked your profile", "A researcher liked your profile.", f"/profile/{res[1]}", False, ts(1))
    conn.close()

    conn = get_conn()
    demo_id = conn.execute("SELECT id FROM problems WHERE title='Water quality monitoring using IoT'").fetchone()["id"]
    conn.close()
    print(f"{'ROLE':<11}{'NAME':<24}{'EMAIL':<28}PASSWORD")
    for role, name, email, pw in creds:
        print(f"{role:<11}{name:<24}{email:<28}{pw}")
    print(f"\nDemo open problem id: {demo_id}")


if __name__ == "__main__":
    run()
