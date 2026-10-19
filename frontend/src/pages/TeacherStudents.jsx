import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";
import * as api from "../api";
import ChangePasswordForm from "../components/ChangePasswordForm";

function RosterUploader({ onImported }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) {
      setError("Elige un archivo .xlsx primero.");
      return;
    }
    setError("");
    setResult(null);
    setUploading(true);
    try {
      const res = await api.importStudentRoster(file);
      setResult(res);
      onImported();
    } catch (err) {
      setError(err.response?.data?.detail || "No se pudo cargar el archivo.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="mt-4 rounded-xl border border-dashed border-white/10 bg-black/20 p-4">
      <p className="text-sm text-slate-300 font-medium">Cargar roster desde .xlsx</p>
      <p className="text-xs text-slate-500 mt-1 mb-3">
        Columnas obligatorias: Nombres y Apellidos, Documento, Correo, Grupo. Las filas con un grupo distinto
        al tuyo se rechazan y se reportan; el resto se importa.
      </p>
      <form onSubmit={handleSubmit} className="flex flex-wrap items-center gap-2">
        <input
          type="file"
          accept=".xlsx"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="text-xs text-slate-300 file:mr-2 file:rounded-lg file:border-0 file:bg-white/10 file:px-2.5 file:py-1.5 file:text-xs file:text-slate-200 file:cursor-pointer max-w-[260px]"
        />
        <button
          type="submit"
          disabled={uploading}
          className="text-xs font-medium rounded-lg border border-brand-500/30 bg-brand-600/20 text-brand-300 hover:bg-brand-600/30 px-3 py-1.5 transition disabled:opacity-60"
        >
          {uploading ? "Cargando..." : "Cargar roster"}
        </button>
      </form>
      {error && <p className="text-xs text-rose-400 mt-2">{error}</p>}
      {result && (
        <>
          <p className="text-xs text-emerald-400 mt-2">
            {result.created} creado(s), {result.skipped} ya existían
            {result.rejected.length > 0 && `, ${result.rejected.length} rechazada(s)`}.
          </p>
          {result.rejected.length > 0 && (
            <ul className="mt-1.5 space-y-1">
              {result.rejected.map((r, i) => (
                <li key={i} className="text-xs text-amber-400/90">
                  Fila {r.row}: {r.motivo}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}

function GuestAdder({ onAdded }) {
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [found, setFound] = useState(null);
  const [adding, setAdding] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleSearch(e) {
    e.preventDefault();
    setError("");
    setMessage("");
    setFound(null);
    if (!query.trim()) {
      setError("Escribe el correo o el documento del estudiante.");
      return;
    }
    setSearching(true);
    try {
      const res = await api.searchGuestStudent(query.trim());
      if (res) setFound(res);
      else setError("No hay ningún estudiante con ese correo o documento.");
    } catch (err) {
      setError(err.response?.data?.detail || "No se pudo buscar.");
    } finally {
      setSearching(false);
    }
  }

  async function handleAdd() {
    setAdding(true);
    setError("");
    try {
      const student = await api.addGuestStudent(found.id);
      onAdded(student);
      setMessage(`${found.full_name || found.email} quedó como invitado: ya ve los exámenes de tu grupo.`);
      setFound(null);
      setQuery("");
    } catch (err) {
      setError(err.response?.data?.detail || "No se pudo agregar el invitado.");
    } finally {
      setAdding(false);
    }
  }

  return (
    <section className="rounded-2xl border border-white/10 bg-white/5 p-5 mb-10">
      <h2 className="text-lg font-semibold text-white mb-1">Agregar estudiante de otro grupo</h2>
      <p className="text-xs text-slate-500 mb-4">
        El estudiante sigue en su grupo (con sus notas allí) y además podrá presentar los exámenes del tuyo. Busca
        por correo o documento exactos.
      </p>
      <form onSubmit={handleSearch} className="flex flex-wrap items-center gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="correo@unal.edu.co o documento"
          className="flex-1 min-w-[220px] rounded-lg bg-black/30 border border-white/10 text-white px-3 py-2 text-sm focus:outline-none focus:border-brand-400/50"
        />
        <button
          type="submit"
          disabled={searching}
          className="rounded-lg border border-white/10 hover:bg-white/5 text-slate-200 text-sm font-medium px-4 py-2 transition disabled:opacity-60"
        >
          {searching ? "Buscando..." : "Buscar"}
        </button>
      </form>
      {found && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-violet-500/30 bg-violet-500/10 px-4 py-3">
          <div className="text-sm">
            <p className="text-white font-medium">{found.full_name || "(sin nombre)"}</p>
            <p className="text-slate-400 text-xs">
              {found.email} · Doc. {found.documento} · Grupo {found.group ?? "—"}
            </p>
          </div>
          {found.already_guest ? (
            <span className="text-xs text-violet-300">Ya es invitado de tu grupo</span>
          ) : (
            <button
              onClick={handleAdd}
              disabled={adding}
              className="rounded-lg bg-violet-600/80 hover:bg-violet-600 text-white text-sm font-medium px-4 py-2 transition disabled:opacity-60"
            >
              {adding ? "Agregando..." : "+ Agregar como invitado"}
            </button>
          )}
        </div>
      )}
      {message && <p className="text-emerald-400 text-sm mt-3">{message}</p>}
      {error && <p className="text-rose-400 text-sm mt-3">{error}</p>}
    </section>
  );
}

export default function TeacherStudents() {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [fullName, setFullName] = useState("");
  const [documento, setDocumento] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [deletingGroup, setDeletingGroup] = useState(false);
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    loadStudents();
  }, []);

  function loadStudents() {
    setLoading(true);
    return api
      .getTeacherStudents()
      .then(setStudents)
      .catch(() => setError("No se pudo cargar el roster."))
      .finally(() => setLoading(false));
  }

  async function handleCreate(e) {
    e.preventDefault();
    setError("");
    if (!fullName.trim() || !documento.trim() || !email.trim()) {
      setError("Completa nombre, documento y correo.");
      return;
    }
    setCreating(true);
    try {
      const student = await api.addTeacherStudent({
        fullName: fullName.trim(),
        documento: documento.trim(),
        email: email.trim(),
      });
      setStudents((prev) => [...prev, student]);
      setFullName("");
      setDocumento("");
      setEmail("");
    } catch (err) {
      setError(err.response?.data?.detail || "No se pudo agregar el estudiante.");
    } finally {
      setCreating(false);
    }
  }

  async function handleRelease(student) {
    try {
      await api.releaseStudentSession(student.id);
      setStudents((prev) => prev.map((s) => (s.id === student.id ? { ...s, session_active: false } : s)));
    } catch (err) {
      window.alert(err.response?.data?.detail || "No se pudo liberar la sesión.");
    }
  }

  async function handleDelete(student) {
    const confirmed = window.confirm(`¿Eliminar a ${student.full_name || student.email}? Esta acción no se puede deshacer.`);
    if (!confirmed) return;

    setDeletingId(student.id);
    try {
      await api.deleteTeacherStudent(student.id);
      setStudents((prev) => prev.filter((s) => s.id !== student.id));
    } catch (err) {
      window.alert(err.response?.data?.detail || "No se pudo eliminar el estudiante.");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleRemoveGuest(student) {
    const confirmed = window.confirm(
      `¿Quitar a ${student.full_name || student.email} como invitado? Deja de ver los exámenes de tu grupo; su cuenta y sus notas en el Grupo ${student.guest_from} no se tocan.`
    );
    if (!confirmed) return;

    setDeletingId(student.id);
    try {
      await api.removeGuestStudent(student.id);
      setStudents((prev) => prev.filter((s) => s.id !== student.id));
    } catch (err) {
      window.alert(err.response?.data?.detail || "No se pudo quitar el invitado.");
    } finally {
      setDeletingId(null);
    }
  }

  const ownCount = students.filter((s) => s.guest_from == null).length;

  async function handleDeleteGroup() {
    const confirmed = window.confirm(
      `¿Eliminar TODO el roster de tu grupo (${ownCount} estudiante(s))? Esto borra también sus intentos y entregas. Los invitados de otros grupos no se borran. Esta acción NO se puede deshacer.`
    );
    if (!confirmed) return;
    const doubleConfirmed = window.confirm("Confirma de nuevo: esto elimina permanentemente a todos los estudiantes del grupo.");
    if (!doubleConfirmed) return;

    setDeletingGroup(true);
    try {
      await api.deleteTeacherGroup();
      setStudents((prev) => prev.filter((s) => s.guest_from != null));
    } catch (err) {
      window.alert("No se pudo eliminar el grupo.");
    } finally {
      setDeletingGroup(false);
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
            <span className="text-white font-semibold">Métodos Numéricos · Docente</span>
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
        <div className="flex items-start justify-between gap-4 mb-1">
          <h1 className="text-2xl font-bold text-white">Estudiantes — Grupo {user?.group}</h1>
          <Link
            to="/teacher/exams"
            className="shrink-0 rounded-lg border border-white/10 hover:bg-white/5 text-slate-200 text-sm font-medium px-4 py-2 transition"
          >
            ← Volver a exámenes
          </Link>
        </div>
        <p className="text-slate-400 mb-8">Roster de estudiantes de tu grupo.</p>

        <section className="rounded-2xl border border-white/10 bg-white/5 p-5 mb-10">
          <h2 className="text-lg font-semibold text-white mb-4">Agregar estudiante</h2>
          <form onSubmit={handleCreate} className="grid gap-3 sm:grid-cols-[1fr_1fr_1fr_auto] sm:items-end">
            <div>
              <label className="block text-sm text-slate-400 mb-1">Nombres y apellidos</label>
              <input
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full rounded-lg bg-black/30 border border-white/10 text-white px-3 py-2 text-sm focus:outline-none focus:border-brand-400/50"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Documento</label>
              <input
                value={documento}
                onChange={(e) => setDocumento(e.target.value)}
                className="w-full rounded-lg bg-black/30 border border-white/10 text-white px-3 py-2 text-sm focus:outline-none focus:border-brand-400/50"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Correo</label>
              <input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg bg-black/30 border border-white/10 text-white px-3 py-2 text-sm focus:outline-none focus:border-brand-400/50"
              />
            </div>
            <button
              type="submit"
              disabled={creating}
              className="rounded-lg bg-brand-600/80 hover:bg-brand-600 text-white text-sm font-medium px-4 py-2 transition disabled:opacity-60"
            >
              {creating ? "Agregando..." : "+ Agregar"}
            </button>
          </form>
          {error && <p className="text-rose-400 text-sm mt-3">{error}</p>}

          <RosterUploader onImported={loadStudents} />
        </section>

        <GuestAdder
          onAdded={(student) =>
            setStudents((prev) =>
              [...prev.filter((s) => s.id !== student.id), student].sort((a, b) =>
                (a.full_name || "").localeCompare(b.full_name || "")
              )
            )
          }
        />

        {loading && <p className="text-slate-500">Cargando...</p>}

        {!loading && students.length > 0 && (
          <div className="rounded-2xl border border-white/10 bg-white/5 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-400 border-b border-white/10">
                  <th className="px-4 py-3">Nombre</th>
                  <th className="px-4 py-3">Documento</th>
                  <th className="px-4 py-3">Correo</th>
                  <th className="px-4 py-3">Sesión</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {students.map((s) => (
                  <tr key={s.id} className="border-b border-white/5 text-slate-300">
                    <td className="px-4 py-2.5">
                      {s.full_name}
                      {s.guest_from != null && (
                        <span
                          className="ml-2 text-[11px] font-medium rounded-full border px-2 py-0.5 bg-violet-500/15 text-violet-300 border-violet-500/30"
                          title={`Estudiante del Grupo ${s.guest_from} invitado a tu grupo`}
                        >
                          Invitado · G{s.guest_from}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2.5">{s.documento}</td>
                    <td className="px-4 py-2.5">{s.email}</td>
                    <td className="px-4 py-2.5">
                      {s.session_active ? (
                        <span className="inline-flex items-center gap-2">
                          <span className="text-xs font-medium rounded-full border px-2 py-0.5 bg-emerald-500/15 text-emerald-400 border-emerald-500/30">
                            Activa
                          </span>
                          <button
                            onClick={() => handleRelease(s)}
                            className="text-xs rounded-lg border border-white/15 px-2 py-0.5 text-slate-300 hover:bg-white/5 transition"
                            title="Cierra su sesión para que pueda volver a ingresar de inmediato"
                          >
                            Liberar
                          </button>
                        </span>
                      ) : (
                        <span className="text-xs text-slate-600">—</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      {s.guest_from != null ? (
                        <button
                          onClick={() => handleRemoveGuest(s)}
                          disabled={deletingId === s.id}
                          className="text-xs font-medium rounded-lg border border-white/15 text-slate-300 hover:bg-white/5 px-2 py-1 transition disabled:opacity-60"
                        >
                          {deletingId === s.id ? "..." : "Quitar invitado"}
                        </button>
                      ) : (
                        <button
                          onClick={() => handleDelete(s)}
                          disabled={deletingId === s.id}
                          className="text-xs font-medium rounded-lg border border-red-900/50 bg-red-950/40 text-red-400 hover:bg-red-900/40 hover:text-red-300 px-2 py-1 transition disabled:opacity-60"
                        >
                          {deletingId === s.id ? "..." : "🗑 Eliminar"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!loading && students.length === 0 && (
          <p className="text-slate-500">No hay estudiantes en tu grupo todavía.</p>
        )}

        {!loading && ownCount > 0 && (
          <button
            onClick={handleDeleteGroup}
            disabled={deletingGroup}
            className="w-full mt-8 rounded-lg text-sm font-medium px-4 py-2 transition disabled:opacity-60 bg-red-950/40 text-red-400 border border-red-900/50 hover:bg-red-900/40 hover:text-red-300"
          >
            {deletingGroup ? "Eliminando grupo..." : "🗑 Eliminar todo el grupo"}
          </button>
        )}
      </main>
    </div>
  );
}
