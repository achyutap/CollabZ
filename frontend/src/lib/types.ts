export type Role = "sponsor" | "researcher" | "student";
export type ProjectRole = "sponsor" | "lead" | "researcher" | "student";
export type ProblemStatus = "open" | "matched" | "completed";
export type RequestStatus = "pending" | "accepted" | "declined" | "expired";
export type ProjectStatus = "active" | "completed";
export type SubmissionStatus = "pending" | "approved" | "rejected";
export type Originality = "original" | "copied";
export type RatingType = "temp" | "final";

export interface UserOut {
  id: string;
  role: Role;
  name: string;
  email: string;
  has_taken_quiz: boolean;
  pending_quiz_skills: string[];
}

export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  user: UserOut;
}

export interface RegisterPayload {
  email: string;
  password: string;
  name: string;
  role: Role;
  skills?: string[];
  bio?: string;
}

export interface ResearcherOut {
  id: string;
  name: string;
  skills: string[];
  rating: number;
  bio: string;
  availability: number;
}

export interface StudentOut {
  id: string;
  name: string;
  skills: string[];
  pending_skills: string[];
  temp_rating: number | null;
  final_rating: number | null;
  rating: number | null;
  rating_type: RatingType | null;
  projects_done: number;
}

export interface ProblemOut {
  id: string;
  sponsor_id: string;
  sponsor_name: string;
  title: string;
  description: string;
  budget: number;
  student_pct: number;
  researcher_pct: number;
  project_pct: number;
  required_skills: string[];
  status: ProblemStatus;
  created_at: string;
}

export interface ResearcherRequestOut {
  id: string;
  problem_id: string;
  researcher_id: string;
  researcher_name: string;
  sponsor_name: string;
  match_score: number;
  status: RequestStatus;
  created_at: string;
  problem: ProblemOut;
  project_id: string | null;
}

export interface SkillNeedOut {
  skill: string;
  count: number;
  filled: number;
}

export interface StudentRequestOut {
  id: string;
  project_id: string;
  project_title: string;
  researcher_name: string;
  student_id: string;
  student_name: string;
  skill: string;
  match_score: number;
  status: RequestStatus;
  created_at: string;
}

export interface ResearcherRef {
  id: string;
  name: string;
  role: "lead" | "researcher";
}

export interface ProjectOut {
  id: string;
  problem_id: string;
  title: string;
  status: ProjectStatus;
  researcher: { id: string; name: string };
  researchers: ResearcherRef[];
  sponsor_name: string;
  member_count: number;
  created_at: string;
}

export interface ProjectMember {
  student_id: string;
  name: string;
  skill: string;
  rating: number | null;
}

export interface ProjectResearcher {
  id: string;
  name: string;
  role: "lead" | "researcher";
  share_pct: number;
}

export interface ProjectBudget {
  total: number;
  student_pool: number;
  researcher_pool: number;
  project_fund: number;
  researcher_share: number;
}

export interface ProjectDetail extends ProjectOut {
  problem: ProblemOut;
  skill_needs: SkillNeedOut[];
  members: ProjectMember[];
  researchers: ProjectResearcher[];
  budget: ProjectBudget;
  my_role: ProjectRole;
  can_manage: boolean;
}

export interface FileOut {
  id: string;
  submission_id: string;
  project_id: string;
  path: string;
  name: string;
  size: number;
  content_type: string;
  is_text: boolean;
  version: number;
  originality: Originality;
  is_public: boolean;
  author_id: string;
  author_name: string;
  status: SubmissionStatus;
  created_at: string;
}

export interface IntegrityInfo {
  action: "none" | "warned";
  message: string;
}

export interface SubmissionOut {
  id: string;
  project_id: string;
  student_id: string;
  student_name: string;
  commit_msg: string;
  description: string | null;
  status: SubmissionStatus;
  reviewer_feedback: string | null;
  ai_quality_score: number | null;
  created_at: string;
  reviewed_at: string | null;
  files: FileOut[];
  originality: Originality;
  integrity: IntegrityInfo | null;
}

export interface FileContent {
  id: string;
  path: string;
  size: number;
  is_text: boolean;
  truncated: boolean;
  content: string | null;
}

export type ActivityType =
  | "project_created"
  | "researcher_joined"
  | "student_joined"
  | "student_removed"
  | "submission_created"
  | "submission_approved"
  | "submission_rejected"
  | "files_published"
  | "files_unpublished"
  | "project_completed";

export interface ActivityItem {
  id: string;
  type: ActivityType;
  actor: { id: string; name: string; role: string } | null;
  message: string;
  ref_id: string | null;
  meta: Record<string, unknown>;
  created_at: string;
}

