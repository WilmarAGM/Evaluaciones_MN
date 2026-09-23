import { Component } from "react";

// Red de seguridad para errores de RENDER de React (un bug real en un
// componente, una respuesta inesperada del backend que rompe un .map(), etc.)
// que de otro modo dejan la página completamente en blanco sin ninguna pista
// para el estudiante ni el docente. Solo las class components pueden usar
// getDerivedStateFromError/componentDidCatch — no existe un equivalente con
// hooks todavía.
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    // No hay backend que avise de esto (el error puede ser justamente que no
    // hay conexión con el backend) — console.error queda en las herramientas
    // de desarrollo del navegador del estudiante, visible si hay que
    // diagnosticar un caso puntual.
    console.error("Error de render capturado por ErrorBoundary:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#0b0d17] flex items-center justify-center px-4">
          <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-[#12142a] p-6 text-center shadow-2xl">
            <p className="text-3xl mb-2">⚠</p>
            <h1 className="text-white font-semibold text-lg mb-2">Algo salió mal</h1>
            <p className="text-slate-400 text-sm mb-5">
              La página tuvo un error inesperado. Recárgala para continuar — si estabas en un examen, tu
              progreso guardado no se pierde.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="w-full rounded-lg bg-gradient-to-r from-brand-600 to-fuchsia-600 hover:from-brand-500 hover:to-fuchsia-500 transition text-white font-medium py-2.5"
            >
              Recargar página
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
