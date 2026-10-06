export const SKILLS: { id: string; label: string }[] = [
  { id: "python", label: "Python" },
  { id: "fastapi", label: "FastAPI" },
  { id: "react", label: "React" },
  { id: "html_css", label: "HTML & CSS" },
  { id: "javascript", label: "JavaScript" },
  { id: "sql", label: "SQL" },
  { id: "ml", label: "Machine Learning" },
  { id: "data_analysis", label: "Data Analysis" },
  { id: "iot", label: "IoT" },
  { id: "embedded_c", label: "Embedded C" },
  { id: "ui_design", label: "UI Design" },
  { id: "technical_writing", label: "Technical Writing" },
];

export function skillLabel(id: string): string {
  return SKILLS.find((s) => s.id === id)?.label ?? id;
}
