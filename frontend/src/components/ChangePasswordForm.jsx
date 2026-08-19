import { useState } from "react";
import * as api from "../api";

export default function ChangePasswordForm() {
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [ok, setOk] = useState(false);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setOk(false);
    if (next.length < 8) {
      setError("La nueva contraseña debe tener al menos 8 caracteres.");
      return;
    }
    if (next !== confirm) {
      setError("Las contraseñas nuevas no coinciden.");
      return;
    }
    setSaving(true);
    try {
      await api.changePassword(current, next);
      setOk(true);
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch (err) {
      setError(err.response?.data?.detail || "No se pudo cambiar la contraseña.");
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="text-sm text-slate-300 hover:text-white border border-white/10 rounded-lg px-3 py-1.5 hover:bg-white/5 transition"
      >
        Cambiar contraseña
      </button>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm bg-[#12142a] border border-white/10 rounded-2xl p-6 shadow-2xl"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-white font-semibold">Cambiar contraseña</h2>
          <button type="button" onClick={() => setOpen(false)} className="text-slate-400 hover:text-white text-sm">
            ✕
          </button>
        </div>

        <label className="block text-sm text-slate-300 mb-1.5">Contraseña actual</label>
        <input
          type="password"
          required
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          className="w-full rounded-lg bg-black/30 border border-white/10 px-3.5 py-2.5 text-white outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-500/30 transition mb-4"
        />

        <label className="block text-sm text-slate-300 mb-1.5">Contraseña nueva</label>
        <input
          type="password"
          required
          value={next}
          onChange={(e) => setNext(e.target.value)}
          className="w-full rounded-lg bg-black/30 border border-white/10 px-3.5 py-2.5 text-white outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-500/30 transition mb-4"
        />

        <label className="block text-sm text-slate-300 mb-1.5">Confirmar contraseña nueva</label>
        <input
          type="password"
          required
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          className="w-full rounded-lg bg-black/30 border border-white/10 px-3.5 py-2.5 text-white outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-500/30 transition mb-2"
        />

        {error && <p className="text-rose-400 text-sm mt-2">{error}</p>}
        {ok && <p className="text-emerald-400 text-sm mt-2">Contraseña actualizada.</p>}

        <button
          type="submit"
          disabled={saving}
          className="w-full mt-4 rounded-lg bg-gradient-to-r from-brand-600 to-fuchsia-600 hover:from-brand-500 hover:to-fuchsia-500 transition text-white font-semibold py-2.5 disabled:opacity-60"
        >
          {saving ? "Guardando..." : "Guardar"}
        </button>
      </form>
    </div>
  );
}