export interface NotificationOut {
  id: string;
  type: string;
  title: string;
  body: string;
  link: string | null;
  is_read: boolean;
  created_at: string;
}

export interface CountsOut {
  requests: number;
  approvals: number;
  notifications: number;
}

export interface ProjectCounts {
  pending_approvals: number;
  my_pending_submissions: number;
  pending_student_requests: number;
}

export interface ResearcherShare {
  researcher_id: string;
  name: string;
  role: "lead" | "researcher";
  share_pct: number;
}

export interface PayoutResearcher {
  researcher_id: string;
  name: string;
  role: "lead" | "researcher";
  share_pct: number;
  amount: number;
}

export interface PayoutStudent {
  student_id: string;
  name: string;
  status: "active" | "removed";
  submitted: number;
  approved: number;
  files_count: number;
  approval_ratio: number;
  impact: number;
  share_pct: number;
  amount: number;
  project_score: number;
  old_rating: number | null;
  new_final_rating: number;
}

export interface PayoutTransaction {
  user_id: string;
  name: string;
  role: Role;
  kind: "student_reward" | "researcher_share" | "project_fund" | "refund";
  amount: number;
}

export interface PayoutOut {
  project_id: string;
  budget: number;
  student_pool: number;
  researcher_pool: number;
  project_fund: number;
  refunded: number;
  completed_at: string;
  researchers: PayoutResearcher[];
  students: PayoutStudent[];
  transactions: PayoutTransaction[];
}

export interface ProfileLinks {
  github?: string;
  linkedin?: string;
  website?: string;
  scholar?: string;
}

export interface WorkItem {
  project_id: string;
  title: string;
  my_role: ProjectRole;
  skill: string | null;
  status: string;
  public_file_count: number;
  started_at: string;
  completed_at: string | null;
}

export interface ProfileOut {
  user: { id: string; role: Role; name: string };
  headline: string;
  about: string;
  location: string;
  links: ProfileLinks;
  details: Record<string, unknown>;
  skills: string[];
  pending_skills: string[];
  rating: number | null;
  projects_done: number;
  likes_count: number;
  liked_by_me: boolean;
  is_me: boolean;
  member_since: string;
  works: WorkItem[];
}

export interface PersonCard {
  id: string;
  name: string;
  role: Role;
  headline: string;
  skills: string[];
  rating: number | null;
  likes_count: number;
}

export interface PublicProjectCard {
  project_id: string;
  title: string;
  summary: string;
  required_skills: string[];
  status: string;
  public_file_count: number;
  researchers: { id: string; name: string }[];
  members: { id: string; name: string }[];
  updated_at: string;
}

export interface PublicProjectDetail {
  project_id: string;
  title: string;
  description: string;
  required_skills: string[];
  status: string;
  sponsor_name: string;
  researchers: { id: string; name: string; role: string; headline: string }[];
  members: { id: string; name: string; skill: string }[];
  started_at: string;
  completed_at: string | null;
  files: FileOut[];
}

export interface WalletEntry {
  id: string;
  amount: number;
  type: string;
  problem_id: string | null;
  project_id: string | null;
  created_at: string;
}

export interface WalletOut {
  balance: number;
  entries: WalletEntry[];
}

export interface MatchOut {
  researcher: ResearcherOut;
  score: number;
  matched_skills: string[];
  missing_skills: string[];
}

export interface ShortlistCandidate {
  student: StudentOut;
  score: number;
  rating: number;
  rating_type: RatingType;
  projects_done: number;
  request_status: RequestStatus | null;
}

export interface ShortlistGroup {
  skill: string;
  count: number;
  filled: number;
  candidates: ShortlistCandidate[];
}

export interface ChatMessageOut {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface IntegrityRecord {
  id: string;
  student_id: string;
  student_name: string;
  action: "warned" | "blocked";
  detail: string;
  created_at: string;
}

export interface MyIntegrityRecord {
  id: string;
  action: "warned" | "blocked";
  detail: string;
  created_at: string;
}

export interface QuizSkill {
  id: string;
  label: string;
}

export interface QuizQuestion {
  id: string;
  skill: string;
  question: string;
  options: string[];
}

export interface QuizStartOut {
  attempt_token: string;
  questions: QuizQuestion[];
}

export interface QuizSkillResult {
  skill: string;
  correct: number;
  total: number;
  passed: boolean;
}

export interface QuizSubmitResult {
  per_skill: QuizSkillResult[];
  added_skills: string[];
  temp_rating: number | null;
  total_correct: number;
  total: number;
}

export interface ApiErrorBody {
  detail: string;
  code: string;
}
