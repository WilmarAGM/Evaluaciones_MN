import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { signIn } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const userInfo = await signIn(email, password);
      navigate(userInfo.role === "teacher" ? "/teacher/exams" : "/exams");
    } catch (err) {
      setError(
        err.response?.data?.detail || "No se pudo iniciar sesión. Intenta de nuevo."
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
          <h1 className="text-2xl font-bold text-white">Evaluaciones · Métodos Numéricos</h1>
          <p className="text-slate-400 text-sm mt-1">
            Ingresa con tu correo institucional y tu número de documento
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-7 shadow-2xl shadow-black/40"
        >
          <label className="block text-sm text-slate-300 mb-1.5">Correo institucional</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="usuario@unal.edu.co"
            className="w-full rounded-lg bg-black/30 border border-white/10 px-3.5 py-2.5 text-white placeholder-slate-500 outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-500/30 transition mb-4"
          />

          <label className="block text-sm text-slate-300 mb-1.5">Contraseña (documento)</label>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Número de documento"
            className="w-full rounded-lg bg-black/30 border border-white/10 px-3.5 py-2.5 text-white placeholder-slate-500 outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-500/30 transition mb-2"
          />

          {error && (
            <p className="text-rose-400 text-sm mt-2 mb-1">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-4 rounded-lg bg-gradient-to-r from-brand-600 to-fuchsia-600 hover:from-brand-500 hover:to-fuchsia-500 transition text-white font-semibold py-2.5 shadow-lg shadow-brand-900/40 disabled:opacity-60"
          >
            {loading ? "Ingresando..." : "Ingresar"}
          </button>
        </form>

        <p className="text-center text-sm text-slate-400 mt-6">
          ¿No tienes cuenta?{" "}
          <Link to="/register" className="text-brand-300 hover:text-brand-200">
            Regístrate
          </Link>
        </p>

        <p className="text-center text-xs text-slate-600 mt-6">
          Prototipo local · Evaluaciones de Métodos Numéricos
        </p>
      </div>
    </div>
  );
}
