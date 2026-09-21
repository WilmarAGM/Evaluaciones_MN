import { createContext, useContext, useState } from "react";
import * as api from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem("user");
    return stored ? JSON.parse(stored) : null;
  });

  async function signIn(email, password) {
    const data = await api.login(email, password);
    localStorage.setItem("token", data.access_token);
    const userInfo = { email: data.email, full_name: data.full_name, role: data.role, group: data.group };
    localStorage.setItem("user", JSON.stringify(userInfo));
    setUser(userInfo);
    return userInfo;
  }

  async function signUp(email, documento, fullName, group) {
    const data = await api.register(email, documento, fullName, group);
    localStorage.setItem("token", data.access_token);
    const userInfo = { email: data.email, full_name: data.full_name, role: data.role, group: data.group };
    localStorage.setItem("user", JSON.stringify(userInfo));
    setUser(userInfo);
    return userInfo;
  }

  async function signOut() {
    // Libera la sesión única en el servidor (mejor esfuerzo: si falla, igual se sale).
    try {
      await api.logout();
    } catch {
      /* sin conexión o sesión ya inválida */
    }
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, signIn, signUp, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
