import axios from "axios";

// En desarrollo (vite dev) el backend corre aparte en :8001. En la imagen de
// Docker, el frontend build se sirve desde el mismo FastAPI que expone la
// API, así que ahí basta con rutas relativas (VITE_API_BASE="").
const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8001";

const client = axios.create({ baseURL: API_BASE });

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function login(email, password) {
  const { data } = await client.post("/api/auth/login", { email, password });
  return data;
}

export async function register(email, documento, fullName, group) {
  const { data } = await client.post("/api/auth/register", {
    email,
    documento,
    full_name: fullName,
    group,
  });
  return data;
}

export async function changePassword(currentPassword, newPassword) {
  const { data } = await client.post("/api/auth/change-password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
  return data;
}

export async function getExams() {
  const { data } = await client.get("/api/exams");
  return data;
}

export async function getExam(examId) {
  const { data } = await client.get(`/api/exams/${examId}`);
  return data;
}

export async function startExam(examId) {
  const { data } = await client.post(`/api/exams/${examId}/start`);
  return data;
}

export async function finishExam(examId) {
  const { data } = await client.post(`/api/exams/${examId}/finish`);
  return data;
}

export async function getExamResults(examId) {
  const { data } = await client.get(`/api/exams/${examId}/results`);
  return data;
}

export async function runCode(problemId, code) {
  const { data } = await client.post(`/api/problems/${problemId}/run`, { code });
  return data;
}

export async function saveCode(problemId, code) {
  const { data } = await client.post(`/api/problems/${problemId}/save`, { code });
  return data;
}

export async function saveDraft(problemId, code) {
  const { data } = await client.post(`/api/problems/${problemId}/save-draft`, { code });
  return data;
}

export async function getMySubmission(problemId) {
  const { data } = await client.get(`/api/problems/${problemId}/my-submission`);
  return data;
}

export async function getTeacherExams() {
  const { data } = await client.get("/api/teacher/exams");
  return data;
}

export async function getTeacherDashboard(examId) {
  const { data } = await client.get(`/api/teacher/exams/${examId}/dashboard`);
  return data;
}

export async function getTeacherStudentSubmissions(examId, studentId) {
  const { data } = await client.get(`/api/teacher/exams/${examId}/students/${studentId}/submissions`);
  return data;
}

export async function toggleExamOpen(examId) {
  const { data } = await client.post(`/api/teacher/exams/${examId}/toggle-open`);
  return data;
}

export async function getTeacherExamPreview(examId) {
  const { data } = await client.get(`/api/teacher/exams/${examId}/preview`);
  return data;
}

export async function getTeacherBanks({ publishedOnly = false } = {}) {
  const { data } = await client.get("/api/teacher/banks", {
    params: publishedOnly ? { published_only: true } : undefined,
  });
  return data;
}

export async function getTeacherProblemDetail(problemId) {
  const { data } = await client.get(`/api/teacher/problems/${problemId}`);
  return data;
}

export async function loadBankFromTex(bankId, file, maxProblems) {
  const formData = new FormData();
  formData.append("file", file);
  if (maxProblems) formData.append("max_problems", maxProblems);
  const { data } = await client.post(`/api/teacher/banks/${bankId}/load-from-tex`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 10 * 60 * 1000, // el pipeline de agentes IA puede tardar varios minutos
  });
  return data;
}

export async function publishTeacherProblem(problemId) {
  const { data } = await client.post(`/api/teacher/problems/${problemId}/publish`);
  return data;
}

export async function deleteTeacherProblem(problemId) {
  const { data } = await client.delete(`/api/teacher/problems/${problemId}`);
  return data;
}

export async function deleteTeacherBank(bankId) {
  const { data } = await client.delete(`/api/teacher/banks/${bankId}`);
  return data;
}

export async function createTeacherBank(payload) {
  const { data } = await client.post("/api/teacher/banks", payload);
  return data;
}

export async function deleteTeacherExam(examId) {
  const { data } = await client.delete(`/api/teacher/exams/${examId}`);
  return data;
}

export async function createTeacherExam(payload) {
  const { data } = await client.post("/api/teacher/exams", payload);
  return data;
}

export async function teacherRunCode(problemId, code) {
  const { data } = await client.post(`/api/teacher/problems/${problemId}/run`, { code });
  return data;
}

export async function teacherSaveCode(problemId, code) {
  const { data } = await client.post(`/api/teacher/problems/${problemId}/save`, { code });
  return data;
}

export async function downloadExamXlsx(examId, filename) {
  const response = await client.get(`/api/teacher/exams/${examId}/export.xlsx`, {
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename || `resultados_examen_${examId}.xlsx`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

// ---- Admin ----

export async function getAdminTeachers() {
  const { data } = await client.get("/api/admin/teachers");
  return data;
}

export async function createAdminTeacher({ email, fullName, group }) {
  const { data } = await client.post("/api/admin/teachers", {
    email,
    full_name: fullName,
    group,
  });
  return data;
}

export async function deleteAdminTeacher(teacherId) {
  const { data } = await client.delete(`/api/admin/teachers/${teacherId}`);
  return data;
}

// ---- Roster de estudiantes (docente) ----

export async function getTeacherStudents() {
  const { data } = await client.get("/api/teacher/students");
  return data;
}

export async function addTeacherStudent({ fullName, documento, email }) {
  const { data } = await client.post("/api/teacher/students", {
    full_name: fullName,
    documento,
    email,
  });
  return data;
}

export async function deleteTeacherStudent(studentId) {
  const { data } = await client.delete(`/api/teacher/students/${studentId}`);
  return data;
}

export async function deleteTeacherGroup() {
  const { data } = await client.delete("/api/teacher/students");
  return data;
}

export async function importStudentRoster(file) {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await client.post("/api/teacher/students/import-xlsx", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export default client;
