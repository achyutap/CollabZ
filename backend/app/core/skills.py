SKILLS = [
    {"id": "python", "label": "Python", "aliases": ["python", "django", "flask", "pandas", "numpy", "script", "scripting"]},
    {"id": "fastapi", "label": "FastAPI", "aliases": ["fastapi", "api", "rest", "backend", "endpoint", "pydantic", "uvicorn"]},
    {"id": "react", "label": "React", "aliases": ["react", "nextjs", "next.js", "frontend", "component", "jsx", "hooks"]},
    {"id": "html_css", "label": "HTML & CSS", "aliases": ["html", "css", "tailwind", "layout", "responsive", "webpage", "styling"]},
    {"id": "javascript", "label": "JavaScript", "aliases": ["javascript", "js", "typescript", "node", "nodejs", "ecmascript", "dom"]},
    {"id": "sql", "label": "SQL", "aliases": ["sql", "database", "sqlite", "postgres", "mysql", "query", "queries"]},
    {"id": "ml", "label": "Machine Learning", "aliases": ["ml", "machine learning", "model", "neural", "classification", "training", "deep learning"]},
    {"id": "data_analysis", "label": "Data Analysis", "aliases": ["data analysis", "analytics", "statistics", "visualization", "dataset", "insights", "dashboard"]},
    {"id": "iot", "label": "IoT", "aliases": ["iot", "sensor", "arduino", "raspberry", "mqtt", "esp32", "telemetry"]},
    {"id": "embedded_c", "label": "Embedded C", "aliases": ["embedded", "firmware", "microcontroller", "c programming", "stm32", "rtos", "avr"]},
    {"id": "ui_design", "label": "UI Design", "aliases": ["ui", "ux", "design", "figma", "wireframe", "prototype", "mockup"]},
    {"id": "technical_writing", "label": "Technical Writing", "aliases": ["writing", "documentation", "docs", "report", "paper", "manual", "technical writing"]},
]

SKILL_IDS = {s["id"] for s in SKILLS}
_LABELS = {s["id"]: s["label"] for s in SKILLS}


def skill_label(skill_id: str) -> str:
    return _LABELS.get(skill_id, skill_id)
