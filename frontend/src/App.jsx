import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./AuthContext";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ExamList from "./pages/ExamList";
import ExamPage from "./pages/ExamPage";
import ResultsPage from "./pages/ResultsPage";
import TeacherExams from "./pages/TeacherExams";
import TeacherCreateExam from "./pages/TeacherCreateExam";
import TeacherExamDashboard from "./pages/TeacherExamDashboard";
import TeacherExamPreview from "./pages/TeacherExamPreview";
import TeacherBanks from "./pages/TeacherBanks";
import TeacherProblemDetail from "./pages/TeacherProblemDetail";
import TeacherStudents from "./pages/TeacherStudents";
import AdminTeachers from "./pages/AdminTeachers";
import AdminBanks from "./pages/AdminBanks";
import AdminProblemDetail from "./pages/AdminProblemDetail";

function PrivateRoute({ children }) {
  const { user } = useAuth();
  return user ? children : <Navigate to="/" replace />;
}

function TeacherRoute({ children }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/" replace />;
  if (user.role !== "teacher") return <Navigate to="/exams" replace />;
  return children;
}

function AdminRoute({ children }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/" replace />;
  if (user.role !== "admin") return <Navigate to="/exams" replace />;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/exams"
            element={
              <PrivateRoute>
                <ExamList />
              </PrivateRoute>
            }
          />
          <Route
            path="/exams/:examId"
            element={
              <PrivateRoute>
                <ExamPage />
              </PrivateRoute>
            }
          />
          <Route
            path="/exams/:examId/results"
            element={
              <PrivateRoute>
                <ResultsPage />
              </PrivateRoute>
            }
          />
          <Route
            path="/teacher/exams"
            element={
              <TeacherRoute>
                <TeacherExams />
              </TeacherRoute>
            }
          />
          <Route
            path="/teacher/exams/new"
            element={
              <TeacherRoute>
                <TeacherCreateExam />
              </TeacherRoute>
            }
          />
          <Route
            path="/teacher/exams/:examId"
            element={
              <TeacherRoute>
                <TeacherExamDashboard />
              </TeacherRoute>
            }
          />
          <Route
            path="/teacher/exams/:examId/preview"
            element={
              <TeacherRoute>
                <TeacherExamPreview />
              </TeacherRoute>
            }
          />
          <Route
            path="/teacher/banks"
            element={
              <TeacherRoute>
                <TeacherBanks />
              </TeacherRoute>
            }
          />
          <Route
            path="/teacher/problems/:problemId"
            element={
              <TeacherRoute>
                <TeacherProblemDetail />
              </TeacherRoute>
            }
          />
          <Route
            path="/teacher/students"
            element={
              <TeacherRoute>
                <TeacherStudents />
              </TeacherRoute>
            }
          />
          <Route
            path="/admin/teachers"
            element={
              <AdminRoute>
                <AdminTeachers />
              </AdminRoute>
            }
          />
          <Route
            path="/admin/banks"
            element={
              <AdminRoute>
                <AdminBanks />
              </AdminRoute>
            }
          />
          <Route
            path="/admin/problems/:problemId"
            element={
              <AdminRoute>
                <AdminProblemDetail />
              </AdminRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
