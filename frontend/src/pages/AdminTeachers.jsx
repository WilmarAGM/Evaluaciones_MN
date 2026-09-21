import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";
import * as api from "../api";
import ChangePasswordForm from "../components/ChangePasswordForm";

export default function AdminTeachers() {
  const [teachers, setTeachers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [group, setGroup] = useState("");
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [studentCounts, setStudentCounts] = useState([]);
  const [deletingGroup, setDeletingGroup] = useState(null);
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    loadTeachers();
  }, []);

  function loadTeachers() {
    setLoading(true);
    return api
      .getAdminTeachers()
      .then(setTeachers)
      .catch(() => setError("No se pudieron cargar los docentes."))
      .finally(() => setLoading(false));
  }

  async function handleCreate(e) {
    e.preventDefault();
    setError("");
    if (!email.trim() || !fullName.trim() || !group) {
      setError("Completa correo, nombre y grupo.");
      return;
    }
    setCreating(true);
    try {
      const teacher = await api.createAdminTeacher({
        email: email.trim(),
        fullName: fullName.trim(),
        group: Number(group),
      });
      setTeachers((prev) => [...prev, teacher]);
      setEmail("");
      setFullName("");
      setGroup("");
    } catch (err) {
      setError(err.response?.data?.detail || "No se pudo crear el docente.");
    } finally {
      setCreating(false);
    }
  }

  function loadStudentCounts() {
    return api
      .getAdminStudentSummary()
      .then(setStudentCounts)
      .catch(() => setStudentCounts([]));
  }

  useEffect(() => {
    loadStudentCounts();
  }, []);

  async function handleDeleteGroupStudents(group, count) {
    const confirmed = window.confirm(
      `¿Eliminar los ${count} estudiante(s) del Grupo ${group}?\n\nSe borran también, de forma permanente, todos sus intentos y entregas. Las cuentas docente y admin no se tocan. Esta acción NO se puede deshacer.`
    );
    if (!confirmed) return;

    setDeletingGroup(group);
    try {
      await api.deleteAdminGroupStudents(group);
      await loadStudentCounts();
    } catch (err) {
      window.alert(err.response?.data?.detail || "No se pudieron eliminar los estudiantes.");
    } finally {
      setDeletingGroup(null);
    }
  }

  async function handleDelete(teacher) {
    const confirmed = window.confirm(
      `¿Eliminar la cuenta docente de ${teacher.full_name || teacher.email} (Grupo ${teacher.group})? Sus estudiantes/exámenes/bancos del grupo NO se borran, solo la cuenta.`
    );
    if (!confirmed) return;

    setDeletingId(teacher.id);
    try {
      await api.deleteAdminTeacher(teacher.id);
      setTeachers((prev) => prev.filter((t) => t.id !== teacher.id));
    } catch (err) {
      window.alert("No se pudo eliminar el docente.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="min-h-screen bg-[#0b0d17]">
      <header className="border-b border-white/10 bg-black/20 backdrop-blur">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-fuchsia-500 flex items-center justify-center text-white font-bold">
              ∑
            </div>
            <span className="text-white font-semibold">Métodos Numéricos · Admin</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-slate-400 text-sm hidden sm:block">
              {user?.full_name || user?.email}
            </span>
            <ChangePasswordForm />
            <button
              onClick={() => {
                signOut();
                navigate("/");
              }}
              className="text-sm text-slate-300 hover:text-white border border-white/10 rounded-lg px-3 py-1.5 hover:bg-white/5 transition"
            >
              Salir
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-10">
        <h1 className="text-2xl font-bold text-white mb-1">Docentes</h1>
        <p className="text-slate-400 mb-8">Una cuenta docente por grupo (1-4).</p>

        <section className="rounded-2xl border border-white/10 bg-white/5 p-5 mb-10">
          <h2 className="text-lg font-semibold text-white mb-4">Crear docente</h2>
          <form onSubmit={handleCreate} className="grid gap-3 sm:grid-cols-[1fr_1fr_auto_auto] sm:items-end">
            <div>
              <label className="block text-sm text-slate-400 mb-1">Correo</label>
              <input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="docente@correo.com"
                className="w-full rounded-lg bg-black/30 border border-white/10 text-white px-3 py-2 text-sm focus:outline-none focus:border-brand-400/50"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Nombre completo</label>
              <input
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full rounded-lg bg-black/30 border border-white/10 text-white px-3 py-2 text-sm focus:outline-none focus:border-brand-400/50"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Grupo</label>
              <select
                value={group}
                onChange={(e) => setGroup(e.target.value)}
                className="w-full rounded-lg bg-black/30 border border-white/10 text-white px-3 py-2 text-sm focus:outline-none focus:border-brand-400/50"
              >
                <option value="">—</option>
                {[1, 2, 3, 4].map((g) => (
                  <option key={g} value={g}>
                    {g}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="submit"
              disabled={creating}
              className="rounded-lg bg-brand-600/80 hover:bg-brand-600 text-white text-sm font-medium px-4 py-2 transition disabled:opacity-60"
            >
              {creating ? "Creando..." : "+ Crear"}
            </button>
          </form>
          {error && <p className="text-rose-400 text-sm mt-3">{error}</p>}
          <p className="text-xs text-slate-500 mt-3">
            La contraseña inicial siempre es <span className="font-mono">123456789</span>; el docente la cambia
            desde "Cambiar contraseña" al entrar.
          </p>
        </section>

        <section className="rounded-2xl border border-white/10 bg-white/5 p-5 mb-10">
          <h2 className="text-lg font-semibold text-white mb-1">Estudiantes por grupo</h2>
          <p className="text-xs text-slate-500 mb-4">
            Elimina todos los estudiantes de un grupo, con sus intentos y entregas (por ejemplo, al empezar un
            semestre nuevo). No afecta a los docentes.
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            {studentCounts.map(({ group: g, count }) => (
              <div
                key={g}
                className="flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-black/20 px-4 py-3"
              >
                <div>
                  <p className="text-white font-medium">Grupo {g}</p>
                  <p className="text-slate-400 text-sm">
                    {count} estudiante{count === 1 ? "" : "s"}
                  </p>
                </div>
                <button
                  onClick={() => handleDeleteGroupStudents(g, count)}
                  disabled={count === 0 || deletingGroup === g}
                  className="text-xs font-medium rounded-lg border border-red-900/50 bg-red-950/40 text-red-400 hover:bg-red-900/40 hover:text-red-300 px-3 py-1.5 transition disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {deletingGroup === g ? "Eliminando..." : "🗑 Eliminar estudiantes"}
                </button>
              </div>
            ))}
          </div>
        </section>

        {loading && <p className="text-slate-500">Cargando...</p>}

        <div className="grid gap-4 sm:grid-cols-2">
          {teachers.map((t) => (
            <div key={t.id} className="rounded-2xl border border-white/10 bg-white/5 p-5 shadow-lg shadow-black/20">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="text-lg font-semibold text-white">{t.full_name}</h3>
                  <p className="text-slate-400 text-sm">{t.email}</p>
                </div>
                <span className="shrink-0 text-xs font-medium rounded-full border px-2.5 py-1 bg-brand-500/15 text-brand-300 border-brand-500/30">
                  Grupo {t.group}
                </span>
              </div>
              <button
                onClick={() => handleDelete(t)}
                disabled={deletingId === t.id}
                className="w-full mt-4 rounded-lg text-sm font-medium px-4 py-2 transition disabled:opacity-60 bg-red-950/40 text-red-400 border border-red-900/50 hover:bg-red-900/40 hover:text-red-300"
              >
                {deletingId === t.id ? "Eliminando..." : "🗑 Eliminar cuenta docente"}
              </button>
            </div>
          ))}
        </div>

        {!loading && teachers.length === 0 && <p className="text-slate-500">No hay docentes creados todavía.</p>}
      </main>
    </div>
  );
}
