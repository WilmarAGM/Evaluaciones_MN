import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";

export default function Register() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [documento, setDocumento] = useState("");
  const [group, setGroup] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { signUp } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (!email.toLowerCase().trim().endsWith("@unal.edu.co")) {
      setError("Debes registrarte con un correo institucional @unal.edu.co");
      return;
    }
    if (!group) {
      setError("Debes indicar tu grupo");
      return;
    }

    setLoading(true);
    try {
      const userInfo = await signUp(email, documento, fullName, Number(group));
      navigate(userInfo.role === "teacher" ? "/teacher/exams" : "/exams");
    } catch (err) {
      setError(
        err.response?.data?.detail || "No se pudo completar el registro. Intenta de nuevo."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-gradient-to-br from-[#0b0d17] via-[#12142a] to-[#1a1030] px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="mx-auto w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-500 to-fuchsia-500 flex items-center justify-center text-2xl font-bold text-white shadow-lg shadow-brand-500/30 mb-4">
            ∑
          </div>
          <h1 className="text-2xl font-bold text-white">Crear cuenta de estudiante</h1>
          <p className="text-slate-400 text-sm mt-1">
            Solo con correo institucional @unal.edu.co
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-7 shadow-2xl shadow-black/40"
        >
          <label className="block text-sm text-slate-300 mb-1.5">Nombre completo</label>
          <input
            type="text"
            required
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Apellidos y nombre"
            className="w-full rounded-lg bg-black/30 border border-white/10 px-3.5 py-2.5 text-white placeholder-slate-500 outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-500/30 transition mb-4"
          />

          <label className="block text-sm text-slate-300 mb-1.5">Correo institucional</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="usuario@unal.edu.co"
            className="w-full rounded-lg bg-black/30 border border-white/10 px-3.5 py-2.5 text-white placeholder-slate-500 outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-500/30 transition mb-4"
          />

          <label className="block text-sm text-slate-300 mb-1.5">Número de documento</label>
          <input
            type="text"
            required
            value={documento}
            onChange={(e) => setDocumento(e.target.value)}
            placeholder="Tu documento de identidad"
            className="w-full rounded-lg bg-black/30 border border-white/10 px-3.5 py-2.5 text-white placeholder-slate-500 outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-500/30 transition mb-2"
          />
          <p className="text-xs text-slate-500 mb-4">
            Tu contraseña para iniciar sesión será tu número de documento.
          </p>

          <label className="block text-sm text-slate-300 mb-1.5">Grupo</label>
          <select
            required
            value={group}
            onChange={(e) => setGroup(e.target.value)}
            className="w-full rounded-lg bg-black/30 border border-white/10 px-3.5 py-2.5 text-white outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-500/30 transition mb-2"
          >
            <option value="" disabled>
              Selecciona tu grupo
            </option>
            {[1, 2, 3, 4].map((g) => (
              <option key={g} value={g}>
                Grupo {g}
              </option>
            ))}
          </select>

          {error && <p className="text-rose-400 text-sm mt-2 mb-1">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-4 rounded-lg bg-gradient-to-r from-brand-600 to-fuchsia-600 hover:from-brand-500 hover:to-fuchsia-500 transition text-white font-semibold py-2.5 shadow-lg shadow-brand-900/40 disabled:opacity-60"
          >
            {loading ? "Creando cuenta..." : "Crear cuenta"}
          </button>
        </form>

        <p className="text-center text-sm text-slate-400 mt-6">
          ¿Ya tienes cuenta?{" "}
          <Link to="/" className="text-brand-300 hover:text-brand-200">
            Inicia sesión
          </Link>
        </p>
      </div>
    </div>
  );
}
